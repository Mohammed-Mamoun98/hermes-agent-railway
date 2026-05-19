#!/usr/bin/env bash
set -e

AUTO_UPDATE="${AUTO_UPDATE:-true}"

if [ "$AUTO_UPDATE" = "true" ]; then
  echo "Checking for Hermes updates..."
  cd /opt/hermes-agent
  if git pull --recurse-submodules 2>&1 | grep -v 'Already up to date'; then
    echo "Updating dependencies..."
    VIRTUAL_ENV=/opt/hermes-agent/venv uv pip install -e ".[all]" --quiet
    echo "Update complete."
  else
    echo "Already up to date."
  fi
fi

# Hermes starts the dashboard as a supported side-process when enabled.
export HERMES_DASHBOARD="${HERMES_DASHBOARD:-1}"
export HERMES_DASHBOARD_HOST="${HERMES_DASHBOARD_HOST:-127.0.0.1}"
export HERMES_DASHBOARD_PORT="${HERMES_DASHBOARD_PORT:-9119}"

# Start the messaging gateway in the background
hermes gateway run &

# Start the auth proxy (listens on $PORT, proxies to dashboard)
exec python /auth_proxy.py
