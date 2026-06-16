import os
import time
import requests
import threading
import subprocess
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# The IP of your Phase 2 Control Plane
MASTER_URL = "http://10.0.0.5:8000"  
WORKER_ID = "kushal-worker-01"

app = FastAPI(title="Worker Node Agent")

class TaskPayload(BaseModel):
    repo_url: str
    app_name: str

def collect_metrics():
    """Gathers real-time hardware metrics from the Linux worker node."""
    # Read system load average (1, 5, 15 minutes)
    cpu_load = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
    
    # Read memory usage from native Linux /proc/meminfo
    total_mem, free_mem = 1, 1
    if os.path.exists('/proc/meminfo'):
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            total_mem = int(lines[0].split()[1])
            free_mem = int(lines[1].split()[1])
            
    ram_usage_percent = round(((total_mem - free_mem) / total_mem) * 100, 2)
    
    return {
        "cpu_load": cpu_load,
        "ram_usage_percent": ram_usage_percent,
        "active_containers": 0 # This would query your Phase 1 script
    }

def heartbeat_loop():
    """Runs continuously in the background, pinging the Master Node."""
    while True:
        metrics = collect_metrics()
        payload = {
            "worker_id": WORKER_ID,
            "status": "HEALTHY",
            "metrics": metrics
        }
        
        try:
            # Pulse the heartbeat to the Master Node API
            requests.post(f"{MASTER_URL}/api/internal/heartbeat", json=payload, timeout=2)
            print(f"💓 Heartbeat sent: CPU {metrics['cpu_load']} | RAM {metrics['ram_usage_percent']}%")
        except requests.exceptions.RequestException:
            print("⚠️ Master node unreachable. Retrying in 10s...")
            
        time.sleep(10)

@app.on_event("startup")
def start_agent():
    """Boot up the heartbeat thread the moment the worker turns on."""
    print(f"🚀 Starting Worker Agent: {WORKER_ID}")
    threading.Thread(target=heartbeat_loop, daemon=True).start()

@app.post("/agent/run")
def execute_work(payload: TaskPayload, background_tasks: BackgroundTasks):
    """The Master Node hits this endpoint to force the worker to deploy code."""
    print(f"📥 Received execution command for {payload.app_name}")
    
    # Here, the worker triggers the Phase 1 bash script natively
    script_path = "/var/paas/scripts/run_isolated.sh"
    target_dir = f"/var/paas/apps/{payload.app_name}"
    
    if os.path.exists(script_path):
        background_tasks.add_task(subprocess.run, ["sudo", script_path, target_dir, payload.app_name])
        return {"status": "ACK", "message": f"Worker {WORKER_ID} is spinning up {payload.app_name}"}
    else:
        return {"status": "FAIL", "message": "Phase 1 isolation engine missing on this worker."}
