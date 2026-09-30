#!/usr/bin/env python3
"""Generate a Portainer-ready Swarm stack YAML for dayz-discord-ops.

Why this exists:
- Portainer's env/.env behavior can be surprising for repo stacks.
- This generator prints a fully-expanded stack with your non-secret defaults,
  while keeping passwords/tokens as ENV or Swarm secrets.

Usage:
  python tools/gen_portainer_stack.py > docker-stack.generated.yml
"""

from __future__ import annotations
import os
from textwrap import dedent

def env(name: str, default: str) -> str:
    return os.getenv(name, default)

def main() -> None:
    # Non-secret defaults (safe to bake into the output if you want)
    dayz_host = env("DAYZ_HOST", "usla352.gamedata.io")
    query_port = env("DAYZ_QUERY_PORT", "11603")
    rcon_port = env("DAYZ_RCON_PORT", "11603")
    metrics_port = env("METRICS_PORT", "9108")

    image = env("IMAGE", "ghcr.io/your-org/dayz-discord-ops:local")

    # Secrets are referenced by name; create them in Swarm first.
    discord_secret = env("DISCORD_SECRET_NAME", "discord_bot_token")
    rcon_secret = env("RCON_SECRET_NAME", "dayz_rcon_password")

    print(dedent(f"""    version: "3.8"
    services:
      dayz-discord-ops:
        image: {image}
        environment:
          - DISCORD_BOT_TOKEN_FILE=/run/secrets/{discord_secret}
          - DISCORD_GUILD_ID=${{DISCORD_GUILD_ID}}
          - DISCORD_ADMIN_ROLE_IDS=${{DISCORD_ADMIN_ROLE_IDS}}
          - DISCORD_USE_PRESENCE=${{DISCORD_USE_PRESENCE:-0}}

          - DAYZ_HOST={dayz_host}
          - DAYZ_QUERY_PORT={query_port}
          - DAYZ_RCON_PORT={rcon_port}
          - DAYZ_RCON_PASSWORD_FILE=/run/secrets/{rcon_secret}

          - STAT_CHANNELS_JSON=${{STAT_CHANNELS_JSON:-}}
          - METRICS_ENABLE=${{METRICS_ENABLE:-0}}
          - METRICS_PORT={metrics_port}
          - TZ=America/Denver
        secrets:
          - {discord_secret}
          - {rcon_secret}
        deploy:
          replicas: 1
          restart_policy:
            condition: on-failure
          placement:
            constraints:
              - node.role == manager
        ports:
          - target: {metrics_port}
            published: {metrics_port}
            protocol: tcp
            mode: host

    secrets:
      {discord_secret}:
        external: true
      {rcon_secret}:
        external: true
    """))

if __name__ == "__main__":
    main()
