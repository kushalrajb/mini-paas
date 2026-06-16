from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import time
import subprocess
import os
import shutil
import sqlite3

# Import our custom modules
import database 
import observability 

app = FastAPI(title="Mini PaaS Control Plane")

# Point FastAPI to the templates directory for our UI dashboard
templates = Jinja2Templates(directory="templates")

# ==========================================
# DATA MODELS
# ==========================================
class DeployRequest(BaseModel):
    repo_url: str
    app_name: str
    replicas: int = 1

class HeartbeatPayload(BaseModel):
    worker_id: str
    status: str
    metrics: Dict[str, Any]

# ==========================================
# BACKGROUND WORKERS & ENGINE PRIMITIVES
# ==========================================
def build_and_isolate(repo_url: str, app_name: str, target_dir: str, worker_id: str):
    """Background engine task that processes git deployments and isolates processes."""
    start_time = time.time()
    try:
        # Clone target git repository into local application space
        subprocess.run(["git", "clone", repo_url, target_dir], check=True)
        container_script = "/var/paas/scripts/run_isolated.sh"
        
        # Execute the true kernel isolation script using custom cgroups/namespaces
        if os.path.exists(container_script):
            subprocess.run(["sudo", container_script, target_dir, app_name], check=True)
            
            # Update app status in storage
            conn = sqlite3.connect("/var/paas/state.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE containers SET status='RUNNING' WHERE app_name=? AND worker_id=?", (app_name, worker_id))
            conn.commit()
            conn.close()

    except subprocess.CalledProcessError:
        # Fallback and clean directories on container runtime failure
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
            
        conn = sqlite3.connect("/var/paas/state.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE containers SET status='FAILED' WHERE app_name=? AND worker_id=?", (app_name, worker_id))
        conn.commit()
        conn.close()
            
    # Record complete pipeline duration to the Prometheus metric histogram
    duration = time.time() - start_time
    observability.DEPLOYMENT_LATENCY.observe(duration)

# ==========================================
# AUTO-HEALER DAEMON
# ==========================================
async def auto_healer():
    """Continuously monitors cluster nodes and reschedules orphaned apps."""
    while True:
        dead_workers = database.get_dead_workers()
        for worker_id in dead_workers:
            print(f"🚨 CRITICAL: Worker {worker_id} missed heartbeats! Marking as DEAD.")
            
            # Increment Prometheus counter tracking total cluster failovers
            observability.FAILOVER_EVENTS.inc()
            
            # Pull apps off the offline worker node
            apps_to_rescue = database.get_and_orphan_apps(worker_id)
            for app_name, repo_url in apps_to_rescue:
                print(f"🔄 SELF-HEALING: Rescheduling {app_name} onto a healthy node...")
                fallback_node = "fallback-worker-01"
                database.register_app(app_name, repo_url, fallback_node)
                
                target_dir = f"/var/paas/apps/{app_name}"
                # Boot workload on fallback infrastructure
                build_and_isolate(repo_url, app_name, target_dir, fallback_node)
                
        await asyncio.sleep(15)

# ==========================================
# STARTUP & CORE PLATFORM ROUTES
# ==========================================
@app.on_event("startup")
async def startup_event():
    # Initialize database state tables
    database.init_db()
    # Spin up the asynchronous auto-healer daemon loop
    asyncio.create_task(auto_healer())

@app.get("/health")
async def health_check():
    return {"status": "Control Plane is alive"}

@app.get("/metrics")
async def metrics():
    """Exposes real-time plain-text metrics for Prometheus scraping."""
    return observability.get_metrics()

@app.post("/deploy")
async def deploy_app(request: DeployRequest, background_tasks: BackgroundTasks):
    """Orchestrates applications across multiple replica nodes."""
    safe_app_name = "".join(c for c in request.app_name if c.isalnum() or c in ("-", "_")).strip()
    target_dir = f"/var/paas/apps/{safe_app_name}"
    
    assigned_nodes = []
    # Distribute workloads evenly across node topology based on requested replicas
    for i in range(request.replicas):
        assigned_worker = f"worker-{i+1}"
        database.register_app(safe_app_name, request.repo_url, assigned_worker)
        assigned_nodes.append(assigned_worker)
        
        # Dispatch background isolation tasks
        background_tasks.add_task(build_and_isolate, request.repo_url, safe_app_name, target_dir, assigned_worker)

    return {
        "status": "success",
        "message": f"Successfully distributed {request.replicas} replicas of {safe_app_name} across the cluster.",
        "nodes": assigned_nodes
    }

@app.post("/api/internal/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload):
    """Processes worker metric heartbeats and propagates values to Gauges."""
    cpu = payload.metrics.get("cpu_load", 0.0)
    ram = payload.metrics.get("ram_usage_percent", 0.0)
    
    database.update_worker_metrics(payload.worker_id, cpu, ram, payload.status)
    
    # Live update of Prometheus gauges per node identity
    observability.NODE_CPU.labels(worker_id=payload.worker_id).set(cpu)
    observability.CONTAINER_RAM.labels(worker_id=payload.worker_id).set(ram)
    
    return {"status": "ACK", "message": "Heartbeat processed."}

# ==========================================
# DASHBOARD UI ROUTE
# ==========================================
@app.get("/dashboard")
async def render_dashboard(request: Request):
    """Renders the cluster administration and monitoring user interface."""
    conn = sqlite3.connect("/var/paas/state.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM workers")
        nodes = cursor.fetchall()
        
        cursor.execute("SELECT * FROM containers")
        apps = cursor.fetchall()
    except sqlite3.OperationalError:
        nodes = []
        apps = []
        
    conn.close()
    
    # Return HTML template dynamically parsed through Jinja2 context mapping
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "nodes": nodes, 
        "apps": apps
    })
