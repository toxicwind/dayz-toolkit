from fastapi import FastAPI
from src.mildlyawesome.api.routes import health, beta, mcp

def create_app(bot):
    app = FastAPI(title="DayZ MildlyAwesome API")
    app.state.bot = bot
    
    app.include_router(health.router, tags=["system"])
    app.include_router(beta.router, prefix="/api/beta", tags=["beta"])
    app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
    
    return app
