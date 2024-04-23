#!/bin/bash

# Name of the tmux session
TARGET_SESSION="CS2"
STEAM_ID="730"

# Path to your script 
EXECUTE_PATH="/home/steam/"
# Flag to check if "validate" is found
validate=false

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
else
	echo "Session already exist. Please close the session first."
	exit 1
fi

for arg in "$@"
do
    if [ "$arg" == "validate" ]; then
        validate=true
        break
    fi
done

if [ "$validate" == true ]; then
    # Send the command to switch to the steam user, change directory, and execute the script
    tmux send-keys -t $TARGET_SESSION "sudo -u steam bash -c 'cd $EXECUTE_PATH && /usr/games/steamcmd +login anonymous +app_update $STEAM_ID validate +quit'" C-m
else
    tmux send-keys -t $TARGET_SESSION "sudo -u steam bash -c 'cd $EXECUTE_PATH && /usr/games/steamcmd +login anonymous +app_update $STEAM_ID +quit'" C-m
fi
