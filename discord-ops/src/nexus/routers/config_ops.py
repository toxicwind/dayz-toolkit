
from fastapi import APIRouter
import subprocess
import logging

router = APIRouter(tags=["Config Ops"])
log = logging.getLogger("mildlyawesome.api.config")

@router.get("/config/backend")
async def fetch_backend_config():
    """Wrapper for tools/fetch_be_config.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.fetch_be_config"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"output": res.stdout, "error": res.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/config/stack_env")
async def fetch_stack_env():
    """Wrapper for tools/fetch_stack_env.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.fetch_stack_env"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"output": res.stdout, "error": res.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}
