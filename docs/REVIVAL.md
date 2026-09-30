# REVIVAL — how to bring a DayZ server back with this toolkit

Honest guide. Nothing here is live; this is the order you'd do it in if you wanted to run a server again.

## What you need (that isn't in this repo)

1. **A DayZ server** — Nitrado game server, or self-hosted. The Nitrado SDK in `nitrado/` automates the hosted path.
2. **A Discord application** — bot token from the [Discord developer portal](https://discord.com/developers/applications).
3. **A Steam account** with DayZ for testing RCON/A2S connectivity.
4. **Mission files** — `missions/dayzxb_missions/dayzOffline.chernarusplus/` is included; mods come from the Steam Workshop.

## Bring-up order

### 1. Configure
```bash
cp .env.example .env
# Fill in: DISCORD_TOKEN, NITRADO_API_TOKEN, NITRADO_SERVICE_ID,
# DAYZ_RCON_HOST/PORT/PASSWORD, FTP + MySQL credentials
```
Every variable is documented in `.env.example`. **Never commit `.env`.**

### 2. Nitrado SDK first (most self-contained)
```bash
cd nitrado/nitrado_api_lib
pip install aiohttp
python -c "import asyncio; from nitrado_api.nitrado_api import NitradoAPI; print('ok')"
```
Note `DISABLE_FTP_PUSH=1` is the default — set it to `0` only when you actually want the automation to write to the server.

### 3. Test server connectivity
Use the admin suite's probes before wiring the bot:
```bash
cd admin-suite/src/dayz_admin_tools/nitrado
python get_nitrado_gs_info.py   # needs NITRADO_API_TOKEN
python list_nitrado_files.py    # lists game-server files
```

### 4. The Discord bot
```bash
cd discord-ops
pip install -r requirements.txt   # check requirements file present
python -m src.nexus.bot          # or however your entrypoint is laid out — read bot.py first
```
Expect to fix import paths — this is archived code from a live era, not a polished package. `docs/ARCHITECTURE.md` maps the modules.

### 5. Trader/economy patches
Review first, then apply:
```bash
ls patches/ezstreet/            # read the JSON — traders, loadouts, heists
# apply_ezstreet_heist_patch.py uploads via FTP; audit it before running
```

### 6. Dashboard (optional)
```bash
cd discord-ops/dashboard/nexus_dashboard
npm install && npm run dev
```

## What will probably break

- **Dependency drift** — `discord.py`, `aiohttp`, Next.js versions have moved on. Pin or upgrade.
- **Nitrado API changes** — endpoints in `nitrado_api.py` target `api.nitrado.net` as of the archive date; verify against current docs.
- **Import paths** — the archive merges several eras (`archives/legacy_nexus/` vs `src/nexus/`); the newer tree is the one to revive.
- **RCON passwords** — DayZ RCON config lives server-side, not here.

## What NOT to do

- Don't point this at anyone else's server. RCON + FTP credentials are power tools.
- Don't "fix" the redacted credentials by guessing — they're dead. Generate new ones.
- Don't run the dashboard + bot + patcher all at once on day one. One piece at a time.
