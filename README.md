# Betting Microservices

[![CI](https://github.com/maximunya/betting-microservices/actions/workflows/ci.yml/badge.svg)](https://github.com/maximunya/betting-microservices/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A small betting platform built as two independently deployable FastAPI services that talk to each other over RabbitMQ instead of direct HTTP calls. It's a compact playground for async Python microservice patterns: request/response over a message broker, event-driven state updates between services, per-service databases, and Redis-backed response caching.

## Contents

- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [API overview](#api-overview)
- [Running tests](#running-tests)
- [Project structure](#project-structure)
- [Possible improvements](#possible-improvements)

## Architecture

```
                 ┌───────────────┐        events CRUD         ┌──────────────┐
   HTTP client ──▶ line-provider │◀────────────────────────▶│  Postgres    │
                 │   :8001       │                            │ (per-service)│
                 └──────┬────────┘                            └──────────────┘
                        │ ▲
      status changed    │ │ get_available_events /
      (fire-and-forget) │ │ get_available_event_detail
                        │ │ (RPC, reply-to queue + timeout)
                        ▼ │
                 ┌──────────────┐
                 │   RabbitMQ   │
                 └──────┬───────┘
                        │ ▲
                        │ │
                 ┌──────▼───────┐        bets CRUD           ┌──────────────┐
   HTTP client ──▶   bet-maker  │◀────────────────────────▶│  Postgres    │
                 │   :8000      │                            │ (per-service)│
                 └──────┬───────┘                            └──────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │    Redis     │  (caches GET /events/ for 30s)
                 └──────────────┘
```

- **line-provider** owns sporting events: creating them, listing them, and updating their odds/deadline/status.
- **bet-maker** owns bets: it needs live event odds to price a bet, so it asks line-provider for them over RabbitMQ using a request/response ("RPC") pattern — a private, auto-deleted reply queue per call, with a timeout, so concurrent requests can never consume each other's replies and a stalled call fails fast instead of hanging forever.
- When line-provider settles an event (marks a team as the winner), it fires a one-way message; bet-maker's background consumer picks it up and updates the status of every affected bet (`WON`/`LOST`).
- Each service owns its own PostgreSQL database — no shared schema, no cross-service joins.

## Tech stack

- **Python 3.12** / **FastAPI** — async HTTP APIs
- **PostgreSQL** + **SQLAlchemy** (async Core) + **Alembic** — per-service storage and migrations
- **RabbitMQ** (`aio-pika`) — inter-service messaging (RPC + fire-and-forget)
- **Redis** (`fastapi-cache2`) — response caching
- **Poetry** — dependency management
- **pytest** / **httpx** — testing
- **Docker** / **Docker Compose** — local orchestration
- **GitHub Actions** — CI (lint + tests, one job per service)

## Getting started

Requires Docker and Docker Compose.

```bash
git clone https://github.com/maximunya/betting-microservices.git
cd betting-microservices

cp .env.example .env

docker-compose up --build
```

Each service applies its own Alembic migrations on startup, then serves:

| Service | URL | Interactive docs |
|---|---|---|
| line-provider | http://localhost:8001 | http://localhost:8001/docs |
| bet-maker | http://localhost:8000 | http://localhost:8000/docs |

Both expose `GET /health` and a Docker `HEALTHCHECK`. `.env` is the single source of truth for the whole stack. `.env.example` contains working, non-secret, container-internal defaults — copying it as-is is enough to run the stack locally.

## API overview

**line-provider**
- `POST /events/` — create an event
- `GET /events/` — list events (offset/limit)
- `PUT /events/{event_id}` — update an event's odds, deadline, or status; setting a winning status locks the deadline and notifies bet-maker to settle bets

**bet-maker**
- `GET /events/` — list events still open for betting, proxied from line-provider (cached 30s)
- `POST /bets/` — place a bet (fetches the event's current odds from line-provider)
- `GET /bets/` — list placed bets (offset/limit)

Full request/response schemas are available via each service's `/docs`.

## Running tests

Each service has its own `tests/` directory and its own dependency group. The DB layer is tested against a real Postgres (started via Compose); RabbitMQ is not required, since the RPC/messaging boundary is mocked at the test level.

```bash
docker-compose up -d bet_maker_db line_provider_db   # exposed on localhost:5432 / :5433

cd bet-maker      # or line-provider
poetry install
DB_HOST=localhost DB_PORT=5432 DB_USER=postgres DB_PASS=postgres DB_NAME=postgres poetry run pytest
```

(use `DB_PORT=5433` for `line-provider`). CI runs the same suite against a fresh `postgres:16` service container on every push.

## Project structure

```
bet-maker/
├── app/
│   ├── routers/        # bets.py, events.py — HTTP endpoints
│   ├── main.py         # app setup, CORS, /health, startup/shutdown
│   ├── config.py       # environment variables
│   ├── database.py     # async engine/session, shared metadata
│   ├── models.py       # SQLAlchemy Core tables
│   ├── schemas.py      # Pydantic models
│   ├── crud.py         # DB access + RabbitMQ RPC calls
│   ├── rabbitmq.py     # RabbitMQ transport (send_message, rpc_call)
│   └── consumers.py    # background queue consumer
├── migrations/         # Alembic
├── tests/
├── Dockerfile
└── pyproject.toml

line-provider/    # same shape (router.py instead of a routers/ package)
```

## Possible improvements

A few things were deliberately left as-is, or chosen for the sake of demonstrating a pattern rather than being the "best" production choice:

- **RPC over RabbitMQ for a synchronous read** (`GET /bet-maker/events/`) is here to show the messaging pattern. A production system fronting a browser client would more likely have bet-maker call line-provider directly (or through a gateway) for this kind of read, and reserve the broker for genuinely asynchronous events like the settlement notification.
- **No authentication/authorization** — out of scope for what this project demonstrates.
- **Offset/limit pagination only** — no cursor pagination or total-count headers on list endpoints.
- **Shared enums duplicated per service** (`BetStatus`, `EventStatus`, …) — an intentional microservice-boundary tradeoff (no shared library dependency between services), worth revisiting if they start to drift.
