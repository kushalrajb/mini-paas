import os
import subprocess

# Standard directory where NGINX looks for server configurations
NGINX_CONF_DIR = "/etc/nginx/conf.d"

def expose_cluster_app(app_name: str, worker_endpoints: list, base_domain: str = "kushalcloud.local"):
    """
    Dynamically generates an NGINX load balancer configuration for an app 
    running across multiple worker nodes, then gracefully reloads the proxy.
    
    worker_endpoints example: ["10.0.0.5:8080", "10.0.0.6:8080"]
    """
    
    # 1. Generate the upstream block (The Load Balancer pool)
    upstream_servers = "\n".join([f"    server {endpoint};" for endpoint in worker_endpoints])
    
    config_content = f"""
# Load Balancing Pool for {app_name}
upstream backend_{app_name} {{
{upstream_servers}
}}

# Internet-Facing Gateway
server {{
    listen 80;
    server_name {app_name}.{base_domain};

    location / {{
        proxy_pass http://backend_{app_name};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
"""
    conf_path = f"{NGINX_CONF_DIR}/{app_name}.conf"
    
    try:
        # 2. Write the new load-balancing rule to the Master Node
        with open(conf_path, "w") as config_file:
            config_file.write(config_content)
            
        print(f"🚦 Created NGINX Load Balancer rule for {app_name} across {len(worker_endpoints)} nodes.")
        
        # 3. Reload NGINX without dropping any current user traffic
        subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)
        print(f"✅ Traffic is now flowing to http://{app_name}.{base_domain}")
        
    except PermissionError:
        print("⚠️ Error: Script needs sudo privileges to write to /etc/nginx/")
    except subprocess.CalledProcessError as e:
        print(f"❌ NGINX reload failed: {e}")

# Quick test execution block
if __name__ == "__main__":
    # Simulate the Master Node telling NGINX to balance traffic for "myapp" across two worker VMs
    test_endpoints = ["10.0.0.15:8000", "10.0.0.16:8000"]
    expose_cluster_app("myapp", test_endpoints)
