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
readonly server_jar='fabric-server-mc.1.20.1-loader.0.15.7-launcher.1.0.0.jar'
# What will be passed to `-Xms` and `-Xmx`
readonly heap_size='20G'
# JVM startup flags, one per line for better readability
# NOTE: -Xms and -Xmx are set separately
# These are mostly "Aikar flags"
# taken from: https://mcflags.emc.gs/
readonly jvm_flags=(
 -XX:+UseG1GC 
 -Dsun.rmi.dgc.server.gcInterval=2147483646 
 -XX:+UnlockExperimentalVMOptions 
 -XX:G1NewSizePercent=20 
 -XX:G1ReservePercent=20 
 -XX:MaxGCPauseMillis=50 
 -XX:G1HeapRegionSize=32M 
 -XX:+ParallelRefProcEnabled 
 -XX:ParallelGCThreads=8 
 -XX:ConcGCThreads=2
)
# Minecraft args you might want to start your server with
# Usually there isn't much to configure here:
readonly mc_args=(
  --nogui # Start the server without GUI
)
# END OF SETTINGS

# Save all arguments in an array
args="$@"

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

# The arguments that will be passed to java:
readonly java_args=(
  -Xms"${heap_size}" # Set heap min size
  -Xmx"${heap_size}" # Set heap max size
  "${jvm_flags[@]}" # Use jvm flags specified above
  -jar "${server_jar}" # Run the server
  "${mc_args[@]}" # And pass it these settings
  "${args}" # Additional args which where given as arguments
)

# Remove restart flag, if it exists,
# so that we won't restart the server after first stop,
# unless restart script was called
rm "${restart_flag}" &>/dev/null || true

# Check if `restart_on_crash` has valid value
should_restart_on_crash || true

while :; do # Loop infinitely
  # Run server
  java "${java_args[@]}" || {
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