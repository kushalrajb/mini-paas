# ☁️ KushalCloud — Native Linux PaaS from Scratch

**Architect:** Kushal Raj B | Cloud & DevOps Engineer

---

## 📌 Project Overview

Modern cloud deployments rely heavily on managed orchestration platforms such as Kubernetes, Docker Swarm, and Heroku. While these systems abstract away infrastructure complexity, they often hide the core operating system and distributed systems concepts responsible for workload orchestration.

**KushalCloud** is a lightweight, distributed Platform-as-a-Service (PaaS) built entirely from scratch using native Linux primitives and custom orchestration logic. 

This platform **does not depend on Docker or Kubernetes**. Instead, it implements core cloud orchestration capabilities manually, including workload scheduling, process isolation, networking, replication, health monitoring, and self-healing infrastructure.

The project demonstrates deep understanding of:
* Linux internals
* Distributed systems architecture
* Cluster scheduling
* Container isolation
* Network virtualization
* Fault-tolerant infrastructure design

---

## ⚙️ Core Architecture & Mechanics

KushalCloud consists of four major subsystems:

### 1. Control Plane (FastAPI Master Node)
The control plane acts as the brain of the cluster. 

**Responsibilities include:**
* Receiving deployment requests
* Scheduling workloads across workers
* Tracking cluster state
* Monitoring health
* Triggering recovery logic
* Updating load balancer configuration

**Core components:** `main.py`, `router.py`, `database.py`

### 2. Worker Runtime (Native Linux Isolation)
Each worker node executes workloads inside isolated runtime environments using Linux kernel primitives.

**Isolation mechanisms include:**
* **Filesystem Isolation:** Uses `chroot` to restrict filesystem visibility. Each workload is jailed inside its own root filesystem and cannot access host-level directories.
* **Namespace Isolation:** Uses `unshare` to isolate PID, UTS, Mount, and IPC namespaces. This ensures workloads run in independent process trees.
* **Resource Restriction:** Uses `cgroups` to enforce hard resource limits:
  * Maximum RAM per container: 256 MB
  * Maximum CPU per container: 50%
  * *This prevents resource starvation on host nodes.*

**Execution engine:** `scripts/run_isolated.sh`

### 3. Cluster Networking (Veth + NGINX)
KushalCloud implements custom internal networking using Linux Virtual Ethernet pairs. Each workload receives an internal IP from `10.0.1.0/24`.

**Traffic flow:**
1. External client sends request
2. NGINX receives traffic
3. Request routed to internal workload IP
4. Load balanced across replicas

**Load balancing uses:** Dynamic upstream generation and round-robin routing.

### 4. Self-Healing & Recovery Engine
Worker nodes continuously send heartbeat signals containing health and telemetry data (CPU usage, Memory usage, Disk usage, Running workloads, Node availability).

**If a node stops responding:**
1. Node marked unhealthy
2. Assigned workloads removed
3. Orphaned apps rescheduled
4. Load balancer updated

**Recovery engine:** `worker.py`, Background auto-healer daemon

---

## 📂 Repository Structure

```text
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

---

## 🚀 Key Features & Execution Guide

> # ==============================================================
> # 💻 KUSHALCLOUD: FEATURES & EXECUTION WALKTHROUGH
> # ==============================================================
>
> # Prerequisites: Must run on a native Linux environment (Ubuntu/Debian) 
> # with sudo privileges. Required Linux features: cgroups, namespaces, 
> # filesystem mounts, veth networking.
>
> # --- Step 1: Clone Repository ---
> git clone https://github.com/kushalrajb/mini-paas.git
> cd mini-paas
>
> # --- Step 2: Install Dependencies ---
> pip install -r requirements.txt
>
> # --- Step 3: Prepare Host Directories and Scripts ---
> sudo mkdir -p /var/paas/apps
> sudo mkdir -p /var/paas/volumes
> sudo mkdir -p /var/paas/scripts
> sudo cp scripts/run_isolated.sh /var/paas/scripts/
> sudo chmod +x /var/paas/scripts/run_isolated.sh
> sudo chown -R $USER:$USER /var/paas
>
> # --- Step 4: Start Control Plane ---
> # [Feature Implemented: Live Dashboard & Hardware Telemetry]
> # This initializes the state database, auto-healer daemon, and exposes:
> # - Metrics endpoint (Prometheus/Grafana): http://localhost:8000/metrics
> # - Live Web Dashboard: http://localhost:8000/dashboard
> uvicorn main:app --host 0.0.0.0 --port 8000 &
>
> # --- Step 5: Validate Cluster Health ---
> python cli.py health
>
> # --- Step 6: Distributed Deployment ---
> # [Feature Implemented: Distributed Scaling]
> # The scheduler will automatically distribute replicas across healthy workers
> python cli.py deploy https://github.com/kushalrajb/sample-web-app my-test-app --replicas 3
>
> # --- Step 7: Load Balancing Validation ---
> # [Feature Implemented: Dynamic Load Balancing]
> # NGINX dynamically updates upstream routing. Behind the scenes, traffic 
> # distribution uses round-robin balancing similar to this generated config:
> # upstream myapp {
> #     server worker1:8080;
> #     server worker2:8080;
> #     server worker3:8080;
> # }
>
> # --- Step 8: Persistent Volumes Validation ---
> # [Feature Implemented: Persistent Storage]
> # Even if a container crashes, the storage controller preserves Databases, 
> # Logs, and App state using secure Linux bind mounts automatically.

---

## 🏗 Deployment Flow

1. **Developer Submits Deployment:** Developer deploys application using the CLI.
2. **Scheduler Selects Workers:** Placement is based on free memory, CPU availability, worker health, and workload density.
3. **Worker Launches Runtime:** The worker clones the application, prepares the filesystem, creates isolation boundaries, applies `cgroups`, and assigns an internal IP.
4. **Load Balancer Updates:** NGINX upstream pool refreshes automatically, making the application externally accessible.

---

## 📊 Scalability Benchmarks

This platform was load-tested under controlled architectural constraints.

| Metric | 10 Containers | 100 Containers | 500 Containers |
| :--- | :--- | :--- | :--- |
| **Max RAM Usage** | ~2.5 GB | ~25 GB | ~128 GB |
| **API Heartbeat Load** | 1 req/sec | 10 req/sec | 50 req/sec |
| **Subnet IP Usage** | 4% | 39% | Exhausted |
| **Database Status** | Stable | Stable | SQLite Lock Risk |

---

## ⚠️ Architectural Constraints

### Network Scaling Limit
* **Current subnet:** `10.0.1.0/24`
* **Maximum usable IPs:** ~253
* **Scaling beyond this requires:** Overlay networking, larger subnet allocation, or multi-subnet architecture.

### Database Scaling Limit
* Current state storage uses **SQLite**. Performs well for small to medium clusters.
* **High-scale clusters may experience:** Write lock contention and reduced concurrency.
* **Future upgrade path:** PostgreSQL or a Distributed KV store.
