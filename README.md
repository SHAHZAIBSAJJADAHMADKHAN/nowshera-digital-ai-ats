# Nowshera Digital

## AI Recruitment & Applicant Tracking System

### AI-Assisted Applicant Tracking & Recruitment Automation Platform

Nowshera Digital is a full-stack recruitment platform for Candidates, Recruiters, and Admins. It centralizes job management, applications, private CV handling, hiring workflow controls, interviews, notifications, and AI-assisted CV summaries in one secure system.

## Project Overview

Nowshera Digital previously relied on fragmented hiring through email, WhatsApp, and spreadsheets. That makes candidate information difficult to track, obscures hiring progress, and increases manual coordination work.

This system provides a shared, role-aware workspace for jobs, applications, CVs, hiring stages, interviews, recruiter assignments, notifications, dashboards, audit records, and AI-assisted CV summaries.

> AI assists recruiters. Humans make hiring decisions.

## Key Features

### Candidate

- Supabase-backed authentication and role-aware access.
- Open-job discovery with draft, closed, and expired roles kept out of candidate discovery.
- Private PDF CV upload and versioning.
- Application submission and a **My Applications** view.
- Current-stage tracking, chronological stage history, and interview visibility.
- Withdrawal and reapplication after withdrawal.
- An immutable CV snapshot attached to every submitted application.

### Recruiter

- Work limited to assigned jobs and applications.
- Assigned-job and application workspaces.
- Authorized private CV access through signed URLs.
- Private recruiter notes.
- Recruiter-facing AI CV summaries.
- Ordered application transitions, rejection, and hiring actions.
- Interview scheduling with persisted interview details.
- Application stage history.

### Admin

- Recruiter management and invitations.
- Job creation and Draft / Open / Closed lifecycle management.
- Recruiter-to-job assignment management.
- All-application visibility and application detail.
- Dashboard counts for each application stage.
- Admin visibility of persisted interview and AI-summary information.

### Automation

- Application Received, Interview Invitation, Hired, and Rejected email events.
- Asynchronous AI CV summary processing.
- Transactional outbox processing with idempotency, retry, and terminal-failure handling.

## Hiring Pipeline

```text
Applied
   ↓
Shortlisted
   ↓
Interview
   ↓
Offer
   ↓
Hired
```

The hiring pipeline is enforced by the server and database:

- Stages cannot be skipped or moved backward.
- `Rejected`, `Withdrawn`, and `Hired` are terminal stages.
- Rejection is allowed from active stages according to the business rules, but not after a terminal decision.
- The generic transition endpoint cannot bypass interview scheduling or the dedicated hiring transaction.
- Critical changes write stage-history and audit records.

## AI-Assisted CV Analysis

The backend integrates with Google Gemini to generate a structured, recruiter-facing summary from the exact CV snapshot associated with an application.

Each completed summary contains:

1. A candidate profile with 3–5 bullets.
2. Requirements analysis: requirements mentioned and requirements not found.
3. Exactly 3 interview questions.

AI does **not** score or rank candidates, decide hiring or rejection, or change application stages. The system includes prompt-injection and sensitive-attribute safeguards, validates the structured result, handles provider failures safely, and supports authorized retry. AI failure does not block application submission, and candidates cannot access recruiter-facing AI summaries.

## System Architecture

```text
React + Vite frontend
        │
        │ HTTPS + Supabase JWT
        ▼
FastAPI backend
        │
        ├── Supabase Auth / JWKS verification
        ├── PostgreSQL, RLS, and transactional RPCs
        ├── Supabase Storage for private CVs
        ├── Automation outbox
        │         │
        │         ▼
        │        n8n
        │       ├── email delivery workflow
        │       └── AI summary worker
        │                 │
        └─────────────────┴── Google Gemini via the backend
```

- **Frontend:** React role workspaces consume versioned backend APIs and never call Gemini directly.
- **Backend:** FastAPI authenticates JWTs, applies server-side authorization, and coordinates application services.
- **Supabase:** Auth, PostgreSQL, storage, RLS policies, and database RPCs provide the persistence and security foundation.
- **n8n:** Claims outbox work for email delivery and asynchronous AI processing.
- **Gemini:** Produces validated, constrained CV summaries through the backend-only AI boundary.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Frontend | React, JavaScript, Vite, React Router, Supabase JavaScript client |
| Backend | Python, FastAPI, Pydantic, Uvicorn, HTTPX |
| Database, Auth, Storage | Supabase, PostgreSQL, Supabase Auth, Supabase Storage |
| Automation | n8n |
| AI | Google Gemini |
| Security | JWT/JWKS verification, RBAC, RLS, signed URLs, server-side RPC boundaries |
| Testing | Pytest and Node's built-in test runner |

