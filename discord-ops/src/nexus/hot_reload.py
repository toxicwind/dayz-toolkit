import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from .bot import OpsBot

log = logging.getLogger("src.mildlyawesome.hot_reload")

class HotReloadHandler(FileSystemEventHandler):
    def __init__(self, bot: "OpsBot", pause_event: asyncio.Event):
        self.bot = bot
        self.pause_event = pause_event
        self.reload_cooldown = asyncio.Lock()
        self.pending_reloads: Set[str] = set()
        self._loop = asyncio.get_event_loop()

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            self._schedule_reload(event.src_path)

    def _schedule_reload(self, path: str):
        # Convert path to module format
        relative_path = os.path.relpath(path, os.getcwd())
        if "modules" in relative_path and "bot.py" in relative_path:
            # It's a module bot file, e.g., modules/bank/bot.py -> modules.bank.bot
            module_name = relative_path.replace("/", ".").replace("\\", ".").replace(".py", "")
            
            # Debounce
            if module_name not in self.pending_reloads:
                self.pending_reloads.add(module_name)
                asyncio.run_coroutine_threadsafe(self._trigger_reload(module_name), self._loop)

    async def _trigger_reload(self, module_name: str):
        await asyncio.sleep(1.0) # Debounce wait
        async with self.reload_cooldown:
            if module_name in self.pending_reloads:
                log.info(f"🔄 Hot Reload triggering for: {module_name}")
                try:
                    await self.bot.reload_extension(module_name)
                    log.info(f"✅ Successfully reloaded {module_name}")
                except Exception as e:
                    log.error(f"❌ Failed to reload {module_name}: {e}")
                finally:
                    self.pending_reloads.discard(module_name)

class HotReloadManager:
    def __init__(self, bot: "OpsBot", watch_dir: str = "."):
        self.bot = bot
        self.watch_dir = watch_dir
        self.observer = Observer()
        self.pause_event = asyncio.Event()
        self.pause_event.set()

    def start(self):
        handler = HotReloadHandler(self.bot, self.pause_event)
        self.observer.schedule(handler, self.watch_dir, recursive=True)
        self.observer.start()
        log.info(f"🔥 Hot Reload Manager watching: {self.watch_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
