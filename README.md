☁️ KushalCloud — Native Linux Container Platform

A lightweight, distributed Platform-as-a-Service (PaaS) built entirely from scratch.

KushalCloud is not a wrapper around Docker or Kubernetes. It is a custom cloud orchestrator that directly leverages native Linux kernel primitives—Namespaces, Cgroups, Chroot, and Virtual Ethernet (Veth) bridging—to isolate, execute, scale, and manage workloads across distributed worker nodes.

This project was built to deeply understand how modern cloud platforms such as Kubernetes, Docker Swarm, and Heroku work under the hood.

⸻

🎯 Problem Statement

Modern developers heavily rely on tools like Docker, Kubernetes, and Heroku.

While powerful, these abstractions often hide the fundamental operating system mechanics behind:

* Process isolation
* Resource control
* Namespace virtualization
* Network overlays
* Cluster orchestration
* Self-healing distributed systems

Goal

Build a Kubernetes-style orchestrator completely from scratch to gain deep understanding of:

* Linux containerization internals
* Distributed systems architecture
* Scheduler design
* Cluster networking
* Self-healing infrastructure
* Hardware telemetry collection

⸻

🏗️ Architecture Diagram

graph TD
    subgraph Control Plane
        API[FastAPI Master Node]
        DB[(SQLite State/Metrics)]
        Healer[Auto-Healer Daemon]
        UI[Jinja2 Dashboard]
        Metrics[Prometheus /metrics]
    end
    subgraph Developer
        CLI[kushalcloud CLI]
    end
    subgraph Worker Node Cluster
        W1[Worker 1: run_isolated.sh]
        W2[Worker 2: run_isolated.sh]
        Veth[veth bridge networking]
        Cgroups[cgroup limits]
    end
    subgraph Networking
        NGINX[Dynamic NGINX Load Balancer]
        Internet((External Traffic))
    end
    CLI --> API
    API <--> DB
    API --> NGINX
    API --> W1
    API --> W2
    Healer --> DB
    W1 --> API
    W2 --> API
    W1 --> Cgroups
    W1 --> Veth
    NGINX --> Veth
    Internet --> NGINX

⸻

🚀 Feature Checklist

✅ Kernel-Level Isolation

* unshare
* chroot
* PID namespace isolation
* UTS namespace isolation
* Mount namespace isolation
* IPC namespace isolation

✅ Resource Quotas

* 256 MB RAM max per container
* 50% CPU max per container
* Managed via cgroups

✅ Distributed Replication

--replicas 3

✅ Self-Healing Automation

* Detect dead nodes
* Reschedule orphaned apps automatically

✅ Veth Bridge Networking
Custom subnet:

10.0.1.0/24

Mapped into NGINX reverse proxy pool.

✅ Persistent Volumes
Uses Linux bind mounts to preserve data during crashes.

✅ Hardware Telemetry
Prometheus-compatible metrics exporter.

✅ Live Dashboard
Shows:

* cluster health
* RAM usage
* CPU usage
* active workloads

⸻

⚙️ How It Works

1. Developer Deploys Application

python cli.py deploy <repo_url> my-app --replicas 3

2. Master Control Plane Receives Request

The master node:

* validates deployment
* stores state
* calculates placement
* updates cluster

3. Scheduler Selects Workers

Scheduling based on:

* free RAM
* CPU availability
* worker health
* workload density

4. Workers Launch Containers

Each worker uses:

* namespaces
* chroot
* cgroups
* veth networking

Execution handled by:

scripts/run_isolated.sh

5. Load Balancer Updates

upstream myapp {
    server worker1:8080;
    server worker2:8080;
    server worker3:8080;
}

Traffic uses round-robin balancing.

⸻

❤️ Health Monitoring

Workers continuously send heartbeats.

Example:

{
  "worker": "worker-1",
  "cpu": 38,
  "memory": 57,
  "alive": true
}

Tracked metrics:

* CPU
* Memory
* Disk
* Container count
* Health state

