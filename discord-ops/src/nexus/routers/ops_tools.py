
from fastapi import APIRouter
import subprocess
import logging

router = APIRouter(tags=["Internal Tools Ops"])
log = logging.getLogger("mildlyawesome.api.tools")

@router.post("/tools/consolidate_prompts")
async def tool_consolidate_prompts():
    """Wrapper for backend/mildlyawesome/ops/consolidate_prompts.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.consolidate_prompts"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tools/inspect_ftp")
async def tool_inspect_ftp():
    """Wrapper for backend/mildlyawesome/ops/inspect_ftp.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.inspect_ftp"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tools/platform_probe")
async def tool_platform_probe():
    """Wrapper for backend/mildlyawesome/ops/platform_probe.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.platform_probe"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tools/mildlyawesome_watchdog")
async def tool_mildlyawesome_watchdog(action: str = "status"):
    """Wrapper for backend/mildlyawesome/ops/mildlyawesome_watchdog.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.mildlyawesome_watchdog", action]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}
    except Exception as e:
        return {"status": "error", "message": str(e)}
