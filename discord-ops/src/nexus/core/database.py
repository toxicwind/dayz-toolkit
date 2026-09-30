import logging
from src.mildlyawesome.core.config import Settings

log = logging.getLogger("mildlyawesome.db")

class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        log.info(f"Connected to database at {settings.bot_mysql.host}")
        
    async def execute(self, query: str, *args):
        # Stub for now
        return []
