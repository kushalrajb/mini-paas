#!/bin/bash

# Phase 1: Core Container Engine
# Usage: sudo ./run_isolated.sh <target_dir> <app_name>

TARGET_DIR=$1
APP_NAME=$2

if [ -z "$TARGET_DIR" ] || [ -z "$APP_NAME" ]; then
    echo "Usage: sudo $0 <target_dir> <app_name>"
    exit 1
fi

CGROUP_NAME="paas_$APP_NAME"
CGROUP_DIR="/sys/fs/cgroup/$CGROUP_NAME"

echo "🚀 Booting Phase 1 isolation engine for $APP_NAME..."

# 1. Resource Control (Cgroups)
# Creates an isolated resource bucket for the app
mkdir -p "$CGROUP_DIR"

# Limit memory to 256MB
echo "256000000" > "$CGROUP_DIR/memory.max"
# Limit CPU allocation
echo "50000 100000" > "$CGROUP_DIR/cpu.max"

echo "🔒 Cgroup limits enforced (256MB RAM, 50% CPU)."

# Assign the current process to the restricted cgroup
echo $$ > "$CGROUP_DIR/cgroup.procs"

# 2. Virtual Filesystem (Jail Prep)
# In production, an Alpine or Ubuntu root filesystem is mounted here
mkdir -p "$TARGET_DIR"

# 3. Process Isolation (Namespaces) & Execution
echo "🛡️ Unsharing native Linux namespaces (PID, NET, MOUNT, UTS, IPC)..."

# unshare: Strips the process of host system awareness
# chroot: Locks the process inside the target directory
unshare --pid --net --mount --uts --ipc --fork \
    chroot "$TARGET_DIR" /bin/sh -c "echo 'Environment isolated.' && sleep infinity" &

# Record the isolated PID so Phase 2 (the API) can track it
CONTAINER_PID=$!
echo "✅ Container spawned successfully. Process ID: $CONTAINER_PID"
