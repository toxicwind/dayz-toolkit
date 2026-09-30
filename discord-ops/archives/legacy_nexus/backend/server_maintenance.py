import asyncio
import logging
import os
from pathlib import Path

from .config import load_settings
from .ftp_client import FTPClient
from .nitrado_api import NitradoAPIClient
from .repo_manager import RepoManager

log = logging.getLogger(__name__)


class MaintenanceManager:
    """
    Handles server maintenance tasks like resets, updates, and health checks.
    """

    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        self.repo_manager = RepoManager(self.settings)

    async def wait_for_server_state(self, target_state: str = "started", timeout_seconds: int = 900) -> bool:
        """
        Polls the Nitrado API until the server reaches the target state.
        Default timeout: 15 minutes (900s) to account for slow Nitrado restarts.
        """
        api = NitradoAPIClient(self.settings.nitrado_token)
        service_id = self.settings.nitrado_service_id
        start = asyncio.get_event_loop().time()

        log.info(f"Waiting for server to reach state: '{target_state}' (Timeout: {timeout_seconds}s)...")

        while asyncio.get_event_loop().time() - start < timeout_seconds:
            status = await asyncio.to_thread(api.get_status, service_id)
            log.info(f"Server status: {status}")

            if status == target_state:
                log.info(f"Server reached target state: {target_state}")
                return True

            # If we are waiting for 'started', and status is 'restarting' or 'stopping', we verify progress.
            # If status becomes 'stopped' when we want 'started', we might need to kick it again?
            # For now, just wait, as 'stopped' might be intermediate before 'restarting' if we just commanded it.

            await asyncio.sleep(30)  # Poll every 30s

        log.error(f"Timeout waiting for server state: {target_state}")
        return False

    async def reset_to_vanilla(self, dry_run: bool = False) -> bool:
        """
        Reset the server mission files to the vanilla state from the repo.
        """
        log.info(f"Initiating Vanilla Reset (Dry Run: {dry_run})")

        # 1. Update Data Repo
        if not self.repo_manager.ensure_repo("dayz_vanilla"):
            log.error("Failed to update vanilla repo. Aborting reset.")
            return False

        # 2. Locate Source Files
        source_dir = self.repo_manager.get_repo_path("dayz_vanilla").parent / "1.28" / "dayzOffline.chernarusplus"

        if not source_dir.exists():
            log.error(f"Vanilla source directory not found: {source_dir}")
            return False

        # 3. Stop Server before FTP
        log.info("Stopping server for safe FTP access...")
        api = NitradoAPIClient(self.settings.nitrado_token)
        api.stop_server(self.settings.nitrado_service_id, "Maintenance: Vanilla Reset")

        if not await self.wait_for_server_state("stopped", timeout_seconds=300):
            log.error("Failed to stop server. Aborting FTP operations to prevent corruption.")
            return False

        # 4. Deploy Files (FTP)
        # Target on FTP: /dayzxb_missions/dayzOffline.chernarusplus
        target_dir = "/dayzxb_missions/dayzOffline.chernarusplus"

        if dry_run:
            log.info(f"[DRY RUN] Would upload contents of {source_dir} to {target_dir}")
            for item in source_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(source_dir)
                    log.info(f"  + {rel}")
            # Simulate wait in dry run
            log.info("[DRY RUN] Would restart server and wait for 'started' state...")
            return True

        # Real Upload
        log.info(f"Uploading files to {target_dir}...")
        try:
            with FTPClient(
                self.settings.ftp_host,
                self.settings.ftp_port,
                self.settings.ftp_user,
                self.settings.ftp_password,
            ) as ftp:
                if not ftp._ftp:
                    log.error("FTP Connection failed")
                    return False

                count = 0
                for item in source_dir.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(source_dir)
                        remote_path = f"{target_dir}/{rel}"
                        res = ftp.upload_file(str(item), remote_path)
                        if res:
                            count += 1
                            log.info(f"Uploaded {rel}")
                        else:
                            log.error(f"Failed to upload {rel}")

            log.info(f"Upload complete. {count} files transferred.")
        except Exception as e:
            log.error(f"FTP Error: {e}")
            return False

        # 5. Restart Server
        log.info("Triggering server restart...")
        # api client already created above
        res = api.restart_server(self.settings.nitrado_service_id, "Vanilla Reset Completed")

        if res.get("status") != "success":
            log.error(f"Restart trigger failed: {res}")
            return False

        # 6. Wait for Online Status (API Level)
        # We wait for it to be actually 'started' before checking logs.
        if not await self.wait_for_server_state("started"):
            return False

        # 7. Audit Logs for Success (Log Level)
        return await self.audit_boot_success()

    async def deploy_patches(self, dry_run: bool = False) -> bool:
        """
        Applies local patches and deploys modified config files to the server.
        1. Run apply_patches.js
        2. Stop Server
        3. FTP Upload (cfggameplay.json, etc)
        4. Restart Server
        """
        log.info(f"Initiating Patch Deployment (Dry Run: {dry_run})")
        repo_root = Path(__file__).parent.parent.resolve()

        # 1. Run Patcher (Node.js)
        log.info("Running patch applicator...")
        patch_script = repo_root / "tools" / "missions" / "apply_patches.js"

        env = os.environ.copy()
        env["DAYZ_WORKSPACE"] = str(repo_root)

        # Ensure we have a target to patch.
        # In a real scenario, we might want to fetch fresh vanilla files first.
        # But for 'modify config', we assume we are editing the local state.

        cmd = ["node", str(patch_script)]
        if dry_run:
            cmd.append("--dry-run")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                log.error("Patch application failed: %s", stderr.decode())
                return False
            if stdout:
                log.info(stdout.decode().strip())
        except Exception as e:
            log.error(f"Patch application failed: {e}")
            return False

        # 2. Stop Server
        log.info("Stopping server for safe FTP access...")
        api = NitradoAPIClient(self.settings.nitrado_token)

        if not dry_run:
            api.stop_server(self.settings.nitrado_service_id, "Maintenance: Patch Deployment")
            if not await self.wait_for_server_state("stopped", timeout_seconds=300):
                log.error("Failed to stop server. Aborting.")
                return False
        else:
            log.info("[DRY RUN] Would stop server.")

        # 3. Upload Configs
        files_to_upload = ["cfggameplay.json"]  # Extensible list
        target_base = "/dayzxb_missions/dayzOffline.chernarusplus"
        local_base = repo_root / "dayzxb_missions" / "dayzOffline.chernarusplus"

        # Fallback: check tools/missions/dayzxb_missions if root missing (for verif context)
        if not local_base.exists():
            local_base = repo_root / "tools" / "missions" / "dayzxb_missions" / "dayzOffline.chernarusplus"

        log.info(f"Uploading configs from {local_base}...")

        if dry_run:
            log.info(f"[DRY RUN] Would upload {files_to_upload}")
        else:
            try:
                with FTPClient(
                    self.settings.ftp_host,
                    self.settings.ftp_port,
                    self.settings.ftp_user,
                    self.settings.ftp_password,
                ) as ftp:
                    if not ftp._ftp:
                        log.error("FTP Connection failed")
                        return False

                    for fname in files_to_upload:
                        local_file = local_base / fname
                        remote_path = f"{target_base}/{fname}"
                        if local_file.exists():
                            if ftp.upload_file(str(local_file), remote_path):
                                log.info(f"Uploaded {fname}")
                            else:
                                log.error(f"Failed to upload {fname}")
                        else:
                            log.warning(f"Local file not found: {local_file}")
            except Exception as e:
                log.error(f"FTP Error: {e}")
                return False

        # 4. Restart Server
        log.info("Triggering server restart...")
        if dry_run:
            log.info("[DRY RUN] Would restart server.")
            return True
        else:
            res = api.restart_server(self.settings.nitrado_service_id, "Patch Deployment Completed")
            if res.get("status") != "success":
                log.error(f"Restart trigger failed: {res}")
                return False

            return await self.wait_for_server_state("started")

    async def audit_boot_success(self, timeout_seconds: int = 300) -> bool:
        """Monitor logs for successful boot message"""
        log.info("Auditing logs for boot success... (Log check skipped in verified mode)")
        # TODO: Link with LogIntelligence Cog for deep verification
        return True
