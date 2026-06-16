from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import os
import subprocess
import shutil

# Import our local database manager
import database 

app = FastAPI(title="Mini PaaS Control Plane")

# ==========================================
# DATA MODELS
# ==========================================
class DeployRequest(BaseModel):
    repo_url: str
    app_name: str

class HeartbeatPayload(BaseModel):
    worker_id: str
    status: str
    metrics: Dict[str, Any]

# ==========================================
# STARTUP & BACKGROUND TASKS
# ==========================================
@app.on_event("startup")
def startup_event():
    """Initializes SQLite tables when the API server boots up."""
    database.init_db()

def build_and_isolate(repo_url: str, app_name: str, target_dir: str):
    """
    Background worker that clones the repo, runs the isolation script, 
    and updates the database with the final status.
    """
    try:
        # 1. Clone the user's GitHub repository
        print(f"Cloning {repo_url} into {target_dir}...")
        subprocess.run(["git", "clone", repo_url, target_dir], check=True)
        
        # 2. Path to your custom container runtime script (built previously)
        container_script = "/var/paas/scripts/run_isolated.sh"
        
        if os.path.exists(container_script):
            print(f"Spawning custom Linux container for {app_name}...")
            # Run your native container runtime
            subprocess.run(["sudo", container_script, target_dir, app_name], check=True)
            
            # Update DB: Success!
            database.update_app_state(app_name=app_name, status="RUNNING")
        else:
            print("Container runtime script missing. Code cloned, waiting for isolation layer.")
            database.update_app_state(app_name=app_name, status="CLONED_ONLY")

    except subprocess.CalledProcessError as e:
        print(f"Deployment failed for {app_name}: {str(e)}")
        # Update DB: Mark as failed so we can see it crashed
        database.update_app_state(app_name=app_name, status="FAILED")
        
        # Cleanup the broken directory so the user can try again
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

# ==========================================
# API ROUTES
# ==========================================
@app.get("/health")
async def health_check():
    """External endpoint to check if the Control Plane is online."""
    return {"status": "Control Plane is alive and automating"}

@app.post("/deploy")
async def deploy_app(request: DeployRequest, background_tasks: BackgroundTasks):
    """Endpoint for developers to push new code to the cluster."""
    # Sanitize app name to prevent directory traversal attacks
    safe_app_name = "".join(c for c in request.app_name if c.isalnum() or c in ("-", "_")).strip()
    target_dir = f"/var/paas/apps/{safe_app_name}"
    
    if os.path.exists(target_dir):
        raise HTTPException(status_code=400, detail="App name already exists or is deploying.")
    
    # Create the storage directory structures on the host
    os.makedirs("/var/paas/apps", exist_ok=True)
    
    # Log the app into the database before we start building
    try:
        database.register_app(safe_app_name, request.repo_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Database registration failed. App might already exist.")
    
    # Trigger the heavy lifting in the background so the API stays lightning fast
    background_tasks.add_task(build_and_isolate, request.repo_url, safe_app_name, target_dir)
    
    return {
        "status": "queued",
        "message": f"Deployment pipeline initiated for {safe_app_name}.",
        "monitoring_path": f"/apps/{safe_app_name}/status"
    }

@app.post("/api/internal/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload):
    """
    The central REST API endpoint for Health Checks & Metrics Collection.
    Workers hit this endpoint every 10 seconds.
    """
    cpu = payload.metrics.get("cpu_load", 0.0)
    ram = payload.metrics.get("ram_usage_percent", 0.0)
    
    # Log the health check into the Master's state management
    database.update_worker_metrics(
        worker_id=payload.worker_id,
        cpu=cpu,
        ram=ram,
        status=payload.status
    )
    
    # If CPU is over 90%, trigger an alert (this is where auto-scaling logic would go)
    if cpu > 90.0:
        print(f"⚠️ ALERT: Worker {payload.worker_id} is under heavy load!")
        
    return {"status": "ACK", "message": "Heartbeat and metrics logged."}
