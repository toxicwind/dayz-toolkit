# Legacy Codebase Audit: Still to Explore

The restoration process has successfully migrated the core bot, dashboard, and primary tools. However, the following assets in `data/archives/` and `backups/` contain potentially valuable logic or data that remains unexplored:

## 📦 High-Value Archives
| Name | Description | Potential Use |
| :--- | :--- | :--- |
| `EZStreetCEKitProPlus.zip` | Professional-grade CE configuration kit. | Advanced item/economy settings. |
| `dayz_console_ce_toolkit_ops_v10.zip` | Version 10 of the Central Economy toolkit. | Latest logic for mission patching. |
| `dayzops_nitrado_console_v3.zip` | V3 of the Nitrado console operations. | Advanced server automation scripts. |
| `dayz_128_boosted/` | Extracted "128-player boosted" mission files. | Reference for high-pop performance cfg. |

## 📂 Extracted Snippets (`backups/cleanup_20251225/`)
- **`expand/`**: Contains hundreds of JSON snippets and file fragments. This directory is a "scratchpad" of processed items that could be audited for specific item lists or metadata.
- **`dayzxb_missions/init.c`**: The entry point for the DayZ mission. It likely contains custom RPT logging or server-side scripts (e.g., spawn modifiers) that haven't been ported to the Python bot yet.
- **`diffs/`**: A collection of diff files showing the changes made during previous iterations. Useful for understanding what was "manually fixed" in the past.

## 🛠️ TODO / Future Roadmap
1. [ ] **Kill Tracker persistence**: Update leaderboards using the data now being parsed by `AnalyticsEngine`.
2. [ ] **Spawn Plotter Integration**: Create a React component in the dashboard to visualize `cfgeventspawns.xml`.
3. [ ] **Slash Command Expansion**: Add commands for `/adm_analyze` and `/rpt_diag` to expose the new parsers.
4. [ ] **Clerk Organization Sync**: Automate the creation of database `tenants` based on Clerk organization IDs.
