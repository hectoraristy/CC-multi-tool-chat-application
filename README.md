# Multi-Tool Chat Application

A full-stack chat application with an AI agent capable of calling multiple tools, built with React, Python/FastAPI, LangGraph, Pants, and deployed to AWS via Terraform.

## Architecture

- **Frontend**: React 19 + TypeScript + Vite 6 + Tailwind CSS 4 + TanStack Query + Radix UI / shadcn
- **Backend**: Python 3.11 + FastAPI + LangGraph
- **Build System**: Pants 2.23
- **Infrastructure**: AWS (App Runner, ECR, DynamoDB, S3) via Terraform
- **CI/CD**: GitHub Actions

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 24+
- Pants 2.23+
- Terraform 1.14+ (for infrastructure provisioning)
- AWS CLI (for DynamoDB local or cloud)
- Docker & Docker Compose (for containerized development)

### Docker Compose (Recommended)

The fastest way to get everything running locally. Spins up DynamoDB Local, the backend (with hot-reload), and the frontend (with Vite HMR) in one command:

```bash
# Copy and configure your environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY

# Start all services
docker compose up --build

# Frontend: http://localhost:5173
# Backend:  http://localhost:8080
# DynamoDB:  http://localhost:8000
```

Source code is bind-mounted into the containers, so changes to `backend/src/` and `frontend/src/` are reflected immediately without rebuilding.

To stop and clean up:

```bash
docker compose down            # stop containers
docker compose down -v         # stop and remove the DynamoDB data volume
```

### Manual Setup

If you prefer running without Docker:

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy and configure environment
cp ../.env.example ../.env

# Run the API server
uvicorn src.api.main:app --reload --port 8080
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Using Pants

```bash
# Run all tests
pants test ::

# Lint
pants lint ::

# Build Docker images
pants package ::
```

### Terraform (AWS Infrastructure)

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan
terraform apply
```

## Project Structure

```
├── .github/workflows/       # CI and deploy pipelines
│   ├── ci.yml               # Lint on PRs (Pants + ESLint)
│   └── deploy.yml           # Build & push Docker images on merge to main
├── backend/
│   ├── Dockerfile           # Production image (Python 3.11-slim + uvicorn)
│   ├── requirements.txt     # Python dependencies
│   ├── data/                # Sample SQLite DB for the database_query tool
│   ├── tests/               # Test directory
│   └── src/
│       ├── config.py        # Pydantic Settings (LLM, DynamoDB, S3, etc.)
│       ├── constants.py     # Shared constants and regexes
│       ├── exceptions.py    # Custom exception classes and handlers
│       ├── logging_config.py
│       ├── api/
│       │   ├── main.py          # FastAPI app, lifespan, CORS, routers
│       │   ├── dependencies.py  # DI: get_store(), get_s3_store(), get_graph()
│       │   ├── models.py        # Request/response Pydantic models
│       │   └── routes/
│       │       ├── chat.py      # POST /api/chat (SSE streaming) + POST /api/chat/upload (file upload)
│       │       └── sessions.py  # Session CRUD, messages, tool results
│       ├── agent/
│       │   ├── state.py         # AgentState TypedDict (messages, session_id, turn count, etc.)
│       │   ├── graph.py         # LangGraph graph: router → plan → agent → tools (chunking) → evaluate
│       │   ├── nodes.py         # plan_node, evaluate_node
│       │   ├── prompt_builder.py # Dynamic system prompt (tool instructions, chunking instructions)
│       │   └── llm_factory.py   # create_llm() — OpenAI, Anthropic, or Bedrock
│       ├── services/
│       │   ├── chat_service.py      # stream_agent_events() — runs graph, yields SSE
│       │   ├── chunking.py          # ChunkingMiddleware — auto-chunk large tool results
│       │   ├── context_manager.py   # Token-aware context compaction and message summarization
│       │   ├── session_service.py   # Session CRUD operations
│       │   ├── message_converter.py # Stored messages → LangChain message format
│       │   └── persistence.py       # Persist user/assistant/tool messages
│       ├── storage/
│       │   ├── protocols.py     # Repository protocols (Session, Message, ToolResult)
│       │   ├── models.py        # Domain models (Session, ChatMessage, ToolResult)
│       │   ├── dynamo.py        # DynamoDB single-table implementation
│       │   └── s3.py            # S3 offload for large tool results
│       └── tools/
│           ├── __init__.py          # Exports ALL_TOOLS
│           ├── session_manager.py   # Store/retrieve/list/download/get_chunk tool results
│           ├── database_query.py    # Read-only SQL queries
│           ├── web_download.py      # Fetch and parse web page content
│           ├── external_api.py      # Generic HTTP API calls
│           ├── file_source.py       # Read CSV/JSON/PDF from local or S3
│           └── data_analysis.py     # Server-side pandas analysis (describe, aggregate, query, etc.)
├── frontend/
│   ├── Dockerfile           # Production build (Node → nginx)
│   ├── Dockerfile.dev       # Dev image with Vite HMR
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf           # Production static serving + SPA fallback
│   └── src/
│       ├── App.tsx              # Root layout: SessionSidebar + ChatWindow
│       ├── main.tsx             # Entry point: React root, QueryClientProvider
│       ├── index.css            # Global styles + Tailwind
│       ├── components/
│       │   ├── ChatWindow.tsx           # Main chat area
│       │   ├── MessageList.tsx          # Message list renderer
│       │   ├── MessageBubble.tsx        # Individual message bubble
│       │   ├── MessageInput.tsx         # Chat input with submit
│       │   ├── SessionSidebar.tsx       # Session list sidebar
│       │   ├── SessionItem.tsx          # Session row with inline title editing
│       │   ├── ToolCallInlineMessage.tsx # Inline tool call display
│       │   ├── EmptyState.tsx           # Empty chat placeholder
│       │   ├── StreamingIndicator.tsx   # Streaming status indicator
│       │   ├── ThinkingIndicator.tsx    # Agent thinking indicator
│       │   ├── ErrorBoundary.tsx        # React error boundary
│       │   └── ui/                      # shadcn/ui primitives (button, input, badge, etc.)
│       ├── hooks/
│       │   ├── useSessions.ts       # Session CRUD (list, create, select, update, delete)
│       │   ├── useChat.ts           # Chat state and send message
│       │   ├── useStreamChat.ts     # SSE streaming for chat responses
│       │   ├── useAutoScroll.ts     # Auto-scroll on new messages
│       │   └── useInlineEdit.ts     # Inline editing (session titles)
│       ├── services/
│       │   └── api.ts               # API client: sessions, messages, streaming
│       ├── lib/
│       │   ├── sse.ts               # readSSEStream() — parse SSE events
│       │   ├── utils.ts             # cn() — tailwind-merge + clsx
│       │   └── queryKeys.ts         # TanStack Query cache key factories
│       └── types/
│           └── index.ts             # Session, ChatMessage, FileAttachment, ToolCall types
├── infra/                   # Terraform (AWS)
│   ├── main.tf              # Root module: ECR, DynamoDB, S3, IAM, App Runner
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # ECR URLs, App Runner URLs, table name
│   ├── terraform.tfvars.example
│   └── modules/
│       ├── ecr/             # ECR repositories for backend and frontend images
│       ├── dynamodb/        # DynamoDB table (single-table design, on-demand)
│       ├── s3/              # S3 bucket for tool result offloading
│       └── apprunner/       # App Runner service (from ECR, with health checks)
├── .env.example             # Environment variable template
├── docker-compose.yml       # Local dev: DynamoDB + backend + frontend
├── pants.toml               # Pants build configuration
├── pyproject.toml           # Python tooling config (black, isort, mypy)
└── .tool-versions           # asdf version pinning
```

## Tools

The agent supports the following tools:

| Tool | Description |
|------|-------------|
| Session Manager | Store, retrieve, list, get download URLs, and get chunks for tool results in DynamoDB. Large results are auto-chunked; the agent retrieves subsequent chunks on demand. |
| Database Query | Execute read-only SQL queries against a SQLite database (sample products table included for demo). |
| Web Download | Fetch a URL, strip HTML tags, and return the text content. |
| External API | Make HTTP requests (GET/POST) to arbitrary external endpoints and return the response. |
| File Source | Read CSV, JSON, or PDF files from local disk or S3 URIs. |
| Data Analysis | Analyze CSV or JSON files server-side using pandas (describe, aggregate, query, filter, search, value_counts). Avoids loading full file contents into the context window. |

## File Uploads

Users can attach CSV or PDF files directly in the chat input (paperclip button). The flow:

1. The frontend uploads the file via `POST /api/chat/upload` (max 50 MB).
2. The backend stores it in S3 under `uploads/{session_id}/` and returns an `s3://` URI.
3. The URI is injected into the user message so the agent can process the file with `file_source` (preview) or `data_analysis` (server-side computation).

