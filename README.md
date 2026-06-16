# ☁️ KushalCloud: Native Linux Container Platform

A lightweight, distributed Platform-as-a-Service (PaaS) built entirely from scratch. This is not a wrapper around Docker or Kubernetes. It is a custom orchestrator that utilizes native Linux kernel primitives—Namespaces, Cgroups, and Virtual Ethernet (Veth) bridging—to isolate, execute, and manage user workloads.

## 🎯 Problem Statement
Modern developers rely heavily on high-level abstractions like Docker, Kubernetes, and Heroku. While these tools are powerful, they obscure the fundamental OS-level mechanics of containerization and distributed systems. 

**The Goal:** Build a custom Kubernetes-style orchestrator from the ground up to deeply understand distributed architecture, networking namespaces, self-healing clusters, and hardware telemetry.

---

## 🏗️ Architecture Diagram



```mermaid
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

    CLI -- "POST /deploy (--replicas)" --> API
    API <--> DB
    API -- "Updates configs" --> NGINX
    API -- "Spawns via subprocess" --> W1
    API -- "Spawns via subprocess" --> W2
    Healer -- "Polls health" --> DB
    W1 -- "Heartbeats & OS Metrics" --> API
    W2 -- "Heartbeats & OS Metrics" --> API
    W1 --> Cgroups
    W1 --> Veth
    NGINX -- "Round Robin" --> Veth
    Internet --> NGINX

🚀 Feature Checklist
 Kernel-Level Isolation: Utilizes ⁠unshare⁠ and ⁠chroot⁠ for PID, UTS, Mount, and IPC namespace isolation.
 Resource Quotas: Hardcoded ⁠cgroups⁠ capping individual containers at 256MB RAM and 50% CPU max.
 Distributed Replication: CLI support for multi-node deployments (⁠--replicas 3⁠).
 Self-Healing Automation: Master API asynchronously hunts for dead nodes and auto-reschedules orphaned applications.
 Veth Bridge Networking: Custom ⁠10.0.1.0/24⁠ subnet mapping internal IPs to an NGINX reverse-proxy pool.
 Persistent Volumes: Storage controller generating Linux ⁠--bind⁠ mounts to prevent database data loss during container crashes.
 Hardware Telemetry: Real-time metrics exporter for Prometheus and Grafana integration.
 Live Dashboard: Dark-mode UI rendering live cluster health, RAM usage, and active workloads.

💻 How to Run It (Step-by-Step)
Prerequisites: You must run this on a Linux machine (Ubuntu/Debian recommended) because the platform natively interacts with the Linux kernel (cgroups/namespaces).

Step 1: Clone & Setup Dependencies
Clone the repository and install the Python dependencies for the Control Plane.
git clone [https://github.com/YOUR_USERNAME/mini-paas.git](https://github.com/YOUR_USERNAME/mini-paas.git)
cd mini-paas
pip install -r requirements.txt

Step 2: Prepare the Host System
Because this platform manages system-level networking and storage, it needs the correct directory structures created on the host server.
