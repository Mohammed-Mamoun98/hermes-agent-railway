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

# Start the dashboard on localhost (web UI pre-built in Docker image)
hermes dashboard --host 127.0.0.1 --port 9119 --no-open --skip-build &

# Wait for the dashboard before exposing the proxy so Railway doesn't route
# traffic to a half-started process.
DASHBOARD_READY_TIMEOUT="${DASHBOARD_READY_TIMEOUT:-300}"
SECONDS=0
until curl -fsS http://127.0.0.1:9119/api/health >/dev/null; do
  if [ "$SECONDS" -ge "$DASHBOARD_READY_TIMEOUT" ]; then
    echo "Dashboard did not become ready within ${DASHBOARD_READY_TIMEOUT}s."
    exit 1
  fi
  sleep 1
done

# Start the auth proxy (listens on $PORT, proxies to dashboard)
exec python /auth_proxy.py
