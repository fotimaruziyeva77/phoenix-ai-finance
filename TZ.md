# BotForge AI — Technical Specification (TZ)

## 1. Overview

**Product:** BotForge AI  
**Type:** AI Sales SaaS Platform  
**Target:** Global SaaS (initial launch in Uzbekistan, scalable worldwide)  

### Core Idea
BotForge AI allows users to create AI-powered sales bots in **3–5 steps** that:
- understand user intent
- ask smart questions
- collect leads
- send them to CRM + Telegram
- operate across Web Widget + Telegram

---

## 2. Core Features (MVP Scope)

### 2.1 Authentication
- Email/Password
- Google OAuth
- GitHub OAuth
- JWT-based auth

### 2.2 Dashboard
- Bot creation wizard
- Bot management
- Leads CRM
- Knowledge base (PDF)
- Widget settings
- Telegram integration

### 2.3 AI Sales Engine
- Intent classification
- Conversation state machine
- Question planner (1-step UX)
- Response planner
- Lead trigger logic

### 2.4 CRM System
- Lead capture
- Lead scoring (cold/warm/hot)
- Lead status pipeline:
  - new → contacted → qualified → proposal → won/lost
- Telegram alerts

### 2.5 Knowledge System
- PDF upload
- Processing → chunking
- Retrieval
- Cost-aware context selection

### 2.6 Channels
- Web Chat Widget (public)
- Telegram Bot

### 2.7 Superadmin Panel
- Users overview
- Bots overview
- Suspension controls
- Platform monitoring

---

## 3. Architecture

### 3.1 Architecture Style
- Modular Monolith (MVP)
- Future-ready for microservices

### 3.2 Backend Stack
- Python + FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis (optional caching/queue)
- MinIO (file storage)

### 3.3 Frontend Stack
- Next.js (App Router)
- TailwindCSS

### 3.4 AI Layer
- Gemini 1.5 Flash
- Cost tracking system
- Prompt builder

---

## 4. Data Model (High-Level)

### Core Entities
- User
- Bot
- Conversation
- Message
- Lead
- KnowledgeFile
- KnowledgeChunk
- WidgetConfig
- TelegramConfig

### Relationships
- User → Bots
- Bot → Conversations
- Conversation → Messages
- Conversation → Lead
- Bot → Knowledge

---

## 5. AI System Design

### Pipeline
1. User message
2. Intent classification
3. Data extraction
4. State transition
5. Question planning
6. Response planning
7. Prompt build
8. Gemini call

### Key Rules
- 1 question per step
- Warm tone
- Lead-focused
- Cost-aware

---

## 6. Lead System

### Lead Trigger Conditions
- Sufficient data collected
- Contact info present (phone optional but recommended)
- Reached closing stage

### Lead Fields
- name
- phone
- summary
- score
- temperature
- source_channel

---

## 7. Knowledge System

### Flow
1. Upload PDF
2. Store in MinIO
3. Extract text
4. Chunk
5. Store chunks
6. Retrieve during chat

### Constraints
- Per-bot isolation
- No cross-tenant access
- Token-limited context

---

## 8. Web Widget

### Features
- Embeddable script
- Domain whitelist
- Public chat API
- Anti-abuse protection

### Security
- public_widget_key
- domain validation

---

## 9. Telegram Integration

### Flow
- User connects bot via token
- Webhook registered
- Messages routed to AI engine
- Responses sent back

### Security
- token encryption
- no plaintext storage

---

## 10. Security

### Requirements
- JWT auth
- RBAC (user/admin/superadmin)
- Owner scoping
- Secret encryption
- Input validation
- File validation

### Risks Covered
- data leakage
- fake leads
- token exposure
- public abuse

---

## 11. Cost Optimization

### Techniques
- Token tracking
- Context limiting
- Retrieval filtering
- Simple query bypass (no AI for trivial input)
- caching layer (future)

---

## 12. Observability

### Logging
- structured logs
- request_id
- bot_id
- channel

### Monitoring
- error tracking (Sentry-ready)
- AI usage logs
- channel logs

---

## 13. CI/CD

### Pipeline
- Lint
- Backend tests
- Frontend tests
- Build

### Environments
- local
- staging
- production

---

## 14. Anti-Abuse

### Controls
- rate limiting
- spam detection
- repeated message filtering

---

## 15. Testing Strategy

### Layers
- Unit tests
- Integration tests
- E2E tests

### Critical Flows
- bot creation
- AI chat
- lead creation
- widget
- Telegram

---

## 16. Release Readiness Checklist

- All APIs connected
- No fake UI flows
- Security validated
- Logs enabled
- CI passing
- E2E verified

---

## 17. Risks & Future Work

### Risks
- AI cost explosion
- poor lead quality
- abuse via widget
- scaling issues

### Future Improvements
- vector search
- advanced analytics
- billing system
- mobile apps

---

## 18. Final CTO Verdict

BotForge AI MVP is designed as a **production-ready AI Sales SaaS platform** with:
- multi-channel capability
- scalable architecture
- cost-aware AI system
- real business value (lead generation)

Ready for **MVP launch after final audit & fixes**.

