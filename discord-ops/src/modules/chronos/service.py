import asyncio
import json
import os
import subprocess
import logging
from pathlib import Path
from typing import Set, Dict, Any, List
from datetime import datetime
import time
import re

log = logging.getLogger("mildlyawesome.modules.chronos.service")

# DISABLE FLAG: Set to True to prevent VS Code settings.json overwrites
DISABLE_VSCODE_SETTINGS_WRITE = True

class ChronosService:
    @classmethod
    def _get_settings(cls):
        from src.mildlyawesome.config import get_settings
        return get_settings()

    @property
    def SETTINGS_FILE(self) -> Path:
        return self._get_settings().vscode_settings_path

    @property
    def EXTENSIONS_DIR(self) -> Path:
        return self._get_settings().vscode_extensions_dir

    @classmethod
    async def exhume_keys(cls) -> Set[str]:
        """Exhume all extension configs using ripgrep."""
        def _sync():
            try:
                # HARDENED: Use rg instead of grep
                result = subprocess.run([
                    "rg", "-rh", "--no-filename", r'"[^"]*\.[^"]*"', str(cls.EXTENSIONS_DIR),
                    "-g", "package.json"
                ], capture_output=True, text=True)
                keys = set()
                for line in result.stdout.split('\n'):
                    line = line.strip().strip('"')
                    if '.' in line and not line.startswith('//'):
                        keys.add(line)
                return keys
            except Exception as e:
                log.error(f"Exhumation failed: {e}")
                return set()

        return await asyncio.to_thread(_sync)

    @classmethod
    async def predator_query(cls, query: str, emergent_mode: bool = True) -> Dict[str, Any]:
        """Perform a multi-vector predatory query (Local RG + Emergent Search)."""
        results = {
            "local": await cls.local_audit(query),
            "emergent": None,
            "decision": "local_satisfied"
        }

        if emergent_mode and (not results["local"] or len(results["local"]) < 100):
            log.info(f"Local context insufficient for '{query}'. Escalating to Emergent Vector...")
            results["emergent"] = await cls.emergent_context_retrieval(query)
            results["decision"] = "hybrid_expansion"

        return results

    @classmethod
    async def emergent_context_retrieval(cls, query: str) -> str:
        """Stub for external context retrieval (Web/Docs)."""
        # In a full emergent implementation, this would call an LLM or Web Search API
        # For now, we simulate a deep-grep across the entire dev environment
        def _sync():
            dev_root = cls._get_settings().chronos_root.parent
            cmd = ["rg", "--no-filename", "-M", "200", f'"{query}"', str(dev_root), "-g", "*.py", "-g", "*.md"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.stdout[:2000] # Cap at 2k chars

        return await asyncio.to_thread(_sync)

    @classmethod
    async def local_audit(cls, query: str) -> str:
        """Execute local audit via ripgrep."""
        def _sync():
            # HARDENED: Use rg instead of grep shell pipe
            cmd = ["rg", "--no-filename", f'"{query}.*"', str(cls.EXTENSIONS_DIR), "-g", "*.json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            # Return first 20 lines
            return "\n".join(result.stdout.splitlines()[:20])

        return await asyncio.to_thread(_sync)
    @classmethod
    async def load_settings(cls) -> Dict[str, Any]:
        """Load VS Code settings."""
        def _sync():
            if cls.SETTINGS_FILE.exists():
                try:
                    with open(cls.SETTINGS_FILE, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    log.error(f"Failed to load settings: {e}")
            return {}

        return await asyncio.to_thread(_sync)

    @classmethod
    async def save_settings(cls, settings: Dict[str, Any]):
        """Save VS Code settings."""
        if DISABLE_VSCODE_SETTINGS_WRITE:
            log.info("VS Code settings write DISABLED (DISABLE_VSCODE_SETTINGS_WRITE=True). Skipping save.")
            return

        def _sync():
            try:
                with open(cls.SETTINGS_FILE, 'w') as f:
                    json.dump(settings, f, indent=4)
            except Exception as e:
                log.error(f"Failed to save settings: {e}")

        await asyncio.to_thread(_sync)

    @classmethod
    def merge_predatory_defaults(cls, current: Dict[str, Any], exhumed: Set[str]) -> Dict[str, Any]:
        """Merge exhumed keys with predatory defaults."""
        predatory_defaults = {
            "true": ["enabled", "auto", "on", "always"],
            "false": ["disabled", "off", "never"],
            "0": ["delay", "timeout"],
            "1000000": ["max", "limit", "capacity"]
        }

        for key in exhumed:
            if key not in current:
                for default_val, keywords in predatory_defaults.items():
                    if any(kw in key.lower() for kw in keywords):
                        current[key] = json.loads(default_val) if default_val in ["true", "false"] else int(default_val)
                        break
                else:
                    current[key] = True
        return current

    @classmethod
    async def cross_reference_usage(cls, keys: Set[str]) -> Dict[str, Dict[str, Any]]:
        """Cross-reference exhumed keys with actual usage in the codebase."""
        results = {}
        project_root = cls._get_settings().chronos_root / "src"

        def _sync():
            for key in keys:
                # Search for usage in .py files
                rg_cmd = ["rg", "-l", key, str(project_root), "-g", "*.py"]
                res = subprocess.run(rg_cmd, capture_output=True, text=True)
                files = res.stdout.splitlines()

                # Search for direct string matches (non-dot version) to catch legacy usage
                short_key = key.split('.')[-1]
                rg_cmd_short = ["rg", "-l", f"\"{short_key}\"", str(project_root), "-g", "*.py"]
                res_short = subprocess.run(rg_cmd_short, capture_output=True, text=True)
                short_files = res_short.stdout.splitlines()

                results[key] = {
                    "occurrences": len(files),
                    "files": files[:5],
                    "legacy_shadows": list(set(short_files) - set(files))[:5],
                    "status": "active" if files else "ghost"
                }
            return results

        return await asyncio.to_thread(_sync)

    @classmethod
    async def blob_scavenge(cls, terms: List[str]) -> List[Dict[str, Any]]:
        """Scavenge dangling git blobs for lost code related to terms."""
        repo_root = cls._get_settings().chronos_root

        def _sync():
            try:
                # 1. Find dangling blobs
                fsck_cmd = ["git", "fsck", "--unreachable", "--dangling"]
                res_fsck = subprocess.run(fsck_cmd, cwd=repo_root, capture_output=True, text=True)
                blobs = re.findall(r"unreachable blob (\w+)", res_fsck.stdout)

                hits = []
                for blob in blobs[:200]: # Limit scan for performance
                    cat_cmd = ["git", "cat-file", "-p", blob]
                    res_cat = subprocess.run(cat_cmd, cwd=repo_root, capture_output=True, text=True)
                    content = res_cat.stdout

                    for term in terms:
                        if term in content:
                            hits.append({
                                "blob": blob,
                                "term": term,
                                "snippet": content[:200].replace('\n', ' ')
                            })
                            break
                return hits
            except Exception as e:
                log.error(f"Blob scavenge failed: {e}")
                return []

        return await asyncio.to_thread(_sync)

    @classmethod
    async def predictive_patch(cls, component: str) -> Dict[str, Any]:
        """Propose a predictive patch based on exhumation insights and component context."""
        exhumed = await cls.exhume_keys()
        emap = await cls.entropy_scan()

        # Simple heuristic: find keys related to component and hotspots
        relevant_keys = [k for k in exhumed if component.lower() in k.lower()]
        hotspots = [k for k, v in emap["map"].items() if component.lower() in k.lower() and v["entropy"] > 5.0]

        proposal = {
            "target_component": component,
            "hotspots_identified": hotspots,
            "relevant_config_keys": relevant_keys,
            "suggested_action": "Harden configuration boundaries and inject exhumed defaults." if relevant_keys else "General entropy reduction."
        }

        return proposal

    @classmethod
    async def sink_insights(cls, insights: Dict[str, Any]):
        """Sink exhumation insights to the Hub Registry for multi-agent awareness."""
        settings = cls._get_settings()
        registry_path = settings.chronos_root.parent / "chronos/.chronos/hub/registry.json"
        repo_hash = "918836acf037"

        def _sync():
            if not registry_path.exists():
                return
            try:
                with open(registry_path, 'r+') as f:
                    data = json.load(f)
                    repo_data = data.get("repos", {}).get(repo_hash, {})
                    repo_data["chronos_meta"] = {
                        "last_audit": datetime.now().isoformat(),
                        "insights": insights,
                        "v": 2
                    }
                    data["repos"][repo_hash] = repo_data
                    f.seek(0)
                    json.dump(data, f, indent=2)
                    f.truncate()
                log.info(f"Insights sunk to Hub Registry for {repo_hash}")
            except Exception as e:
                log.error(f"Failed to sink insights: {e}")

        await asyncio.to_thread(_sync)

    @classmethod
    async def entropy_scan(cls) -> Dict[str, Any]:
        """Map system entropy by combining file volatility, exhumation hits, and process metrics."""
        project_root = cls._get_settings().chronos_root / "src"

        def _sync():
            # Get process list for metrics integration
            ps_cmd = ["ps", "-eo", "pcpu,pmem,args", "--sort=-pcpu", "--no-headers"]
            res_ps = subprocess.run(ps_cmd, capture_output=True, text=True)
            proc_lines = res_ps.stdout.splitlines()[:10]

            # Find command to gather mod times
            find_cmd = ["find", str(project_root), "-type", "f", "-printf", "%T@ %p\n"]
            res = subprocess.run(find_cmd, capture_output=True, text=True)
            files = []
            for line in res.stdout.splitlines():
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    files.append((float(parts[0]), parts[1]))

            files.sort(reverse=True)
            hot_files = files[:20]

            entropy_map = {}
            total_hits = 0
            for ts, path in hot_files:
                rg_cmd = ["rg", "-c", r"settings\.|config\[", path]
                res_hits = subprocess.run(rg_cmd, capture_output=True, text=True)
                hits = int(res_hits.stdout.strip()) if res_hits.stdout.strip().isdigit() else 0
                total_hits += hits

                rel_path = Path(path).relative_to(project_root)
                # Combine volatility with config density and simulated performance pressure
                volatility = 1 / (time.time() - ts + 1)
                entropy_score = hits * volatility * 1000

                entropy_map[str(rel_path)] = {
                    "last_modified": datetime.fromtimestamp(ts).isoformat(),
                    "config_density": hits,
                    "entropy": round(entropy_score, 2)
                }

            # Global insights
            insights = {
                "top_hotspot": max(entropy_map.items(), key=lambda x: x[1]["entropy"])[0] if entropy_map else None,
                "total_config_density": total_hits,
                "system_load_sample": proc_lines[0] if proc_lines else "N/A"
            }

            return {"map": entropy_map, "insights": insights}

        return await asyncio.to_thread(_sync)

    @classmethod
    async def run_chronos_audit(cls):
        """High-level audit workflow."""
        exhumed = await cls.exhume_keys()
        usage = await cls.cross_reference_usage(exhumed)
        current = await cls.load_settings()
        updated = cls.merge_predatory_defaults(current, exhumed)

        # Identity ghosts vs used
        ghosts = [k for k, v in usage.items() if v["status"] == "ghost"]

        await cls.save_settings(updated)

        results = {
            "total_keys": len(updated),
            "exhumed_count": len(exhumed),
            "usage_mapped": len(usage),
            "ghosts": len(ghosts)
        }

        # Sink to Hub Registry
        await cls.sink_insights(results)

        return results
