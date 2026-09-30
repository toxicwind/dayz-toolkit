Serena MCP — Quick emergent setup (for this repo)

What I added

- docker-compose.serena.yml — a small compose file to run Serena as a container with MCP (port 9121) and dashboard (port 24282).
- serena-config/serena_config.docker.yml — a Docker-friendly Serena config (disables GUI log window, binds dashboard to 0.0.0.0, default context set to "claude-code").
- scripts/serena/start_serena.sh — convenience script to bring Serena up and wait for health.

Why this approach

- The Serena docs recommend Docker support (DOCKER.md) and suggest mounting your project and config into the container.
- Using Docker avoids host dependency issues (language servers and system-level packages) and isolates shell tooling.
- We explicitly provide --context claude-code and --project with an absolute mount to avoid the "positional project arg" errors (e.g., "Project 'serena==latest' not found").

Important operational notes & recommendations

- Run: docker compose -f docker-compose.serena.yml up -d
  Or use scripts/serena/start_serena.sh (chmod +x it first)

- If you prefer to add Serena to an existing docker-compose stack, merge this file via -f flags or create a compose.override.yml.

- If you want the server to index this repository, the project is mounted read-only by default in the compose file (to avoid accidental writes); change to read-write if you want Serena to create .serena/ memories and indexes:
    - ./:/workspaces/projects/my-project:rw

- Avoid passing project names as positional args. Use --project /absolute/path or pass project via the command above.

Community & real-world findings (quick)

- Serena is widely used with MCP-enabled clients (Claude Code, Claude Desktop, GitHub Copilot Chat and others). See: https://github.com/oraios/serena and the project docs.
- Reddit threads show many users reporting strong productivity gains, but also some caveats:
  - Token/context bloat can occur (monitor what is being loaded into the client's context). Example discussions: "Serena MCP users - share your setup and best practices?" and "Try out Serena MCP. Thank me later." (r/ClaudeAI/ClaudeCode).
  - Recent changelogs/updates (keep Serena up-to-date; different versions and config patterns matter).

Next steps (I can do these for you now)

1. Bring up the service with docker compose and verify the MCP ports and dashboard are reachable.
2. Optionally switch the mount to read-write and run a Serena "project create" and index step inside the container so your project is onboarded.
3. Update any existing automation that accidentally runs 'serena==latest' as a positional project arg (search the environment and service definitions, or global shell aliases) — I can scan common startup files if you'd like.

If you want, I can:
- Start the container and show it becoming healthy (logs + minimal health-check).
- Activate and index this repo as a Serena project inside the container, performing the onboarding step (will create .serena folder and memories).
- Search your system for any scripts or cron/systemd units that invoke 'serena' with the erroneous positional argument and fix them.

Notes about context names

- The server logs may warn that the context name 'ide-assistant' is deprecated and renamed to 'claude-code'. The docker configuration above uses 'claude-code'. If you have a local serena_config.yml specifying 'ide-assistant', update it.

References

- Serena docs (Docker + Quick Start): https://github.com/oraios/serena/blob/main/DOCKER.md
- Serena User Guide: https://oraios.github.io/serena/
- Example community threads: Reddit search for "Serena MCP" (r/ClaudeAI, r/ClaudeCode, r/mcp)

