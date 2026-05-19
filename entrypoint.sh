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

# Start the messaging gateway in the background
hermes gateway run &

# Start the dashboard on localhost, auth proxy handles external access
hermes dashboard --host 127.0.0.1 --port 9119 --no-open &

# Start the auth proxy (listens on $PORT, proxies to dashboard)
exec python /auth_proxy.py
