import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings
from ..ftp_client import FTPClient
from ..log_parser import DayZLogParser, LogEvent

log = logging.getLogger(__name__)


@dataclass
class IngestionState:
    file_path: str
    last_size: int = 0
    last_mtime: float = 0
    offset: int = 0
    file_hash: str = ""


class FTPService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
        self.parser = DayZLogParser()

        # State management for ingestion
        self.state_file = Path(settings.state_dir) / "ftp_service_state.json"
        self.state_file.parent.mkdir(exist_ok=True, parents=True)
        self.ingest_states: dict[str, IngestionState] = self._load_state()

    def _load_state(self) -> dict[str, IngestionState]:
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file) as f:
                data = json.load(f)
                return {k: IngestionState(**v) for k, v in data.items()}
        except Exception as e:
            log.error(f"Failed to load FTP state: {e}")
            return {}

    def _save_state(self):
        try:
            data = {k: v.__dict__ for k, v in self.ingest_states.items()}
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save FTP state: {e}")

    # --- FULL DUMP LOGIC ---
    async def dump_full(self, remote_path: str | None = None, local_path: Path | None = None):
        """Recursively dumps remote content to local path."""
        remote_path = remote_path or self.settings.ftp_base_path
        local_path = local_path or Path(self.settings.ftp_dump_local_path)

        log.info(f"Starting FULL FTP dump: {remote_path} -> {local_path}")
        await asyncio.to_thread(self._dump_recursive, remote_path, local_path)
        log.info("FULL FTP dump completed.")

    def _dump_recursive(self, remote_path: str, local_path: Path):
        self.client.connect()
        items = self.client.list_files(remote_path)
        local_path.mkdir(parents=True, exist_ok=True)

        for item in items:
            name = item["name"]
            if name in [".", ".."]:
                continue

            # Clean remote path
            if remote_path == "/":
                r_item = f"/{name}"
            else:
                r_item = f"{remote_path.rstrip('/')}/{name}"

            l_item = local_path / name
            raw = item.get("raw", "")
            is_dir = raw.startswith("d")

            if is_dir:
                self._dump_recursive(r_item, l_item)
            else:
                self._download_file(r_item, l_item)

    def _download_file(self, remote_path: str, local_path: Path):
        try:
            with open(local_path, "wb") as f:
                self.client._ftp.retrbinary(f"RETR {remote_path}", f.write)
        except Exception as e:
            log.error(f"Failed to download {remote_path}: {e}")

    # --- INGESTION LOGIC ---
    async def ingest_logs(self) -> list[LogEvent]:
        """Incremental log ingestion from the configured log_path."""
        target_dir = self.settings.ftp_log_path
        events = await asyncio.to_thread(self._ingest_blocking, target_dir)
        return events

    def _ingest_blocking(self, directory: str) -> list[LogEvent]:
        self.client.connect()
        files = self.client.list_files(directory)

        # Newest ADM and RPT
        adms = sorted([f["name"] for f in files if f["name"].upper().endswith(".ADM")])
        rpts = sorted([f["name"] for f in files if f["name"].upper().endswith(".RPT")])

        targets = []
        if adms:
            targets.append(f"{directory.rstrip('/')}/{adms[-1]}")
        if rpts:
            targets.append(f"{directory.rstrip('/')}/{rpts[-1]}")

        all_events = []
        for target in targets:
            lines = self._fetch_delta(target)
            if lines:
                log.info(f"Ingested {len(lines)} lines from {target}")
                for line in lines:
                    event = self.parser.parse_line(line)
                    if event:
                        event.data["source_file"] = target
                        all_events.append(event)
        return all_events

    def _fetch_delta(self, file_path: str) -> list[str]:
        try:
            # SIZE command requires binary mode
            self.client._ftp.sendcmd("TYPE I")
            size_resp = self.client._ftp.sendcmd(f"SIZE {file_path}")
            current_size = int(size_resp.split()[1])
        except:
            return []

        state = self.ingest_states.get(file_path, IngestionState(file_path=file_path))
        if current_size < state.offset:
            state.offset = 0  # Rotated

        if current_size == state.offset:
            return []

        new_data = bytearray()
        try:
            self.client._ftp.sendcmd("TYPE I")
            conn = self.client._ftp.transfercmd(f"RETR {file_path}", rest=state.offset)
            while True:
                data = conn.recv(16384)  # Larger buffer for speed
                if not data:
                    break
                new_data.extend(data)
            conn.close()
            self.client._ftp.voidresp()

            lines = new_data.decode("utf-8", errors="replace").splitlines()
            state.offset += len(new_data)
            state.last_size = current_size
            self.ingest_states[file_path] = state
            self._save_state()
            return lines
        except Exception as e:
            log.error(f"Delta fetch error for {file_path}: {e}")
            return []
