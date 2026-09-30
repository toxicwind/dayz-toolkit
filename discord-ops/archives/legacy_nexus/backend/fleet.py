from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from functools import lru_cache

from .config import Settings, load_settings

log = logging.getLogger(__name__)

@dataclass
class ServiceMetadata:
    id: str
    name: str
    description: str
    platform: str
    region: str

class ServiceRegistry:
    _instance: Optional[ServiceRegistry] = None
    _services: Dict[str, Settings] = {}
    _metadata: Dict[str, ServiceMetadata] = {}

    def __init__(self):
        self._load_registry()

    @classmethod
    def get_instance(cls) -> ServiceRegistry:
        if cls._instance is None:
            cls._instance = ServiceRegistry()
        return cls._instance

    def _load_registry(self):
        """Scans config/teams/*.yaml and registers available services."""
        repo_root = Path(__file__).parent.parent
        teams_dir = repo_root / "config" / "teams"
        
        if not teams_dir.exists():
            log.warning(f"Teams directory not found: {teams_dir}")
            return

        log.info(f"Scanning for services in {teams_dir}...")
        
        for config_file in teams_dir.glob("*.yaml"):
            service_id = config_file.stem
            try:
                # We load the full settings to validate and extract metadata
                # We force 'prod' env by default for registry scanning to see "real" names
                settings = load_settings(service=service_id)
                self._services[service_id] = settings
                
                # Extract metadata
                self._metadata[service_id] = ServiceMetadata(
                    id=service_id,
                    name=settings.server_name or service_id.title(),
                    description=f"Managed Fleet: {settings.server_name}",
                    platform=settings.platform,
                    region="Global" # Placeholder until region is in config
                )
                log.info(f"✅ Registered Service: {service_id} ({settings.server_name})")
            except Exception as e:
                log.error(f"❌ Failed to register service {service_id}: {e}")

    @lru_cache(maxsize=32)
    def get_service(self, service_id: str) -> Optional[Settings]:
        """Returns the settings context for a specific service ID."""
        return self._services.get(service_id)

    @lru_cache(maxsize=1)
    def list_services(self) -> List[ServiceMetadata]:
        """Returns metadata for all registered services."""
        return list(self._metadata.values())

    def reload(self):
        """Force reload of the registry and clear caches."""
        self._services.clear()
        self._metadata.clear()
        self.get_service.cache_clear()
        self.list_services.cache_clear()
        self._load_registry()

def get_registry() -> ServiceRegistry:
    return ServiceRegistry.get_instance()
