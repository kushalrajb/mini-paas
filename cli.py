import argparse
import requests
import sys

API_URL = "http://127.0.0.1:8000"

def deploy(repo_url, app_name, replicas):
    print(f"🚀 Pushing '{app_name}' ({replicas} replicas) to the KushalCloud control plane...")
    payload = {"repo_url": repo_url, "app_name": app_name, "replicas": replicas}
    
    try:
        response = requests.post(f"{API_URL}/deploy", json=payload)
        data = response.json()
        
        if response.status_code == 200:
            print(f"✅ Success: {data.get('message')}")
        else:
            print(f"❌ Deployment Rejected: {data.get('detail')}")
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Fatal Error: Could not connect to the Control Plane.\n{e}")

def health_check():
    print("🔍 Pinging Control Plane...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print(f"✅ Status: {response.json().get('status')}")
    except requests.exceptions.RequestException:
        print("❌ Offline: Control Plane unreachable.")

def main():
    parser = argparse.ArgumentParser(description="KushalCloud CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy", help="Deploy an app")
    deploy_parser.add_argument("repo_url", help="GitHub URL")
    deploy_parser.add_argument("app_name", help="Unique app name")
    # NEW: The Replicas Flag!
    deploy_parser.add_argument("--replicas", type=int, default=1, help="Number of container instances")

    subparsers.add_parser("health", help="Check API status")

    args = parser.parse_args()

    if args.command == "deploy":
        deploy(args.repo_url, args.app_name, args.replicas)
    elif args.command == "health":
        health_check()

if __name__ == "__main__":
    main()
