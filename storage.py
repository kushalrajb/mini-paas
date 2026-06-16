import os
import shutil

# The master directory on the host server where all persistent data lives
VOLUME_DIR = "/var/paas/volumes"

def create_volume(volume_name: str):
    """Creates a permanent storage folder on the host machine."""
    path = f"{VOLUME_DIR}/{volume_name}"
    
    if os.path.exists(path):
        print(f"⚠️ Volume '{volume_name}' already exists.")
        return path
    
    # Create the directory with open permissions so the isolated container process can write to it
    os.makedirs(path, exist_ok=True)
    os.chmod(path, 0o777) 
    
    print(f"✅ Created persistent volume at {path}")
    return path

def delete_volume(volume_name: str):
    """Destroys the volume and permanently deletes all its data."""
    path = f"{VOLUME_DIR}/{volume_name}"
    
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"🗑️ Volume '{volume_name}' destroyed.")
        return True
        
    return False

def generate_mount_args(volume_name: str, container_mount_point: str):
    """
    Generates the Linux bind mount arguments for your Phase 1 container engine.
    This string is passed to your low-level run_isolated.sh script.
    """
    host_path = f"{VOLUME_DIR}/{volume_name}"
    
    if not os.path.exists(host_path):
        raise ValueError(f"Cannot mount missing volume: {volume_name}")
        
    # The native Linux kernel command to bridge the host folder into the container's jailed filesystem
    return f"--bind {host_path} {container_mount_point}"

# Quick test execution block
if __name__ == "__main__":
    # Simulate a user requesting a database volume
    vol_path = create_volume("database_storage")
    
    # Simulate generating the bridge command to mount it to /var/lib/mysql inside the container
    mount_cmd = generate_mount_args("database_storage", "/var/lib/mysql")
    print(f"Linux Mount Command Generated: mount {mount_cmd}")
