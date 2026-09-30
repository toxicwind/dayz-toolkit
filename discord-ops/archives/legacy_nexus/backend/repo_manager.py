import logging
from pathlib import Path

import git
import yaml

# Use unified config
from .config import load_settings

log = logging.getLogger(__name__)


class RepoManager:
    """
    Manages external git repositories for data syncing.
    Integrates with config to find repo definitions.
    """

    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        self.repo_root = Path(__file__).resolve().parent.parent

        # Reading raw yaml is safer to avoid deeper changes to Settings dataclass for dynamic keys.
        config_path = self.repo_root / "config/global.yaml"
        if config_path.exists():
            with open(config_path) as f:
                global_conf = yaml.safe_load(f) or {}
            self.repos_config = global_conf.get("data_repos", {})
        else:
            self.repos_config = {}

    def ensure_repo(self, name: str) -> bool:
        """Ensure a named repo is cloned and up to date"""
        if name not in self.repos_config:
            log.error(f"Repo config not found for: {name}")
            return False

        conf = self.repos_config[name]
        url = conf.get("url")
        rel_path = conf.get("path")
        branch = conf.get("branch", "master")

        if not url or not rel_path:
            log.error(f"Invalid config for repo {name}: missing url or path")
            return False

        abs_path = self.repo_root / rel_path

        try:
            if not abs_path.exists():
                log.info(f"Cloning {name} from {url}...")
                git.Repo.clone_from(url, abs_path, branch=branch)
                log.info(f"Cloned {name} successfully.")
            else:
                # Check if it's a git repo
                try:
                    repo = git.Repo(abs_path)
                    log.info(f"Updating {name}...")
                    origin = repo.remotes.origin
                    origin.pull()
                    log.info(f"Updated {name}.")
                except git.exc.InvalidGitRepositoryError:
                    log.error(f"Directory {abs_path} exists but is not a git repo.")
                    return False
            return True
        except Exception as e:
            log.error(f"Failed to ensure repo {name}: {e}")
            return False

    def get_repo_path(self, name: str) -> Path | None:
        if name in self.repos_config:
            return self.repo_root / self.repos_config[name]["path"]
        return None
