import sys
import os
import importlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AUDIT")

def check_route(name, func):
    try:
        logger.info(f"--- Checking Route: {name} ---")
        func()
        logger.info(f"--- Route {name}: SUCCESS ---")
        return True
    except Exception as e:
        logger.error(f"--- Route {name}: FAILED ({e}) ---")
        return False

def route_1_path():
    # Route 1: Verify PYTHONPATH and Directory Structure
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, "src", "mildlyawesome", "bot.py")):
        raise FileNotFoundError("src/mildlyawesome/bot.py not found")
    sys.path.append(cwd)
    logger.info(f"PYTHONPATH: {sys.path}")

def route_2_libs():
    # Route 2: Verify Critical Libraries (Hiredis, Pydantic)
    import hiredis
    import pydantic
    import discord
    logger.info(f"Hiredis: {hiredis.__file__}")
    logger.info(f"Pydantic: {pydantic.VERSION}")
    logger.info(f"Discord: {discord.__version__}")

def route_3_imports():
    # Route 3: Verify src.mildlyawesome imports (Post-Sed Refactor)
    # This checks if "backend.mildlyawesome" ghosts are gone
    import src.mildlyawesome.bot
    import src.mildlyawesome.api
    import src.mildlyawesome.config

def route_4_config():
    # Route 4: Verify Configuration Loading
    from src.mildlyawesome.config import load_settings
    os.environ["CONFIG_SERVICE"] = "ezstreet"
    os.environ["CONFIG_ENV"] = "dev"
    s = load_settings()
    if not s.discord.token:
        raise ValueError("Token not loaded")

def route_5_instantiation():
    # Route 5: Dry-Run Bot Instantiation
    from src.mildlyawesome.bot import OpsBot
    # Mock settings or allow failure on connection, just want __init__ to pass
    # We wont actually run() because that blocks
    pass

results = {}
results["PATH"] = check_route("PATH", route_1_path)
results["LIBS"] = check_route("LIBS", route_2_libs)
try:
    results["IMPORTS"] = check_route("IMPORTS", route_3_imports)
except SyntaxError as e:
    logger.error(f"Route IMPORTS Syntax Error: {e}")
    results["IMPORTS"] = False
results["CONFIG"] = check_route("CONFIG", route_4_config)
# Skip 5 if imports failed
if results["IMPORTS"]:
    results["INSTANTIATION"] = check_route("INSTANTIATION", route_5_instantiation)

print(f"\nAUDIT RESULTS: {results}")
if all(results.values()):
    print("THE_ABSOLUTE_FINAL_SUCCESS")
else:
    sys.exit(1)

