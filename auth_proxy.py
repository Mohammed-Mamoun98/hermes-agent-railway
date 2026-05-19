#!/usr/bin/env python3
"""Minimal cookie-based auth proxy for Hermes dashboard on Railway."""

import hashlib
import hmac
import os
import secrets
import string
import time
from aiohttp import web, ClientSession, WSMsgType

UPSTREAM = "http://127.0.0.1:9119"
USERNAME = os.environ.get("DASHBOARD_USER", "admin")
PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
SECRET = secrets.token_bytes(32)
COOKIE = "hermes_auth"
MAX_AGE = 7 * 86400

if not PASSWORD:
    print("ERROR: DASHBOARD_PASSWORD must be set.")
    raise SystemExit(1)


def make_token():
    expires = str(int(time.time()) + MAX_AGE)
    sig = hmac.new(SECRET, expires.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{sig}"


def check_token(token):
    try:
        expires, sig = token.rsplit(".", 1)
        if int(expires) < time.time():
            return False
        expected = hmac.new(SECRET, expires.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hermes Agent</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0f14; --surface: #111920;
    --border: rgba(255,255,255,0.06);
    --text: #e0f0f0; --text-muted: #7899aa;
    --accent: #2dd4bf; --accent-dim: rgba(45,212,191,0.1);
    --error-bg: rgba(180,60,60,0.1); --error-text: #d4908a;
  }
  body {
    font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }
  .card { background: var(--surface); padding: 2.5rem; border-radius: 12px; width: 360px; }
  h1 { font-size: 1.4rem; margin-bottom: 1.5rem; text-align: center; color: var(--accent); }
  .field { margin-bottom: 1.25rem; }
  label { display: block; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.4rem; }
  input {
    width: 100%; padding: 0.7rem 0.9rem;
    background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-size: 0.9rem; outline: none;
  }
  input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-dim); }
  button {
    width: 100%; padding: 0.75rem; margin-top: 0.25rem;
    background: var(--accent); color: var(--bg);
    border: none; border-radius: 8px; font-size: 0.85rem; font-weight: 600;
    cursor: pointer;
  }
  button:hover { opacity: 0.88; }
  .error {
    background: var(--error-bg); color: var(--error-text);
    padding: 0.6rem; border-radius: 8px; font-size: 0.8rem;
    margin-bottom: 1.25rem; text-align: center;
  }
</style>
</head>
<body>
<div class="card">
  <h1>Hermes Agent</h1>
  $error
  <form method="POST" action="/login">
    <div class="field">
      <label for="username">Username</label>
      <input id="username" name="username" type="text" autocomplete="username" required>
    </div>
    <div class="field">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required>
    </div>
    <button type="submit">Sign in</button>
  </form>
</div>
</body>
</html>"""


async def login_page(request):
    error = ""
    if request.query.get("error"):
        error = '<div class="error">Invalid username or password</div>'
    return web.Response(
        text=string.Template(LOGIN_HTML).safe_substitute(error=error),
        content_type="text/html",
    )


async def login_post(request):
    data = await request.post()
    username = data.get("username", "")
    password = data.get("password", "")

    if hmac.compare_digest(username, USERNAME) and hmac.compare_digest(password, PASSWORD):
        resp = web.HTTPFound("/")
        resp.set_cookie(COOKIE, make_token(), max_age=MAX_AGE, httponly=True, samesite="Lax")
        return resp

    raise web.HTTPFound("/login?error=1")


async def logout(request):
    resp = web.HTTPFound("/login")
    resp.del_cookie(COOKIE)
    return resp


@web.middleware
async def auth_middleware(request, handler):
    if request.path in ("/login", "/logout", "/api/health"):
        return await handler(request)

    token = request.cookies.get(COOKIE)
    if not token or not check_token(token):
        if request.path.startswith("/api/"):
            raise web.HTTPUnauthorized()
        raise web.HTTPFound("/login")

    return await handler(request)


async def health(request):
    return web.json_response({"status": "ok"})


async def proxy_ws(request):
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    async with ClientSession() as session:
        url = f"ws://127.0.0.1:9119{request.path_qs}"
        async with session.ws_connect(url) as ws_upstream:
            async def forward(src, dst):
                async for msg in src:
                    if msg.type == WSMsgType.TEXT:
                        await dst.send_str(msg.data)
                    elif msg.type == WSMsgType.BINARY:
                        await dst.send_bytes(msg.data)
                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break

            import asyncio
            await asyncio.gather(
                forward(ws_client, ws_upstream),
                forward(ws_upstream, ws_client),
            )

    return ws_client


async def proxy(request):
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await proxy_ws(request)

    async with ClientSession() as session:
        url = f"{UPSTREAM}{request.path_qs}"
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "transfer-encoding")}

        body = await request.read()
        async with session.request(
            request.method, url, headers=headers, data=body, allow_redirects=False,
        ) as resp:
            excluded = {"transfer-encoding", "content-encoding", "content-length"}
            proxy_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
            content = await resp.read()
            return web.Response(status=resp.status, headers=proxy_headers, body=content)


def create_app():
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/login", login_page)
    app.router.add_post("/login", login_post)
    app.router.add_get("/logout", logout)
    app.router.add_get("/api/health", health)
    app.router.add_route("*", "/{path_info:.*}", proxy)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(create_app(), host="0.0.0.0", port=port)
