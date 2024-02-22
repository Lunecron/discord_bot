#!/bin/bash

# Name of the tmux session
TARGET_SESSION="Minecraft"

# Path to your script 
SCRIPT_PATH="/home/minecraft/startserver.sh"

#User to execute command with and command
#string_to_send = 'sudo -u steam bash -c \"cd \$(dirname \"'$SCRIPT_PATH') && ./\$(basename \'$SCRIPT_PATH')\"'

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

# Send the script command to the tmux session
tmux send-keys -t $TARGET_SESSION 'sudo -u minecraft bash -c "cd $(dirname '$SCRIPT_PATH') && ./$(basename '$SCRIPT_PATH')"' C-m
