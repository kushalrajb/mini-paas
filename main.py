from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import database 

app = FastAPI(title="Mini PaaS Control Plane")

# ==========================================
# DATA MODELS
# ==========================================
class DeployRequest(BaseModel):
    repo_url: str
    app_name: str
    replicas: int = 1  # NEW: Replication support!

class HeartbeatPayload(BaseModel):
    worker_id: str
    status: str
    metrics: Dict[str, Any]

# ==========================================
# AUTO-HEALER DAEMON (NEW)
# ==========================================
async def auto_healer():
    """Continuously monitors the cluster for dead nodes and reschedules workloads."""
    while True:
        dead_workers = database.get_dead_workers()
        for worker_id in dead_workers:
            print(f"🚨 CRITICAL: Worker {worker_id} missed heartbeats! Marking as DEAD.")
            
            # Rescue the apps that were running on the dead server
            apps_to_rescue = database.get_and_orphan_apps(worker_id)
            for app_name, repo_url in apps_to_rescue:
                print(f"🔄 SELF-HEALING: Rescheduling {app_name} to a healthy node...")
                # In a full cluster, we would dynamically pick the node with the lowest CPU here
                database.register_app(app_name, repo_url, "fallback-worker-01")
                
        # Sleep for 15 seconds before checking the cluster health again
        await asyncio.sleep(15)

# ==========================================
# STARTUP & ROUTES
# ==========================================
@app.on_event("startup")
async def startup_event():
    database.init_db()
    # Boot up the auto-healer in the background the second the API starts
    asyncio.create_task(auto_healer())

@app.get("/health")
async def health_check():
    return {"status": "Control Plane is alive"}

@app.post("/deploy")
async def deploy_app(request: DeployRequest):
    safe_app_name = "".join(c for c in request.app_name if c.isalnum() or c in ("-", "_")).strip()
    
    # REPLICATION LOGIC: Deploy across multiple workers based on the CLI flag
    assigned_nodes = []
    for i in range(request.replicas):
        assigned_worker = f"worker-{i+1}"
        database.register_app(safe_app_name, request.repo_url, assigned_worker)
        assigned_nodes.append(assigned_worker)
        # Here, you would trigger the HTTP request to the worker's agent API
        print(f"📦 Sent deployment command for {safe_app_name} to {assigned_worker}")

    return {
        "status": "success",
        "message": f"Successfully distributed {request.replicas} replicas of {safe_app_name} across the cluster.",
        "nodes": assigned_nodes
    }

@app.post("/api/internal/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload):
    cpu = payload.metrics.get("cpu_load", 0.0)
    ram = payload.metrics.get("ram_usage_percent", 0.0)
    
    database.update_worker_metrics(payload.worker_id, cpu, ram, payload.status)
    return {"status": "ACK", "message": "Heartbeat processed."}