## Database Design

| Table | Purpose |
| --- | --- |
| `profiles` | Role and active-status profile for each authenticated user. |
| `candidate_cvs` | Versioned candidate CV metadata and private-storage references. |
| `jobs` | Job details, capacity, deadline, and lifecycle state. |
| `job_recruiters` | Recruiter-to-job assignment boundary. |
| `applications` | Candidate/job application with immutable CV snapshot reference. |
| `application_stage_history` | Chronological application transition history. |
| `recruiter_notes` | Private recruiter notes. |
| `interviews` | Scheduled interview details and recruiter scheduling constraint. |
| `ai_summaries` | Validated AI summary state and structured result. |
| `automation_events` | Transactional outbox events for email and AI work. |
| `audit_logs` | Security-sensitive and workflow audit records. |

Important protections include immutable application CV references, one active application per candidate/job, same-recruiter interview-overlap prevention, hiring-capacity enforcement, automatic job closure when capacity is filled, RLS boundaries, and transactional RPCs for critical changes.

## Security & Privacy

- JWT authentication is verified through Supabase JWKS; backend role authorization is based on the database profile, not client-provided role data.
- RBAC and Supabase RLS protect Candidate, Recruiter, and Admin boundaries.
- Candidates can access only their own applications and CV snapshots.
- Recruiters can access only applications for jobs assigned to them.
- CV files remain private and are exposed only through short-lived signed URLs after server-side authorization.
- Recruiter notes and AI summaries are not exposed to candidates.
- Gemini credentials remain backend-only; the browser does not receive or call Gemini credentials.
- Automation endpoints require an internal automation key rather than a browser JWT.
- Audit records capture important workflow and lifecycle actions.

## Automation Workflows

The transactional outbox decouples application and hiring transactions from external delivery work. The n8n workflows in [`n8n/workflows/`](n8n/workflows/) claim only supported events and complete or fail them through protected internal endpoints.

- **Application Received:** created with application submission.
- **Interview Invitation:** created by the dedicated interview scheduling transaction.
- **Hired:** created by the capacity-safe hiring transaction.
- **Rejected:** created by the allowed rejection transition.
- **AI CV Summary:** processed asynchronously from dedicated AI work events.

Idempotency keys prevent duplicate logical events. Claimed events support retry and terminal failure handling. Application submission remains successful even when AI generation is unavailable.

## Project Structure

```text
nowshera-digital-ai-ats/
├── frontend/
│   ├── src/
│   │   ├── context/       # Authentication state
│   │   ├── pages/         # Candidate, Recruiter, Admin, and public pages
│   │   ├── routes/        # Protected and role guards
│   │   └── services/      # Backend API clients
│   ├── .env.example
│   ├── package.json
│   └── package-lock.json
├── backend/
│   ├── app/
│   │   ├── ai/            # PDF extraction, Gemini, and summary contracts
│   │   ├── api/v1/        # FastAPI routes
│   │   ├── core/          # Configuration, auth, authorization
│   │   ├── repositories/  # Data access boundaries
│   │   ├── schemas/       # Request/response schemas
│   │   └── services/      # Application services
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── supabase/
│   └── migrations/        # PostgreSQL schema, RLS, and RPC migrations
├── n8n/
│   └── workflows/         # Email-delivery and AI-summary workflow exports
├── docs/                  # Phase design, security, and verification records
├── .gitignore
└── README.md
```

## Local Development & Setup

### Prerequisites

- Node.js and npm.
- Python 3.12 or a compatible Python 3 release.
- A Supabase project with Auth, PostgreSQL, and Storage configured.
- n8n for automation workflows.
- A Google Gemini API key for backend AI-summary processing.

### Clone and configure

```bash
git clone <repository-url>
cd nowshera-digital-ai-ats
```

Create local environment files from the supplied templates. Never commit the resulting `.env` files.

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend runs at `http://127.0.0.1:8000` by default.

### Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Vite serves the application at `http://localhost:5173` by default.

### Supabase configuration and migrations

1. Create/configure a Supabase project for Auth, PostgreSQL, and private CV storage.
2. Fill the backend and frontend environment files with your project values.
3. Apply the SQL files in [`supabase/migrations/`](supabase/migrations/) in ascending filename order using the Supabase SQL Editor or a configured Supabase CLI project.
4. Verify the migrations create the required schema, RLS policies, storage access controls, and RPC functions before using the application.

### n8n workflows

