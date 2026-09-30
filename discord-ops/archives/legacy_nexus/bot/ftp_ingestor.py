import logging
from typing import List
from .services.ftp_service import FTPService
from .log_parser import LogEvent

log = logging.getLogger(__name__)

class FTPLogIngestor:
    """
    Lightweight wrapper around FTPService for backward compatibility.
    """
    def __init__(self, ftp_service: FTPService = None):
        if ftp_service:
            self.ftp_service = ftp_service
        else:
            # Fallback for standalone usage (like in log_streamer.py)
            from .config import load_settings
            self.ftp_service = FTPService(load_settings())
        
    async def process(self) -> List[LogEvent]:
        """Main loop iteration delegated to FTPService"""
        return await self.ftp_service.ingest_logs()
