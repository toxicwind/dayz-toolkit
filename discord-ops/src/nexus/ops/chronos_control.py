#!/usr/bin/env python3
"""
CHRONOS FORGE :: CONTROL PLANE CLI
Orchestrates deployments across Chronos Dedi-Agents.
"""
import httpx
import yaml
import sys
import os
import argparse

def deploy_stack(agent_url, stack_path):
    """Pushes a compose stack to the remote agent."""
    if not os.path.exists(stack_path):
        print(f"Error: Stack file {stack_path} not found.")
        return

    with open(stack_path, 'r') as f:
        stack_content = f.read()

    payload = {
        "action": "deploy_stack",
        "stack_yaml": stack_content
    }

    print(f"🚀 Deploying stack {stack_path} to {agent_url}...")
    try:
        response = httpx.post(f"{agent_url}/docker", json=payload, timeout=60.0)
        response.raise_for_status()
        result = response.json()
        
        print("\n--- DEPLOYMENT RESULT ---")
        print(f"Exit Code: {result.get('exit_code')}")
        if result.get('stdout'):
            print(f"STDOUT:\n{result['stdout']}")
        if result.get('stderr'):
            print(f"STDERR:\n{result['stderr']}")
        
        if result.get('exit_code') == 0:
            print("\n✅ Deployment Successful.")
        else:
            print("\n❌ Deployment Failed.")
            
    except Exception as e:
        print(f"Error communicating with agent: {e}")

def main():
    parser = argparse.ArgumentParser(description="Chronos Control Plane CLI")
    parser.add_argument("action", choices=["deploy"], help="Action to perform")
    parser.add_argument("--agent", default="http://agent.mildlyawesome.com", help="Agent URL")
    parser.add_argument("--stack", required=True, help="Path to the compose stack YAML")

    args = parser.parse_args()

    if args.action == "deploy":
        deploy_stack(args.agent, args.stack)

if __name__ == "__main__":
    main()
