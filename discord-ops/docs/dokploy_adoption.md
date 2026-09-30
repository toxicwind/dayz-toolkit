# Dokploy Adoption Plan

## Goal
Adopt **Dokploy** as the sole control plane for stack mutations, replacing Portainer.

## 1. Inventory
*   **Active Control Plane**: Dokploy (`dokploy`, port 3000).
*   **Registry**: Local (`registry`, port 5000).
*   **Ingress**: Traefik + Cloudflare.

## 2. Usage Policy
*   **Mutations**: ALL mutations must go through the CD pipeline.
*   **Portainer**: READ-ONLY. Do not use for `recreate` or `env` changes.
*   **Images**: All production images must be pulled from the local registry `localhost:5000`.

## 3. The Deploy Contract
See `deploy.contract.json` in the root. This file defines the "Source of Truth" for versions.

## 4. Pipeline (`scripts/deploy_dokploy.py`)
1.  **Build** app from source.
2.  **Tag** with git hash + timestamp.
3.  **Push** to `localhost:5000`.
4.  **Update** Dokploy/Stack to use new tag.
5.  **Verify** health.

## 5. Verification
Run `scripts/drift_check.py` to ensure running containers match the contract.
