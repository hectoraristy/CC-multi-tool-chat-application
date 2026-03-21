# Design Document: Multi-Tool Chat Application

## 1. Overview

This document describes the architecture, key technical decisions, trade-offs, and proposed designs for the Multi-Tool Chat Application — a full-stack system where users interact with an AI agent that can call multiple tools, persist results across sessions, and handle oversized outputs via summarization.

## 2. Architecture

### 2.1 High-Level System Diagram

```
┌──────────────────┐         ┌──────────────────────────────────────┐
│                  │  HTTP/  │           Backend (FastAPI)           │
│   React SPA      │  SSE    │                                      │
│   (Vite + TS)    │◄───────►│  /api/chat      → LangGraph Agent   │
│                  │         │  /api/sessions  → Session CRUD       │
│   Hosted on      │         │                                      │
│   App Runner     │         │  ┌────────────┐  ┌────────────────┐ │
│   (nginx)        │         │  │ Tool Router │──│ Session Manager │ │
└──────────────────┘         │  │            │  │ DB Query       │ │
                             │  │            │  │ Web Download   │ │
                             │  │            │  │ External API   │ │
                             │  │            │  │ File Source    │ │
                             │  └────────────┘  └───────┬────────┘ │
                             │                          │          │
                             │  ┌───────────────────────▼────────┐ │
                             │  │ Summarization Node             │ │
                             │  │ (conditional, for large results)│ │
                             │  └────────────────────────────────┘ │
                             └──────────┬──────────────┬──────────┘
                                        │              │
                            ┌───────────▼──────┐ ┌─────▼──────────┐
                            │     DynamoDB     │ │       S3       │
                            │ (single-table)   │ │ (large results │
                            │                  │ │  offloading)   │
                            │ Sessions, Msgs,  │ │                │
                            │ Tool Results     │ │ results/{id}/  │
                            └──────────────────┘ └────────────────┘
```

### 2.2 Component Responsibilities

| Component | Technology | Responsibility |
|-----------|-----------|---------------|
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS 4, TanStack Query, Radix UI / shadcn, Lucide | Chat UI, session management, SSE streaming display |
| Backend API | FastAPI, Python 3.11 | HTTP endpoints, request validation, SSE streaming |
| Agent | LangGraph | Orchestration of LLM calls, tool routing, conditional summarization |
| Tools | LangChain @tool decorator | Session Manager, DB Query, Web Download, External API, File Source |
| Storage | DynamoDB (single-table), S3 | Sessions, chat history, persisted tool results, large-result offloading |
| Infrastructure | Terraform | App Runner, ECR, DynamoDB, S3 |
| Build System | Pants 2.23 | Monorepo build, test, lint, Docker packaging |

### 2.3 Data Flow

1. **User sends a message** → Frontend POSTs to `/api/chat` with `session_id` and `message`.
2. **Backend stores the user message** in DynamoDB, then loads the full conversation history.
3. **LangGraph agent is invoked** with the message history. The agent node calls the LLM with bound tools.
4. **If the LLM requests a tool call**, the `tools` node executes it. The result flows through a conditional edge:
   - If the result exceeds the token threshold → `summarize` node condenses it, stores the full result in S3 (if configured) or DynamoDB, and returns a compact summary → back to `agent`.
   - Otherwise → directly back to `agent`.
5. **The agent may call more tools** or produce a final text response.
6. **Streaming**: Each step emits SSE events (`token`, `tool_call`, `tool_result`, `error`, `done`). Internal `session_manager` tool calls are hidden from the user-facing message list.
7. **The final response is persisted** to DynamoDB and the session timestamp is updated.

## 3. Key Technical Decisions

### 3.1 Session Manager Tool — Context Window Management

**Problem**: Tool results can be very large (database dumps, web pages, API responses). Loading all of them into every LLM call wastes tokens and can exceed context limits.

**Solution**: The Session Manager Tool provides four operations:
- **store**: Persists the full result in DynamoDB (or S3 for results > 100KB); only returns a compact confirmation with the `result_id` and a brief summary to the LLM.
- **list**: Returns metadata (IDs, tool names, summaries, sizes) of all stored results — no full content.
- **retrieve**: Fetches the full content of a specific stored result when the agent explicitly needs it.
- **get_download_url**: Generates a presigned S3 URL for downloading a stored result, or returns the content inline if the result is stored in DynamoDB only.

This gives the agent the ability to "remember" what data is available without polluting the context window. The agent decides when to pull in specific results based on the user's current question.

Results exceeding `S3_OFFLOAD_THRESHOLD` (100KB) are automatically offloaded to S3 under the key `results/{session_id}/{result_id}.txt`, with the DynamoDB item storing only metadata and an `s3_key` pointer.

