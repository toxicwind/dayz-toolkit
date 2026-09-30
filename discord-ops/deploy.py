#!/usr/bin/env python3
"""
Centralized deployment orchestration for DayZ Discord Ops Bot.
Consolidates all deployment logic - use this instead of scattered commands.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

class DeploymentManager:
    """Handles all deployment operations for the bot."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.root = workspace_root or Path(__file__).parent
        self.docker_compose = self.root / "docker-compose.yml"
        self.env_file = self.root / ".env"
        self.bin_dir = self.root / "bin"

    def validate_environment(self) -> bool:
        """Verify all required environment variables and files exist."""
        # Load from .env if exists
        if self.env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(self.env_file)
            except ImportError:
                print("⚠️  python-dotenv not installed, skipping .env file")

        # Basic validation
        if not self.docker_compose.exists():
            print(f"❌ docker-compose.yml not found at {self.docker_compose}")
            return False

        return True

    def deploy_docker(self, rebuild: bool = False) -> int:
        """Deploy via Docker Compose."""
        cmd = ["docker", "compose", "up", "-d"]
        if rebuild:
            cmd.insert(3, "--build")

        print(f"🚀 Deploying with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.root)

        if result.returncode == 0:
            print("✅ Deployment successful")
            print("📊 View logs: docker compose logs -f")
        else:
            print("❌ Deployment failed")

        return result.returncode

    def deploy_dedi_ops(self, target: Optional[str] = None) -> int:
        """Deploy using the dedi-ops shell script."""
        deploy_script = self.bin_dir / "deploy_dedi_ops.sh"

        if not deploy_script.exists():
            print(f"❌ deploy_dedi_ops.sh not found at {deploy_script}")
            return 1

        env = os.environ.copy()
        if target:
            env["DEPLOY_ROOT"] = target

        print(f"🚀 Running dedi-ops deployment to {target or '/home/toxic/dedi-ops'}")
        result = subprocess.run([str(deploy_script)], env=env, cwd=self.root)

        if result.returncode == 0:
            print("✅ Dedi-ops deployment successful")
        else:
            print("❌ Dedi-ops deployment failed")

        return result.returncode

    def deploy_ftp(self, dry_run: bool = False) -> int:
        """Deploy via smart FTP (hash-diff)."""
        ftp_script = self.root / "src" / "mildlyawesome" / "scripts" / "smart_deploy_ftp.py"

        if not ftp_script.exists():
            print(f"❌ smart_deploy_ftp.py not found at {ftp_script}")
            return 1

        cmd = [sys.executable, str(ftp_script)]
        if dry_run:
            cmd.append("--dry-run")

        print(f"🚀 Starting FTP deployment (dry_run={dry_run})")
        return subprocess.run(cmd, cwd=self.root).returncode

    def deploy_local(self) -> int:
        """Deploy locally (direct Python execution)."""
        main_py = self.root / "src" / "mildlyawesome" / "main.py"

        if not main_py.exists():
            print(f"❌ main.py not found at {main_py}")
            return 1

        print(f"🚀 Starting local deployment: {main_py}")
        return subprocess.run([sys.executable, str(main_py)], cwd=self.root).returncode

    def stop(self) -> int:
        """Stop running deployment."""
        print("🛑 Stopping deployment...")
        result = subprocess.run(["docker", "compose", "down"], cwd=self.root)

        if result.returncode == 0:
            print("✅ Stopped successfully")
        else:
            print("❌ Stop failed")

        return result.returncode

    def logs(self, follow: bool = True, service: Optional[str] = None) -> int:
        """Show deployment logs."""
        cmd = ["docker", "compose", "logs"]
        if follow:
            cmd.append("-f")
        if service:
            cmd.append(service)

        return subprocess.run(cmd, cwd=self.root).returncode

    def status(self) -> int:
        """Show deployment status."""
        return subprocess.run(["docker", "compose", "ps"], cwd=self.root).returncode

def main():
    """CLI entrypoint for deployment operations."""
    import argparse

    parser = argparse.ArgumentParser(
        description="DayZ Discord Ops Deployment Manager",
        epilog="""Examples:
  python deploy.py start --rebuild         # Build and deploy via Docker
  python deploy.py dedi-ops                # Deploy to dedi-ops directory
  python deploy.py ftp --dry-run           # Test FTP deployment
  python deploy.py local                   # Run locally
  python deploy.py logs                    # View logs
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "local", "logs", "status", "dedi-ops", "ftp"],
        help="Deployment action to perform"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild Docker images before deploying"
    )
    parser.add_argument(
        "--no-follow",
        action="store_true",
        help="Don't follow logs (for 'logs' action)"
    )
    parser.add_argument(
        "--service",
        type=str,
        help="Specific service to show logs for"
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Target directory for dedi-ops deployment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (for FTP deployment)"
    )

    args = parser.parse_args()
    manager = DeploymentManager()

    # Validate environment for most actions
    if args.action not in ["stop", "status", "logs"]:
        if not manager.validate_environment():
            print("⚠️  Validation failed, but continuing anyway...")

    if args.action == "start":
        sys.exit(manager.deploy_docker(rebuild=args.rebuild))
    elif args.action == "stop":
        sys.exit(manager.stop())
    elif args.action == "restart":
        manager.stop()
        sys.exit(manager.deploy_docker(rebuild=args.rebuild))
    elif args.action == "local":
        sys.exit(manager.deploy_local())
    elif args.action == "logs":
        sys.exit(manager.logs(follow=not args.no_follow, service=args.service))
    elif args.action == "status":
        sys.exit(manager.status())
    elif args.action == "dedi-ops":
        sys.exit(manager.deploy_dedi_ops(target=args.target))
    elif args.action == "ftp":
        sys.exit(manager.deploy_ftp(dry_run=args.dry_run))

if __name__ == "__main__":
    main()
