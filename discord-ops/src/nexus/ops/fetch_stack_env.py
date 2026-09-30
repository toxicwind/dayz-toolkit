import requests
import sys

PORTAINER_URL = "http://mildlyawesome.com:9000"
PASSWORD = "REDACTED#9!a"
STACK_NAME = "dayz-ezstreet-ops-43200"

def get_jwt():
    url = f"{PORTAINER_URL}/api/auth"
    payload = {"username": USERNAME, "password": PASSWORD}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["jwt"]
    except Exception as e:
        print(f"Auth failed: {e}")
        sys.exit(1)

def get_stack_env(jwt):
    headers = {"Authorization": f"Bearer {jwt}"}
    # List stacks to find ID
    try:
        r = requests.get(f"{PORTAINER_URL}/api/stacks", headers=headers)
        r.raise_for_status()
        stacks = r.json()
        stack = next((s for s in stacks if s["Name"] == STACK_NAME), None)
        if not stack:
            print(f"Stack {STACK_NAME} not found")
            return
        
        print(f"Found Stack ID: {stack['Id']}")
        # The stack object itself might have Env
        if "Env" in stack:
            print("Environment Variables in Stack List:")
            for e in stack["Env"]:
                print(f"{e['name']}={e['value']}")
        else:
            # Try getting specific stack details
            r2 = requests.get(f"{PORTAINER_URL}/api/stacks/{stack['Id']}", headers=headers)
            r2.raise_for_status()
            details = r2.json()
            if "Env" in details:
                print("Environment Variables in Stack Details:")
                for e in details["Env"]:
                    print(f"{e['name']}={e['value']}")
            else:
                print("No Env section found in stack details.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    jwt = get_jwt()
    get_stack_env(jwt)
