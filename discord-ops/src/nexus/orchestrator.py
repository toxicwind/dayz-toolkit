import asyncio
import logging
import multiprocessing
import os
import signal
import sys
import time
from typing import Dict, List

log = logging.getLogger("src.mildlyawesome.orchestrator")

def run_shard(shard_id: int, total_shards: int, config_env: Dict[str, str]):
    """Entry point for a single bot shard process."""
    # Set environment variables for this process
    os.environ.update(config_env)
    os.environ["SHARD_ID"] = str(shard_id)
    os.environ["SHARD_COUNT"] = str(total_shards)
    
    # Import here to avoid pre-fork side effects
    from src.mildlyawesome.bot import main
    
    log.info(f"💎 Starting Shard {shard_id}/{total_shards}")
    try:
        main()
    except Exception as e:
        log.critical(f"Shard {shard_id} crashed: {e}")
        sys.exit(1)

class Orchestrator:
    def __init__(self, total_shards: int = 1):
        self.total_shards = total_shards
        self.processes: Dict[int, multiprocessing.Process] = {}
        self.running = True

    def start(self):
        log.info(f"🎼 Orchestrator starting with {self.total_shards} shards...")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        for i in range(self.total_shards):
            self._spawn_shard(i)

        self._monitor_loop()

    def _spawn_shard(self, shard_id: int):
        env_copy = os.environ.copy()
        p = multiprocessing.Process(
            target=run_shard,
            args=(shard_id, self.total_shards, env_copy),
            name=f"Shard-{shard_id}"
        )
        p.start()
        self.processes[shard_id] = p
        log.info(f"🚀 Shard {shard_id} spawned (PID: {p.pid})")

    def _handle_shutdown(self, signum, frame):
        log.info("🛑 Shutdown signal received. Terminating shards...")
        self.running = False
        for pid, p in self.processes.items():
            if p.is_alive():
                p.terminate()
        sys.exit(0)

    def _monitor_loop(self):
        while self.running:
            for shard_id, p in list(self.processes.items()):
                if not p.is_alive():
                    log.warning(f"⚠️ Shard {shard_id} died (Exit Code: {p.exitcode}). Respawning in 5s...")
                    time.sleep(5)
                    self._spawn_shard(shard_id)
            time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    
    # Determine shard count (default 1, or env override)
    shards = int(os.getenv("SHARD_COUNT", "1"))
    
    orch = Orchestrator(total_shards=shards)
    orch.start()
