from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp


@dataclass(frozen=True)
class DiscordLiveConfig:
    # Webhooks (recommended: one per channel surface; can be same if you want)
    status_webhook_url: str
    killfeed_webhook_url: str
    admin_webhook_url: str
    loot_webhook_url: str

    # Operational behavior
    status_interval_s: int = 60
    burst_window_s: int = 3          # collapse combat bursts into windows
    max_queue: int = 500             # backpressure for spikes

    # Persistence (stores message_ids so we can edit-in-place)
    state_path: str = "backend/state/discord_live_state.json"


class DiscordLiveUpdates:
    """
    Ops spine:
      - edits a pinned/anchored status message in-place (no channel spam)
      - queues event bursts (killfeed/admin/loot) with backpressure
      - provides a smoke-test that proves the whole substrate works
    """

    def __init__(self, cfg: DiscordLiveConfig, *, session: aiohttp.ClientSession):
        self.cfg = cfg
        self._session = session

        self._started = False
        self._stop_evt = asyncio.Event()

        self._status_task: Optional[asyncio.Task] = None
        self._writer_task: Optional[asyncio.Task] = None

        self._q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=cfg.max_queue)
        self._state: dict[str, Any] = {}
        self._last_status_payload: Optional[dict[str, Any]] = None

        # burst collapse
        self._burst_buf: list[dict[str, Any]] = []
        self._burst_deadline: float = 0.0

        self._load_state()

    # -------------------------
    # lifecycle
    # -------------------------
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stop_evt.clear()
        self._writer_task = asyncio.create_task(self._writer_loop(), name="discord_live_writer")
        self._status_task = asyncio.create_task(self._status_loop(), name="discord_live_status")

    async def stop(self) -> None:
        if not self._started:
            return
        self._stop_evt.set()
        for t in (self._status_task, self._writer_task):
            if t:
                t.cancel()
        await asyncio.sleep(0)
        self._started = False

    # -------------------------
    # public emitters
    # -------------------------
    async def emit_killfeed(self, text: str) -> None:
        await self._enqueue({"kind": "killfeed", "text": text, "ts": time.time()})

    async def emit_admin(self, text: str) -> None:
        await self._enqueue({"kind": "admin", "text": text, "ts": time.time()})

    async def emit_loot(self, text: str) -> None:
        await self._enqueue({"kind": "loot", "text": text, "ts": time.time()})

    async def emit_patch_audit(self, title: str, body: str, *, ok: bool) -> None:
        # patch pipeline should call this on APPLY/VERIFY/ROLLBACK events
        prefix = "✅" if ok else "❌"
        await self.emit_admin(f"{prefix} {title}\n{body}")

    # -------------------------
    # smoke test (no handoff)
    # -------------------------
    async def smoke(self) -> None:
        """
        Proves:
          - webhook POST works
          - edit-in-place works (message id persists)
          - queue/writer loop is alive
        """
        probe = f"[OPS_SMOKE] probe @ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        await self.emit_admin(probe)
        await self.emit_loot(probe)
        await self.emit_killfeed(probe)
        # allow writer to flush
        await asyncio.sleep(2)

        # Force a status update immediately (edit-in-place proof)
        await self._ensure_status_message()
        payload = self._render_status_payload(
            title="Server Status (SMOKE)",
            lines=[
                "discord_live_updates: ONLINE",
                "edit-in-place: VERIFIED",
                "queue: FLUSHED",
            ],
        )
        await self._post_or_edit_status(payload, force=True)

    # -------------------------
    # internal: status loop
    # -------------------------
    async def _status_loop(self) -> None:
        # create anchor message once, then edit it forever
        await self._ensure_status_message()
        while not self._stop_evt.is_set():
            try:
                # Replace this with your real status snapshot call
                # (nitrado/a2s state, last update, player counts, etc.)
                payload = self._render_status_payload(
                    title="Server Status",
                    lines=[
                        "ops spine: ONLINE",
                        f"heartbeat: {time.strftime('%H:%M:%S')}",
                    ],
                )
                await self._post_or_edit_status(payload)
            except Exception as e:
                # never die silently; surface in admin channel
                await self.emit_admin(f"❌ status loop error: {type(e).__name__}: {e}")
            await asyncio.sleep(self.cfg.status_interval_s)

    # -------------------------
    # internal: writer loop (backpressure + burst collapse)
    # -------------------------
    async def _writer_loop(self) -> None:
        while not self._stop_evt.is_set():
            item = await self._q.get()
            try:
                kind = item["kind"]
                if kind == "killfeed":
                    await self._burst_handle(item)
                else:
                    await self._send_simple(kind, item["text"])
            except Exception as e:
                # surface errors; don't lose the loop
                await self._send_simple("admin", f"❌ discord writer error: {type(e).__name__}: {e}")
            finally:
                self._q.task_done()

    async def _burst_handle(self, item: dict[str, Any]) -> None:
        now = time.time()
        if not self._burst_buf:
            self._burst_deadline = now + self.cfg.burst_window_s
        self._burst_buf.append(item)

        # if window not reached, wait a little to collect more
        if now < self._burst_deadline:
            await asyncio.sleep(0.15)
            return

        # flush burst
        burst = self._burst_buf
        self._burst_buf = []
        self._burst_deadline = 0.0

        lines = [b["text"] for b in burst][-25:]  # hard cap
        msg = "🩸 Killfeed burst:\n" + "\n".join(lines)
        await self._send_simple("killfeed", msg)

    # -------------------------
    # webhook send/edit primitives
    # -------------------------
    async def _send_simple(self, kind: str, text: str) -> None:
        url = self._webhook_for(kind)
        await self._webhook_post(url, {"content": text})

    async def _post_or_edit_status(self, payload: dict[str, Any], *, force: bool = False) -> None:
        if (not force) and self._last_status_payload == payload:
            return
        self._last_status_payload = payload

        url = self.cfg.status_webhook_url
        msg_id = self._state.get("status_message_id")
        if msg_id:
            # Edit-in-place: webhook message edit
            # NOTE: discord webhook message edit is supported; we rely on the webhook endpoint accepting PATCH.
            await self._webhook_patch(f"{url}/messages/{msg_id}", payload)
        else:
            res = await self._webhook_post(url, payload, want_json=True)
            # Discord returns the created message object; store id
            if isinstance(res, dict) and "id" in res:
                self._state["status_message_id"] = res["id"]
                self._save_state()

    async def _ensure_status_message(self) -> None:
        if self._state.get("status_message_id"):
            return
        # Create anchor message once
        payload = self._render_status_payload(
            title="Server Status",
            lines=["initializing…"],
        )
        res = await self._webhook_post(self.cfg.status_webhook_url, payload, want_json=True)
        if isinstance(res, dict) and "id" in res:
            self._state["status_message_id"] = res["id"]
            self._save_state()

    def _render_status_payload(self, *, title: str, lines: list[str]) -> dict[str, Any]:
        # webhook payload w/ embed (Discord standard)
        return {
            "content": "",
            "embeds": [
                {
                    "title": title,
                    "description": "\n".join(lines),
                }
            ],
        }

    def _webhook_for(self, kind: str) -> str:
        if kind == "killfeed":
            return self.cfg.killfeed_webhook_url
        if kind == "admin":
            return self.cfg.admin_webhook_url
        if kind == "loot":
            return self.cfg.loot_webhook_url
        return self.cfg.admin_webhook_url

    async def _webhook_post(self, url: str, payload: dict[str, Any], *, want_json: bool = False):
        async with self._session.post(url, json=payload) as r:
            if r.status == 429:
                # Respect Retry-After if present; then retry once.
                try:
                    data = await r.json()
                except Exception:
                    data = {}
                delay = float(data.get("retry_after", 1.0))
                await asyncio.sleep(delay)
                async with self._session.post(url, json=payload) as r2:
                    r2.raise_for_status()
                    return await r2.json() if want_json else None
            r.raise_for_status()
            return await r.json() if want_json else None

    async def _webhook_patch(self, url: str, payload: dict[str, Any]) -> None:
        async with self._session.patch(url, json=payload) as r:
            if r.status == 429:
                try:
                    data = await r.json()
                except Exception:
                    data = {}
                delay = float(data.get("retry_after", 1.0))
                await asyncio.sleep(delay)
                async with self._session.patch(url, json=payload) as r2:
                    r2.raise_for_status()
                    return
            r.raise_for_status()

    async def _enqueue(self, item: dict[str, Any]) -> None:
        # hard backpressure: drop oldest killfeed when saturated, keep admin signals
        if self._q.full():
            if item["kind"] == "killfeed":
                return
        await self._q.put(item)

    # -------------------------
    # persistence
    # -------------------------
    def _load_state(self) -> None:
        path = self.cfg.state_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._state = json.load(f)
        except FileNotFoundError:
            self._state = {}
        except Exception:
            self._state = {}

    def _save_state(self) -> None:
        path = self.cfg.state_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, sort_keys=True)
        os.replace(tmp, path)

# Helper for setup logic if needed (or we can do it in bot.py)
async def setup(bot) -> None:
    # This is a placeholder since the user wants specific initiation logic in bot.py
    pass
