# Discord TODO Bot Roadmap

Context: Reaction-driven TODO channel for Tony's DayZ backlog is live (see `bot/cogs/todo.py`, `bot/todo_store.py`, `seed_tasks.yaml`). Next iterations focus on durability, operator UX, and automation. Prior art references pulled via `github-advanced-search-mcp` (Hyena-Bot/Hyena `src/cogs/todo.py`, Adala `environments/servers/discord_bot.py`, etc.) inform several of the enhancements below.

## Phase 0 — Baseline Validation
1. **Dependency sync + hot reload**: Reinstall `requirements.txt`, verify `aiosqlite` availability, and ensure `python -m bot.bot` hot reload path watches new files (TodoStore, YAML). Capture logs for `/todo seed` and reaction flows.
2. **Ensure TODO channel exists**: ✅ Channel `server-todo` (`1454568932051783918`) created under ops category `1454365349918277704` via Discord API and stored in `state/todo.db`. `/todo ensure_channel` remains available if you need to recreate/move.

## Phase 1 — Task Metadata & Controls
3. **Owner/priority maintenance slash commands**: Add `/todo owner` & `/todo priority` to update fields without reseeding. ✅
4. **Manual status override command**: `/todo status` (with autocomplete) to fix cards when reactions fail or perms block emoji removal. ✅
5. **Task info + link command**: `/todo info` that surfaces Scope/Surface/Acceptance, Discord URL, and seed key so context is available via slash instead of scrolling. ✅

## Phase 2 — Activity Logging & Reporting
6. **Activity log table**: Extend `TodoStore` with `task_activity` table storing user, timestamp, old/new status/owner. Emit console + optional channel log (pattern borrowed from Hyena bot change feed).
7. **/todo summary embed**: Aggregate counts per status/priority and post as embed; optionally auto-refresh on schedule.
8. **/todo export filters**: Allow filtering by status/priority/owner and include reaction history when exporting YAML.

## Phase 3 — Card Lifecycle Hardening
9. **Archive/drop individual cards**: `/todo archive task-id`, `/todo drop task-id reason` marking cards as dropped without deleting history.
10. **Reaction cleanup resilience**: Mirror `on_raw_reaction_remove` to restore single source of truth when someone removes the bot reaction; auto-reapply status emoji.
11. **Repair diffing**: Enhance `/todo repair` to compare message content hash vs. DB, rewriting if Scope/Surface changed in YAML, not just missing messages.

## Phase 4 — Automation & Integrations
12. **Seed diff preview**: Dry-run mode showing which tasks will be added/updated by `/todo seed`, leveraging YAML + DB diff.
13. **Notification hooks**: Optional channel or webhook that receives status transitions (blocked/done) for pager visibility.
14. **Dashboard API exposure**: Expose `/api/todo` endpoints backed by `TodoStore` so the Next.js dashboard can visualize the backlog without scraping Discord.

## Notes
- Each feature batch should include `python -m py_compile bot/todo_store.py bot/cogs/todo.py` and targeted unit/integration tests when feasible.
- Continue using `github-advanced-search-mcp` before implementing each module to borrow mature patterns (reaction enforcement, slash UI flows, SQLite migrations).
- Favor Unicode emoji (per spec). Custom/guild emoji support remains optional.
