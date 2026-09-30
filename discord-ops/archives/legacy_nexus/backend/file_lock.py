import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("dayz-discord-ops.file_lock")


class FileOps:
    """
    Provides robust file operations to prevent race conditions.
    """

    @staticmethod
    def atomic_write_json(path: str | Path, data: Any, indent: int = 2):
        """
        Writes JSON data to a file atomically.
        Writes to a temp file first, then strictly renames it to target.
        This prevents partial reads by other processes (like Node.js).
        """
        path = Path(path)
        dir_name = path.parent

        # Ensure dir exists
        dir_name.mkdir(parents=True, exist_ok=True)

        # Write to temp file in same directory (important for atomic rename across filesystems)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_name, text=True)

        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(data, f, indent=indent)
                f.flush()
                os.fsync(f.fileno())  # Ensure write hits disk

            # Atomic rename
            os.replace(tmp_path, path)
            log.debug(f"Atomically wrote {path}")

        except Exception as e:
            log.error(f"Failed to write atomic JSON {path}: {e}")
            # Cleanup temp if rename failed
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    @staticmethod
    def atomic_write_text(path: str | Path, content: str):
        """
        Writes text content to a file atomically.
        """
        path = Path(path)
        dir_name = path.parent
        dir_name.mkdir(parents=True, exist_ok=True)

        tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_name, text=True)
        try:
            with os.fdopen(tmp_fd, "w") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, path)
            log.debug(f"Atomically wrote {path}")

        except Exception as e:
            log.error(f"Failed to write atomic text {path}: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