**DynamoDB Schema** (single-table design):

| PK | SK | Use |
|----|-----|-----|
| `SESSION#{id}` | `META` | Session metadata (title, timestamps) |
| `SESSION#{id}` | `MSG#{iso_ts}#{msg_id}` | Chat messages (sorted by time) |
| `SESSION#{id}` | `RESULT#{result_id}` | Tool results (metadata + full content or `s3_key` pointer) |

### 3.2 Pluggable LLM Provider

The LLM is created by a factory function (`agent/llm_factory.py`) that reads the `LLM_PROVIDER` environment variable and returns the appropriate LangChain chat model. Three providers are supported:

| Provider | Package | Default Model |
|----------|---------|---------------|
| `openai` | `langchain-openai` | `gpt-4o` (`OPENAI_MODEL`) |
| `anthropic` | `langchain-anthropic` | `claude-sonnet-4-20250514` (`ANTHROPIC_MODEL`) |
| `bedrock` | `langchain-aws` | Uses `OPENAI_MODEL` + `AWS_REGION` |

All providers are configured with `streaming=True` and the factory is cached with `@lru_cache`. This means:
- Local development can use OpenAI or Anthropic.
- Production on AWS can use Bedrock without code changes.
- The provider can be swapped by changing a single env var.

### 3.3 SSE Streaming over WebSockets

SSE was chosen over WebSockets because:
- The communication is unidirectional (server → client for streaming).
- SSE is simpler to implement (no connection upgrade, works through most proxies/CDNs).
- User messages are sent via standard HTTP POST — no need for a persistent bidirectional channel.
- If collaborative features were needed (e.g., multiple users in one session), WebSockets would be the right choice.

### 3.4 LangGraph over Plain LangChain Chains

LangGraph provides:
- Explicit graph-based control flow (agent → tools → conditional summarization → agent).
- Native support for conditional edges (the summarization routing).
- Clean separation of concerns: each node is independently testable.
- Stream mode `updates` allows us to emit SSE events as each node completes.

### 3.5 Pants Build System

Pants provides a unified build for the monorepo:
- **Python backend**: `python_sources`, `python_tests`, `python_requirements` targets. Tests run via `pants test backend/tests::`.
- **Frontend**: Wrapped in `shell_command` (Pants' native Node.js support is experimental). `npm ci && npm run build` is a reliable approach.
- **Docker**: `docker_image` targets for both frontend and backend.
- **Lint**: Black, isort, and mypy integrated via Pants backends.

### 3.6 Single-Table DynamoDB Design

A single DynamoDB table stores sessions, messages, and tool results using composite keys. Benefits:
- One table to provision, monitor, and back up.
- All data for a session is co-located (efficient `Query` operations).
- PAY_PER_REQUEST billing for simplicity.

The trade-off is that cross-session queries (e.g., "find all sessions") require a `Scan`, which is acceptable at the expected scale.

## 4. Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| SSE instead of WebSocket | Simpler implementation, good proxy compatibility | No bidirectional streaming |
| DynamoDB single-table | Co-located data, simple provisioning | Scan needed for cross-partition queries |
| SQLite for local DB tool | Zero setup for development | Not representative of production (RDS) |
| Pants shell_command for frontend | Reliable, no experimental dependencies | Less integrated than native Pants Node support |
| No authentication | Faster development | Not production-ready without auth layer |
| App Runner instead of ECS Fargate | Simpler provisioning, built-in TLS/auto-scaling, no VPC/ALB management | Less control over networking, fewer customization options |
| API key in Secrets Manager | Secure secret injection into App Runner at runtime | Requires `secretsmanager:GetSecretValue` IAM permission |
| S3 offloading for large results | Bypasses DynamoDB 400KB item limit, enables presigned download URLs | Additional service dependency, eventual consistency for reads |

## 5. Feature Status and Proposed Designs

1. The file source tools was not fully tested but I don't it will hard to get approach to this one.


## 7. Assumptions

1. The application is single-tenant for the PoC (no multi-user auth).
2. DynamoDB items are limited to 400KB — tool results larger than this are automatically offloaded to S3 when the S3 bucket is configured (see `S3_OFFLOAD_THRESHOLD`).
3. The SQLite database tool is for demonstration; production would use RDS via SQLAlchemy.
4. LLM API keys are stored in AWS Secrets Manager for production (App Runner injects them at runtime). Locally, they are read from the `.env` file. No fallback if the LLM is unreachable.
5. The sample database and CSV files are included for demonstration purposes.
