#!/bin/bash

# SETTINGS
# Path to file used to communicate from restart script
readonly restart_flag='.restart_flag'
# How long (in seconds) to wait before restarting
readonly restart_delay=10
# Whether to restart on crash or not
# The `settings.restart-on-crash` setting in spigot.yml doesn't always work
# but also sometimes server might not return proper exit code,
# so it's best to keep both options enabled
# Accepted values: y/yes/true/n/no/false
readonly restart_on_crash='yes'
# The name of your server jar
readonly server_file='PalServer.sh'



should_restart_on_crash() {
  case "${restart_on_crash,,}" in
    y|yes|true) return 0;;
    n|no|false) return 1;;
    *)
      printf 'ERROR: Invalid value for "restart_on_crash" variable: %s\n' "${restart_on_crash}" >&2
      exit 1
      ;;
  esac
}

# Save all arguments in an array
args="$@"

# Remove restart flag, if it exists,
# so that we won't restart the server after first stop,
# unless restart script was called
rm "${restart_flag}" &>/dev/null || true

# Check if `restart_on_crash` has valid value
should_restart_on_crash || true

readonly startup_args=(
  -useperfthreads
  -NoAsyncLoadingThread
  -UseMultithreadForDS
  "${args}" # Additional args which where given as arguments
)

while :; do # Loop infinitely
  # Run server
  bash PalServer.sh "${startup_args}" || {
    # Oops, server didn't exit gracefully
    printf 'Detected server crash (exit code: %s)\n' "${?}" >&2
    # Check if we should restart on crash or not
    if should_restart_on_crash; then
      touch "${restart_flag}"
    fi
  }
  # Check if restart file exists or exit
  if [ -e "${restart_flag}" ]; then
    # The flag exists - try to remove it
    rm "${restart_flag}" || {
      # If we can't remove it (permissions?), then exit to avoid endless restart loop
      printf 'Error removing restart flag (exit code: %s) - cowardly exiting\n' "${?}" >&2
      exit 1
    }
  else
    break # Flag doesn't exist, so break out of the loop
  fi
  printf 'Restarting server in 10 seconds, press Ctrl+C to abort.\n' >&2
  sleep "${restart_delay}" || break # Exit if sleep is interrupted (for example Ctrl+C)
done

printf 'Server stopped\n' >&2