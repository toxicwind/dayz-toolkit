
from fastapi import APIRouter
import logging
import asyncio
import os
import shutil
import json
from pathlib import Path
from pydantic import BaseModel
from src.mildlyawesome.mission_tools import validate_mission, diagnose_mission, scale_types_xml
from src.mildlyawesome.config import load_settings
from src.mildlyawesome.ftp_client import FTPClient
from src.mildlyawesome.economy_intelligence import EconomyIntelligence

router = APIRouter(tags=["Mission Ops"])
log = logging.getLogger("mildlyawesome.api.mission")

# --- Models ---
class MissionValidateRequest(BaseModel):
    path: str

class MissionScaleRequest(BaseModel):
    path: str
    nominal_mult: float
    min_mult: float | None = None
    round_mode: str = "ceil"

class FileUpdateRequest(BaseModel):
    content: str
    backup: bool = True

class EconomyUpdateRequest(BaseModel):
    loot_multiplier: float
    lifetime_multiplier: float
    zombie_max: int
    animal_max: int

# --- Endpoints ---

@router.post("/mission/validate")
async def validate_mission_endpoint(req: MissionValidateRequest):
    """Validate DayZ mission structure and CE configuration"""
    try:
        findings = validate_mission(Path(req.path))
        return {
            "status": "ok",
            "errors": [f.as_line() for f in findings if f.level == "ERROR"],
            "warnings": [f.as_line() for f in findings if f.level == "WARN"],
            "total": len(findings),
        }
    except Exception as e:
        log.error(f"Mission validation failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/mission/diagnose")
async def diagnose_mission_endpoint(req: MissionValidateRequest):
    """Run opinionated diagnostics on mission"""
    try:
        notes = diagnose_mission(Path(req.path))
        return {"status": "ok", "notes": [{"title": n.title, "detail": n.detail} for n in notes]}
    except Exception as e:
        log.error(f"Mission diagnostics failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/mission/scale")
async def scale_mission_endpoint(req: MissionScaleRequest):
    """Scale nominal/min counts in types.xml"""
    try:
        target_dir = Path(req.path)
        types_path = None
        for cand in [target_dir / "types.xml", target_dir / "db" / "types.xml"]:
            if cand.exists():
                types_path = cand
                break

        if not types_path:
            return {"status": "error", "message": "Could not locate types.xml"}

        res = scale_types_xml(types_path, req.nominal_mult, req.min_mult, req.round_mode)
        return {"status": "ok", "touched": res.touched, "changed": res.changed, "path": str(types_path)}
    except Exception as e:
        log.error(f"Mission scaling failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/mission/files")
async def list_mission_files():
    """List XML files in the mission db directory"""
    settings = load_settings()
    mission_path = Path(settings.mission_path)
    db_path = mission_path / "db"
    container_staging = Path("staging/ezstreet/dayzxb_missions/dayzOffline.chernarusplus/db")

    try:
        if db_path.exists():
            files = [f for f in db_path.iterdir() if f.is_file() and f.name.endswith(".xml")]
            return {"files": sorted([f.name for f in files]), "source": "local"}
        elif container_staging.exists():
            files = [f for f in container_staging.iterdir() if f.is_file() and f.name.endswith(".xml")]
            return {"files": sorted([f.name for f in files]), "source": "container_staging"}
    except Exception as e:
        log.warning(f"Local mission files failed: {e}")

    try:
        if not settings.ftp_host:
            return {"error": "Mission files not accessible", "files": []}
        client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
        client.connect()
        files_raw = client.list_files(f"{settings.ftp_mission_path}/db/")
        client._close()
        files = [f["name"] for f in files_raw if f["name"].endswith(".xml")]
        return {"files": sorted(files), "source": "ftp"}
    except Exception as e:
        return {"error": str(e), "files": []}

@router.get("/mission/files/{filename}")
async def get_mission_file(filename: str):
    """Read a specific XML file from db directory"""
    settings = load_settings()
    file_path = Path(settings.mission_path) / "db" / filename
    if ".." in filename or filename.startswith("/"):
        return {"error": "Invalid filename"}
    try:
        content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        return {"filename": filename, "content": content}
    except Exception as e:
        return {"error": str(e)}

@router.post("/mission/files/{filename}")
async def update_mission_file(filename: str, req: FileUpdateRequest):
    """Update a specific XML file"""
    settings = load_settings()
    file_path = Path(settings.mission_path) / "db" / filename
    if ".." in filename or filename.startswith("/"):
        return {"error": "Invalid filename"}
    try:
        if req.backup and file_path.exists():
            shutil.copy2(file_path, file_path.with_suffix(file_path.suffix + ".bak"))
        await asyncio.to_thread(file_path.write_text, req.content, "utf-8")
        return {"status": "success", "message": f"Updated {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/server/economy/config")
async def get_economy_settings():
    """Get economy configuration from JSON"""
    base_path = Path("staging") if os.path.exists("staging") else Path(__file__).parent.parent.parent / "staging"
    config_path = base_path / "EZStreet_ServerConfig.json"
    try:
        data = await asyncio.to_thread(json.loads, config_path.read_text())
        return data
    except Exception as e:
        return {"error": str(e), "economy": {}}

@router.post("/server/economy/config")
async def update_economy_settings(req: EconomyUpdateRequest):
    """Update economy configuration and run apply script"""
    base_path = Path("staging") if os.path.exists("staging") else Path(__file__).parent.parent.parent / "staging"
    config_path = base_path / "EZStreet_ServerConfig.json"
    script_path = base_path / "configeconomy.py"
    try:
        current_data = await asyncio.to_thread(json.loads, config_path.read_text())
    except Exception:
        current_data = {"organization": "EZStreet", "version": "1.0", "economy": {}}
    current_data["economy"] = req.dict()
    try:
        await asyncio.to_thread(config_path.write_text, json.dumps(current_data, indent=2))
        proc = await asyncio.create_subprocess_exec("python3", str(script_path), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return {"status": "warning", "message": "Config saved but script failed", "stderr": stderr.decode()}
        return {"status": "success", "message": "Configuration updated and applied"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/server/economy/intelligence/clusters")
async def get_economy_clusters():
    settings = load_settings()
    intel = EconomyIntelligence(Path(settings.mission_path) / "db" / "types.xml")
    return intel.get_smart_clusters()

@router.get("/server/economy/intelligence/validate")
async def validate_economy_logic():
    settings = load_settings()
    intel = EconomyIntelligence(Path(settings.mission_path) / "db" / "types.xml")
    return {"warnings": intel.validate_logic()}
