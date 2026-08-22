# NutriGuard AI — AI-Powered Personalized Diet & Medication Nutrition System

## Overview

NutriGuard is a deterministic AI-assisted food safety and nutrition guidance system. The LLM is used **only** for natural language parsing and explanation generation — all medical decisions are made by deterministic rule engines.

**Architecture:**
```
User Input → NLP Extraction → Entity Normalization → Validated UserContext
→ Safety Engine → Allergy Engine → Interaction Engine → Rule Engine → Scoring Engine
→ Final Deterministic Classification → AI Explanation → API Response
```

The AI **never** overrides a safety veto, allergy block, or drug-food interaction.

## Quick Start

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set DATABASE_URL, JWT_SECRET, GEMINI_API_KEY

cd backend
python -m alembic upgrade head
python -m data.seed
uvicorn main:app --reload
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL URL (production) or SQLite path (dev) |
| `JWT_SECRET` | Yes | At least 32 character random secret |
| `GEMINI_API_KEY` | No | Google Gemini key (NLP/explanation degrades gracefully without it) |
| `DEBUG` | No | Set `true` for development trace output |
| `ENVIRONMENT` | No | `development` or `production` |

## API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | None | API health check |
| `GET /health/ready` | None | Database readiness |
| `POST /api/v1/auth/login` | None | Get JWT token |
| `POST /api/v1/chat/food` | JWT | Conversational food query |
| `POST /api/v1/recommendations/evaluate/{food_id}` | JWT | Direct food evaluation |
| `POST /api/v1/nlp/parse-context` | JWT | NLP context extraction |
| `POST /api/v1/admin/rules/simulate` | JWT (Reviewer+) | Rule simulator |
| `GET /docs` | None | Swagger UI |

## Running Tests

```bash
cd backend
python -m pytest tests/regression/test_engines.py -v
```

## Demo Scenarios

Login first:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=user@nutriguard.com" -F "password=password123"
```

Then use the token with chat queries:
```bash
curl -X POST http://localhost:8000/api/v1/chat/food \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "I am allergic to peanuts. Can I eat peanuts?", "user_context": {"allergies": ["peanut"]}}'
```

## Deployment

See [Railway deployment guide](https://railway.app).

Set environment variables in Railway dashboard, the container runs:
1. `alembic upgrade head` (migrations)
2. `python -m data.seed` (seed data — idempotent)
3. `uvicorn main:app --host 0.0.0.0 --port $PORT`
