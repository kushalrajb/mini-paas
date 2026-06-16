#!/bin/bash

# Phase 1: Core Container Engine
# Usage: sudo ./run_isolated.sh <target_dir> <app_name> <internal_ip>

TARGET_DIR=$1
APP_NAME=$2
# Default to an internal IP if the Master API doesn't provide one
CONTAINER_IP=${3:-"10.0.1.5"}

if [ -z "$TARGET_DIR" ] || [ -z "$APP_NAME" ]; then
    echo "Usage: sudo $0 <target_dir> <app_name> [container_ip]"
    exit 1
fi

echo "🚀 Booting Phase 1 isolation engine for $APP_NAME..."

# ==========================================
# 1. RESOURCE CONTROL (CGROUPS)
# ==========================================
CGROUP_NAME="paas_$APP_NAME"
CGROUP_DIR="/sys/fs/cgroup/$CGROUP_NAME"

mkdir -p "$CGROUP_DIR"
# Limit memory to 256MB and CPU to 50%
echo "256000000" > "$CGROUP_DIR/memory.max"
echo "50000 100000" > "$CGROUP_DIR/cpu.max"
echo "🔒 Cgroup limits enforced (256MB RAM, 50% CPU)."

# ==========================================
# 2. VIRTUAL NETWORKING (VETH & BRIDGE)
# ==========================================
BRIDGE_NAME="kushal_bridge"
NETNS_NAME="netns_$APP_NAME"
VETH_HOST="veth0_$APP_NAME"
VETH_GUEST="veth1_$APP_NAME"

# Create the master host bridge if it doesn't exist yet
if ! ip link show $BRIDGE_NAME > /dev/null 2>&1; then
    ip link add name $BRIDGE_NAME type bridge
    ip addr add 10.0.1.1/24 dev $BRIDGE_NAME
    ip link set dev $BRIDGE_NAME up
    echo "🌉 Created host network bridge ($BRIDGE_NAME)."
fi

# Create a dedicated network namespace for this specific container
ip netns add $NETNS_NAME

# Create the "invisible ethernet cable" (veth pair)
ip link add $VETH_HOST type veth peer name $VETH_GUEST

# Plug one end of the cable into the host's master bridge
ip link set $VETH_HOST master $BRIDGE_NAME
ip link set $VETH_HOST up

# Plug the other end into the container's isolated network namespace
ip link set $VETH_GUEST netns $NETNS_NAME

# Assign the internal IP address inside the namespace and route it out
ip netns exec $NETNS_NAME ip addr add $CONTAINER_IP/24 dev $VETH_GUEST
ip netns exec $NETNS_NAME ip link set $VETH_GUEST up
ip netns exec $NETNS_NAME ip link set lo up
ip netns exec $NETNS_NAME ip route add default via 10.0.1.1

echo "🌐 Veth networking established. Container IP: $CONTAINER_IP"

# ==========================================
# 3. VIRTUAL FILESYSTEM & EXECUTION
# ==========================================
mkdir -p "$TARGET_DIR"

echo "🛡️ Unsharing native namespaces and launching jailed process..."

# 1. ip netns exec: Puts the process inside the network we just built
# 2. unshare: Isolates PID, Mount, UTS (Hostname), and IPC
# 3. We write the isolated PID to the cgroup file
# 4. chroot: Locks the filesystem to the target directory
ip netns exec $NETNS_NAME unshare --pid --uts --mount --ipc --fork \
    bash -c "echo \$\$ > $CGROUP_DIR/cgroup.procs && chroot $TARGET_DIR /bin/sh -c 'echo \"Environment isolated.\" && sleep infinity'" &

CONTAINER_PID=$!
echo "✅ Container spawned successfully. Process ID: $CONTAINER_PID"
