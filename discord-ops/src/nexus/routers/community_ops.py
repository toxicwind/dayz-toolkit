
from fastapi import APIRouter
import subprocess
import logging

router = APIRouter(tags=["Community Ops"])
log = logging.getLogger("mildlyawesome.api.community")

@router.post("/community/donors/ingest")
async def ingest_donors():
    """Wrapper for tools/ingest_donors.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.ingest_donors"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "executed", "output": res.stdout}
    except Exception as e:
         return {"status": "error", "message": str(e)}

@router.post("/community/donors/normalize")
async def normalize_donors():
    """Wrapper for tools/normalize_donors.py"""
    try:
        cmd = ["python3", "-m", "src.mildlyawesome.ops.normalize_donors"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "executed", "output": res.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}
