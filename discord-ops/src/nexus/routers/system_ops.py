
from fastapi import APIRouter
import subprocess
import logging

router = APIRouter(tags=["System Ops"])
log = logging.getLogger("mildlyawesome.api.system")

@router.get("/system/verify/files")
async def verify_file_access():
    """Wrapper for tools/verify_file_access.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.verify_file_access"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"output": res.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/system/verify/suite")
async def verify_suite():
    """Wrapper for tools/verify_suite.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.verify_suite"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"output": res.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}
