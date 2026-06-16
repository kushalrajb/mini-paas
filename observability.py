from prometheus_client import Counter, Gauge, Histogram, generate_latest
from fastapi import Response

# 1. NODE CPU (Gauge: goes up and down)
NODE_CPU = Gauge(
    'kushalcloud_node_cpu_load', 
    'CPU load per worker node', 
    ['worker_id']
)

# 2. CONTAINER RAM (Gauge: goes up and down)
CONTAINER_RAM = Gauge(
    'kushalcloud_container_ram_usage_percent', 
    'RAM usage per container', 
    ['worker_id']
)

# 3. FAILOVER EVENTS (Counter: only goes up)
FAILOVER_EVENTS = Counter(
    'kushalcloud_failover_events_total', 
    'Total number of self-healing auto-reschedules'
)

# 4. DEPLOYMENT LATENCY (Histogram: measures duration)
DEPLOYMENT_LATENCY = Histogram(
    'kushalcloud_deployment_latency_seconds', 
    'Time taken to clone, build, and isolate an app'
)

def get_metrics():
    """Generates the plain-text metrics payload for Prometheus to scrape."""
    return Response(generate_latest(), media_type="text/plain")
