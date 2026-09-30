from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hardened_main")

# ATTEMPT EMERGENT IMPORT
try:
    from dedi_agent import app as app
    logger.info("Successfully imported emergent dedi_agent app")
except Exception as e:
    logger.error(f"Failed to import dedi_agent: {e}")
    app = FastAPI(title="Chronos Safeguard Mode")

    @app.get("/health")
    def health():
        return {
            "status": "safeguard_mode",
            "reason": "dedi_agent_import_failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=35100)
