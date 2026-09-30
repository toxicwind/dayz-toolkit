# CHRONOS-FORGE TASK PROTOCOL

## Overview
This document defines the standard for creating and maintaining VS Code tasks within the `dedi-ops` workspace. Tasks must be robust, self-contained, and provide clear feedback.

## Standards for Task Creation

### 1. Absolute Pathing & Context
Never assume the terminal starts in a specific directory. Always `cd` to the repository root or use absolute paths.
*   **Bad:** `python3 scripts/script.py`
*   **Good:** `cd /home/toxic/development/dedi-ops && python3 scripts/script.py`

### 2. Error Handling
Tasks should fail loudly and provide context. Use `&&` to chain dependent commands.
*   **Good:** `cd ... && cmd1 && cmd2`

### 3. Problem Matchers
Include `problemMatcher` whenever possible to allow VS Code to parse errors into the Problems view.
*   Example: `"$tsc"`, `"$eslint-stylish"`, or a custom regex.

### 4. Grouping
Categorize tasks using the `group` property.
*   `build`: For compilation/bundling.
*   `test`: For test suites.
*   `none`: For general operations.

### 5. Task Manager Tool
Use `tools/task_manager.py` to programmatically manage tasks. This ensures consistency and allows for automated auditing.

## Automated Auditing
Run the audit frequently:
`python3 tools/task_manager.py audit`

## Reporting Broken Tasks
If a task fails unexpectedly:
1.  Run with `-v` or check `stderr`.
2.  Update the task definition in `.vscode/tasks.json` using the standards above.
3.  Notify the next agent cycle via `state.json` or `CHRONOS-FORGE-PLAN.md`.
