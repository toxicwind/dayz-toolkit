import asyncio
import logging
import sys
from src.mildlyawesome.config import load_settings
from src.mildlyawesome.bot import OpsBot
import src.mildlyawesome.api as api_module
import uvicorn

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mildlyawesome")

async def main():
    settings = load_settings()
    log.info(f"🚀 MildlyAwesome Orchestrator Starting for Service: {settings.org_id}")
    
    # Initialize Bot
    bot = OpsBot(settings)
    
    # Inject bot into API (Monolithic Link)
    api_module._bot_ref = bot
    app = api_module.app
    
    # Run both
    config = uvicorn.Config(app, host="0.0.0.0", port=43200, log_level="info")
    server = uvicorn.Server(config)
    
    log.info("🔥 MildlyAwesome Ignition: Bot + API")
    await asyncio.gather(
        bot.start(settings.discord_token),
        server.serve()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Stopping MildlyAwesome...")
        sys.exit(0)
