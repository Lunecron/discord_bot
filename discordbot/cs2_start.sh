#!/bin/bash

# Name of the tmux session
TARGET_SESSION="CS2"

# Path to your script 
SCRIPT_PATH="/home/steam/.steam/SteamApps/common/Counter-Strike Global Offensive/game/bin/linuxsteamrt64/startserver.sh"

SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
SCRIPT_NAME=$(basename "$SCRIPT_PATH")

# Check if an argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <map>"
    echo "Example: $0 +map de_dust2"
    exit 1
fi

# Save all arguments in an array
args="$@"

# Check if the tmux server is running
TMUX_PATH=$(which tmux)

if [ -z "$TMUX_PATH" ]; then
    echo "Error: tmux is not installed. Please install tmux before running this script."
    exit 1
fi

# Check if the tmux server is already running
tmux has-session -t $TARGET_SESSION 2>/dev/null

# Check the return code to determine if the session exists
if [ $? != 0 ]; then
    # Create a new session if it doesn't exist
    tmux new-session -d -s $TARGET_SESSION
fi

# Send the command to switch to the steam user, change directory, and execute the script
tmux send-keys -t $TARGET_SESSION "sudo -u steam bash -c 'cd \"$SCRIPT_DIR\" && ./$SCRIPT_NAME ${args}'" C-m