1. Import [`n8n/workflows/nowshera-digital-email-delivery.json`](n8n/workflows/nowshera-digital-email-delivery.json).
2. Import [`n8n/workflows/nowshera-digital-ai-summary-worker.json`](n8n/workflows/nowshera-digital-ai-summary-worker.json).
3. Configure `ATS_INTERNAL_API_BASE_URL` and `INTERNAL_AUTOMATION_KEY` in n8n.
4. Configure the required email-provider credential in n8n; do not export or commit it.
5. Ensure the backend is reachable from n8n before activating the workflows.

## Environment Variables

Copy the provided `.env.example` files and supply values appropriate to your own environment. Never commit `.env` files, service-role keys, Gemini keys, tokens, or credentials.

### Backend (`backend/.env`)

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | Backend environment label. |
| `FRONTEND_ORIGINS` | Allowed frontend origin(s) for CORS. |
| `SUPABASE_URL` | Supabase project URL. |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key used where configured. |
| `SUPABASE_SECRET_KEY` | Backend-only Supabase secret/service credential. |
| `SUPABASE_JWT_ISSUER` | Expected Supabase JWT issuer. |
| `SUPABASE_JWKS_URL` | Supabase JWKS endpoint used for JWT verification. |
| `INTERNAL_AUTOMATION_KEY` | Shared backend/n8n key for protected automation endpoints. |
| `GEMINI_API_KEY` | Backend-only Google Gemini API key. |
| `GEMINI_MODEL` | Gemini model identifier. |
| `GEMINI_TIMEOUT_SECONDS` | AI-provider request timeout. |

### Frontend (`frontend/.env`)

| Variable | Purpose |
| --- | --- |
| `VITE_SUPABASE_URL` | Supabase project URL. |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Browser-safe Supabase publishable key. |
| `VITE_API_BASE_URL` | FastAPI API base URL. |

### Automation / n8n

| Variable | Purpose |
| --- | --- |
| `ATS_INTERNAL_API_BASE_URL` | Backend URL used by n8n internal automation calls. |
| `INTERNAL_AUTOMATION_KEY` | Internal automation key shared with the backend. |

## Testing

### Backend tests

```powershell
cd backend
& .\.venv\Scripts\python.exe -m pytest
```

### Frontend tests

```powershell
cd frontend
node --test src\*.test.js
```

### Production build

```powershell
cd frontend
npm run build
```

Final completed-project verification results:

| Check | Result |
| --- | --- |
| Backend regression | 280 passed, 0 failed, 0 skipped |
| Frontend regression | 23 passed, 0 failed |
| Production build | PASS |
| Official acceptance suite | 14 / 14 PASS |

## Official Acceptance Coverage

| # | Acceptance Area | Status |
| --- | --- | --- |
| AT-01 | Application submission | PASS |
| AT-02 | Full hiring pipeline | PASS |
| AT-03 | Duplicate active application prevention | PASS |
| AT-04 | Hiring capacity and auto-close | PASS |
| AT-05 | Invalid and closed transitions | PASS |
| AT-06 | Withdraw and reapply with a new CV | PASS |
| AT-07 | Input and interview validation | PASS |
| AT-08 | Server-side authorization | PASS |
| AT-09 | Candidate privacy | PASS |
| AT-10 | Dashboard, email, and mobile behavior | PASS |
| AT-11 | AI summary success | PASS |
| AT-12 | AI safety and prompt injection | PASS |
| AT-13 | AI failure and retry | PASS |
| AT-14 | AI privacy and secret security | PASS |

## Responsive Design

Candidate, Recruiter, and Admin interfaces support desktop, tablet, and mobile layouts. Responsive layout contracts are included in frontend verification for all three authenticated workspaces.

## Out of Scope

This project intentionally does not include:

- AI candidate scoring, ranking, or automated hiring decisions.
- LinkedIn or job-board publishing.
- Built-in video interviews.
- Offer-letter e-signatures.
- Payroll.
- Real SMS or WhatsApp delivery.
- A native mobile application.
- Multi-company tenancy.

## Screenshots

> Screenshots will be added here for the Candidate Portal, Recruiter Dashboard, Admin Dashboard, AI CV Summary, and Hiring Pipeline.

## Engineering Highlights

- Server-enforced hiring state machine.
- Transactional hiring-capacity enforcement and automatic job closure.
- Immutable application CV snapshots.
- Database-level same-recruiter interview-overlap constraint.
- Asynchronous, idempotent outbox automation.
- AI safety boundaries and validated structured output.
- JWT authorization, RBAC, RLS, and signed private file access.
- Automated acceptance, security, backend, and frontend verification.

## Author

**Shahzaib Sajjad Ahmad Khan**
Software Engineering Student
AI Full-Stack & AI Automation Developer

## Project Status

**Completed**

**Official Acceptance Tests: 14/14 PASS**