File uploads require an S3 bucket to be configured (`S3_RESULTS_BUCKET`).

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | LLM provider: `openai`, `anthropic`, or `bedrock` |
| `OPENAI_API_KEY` | — | OpenAI API key (required when using `openai` provider) |
| `OPENAI_MODEL` | `gpt-4o` | Model name for the OpenAI provider |
| `AWS_REGION` | `us-east-1` | AWS region for DynamoDB and S3 |
| `DYNAMODB_TABLE_NAME` | `tool_results` | DynamoDB table name |
| `DYNAMODB_ENDPOINT_URL` | `http://localhost:8000` | DynamoDB endpoint (use local for development) |
| `S3_RESULTS_BUCKET` | — | S3 bucket for offloading large tool results and file uploads |
| `S3_PRESIGNED_URL_EXPIRY` | `3600` | Presigned URL expiry in seconds |
| `CHUNK_TOKEN_BUDGET` | `10000` | Token budget per chunk when auto-chunking large tool results |
| `MAX_CONTEXT_TOKENS` | `25000` | Maximum token budget for conversation context sent to the LLM |
| `RECENT_TURNS_TO_PRESERVE` | `5` | Number of recent user/assistant turns always kept when trimming |
| `BACKEND_PORT` | `8080` | Port the backend listens on |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin |
| `LOG_LEVEL` | `INFO` | Logging level |

## CI/CD

Two GitHub Actions workflows are configured:

**CI** (`.github/workflows/ci.yml`) — runs on every pull request:
- Backend lint via Pants (`pants lint backend::`)
- Frontend lint via ESLint (`npm run lint`)

**Deploy** (`.github/workflows/deploy.yml`) — runs on push to `main`:
- Detects which services changed (`backend/` or `frontend/`)
- Builds Docker images and pushes to ECR (tagged with commit SHA and `latest`)
- App Runner auto-deploys when new images are pushed to ECR

## Infrastructure

The `infra/` directory contains Terraform modules that provision the AWS resources:

| Module | Resources |
|--------|-----------|
| **ecr** | ECR repositories for backend and frontend Docker images |
| **dynamodb** | Single DynamoDB table (PAY_PER_REQUEST) with composite PK/SK for sessions, messages, and tool results |
| **s3** | S3 bucket with lifecycle expiration for tool result offloading |
| **apprunner** | App Runner services for both backend and frontend, pulling images from ECR |

IAM roles grant the backend App Runner service access to DynamoDB, S3, and Secrets Manager.

## Design Document

See [design-doc.md](design-doc.md) for architecture details, trade-offs, and design proposals.
