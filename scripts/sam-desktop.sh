#!/usr/bin/env bash
# Switch SAM Desktop between the NSE-only instance and the default one.
#
# SAM keeps all state (agents, connectors, models, chats, artifacts, logs) in
# its home directory. The default home (~/Library/Application Support/sam)
# holds your other projects; the NSE desk runs from its own home so the two
# never mix. The app runs one instance at a time (fixed ports 8800/8001), so
# switching quits the running app and relaunches it with the other home.
#
# Usage:
#   scripts/sam-desktop.sh nse       # NSE-only instance (SAM_HOME=$NSE_SAM_HOME)
#   scripts/sam-desktop.sh default   # your usual instance
#   scripts/sam-desktop.sh status    # which instance is running
#
# For sam CLI commands against the NSE instance, point the CLI at the same home:
#   export SAM_HOME="$HOME/sam-homes/nse-desk"   # or pass --sam-home on each command
set -euo pipefail

APP="Solace Agent Mesh"
NSE_SAM_HOME="${NSE_SAM_HOME:-$HOME/sam-homes/nse-desk}"
# The NSE instance keeps only the desk's own agents plus SAM's Builder. The
# built-in Orchestrator was deleted once (it is only seeded into an empty
# database); the Activity Monitor is re-seeded at every start unless its
# feature is off, so the NSE launch turns it off.
NSE_FEATURE_FLAGS=(${NSE_FEATURE_FLAGS:-SAM_FEATURE_ACTIVITY_MONITOR=false})
DEFAULT_SAM_HOME="$HOME/Library/Application Support/sam"

running() { pgrep -x sam-desktop >/dev/null 2>&1; }

current_home() {
  # The running instance's SAM_HOME, if set via `open --env`.
  local pid
  pid="$(pgrep -x sam-desktop | head -1 || true)"
  [ -n "$pid" ] || return 0
  ps eww -p "$pid" 2>/dev/null | tr ' ' '\n' | sed -n 's/^SAM_HOME=//p' | head -1
}

quit_app() {
  running || return 0
  echo "Quitting $APP..."
  osascript -e "quit app \"$APP\"" >/dev/null 2>&1 || true
  for _ in $(seq 1 60); do running || return 0; sleep 1; done
  echo "$APP did not quit within 60s; quit it manually and re-run." >&2
  exit 1
}

wait_ready() {
  echo -n "Waiting for SAM on 127.0.0.1:8800"
  for _ in $(seq 1 90); do
    if curl -s -o /dev/null -m 2 http://127.0.0.1:8800/; then echo " ready."; return 0; fi
    echo -n "."; sleep 2
  done
  echo; echo "SAM did not come up; see <home>/diagnostics/logs/desktop.log" >&2
  exit 1
}

case "${1:-status}" in
  nse)
    quit_app
    mkdir -p "$NSE_SAM_HOME"
    echo "Launching $APP with SAM_HOME=$NSE_SAM_HOME"
    env_args=(--env "SAM_HOME=$NSE_SAM_HOME")
    for flag in ${NSE_FEATURE_FLAGS[@]+"${NSE_FEATURE_FLAGS[@]}"}; do env_args+=(--env "$flag"); done
    open -n -a "$APP" "${env_args[@]}"
    wait_ready
    echo "CLI: export SAM_HOME=\"$NSE_SAM_HOME\"   (then: sam config apply --target desktop)"
    ;;
  default)
    quit_app
    echo "Launching $APP with its default home ($DEFAULT_SAM_HOME)"
    open -a "$APP"
    wait_ready
    echo "CLI: unset SAM_HOME"
    ;;
  status)
    if running; then
      h="$(current_home)"
      echo "$APP is running with SAM_HOME=${h:-<default: $DEFAULT_SAM_HOME>}"
    else
      echo "$APP is not running."
    fi
    ;;
  *)
    echo "usage: $0 {nse|default|status}" >&2
    exit 2
    ;;
esac