⸻

🩹 Auto-Healing

Background daemon watches cluster state.

Before failure:

worker1 -> appA
worker2 -> appB

Worker1 crashes.

Auto-healer:

* detects missed heartbeat
* marks node unhealthy
* removes workloads
* reschedules apps

After healing:

worker2 -> appA + appB

Provides:

* self-healing
* fault tolerance
* high availability

⸻

📦 Persistent Storage

Applications can attach persistent volumes.

Supported:

* volume creation
* secure mounting
* restart persistence
* workload isolation

Use cases:

* databases
* logs
* uploaded files
* cache

⸻

💻 How to Run It

Prerequisites

Must run on Linux (Ubuntu/Debian recommended).

Reason:
KushalCloud directly uses:

* Linux cgroups
* Linux namespaces
* host networking
* filesystem mounts

⸻

Step 1: Clone & Install

git clone https://github.com/YOUR_USERNAME/mini-paas.git
cd mini-paas
pip install -r requirements.txt

⸻

Step 2: Prepare Host

sudo mkdir -p /var/paas/apps
sudo mkdir -p /var/paas/volumes
sudo mkdir -p /var/paas/scripts
sudo cp scripts/run_isolated.sh /var/paas/scripts/
sudo chmod +x /var/paas/scripts/run_isolated.sh
sudo chown -R $USER:$USER /var/paas

⸻

Step 3: Boot Control Plane

uvicorn main:app --host 0.0.0.0 --port 8000

This automatically:

* initializes SQLite
* starts auto-healer daemon
* exposes dashboard
* starts metrics exporter

⸻

Step 4: Use CLI

Check cluster health:

python cli.py health

Deploy sample app:

python cli.py deploy https://github.com/kushalrajb/sample-web-app my-test-app --replicas 3

⸻

Step 5: Monitor Cluster

Dashboard:

http://localhost:8000/dashboard

Metrics:

http://localhost:8000/metrics

⸻

📈 Scalability Benchmarks

Metric	10 Containers	100 Containers	500 Containers
Max RAM Usage	~2.5 GB	~25 GB	~128 GB
API Load	1 req/sec	10 req/sec	50 req/sec
Subnet IP Usage	4%	39%	Fails (>253 IPs)
Database Status	Stable	Stable	SQLite write locks

⸻

⚠️ Known Bottlenecks

1. Subnet Exhaustion

Current subnet:

10.0.1.0/24

Supports roughly 253 usable IPs.

Scaling beyond requires:

* larger subnet
* overlay networking
* multi-subnet architecture

⸻

2. SQLite Write Contention

SQLite works well for:

* small clusters
* medium clusters

Future upgrade:

* PostgreSQL
* distributed key-value store

⸻

🛠 Tech Stack

Backend

* Python
* FastAPI
* SQLite
* Jinja2

Linux Systems

* Namespaces
* Cgroups
* Chroot
* Veth Networking
* Bash

Infrastructure

* NGINX
* Prometheus
* Grafana

⸻

📂 Repository Structure

mini-paas/
│
├── scripts/
│   └── run_isolated.sh
│
├── cli.py
├── main.py
├── router.py
├── worker.py
├── database.py
├── storage.py
│
└── README.md

⸻

🔥 Why This Project Stands Out

Most cloud projects are wrappers around:

* Docker
* Kubernetes
* managed AWS services

KushalCloud is different.

This project demonstrates deep understanding of:

* Operating systems
* Linux internals
* Distributed systems
* Scheduling algorithms
* Networking
* Fault tolerance
* Platform engineering

It recreates concepts behind:

* Kubernetes
* Docker Swarm
* Heroku
* Nomad

Using first-principles systems engineering.

⸻

👨‍💻 Author

Kushal Raj B

Cloud / DevOps / Infrastructure Engineer focused on:

* Linux Internals
* Cloud Architecture
* Distributed Systems
* Platform Engineering

GitHub: github.com/kushalrajb
