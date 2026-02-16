[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)


# 🛒 ADMarket

![](.github/assets/admarket.gif)

## Summary

Telegram mini-app for buying and selling advertising spots in Telegram channels.

**Telegram Bot:** [@ADMarkett_Bot](https://t.me/ADMarkett_Bot)

## Tech Stack

| Layer         | Technology                                |
| ------------- | ----------------------------------------- |
| Backend       | Python 3.11+, FastAPI, SQLAlchemy, Alembic |
| Database      | PostgreSQL                                |
| Queue / Cache | Redis, RQ, rq-scheduler                   |
| Blockchain    | TON (escrow via tonutils)                 |
| Bot           | Telegram Bot API (long polling), Telethon (MTProto) |
| Frontend      | React 18, TypeScript, Vite, Sass          |
| Real-time     | WebSocket + Redis Pub/Sub                 |

## Architecture

```
API (routers)  →  Domain (services, state machine, events)  →  Infrastructure (Telegram, TON, Redis, WS)
      ↕                        ↕
   Schemas               DB Models
```

- **api/** — HTTP controllers (FastAPI routers): auth, channels, deals, campaigns, templates, webhooks.
- **domain/** — Business logic: deal state machine, service layer, domain events, scheduling.
- **infra/** — External integrations: Telegram Bot API, TON blockchain, Redis pub/sub, WebSocket manager, RQ queue.
- **db/** — SQLAlchemy models and session management.
- **schemas/** — Pydantic request/response schemas.
- **tasks/** — Background jobs executed by RQ workers.
- **core/** — Configuration and dependency injection.

### Deal State Machine

Deals follow a deterministic lifecycle:

```
negotiation → pending_payment → creative_draft → creative_review → approved
→ scheduling → awaiting_confirmation → scheduled → posted → released
```

At any funded stage, a deal can be cancelled with automatic refund.

## Project Structure

```
AdMarketplace/
├── backend/
│   ├── app/
│   │   ├── api/routers/      # HTTP endpoints
│   │   ├── core/             # Config, dependencies
│   │   ├── db/models/        # SQLAlchemy models (16 models)
│   │   ├── domain/           # Business logic
│   │   │   ├── channels/     # Channel verification, management
│   │   │   ├── chat/         # In-app chat service
│   │   │   ├── deals/        # Deal state machine, service, permissions
│   │   │   ├── events/       # Domain event signals & handlers
│   │   │   └── scheduling/   # Publication scheduling
│   │   ├── infra/            # External integrations
│   │   │   ├── telegram/     # Bot handlers, polling
│   │   │   ├── ton/          # Escrow, sender, webhook
│   │   │   ├── redis/        # Centralized Redis service
│   │   │   ├── websocket/    # WS manager with Redis Pub/Sub
│   │   │   └── queue/        # RQ job queue
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── tasks/            # Background jobs (RQ)
│   │   └── utils/            # Helpers
│   ├── alembic/              # Database migrations
│   ├── scripts/              # Utility scripts (session gen, analytics, cleanup)
│   ├── run.py                # Backend entry point
│   ├── run_rq_worker.py      # RQ worker process
│   ├── run_rq_scheduler.py   # RQ scheduler process
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/            # 17 page components
│       ├── components/       # Shared UI components
│       ├── features/         # Feature-specific components
│       ├── layout/           # App layout wrappers
│       ├── api/              # API client layer
│       ├── domain/           # Frontend domain logic
│       ├── state/            # State management
│       ├── styles/           # SCSS styles
│       ├── utils/            # Utility functions
│       └── ui/               # Base UI kit
├── .env.example              # Environment template
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

## Setup

### 1. Clone and configure

```bash
git clone <repository-url>
cd AdMarketplace
cp .env.example .env
```

Edit `.env` and fill in all values. See `.env.example` for descriptions.

Required credentials:
- **DATABASE_URL** — PostgreSQL connection string
- **TELEGRAM_BOT_TOKEN** — from [@BotFather](https://t.me/BotFather)
- **TELEGRAM_BOT_USERNAME** / **TELEGRAM_BOT_ID** — your bot's username and numeric ID
- **TELEGRAM_API_ID** / **TELEGRAM_API_HASH** — from [my.telegram.org](https://my.telegram.org)
- **TELEGRAM_USER_SESSION** — Telethon StringSession (generate with `python backend/scripts/generate_session.py`)
- **TON_MNEMONIC** — 24-word wallet mnemonic for escrow
- **TON_API_KEY** — from [tonapi.io](https://tonapi.io)
- **VITE_API_BASE_URL** — your public domain (e.g. `https://yourdomain.com`)

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python run.py
```

The backend starts on port `5002` by default (configurable in `run.py`).

### 3. Frontend

```bash
cd frontend
npm install
npm run build
```

The built frontend (`frontend/dist/`) is served automatically by FastAPI on the same domain.

For local development with hot reload:

```bash
npm run dev
```

This starts Vite on `localhost:5173` with API proxy to `localhost:5002`.

### 4. Background workers

In separate terminals:

```bash
cd backend
python run_rq_worker.py       # executes background jobs
python run_rq_scheduler.py    # runs delayed/scheduled jobs
```

Both processes are required for:
- Scheduled post publication
- Auto-release escrow after timeout
- Blockchain balance checks
- Notification delivery

## Running in Production

Summary of processes to run:

| Process              | Command                                | Purpose                          |
| -------------------- | -------------------------------------- | -------------------------------- |
| API + Bot            | `python backend/run.py`                | FastAPI server + Telegram polling |
| RQ Worker            | `python backend/run_rq_worker.py`      | Background job execution         |
| RQ Scheduler         | `python backend/run_rq_scheduler.py`   | Delayed job scheduling           |

### Production deployment checklist

1. **Environment** — Set `ENVIRONMENT=production` in `.env`
2. **Domain** — Set `VITE_API_BASE_URL` to your public domain (e.g. `https://yourdomain.com`)
3. **Database** — Create the PostgreSQL database and run `alembic upgrade head`
4. **Frontend build** — Run `npm run build` in `frontend/` to generate static files
5. **Redis** — Ensure Redis is running and `REDIS_URL` in `.env` points to it
6. **TON wallet** — Set `TON_MNEMONIC` with a funded wallet and `TON_API_KEY` from tonapi.io
7. **Telegram session** — Generate a Telethon session with `python backend/scripts/generate_session.py`
8. **Process manager** — Use systemd (or PM2 / supervisor) to keep all 3 processes running
9. **Reverse proxy** — Put Nginx in front with SSL termination

### Example Nginx config

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:5002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Example systemd service (repeat for each process)

```ini
[Unit]
Description=AdMarketplace API
After=network.target postgresql.service redis.service

[Service]
User=deploy
WorkingDirectory=/opt/admarketplace/backend
Environment="PATH=/opt/admarketplace/venv/bin"
EnvironmentFile=/opt/admarketplace/.env
ExecStart=/opt/admarketplace/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```