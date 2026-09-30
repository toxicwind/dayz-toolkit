
from fastapi import APIRouter
import subprocess
import logging

router = APIRouter(tags=["Shell Ops"])
log = logging.getLogger("mildlyawesome.api.shell")

@router.post("/shell/mildlyawesome/rsync")
async def shell_mildlyawesome_rsync():
    """Wrapper for tools/mildlyawesome_rsync.sh"""
    try:
        cmd = ["bash", "backend/mildlyawesome/ops/mildlyawesome_rsync.sh"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/shell/fast_audit")
async def shell_fast_audit():
    """Wrapper for tools/ms_fast_audit.sh"""
    try:
        cmd = ["bash", "backend/mildlyawesome/ops/ms_fast_audit.sh"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}
