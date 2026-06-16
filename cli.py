import argparse
import requests
import sys

# This points to your Control Plane (Phase 2). 
# We default to localhost for when you run this on your server.
API_URL = "http://127.0.0.1:8000"

def deploy(repo_url, app_name):
    print(f"🚀 Pushing '{app_name}' to the KushalCloud control plane...")
    payload = {"repo_url": repo_url, "app_name": app_name}
    
    try:
        response = requests.post(f"{API_URL}/deploy", json=payload)
        data = response.json()
        
        if response.status_code == 200:
            print(f"✅ Success: {data.get('message')}")
            print(f"📡 Monitor at: {data.get('monitoring_path')}")
        else:
            print(f"❌ Deployment Rejected: {data.get('detail')}")
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Fatal Error: Could not connect to the Control Plane. Is the API running?\n{e}")

def health_check():
    print("🔍 Pinging Control Plane...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print(f"✅ Status: {response.json().get('status')}")
    except requests.exceptions.RequestException:
        print("❌ Offline: The KushalCloud Control Plane is currently unreachable.")

def main():
    # Set up the command line argument parser
    parser = argparse.ArgumentParser(description="KushalCloud CLI - Manage your Mini PaaS platform.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a new application to the platform")
    deploy_parser.add_argument("repo_url", help="The GitHub URL of the application code")
    deploy_parser.add_argument("app_name", help="A unique name for your application")

    # Command: health
    subparsers.add_parser("health", help="Check if the platform API is online")

    # Parse what the user typed
    args = parser.parse_args()

    # Route to the correct function
    if args.command == "deploy":
        deploy(args.repo_url, args.app_name)
    elif args.command == "health":
        health_check()

if __name__ == "__main__":
    main()
