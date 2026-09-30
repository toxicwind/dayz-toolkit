from fastapi import FastAPI, WebSocket, Header, HTTPException, Body, BackgroundTasks, APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import logging
import asyncio

from .service import ChronosService

log = logging.getLogger("mildlyawesome.modules.chronos.api")
router = APIRouter(prefix="/chronos", tags=["chronos"])

class QueryRequest(BaseModel):
    query: str
    emergent_mode: bool = True

class ExhumationResponse(BaseModel):
    exhumed_keys: List[str]
    merged_count: int
    latency_ns: int

@router.get("/status")
async def chronos_status():
    """Returns Chronos module health and status."""
    return {
        "status": "predatory",
        "version": "2025.1.1",
        "features": ["exhumation", "local_audit", "ghost_mapping", "entropy_scan"],
        "orchestrator_linked": True
    }

@router.get("/entropy")
async def chronos_entropy():
    """Returns system entropy map."""
    try:
        emap = await ChronosService.entropy_scan()
        return emap
    except Exception as e:
        log.error(f"Entropy scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ghosts")
async def chronos_ghosts():
    """Returns exhumed keys that are currently unused (ghosts)."""
    try:
        exhumed = await ChronosService.exhume_keys()
        usage = await ChronosService.cross_reference_usage(exhumed)
        return {k: v for k, v in usage.items() if v["status"] == "ghost"}
    except Exception as e:
        log.error(f"Ghost mapping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recover")
async def chronos_recover(terms: List[str]):
    """Scavenge dangling blobs for lost code."""
    try:
        hits = await ChronosService.blob_scavenge(terms)
        return {"hits": hits, "count": len(hits)}
    except Exception as e:
        log.error(f"Recovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/patch/{component}")
async def chronos_patch(component: str):
    """Generate a predictive patch proposal."""
    try:
        proposal = await ChronosService.predictive_patch(component)
        return proposal
    except Exception as e:
        log.error(f"Patching failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", response_class=HTMLResponse)
async def chronos_dashboard_route():
    """Proxy route to dashboard logic."""
    from .dashboard import chronos_dashboard
    return await chronos_dashboard()

@router.post("/exhume", response_model=ExhumationResponse)
async def chronos_exhume(background_tasks: BackgroundTasks):
    """Triggers autonomous exhumation of config keys."""
    start = asyncio.get_event_loop().time_ns()
    
    try:
        exhumed = await ChronosService.exhume_keys()
        current = await ChronosService.load_settings()
        updated = ChronosService.merge_predatory_defaults(current, exhumed)
        await ChronosService.save_settings(updated)
        
        latency = asyncio.get_event_loop().time_ns() - start
        
        # In a real scenario, we might trigger the background mutation loop here
        # For now, we'll just log it.
        log.info(f"Chronos exhumation complete. Latency: {latency}ns")
        
        return ExhumationResponse(
            exhumed_keys=list(exhumed)[:50], # Limit response size
            merged_count=len(updated),
            latency_ns=latency
        )
    except Exception as e:
        log.error(f"API exhumation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def chronos_query(request: QueryRequest):
    """Execute emergent query across local and emergent ecosystem."""
    try:
        results = await ChronosService.predator_query(request.query, request.emergent_mode)
        return results
    except Exception as e:
        log.error(f"API query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
