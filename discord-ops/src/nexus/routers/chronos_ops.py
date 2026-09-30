
from fastapi import APIRouter
import subprocess
import logging

router = APIRouter(tags=["Chronos Ops"])
log = logging.getLogger("mildlyawesome.api.chronos")

@router.post("/chronos/control")
async def chronos_control(action: str):
    """Wrapper for tools/chronos_control.py"""
    try:
        # Call as a module from the repo root
        cmd = ["python3", "-m", "src.mildlyawesome.ops.chronos_control", action]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "status": "ok" if res.returncode == 0 else "error",
            "stdout": res.stdout,
            "stderr": res.stderr,
            "rc": res.returncode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/chronos/captain_hook")
async def captain_to_chronos():
    """Wrapper for tools/captain_to_chronos.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.captain_to_chronos"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "status": "ok" if res.returncode == 0 else "error",
            "stdout": res.stdout,
            "stderr": res.stderr,
             "rc": res.returncode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
