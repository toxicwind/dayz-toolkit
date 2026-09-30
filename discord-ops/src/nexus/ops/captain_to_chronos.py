#!/usr/bin/env python3
"""
CHRONOS FORGE :: CAPTAIN TO CHRONOS MIGRATOR (v2)
Transforms CapRover (config-captain.json) app definitions into 
hardened Chronos Stack Specifications.
"""
import json
import yaml
import os

def load_captain_config(path):
    with open(path, 'r') as f:
        return json.load(f)

def transform_app(name, app_def):
    """Converts a CapRover app definition to a Docker Compose service."""
    
    # Extract Latest Image
    versions = app_def.get("versions", [])
    if versions:
        latest_version = max(versions, key=lambda v: v.get("version", 0))
        image = latest_version.get("deployedImageName", "unknown")
    else:
        image = app_def.get("deployedImageName", "unknown")

    service = {
        "container_name": name,
        "image": image,
        "restart": "always",
        "environment": [],
        "networks": ["web_net", "internal_net"],
        "labels": [
            "traefik.enable=true",
        ]
    }

    # Handle Env Vars
    for env in app_def.get("envVars", []):
        service["environment"].append(f"{env['key']}={env['value']}")

    # Handle Ingress (Traefik Labels)
    domains = app_def.get("customDomain", [])
    if domains:
        # Filter for domains with publicDomain key
        public_domains = [d["publicDomain"] for d in domains if "publicDomain" in d]
        if public_domains:
            primary_domain = public_domains[0]
            # Use raw string for labels to avoid escaping issues
            service["labels"].append(f"traefik.http.routers.{name}.rule=Host(`{primary_domain}`)")
            service["labels"].append(f"traefik.http.services.{name}.loadbalancer.server.port={app_def.get('containerHttpPort', 80)}")

    return service

def main():
    from src.mildlyawesome.config import get_settings
    settings = get_settings()
    repo_root = str(settings.chronos_root)
    config_path = os.path.join(repo_root, "config-captain.json")
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return

    data = load_captain_config(config_path)
    apps = data.get("appDefinitions", {})

    chronos_stacks = {}
    for app_name, app_def in apps.items():
        chronos_stacks[app_name] = transform_app(app_name, app_def)

    # Output as a unified compose file
    compose = {
        "version": "3.8",
        "services": chronos_stacks,
        "networks": {
            "web_net": {"external": True},
            "internal_net": {"external": True}
        }
    }

    output_path = os.path.join(repo_root, "chronos-migration-stack.yml")
    # Clean output using yaml.dump with proper formatting
    with open(output_path, 'w') as f:
        yaml.dump(compose, f, sort_keys=False, default_flow_style=False)
    
    print(f"✅ Migrated {len(apps)} apps to {output_path}")

if __name__ == "__main__":
    main()
