"""
Hot Reload Module for Discord Bot
Watches bot/ directory for changes and automatically reloads extensions/cogs
"""
import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

import importlib
import sys

log = logging.getLogger("hot_reload")

class BotReloadHandler(FileSystemEventHandler):
    def __init__(self, bot, watch_dir: Path):
        self.bot = bot
        self.watch_dir = watch_dir
        self.debounce_time = 0.5  # 500ms debounce
        self.pending_reloads = set()
        
    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.py'):
            # Ignore __pycache__ and test files
            if '__pycache__' in event.src_path or '/tests/' in event.src_path:
                return
                
            file_path = Path(event.src_path)
            # Convert file path to module name
            try:
                rel_path = file_path.relative_to(self.watch_dir.parent)
                module_name = str(rel_path.with_suffix('')).replace('/', '.')
                
                # Aggressive scheduling in bot loop
                asyncio.run_coroutine_threadsafe(
                    self.debounced_reload(module_name),
                    self.bot.loop
                )
            except ValueError:
                pass  # File not in watch dir
                
    async def debounced_reload(self, module_name: str):
        """Debounce rapid file changes"""
        if module_name in self.pending_reloads:
            return
            
        self.pending_reloads.add(module_name)
        await asyncio.sleep(self.debounce_time)
        
        try:
            log.info(f"🔄 Aggressive reload: {module_name}")
            
            # 1. Force reload module via importlib for core logic
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                log.info(f"✨ Module cache refreshed: {module_name}")

            # 2. Special handling for config
            if module_name == 'bot.config':
                self.bot.reload_config()
                log.info("⚙️ Configuration reloaded into Bot state")

            # 3. Reload as Discord extension if applicable
            if module_name in self.bot.extensions:
                await self.bot.reload_extension(module_name)
                log.info(f"🧩 Extension re-synced: {module_name}")
                
            log.info(f"✅ Reload complete: {module_name}")
        except Exception as e:
            log.error(f"❌ Reload failure for {module_name}: {e}")
        finally:
            self.pending_reloads.discard(module_name)

class HotReloadManager:
    def __init__(self, bot, watch_dir: str = "bot"):
        self.bot = bot
        self.watch_dir = Path(watch_dir)
        self.observer = None
        self.handler = None
        
    def start(self):
        """Start watching for file changes"""
        if not self.watch_dir.exists():
            log.warning(f"Watch directory {self.watch_dir} does not exist")
            return
            
        self.handler = BotReloadHandler(self.bot, self.watch_dir)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=True)
        self.observer.start()
        log.info(f"🔥 Hot reload enabled - watching {self.watch_dir}")
        
    def stop(self):
        """Stop watching for file changes"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            log.info("Hot reload watcher stopped")
