from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import time
import subprocess
import os
import shutil

# Import our custom modules
import database 
import observability  # NEW: Our Prometheus registry

app = FastAPI(title="Mini PaaS Control Plane")

class DeployRequest(BaseModel):
    repo_url: str
    app_name: str
    replicas: int = 1

class HeartbeatPayload(BaseModel):
    worker_id: str
    status: str
    metrics: Dict[str, Any]

def build_and_isolate(repo_url: str, app_name: str, target_dir: str):
    """Background worker that measures deployment latency."""
    start_time = time.time() # START THE TIMER
    try:
        subprocess.run(["git", "clone", repo_url, target_dir], check=True)
        container_script = "/var/paas/scripts/run_isolated.sh"
        
        if os.path.exists(container_script):
            subprocess.run(["sudo", container_script, target_dir, app_name], check=True)
            database.update_app_state(app_name=app_name, status="RUNNING")
        else:
            database.update_app_state(app_name=app_name, status="CLONED_ONLY")

    except subprocess.CalledProcessError:
        database.update_app_state(app_name=app_name, status="FAILED")
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
            
    # STOP THE TIMER AND RECORD LATENCY
    duration = time.time() - start_time
    observability.DEPLOYMENT_LATENCY.observe(duration)

async def auto_healer():
    """Continuously monitors the cluster and records failover events."""
    while True:
        dead_workers = database.get_dead_workers()
        for worker_id in dead_workers:
            print(f"🚨 CRITICAL: Worker {worker_id} DEAD.")
            
            # TRIGGER THE FAILOVER METRIC
            observability.FAILOVER_EVENTS.inc()
            
            apps_to_rescue = database.get_and_orphan_apps(worker_id)
            for app_name, repo_url in apps_to_rescue:
                database.register_app(app_name, repo_url, "fallback-worker-01")
                
        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    database.init_db()
    asyncio.create_task(auto_healer())

@app.get("/health")
async def health_check():
    return {"status": "Control Plane is alive"}

# NEW: The Prometheus Scrape Endpoint!
@app.get("/metrics")
async def metrics():
    return observability.get_metrics()

@app.post("/deploy")
async def deploy_app(request: DeployRequest, background_tasks: BackgroundTasks):
    safe_app_name = "".join(c for c in request.app_name if c.isalnum() or c in ("-", "_")).strip()
    target_dir = f"/var/paas/apps/{safe_app_name}"
    
    assigned_nodes = []
    for i in range(request.replicas):
        assigned_worker = f"worker-{i+1}"
        database.register_app(safe_app_name, request.repo_url, assigned_worker)
        assigned_nodes.append(assigned_worker)
        background_tasks.add_task(build_and_isolate, request.repo_url, safe_app_name, target_dir)

    return {"status": "success", "message": "Deployment triggered.", "nodes": assigned_nodes}

@app.post("/api/internal/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload):
    cpu = payload.metrics.get("cpu_load", 0.0)
    ram = payload.metrics.get("ram_usage_percent", 0.0)
    
    database.update_worker_metrics(payload.worker_id, cpu, ram, payload.status)
    
    # NEW: UPDATE THE LIVE PROMETHEUS DASHBOARD GAUGES
    observability.NODE_CPU.labels(worker_id=payload.worker_id).set(cpu)
    observability.CONTAINER_RAM.labels(worker_id=payload.worker_id).set(ram)
    
    return {"status": "ACK", "message": "Heartbeat processed."}
