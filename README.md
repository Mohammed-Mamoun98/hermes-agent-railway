# Hermes Agent on Railway

Deploy [Hermes Agent](https://hermes-agent.nousresearch.com/) to Railway — an open-source AI agent by Nous Research with tool use, persistent memory, messaging platform integrations, and a web dashboard.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/TEMPLATE_ID?referralCode=REFERRAL_CODE)

## Features

- **Full dashboard access** — manage config, API keys, sessions, logs, analytics, cron jobs, and skills from your browser. No SSH or CLI needed.
- **Messaging gateway included** — Telegram, Discord, and Slack bots run alongside the dashboard. Configure platform tokens in the UI, restart, and your bot is live.
- **Password-protected login** — cookie-based auth proxy in front of the dashboard. Simple, secure, no repeated browser auth prompts.
- **Auto-updates** — pulls the latest Hermes release on every container restart. Always up to date. Disable with `AUTO_UPDATE=false`.
- **Zero config to start** — deploy with just a password, then set up everything else (LLM provider, API keys, messaging platforms) from the dashboard UI.
- **Persistent storage** — attach a Railway volume to keep sessions, memories, config, and logs across redeploys.

## Setup

1. Click the **Deploy on Railway** button above
2. Set `DASHBOARD_PASSWORD` (required)
3. Deploy — log in at your Railway URL
4. Add your LLM provider key (e.g. OpenRouter, DeepSeek) on the **API Keys** page
5. Optionally configure Telegram/Discord/Slack tokens

## Environment Variables

| Variable | Description |
|---|---|
| `DASHBOARD_USER` | Login username (default: `admin`) |
| `DASHBOARD_PASSWORD` | Login password (**required**) |
| `AUTO_UPDATE` | Pull latest Hermes on every restart (default: `true`, set to `false` to pin version) |

All other configuration (LLM providers, API keys, messaging platforms) is done through the dashboard after deploy.

## Persistent Storage

To keep your data across redeploys, attach a Railway volume:

1. Right-click the service in your Railway project
2. Select **Attach Volume**
3. Set mount path to `/root/.hermes`

This persists sessions, memories, API keys, config, logs, and cron jobs.

## Architecture

```
Internet → Railway → Auth Proxy (cookie login, port $PORT)
                         │
                     ┌───┴───┐
                     │       │
               Hermes Dashboard  Messaging Gateway
               (127.0.0.1:9119)  (Telegram/Discord/Slack)
                         │
                   /api/health
                   (unauthenticated,
                    Railway health checks)
```

## Resources

- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Web Dashboard Guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard)
