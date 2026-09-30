import ftplib
import io
import logging
import os
from typing import List, Optional, Tuple

log = logging.getLogger("dayz-discord-ops.ftp")

class FTPClient:
    def __init__(self, host: str, port: int, user: str, passwd: str):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self._ftp: Optional[ftplib.FTP] = None

    def connect(self):
        try:
            self._ftp = ftplib.FTP()
            self._ftp.connect(self.host, self.port)
            self._ftp.login(self.user, self.passwd)
            log.info(f"Connected to FTP: {self.host}")
            return True
        except Exception as e:
            log.error(f"FTP Connection failed: {e}")
            return False

    def list_files(self, directory: str = "/") -> List[Tuple[str, dict]]:
        """
        List files in a directory. Returns list of (filename, metadata).
        """
        if not self._ftp:
            if not self.connect():
                return []
        
        try:
            files = []
            self._ftp.cwd(directory)
            items = []
            self._ftp.dir(items.append)
            
            # Basic parsing of LIST command output (Unix style usually)
            parsed_files = []
            for item in items:
                parts = item.split()
                if len(parts) >= 9:
                    name = " ".join(parts[8:])
                    is_dir = parts[0].startswith("d")
                    size = None
                    try:
                        size = int(parts[4])
                    except (ValueError, IndexError):
                        pass
                    parsed_files.append({"name": name, "raw": item, "is_dir": is_dir, "size": size})
            return parsed_files
        except Exception as e:
            log.error(f"FTP List failed: {e}")
            self._close()
            return []

    def read_file(self, path: str) -> Optional[str]:
        if not self._ftp:
            if not self.connect():
                return None
        
        try:
            bio = io.BytesIO()
            self._ftp.retrbinary(f"RETR {path}", bio.write)
            return bio.getvalue().decode("utf-8", errors="replace")
        except Exception as e:
            log.error(f"FTP Read failed: {e}")
            self._close()
            return None

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the FTP server"""
        if not self._ftp:
            if not self.connect():
                return False
        
        try:
            with open(local_path, 'rb') as f:
                self._ftp.storbinary(f"STOR {remote_path}", f)
            log.info(f"Uploaded {local_path} -> {remote_path}")
            return True
        except Exception as e:
            log.error(f"FTP Upload failed: {e}")
            self._close()
            return False

    def upload_content(self, content: str, remote_path: str) -> bool:
        """Upload string content directly to FTP"""
        if not self._ftp:
            if not self.connect():
                return False
        
        try:
            bio = io.BytesIO(content.encode('utf-8'))
            self._ftp.storbinary(f"STOR {remote_path}", bio)
            log.info(f"Uploaded content -> {remote_path}")
            return True
        except Exception as e:
            log.error(f"FTP Upload content failed: {e}")
            self._close()
            return False

    def tail_file(self, path: str, size: int = 10240) -> Optional[str]:
        """
        Download the content of a file. For true 'tail' on FTP, 
        we usually have to download the whole thing or use REST (restart marker) 
        if supported. 
        Nitrado FTP might support REST. Let's try to just download and truncate for now
        as log files rotate and might not be huge-huge.
        """
        # TODO: Implement partial download if files are massive.
        return self.read_file(path)

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a single file to the provided path. Returns True on success."""
        if not self._ftp:
            if not self.connect():
                return False
        try:
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            with open(local_path, "wb") as f:
                self._ftp.retrbinary(f"RETR {remote_path}", f.write)
            log.info(f"Downloaded {remote_path} -> {local_path}")
            return True
        except Exception as e:
            log.error(f"FTP Download failed ({remote_path}): {e}")
            self._close()
            return False

    def _close(self):
        try:
            if self._ftp:
                self._ftp.quit()
        except:
            pass
        self._ftp = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
