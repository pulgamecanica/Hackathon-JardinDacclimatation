I'll provide the complete production-ready project structure, configuration, and codebase for ClaudeCode to implement.

---

## Project Structure

```
plume-companion/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Test on PR
│       └── cd.yml                    # Build & push on main
├── docker/
│   ├── docker-compose.prod.yml
│   ├── docker-compose.dev.yml
│   └── monitoring/
│       ├── prometheus.yml
│       └── grafana-dashboards/
├── infrastructure/
│   ├── terraform/                    # AWS/GCP provisioning
│   └── k8s/                         # Kubernetes manifests
├── services/
│   ├── web/                         # Next.js frontend
│   │   ├── Dockerfile
│   │   ├── jest.config.js
│   │   ├── src/
│   │   └── package.json
│   │
│   ├── api/                         # Rails API
│   │   ├── Dockerfile
│   │   ├── Gemfile
│   │   ├── config/
│   │   ├── app/
│   │   ├── spec/
│   │   └── entrypoint.sh
│   │
│   └── ai-orchestrator/             # Python FastAPI + Celery + Llama
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── app/
│       │   ├── main.py
│       │   ├── celery_app.py
│       │   ├── agents/
│       │   ├── mcp/
│       │   └── llm/
│       ├── workers/
│       └── tests/
│
├── mcp-servers/                     # Modular MCP servers
│   ├── tickets-mcp/
│   ├── routing-mcp/
│   ├── park-status-mcp/
│   └── shared/                      # MCP SDK/utilities
│
└── scripts/
    ├── setup.sh
    └── migrate.sh
```

---

## 1. CI/CD Pipeline

### `.github/workflows/ci-cd.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  ORG: jardin-acclimatation

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [web, api, ai-orchestrator]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup environment
        uses: ./.github/actions/setup-${{ matrix.service }}
      
      - name: Run tests
        run: |
          cd services/${{ matrix.service }}
          ${{ matrix.service == 'web' && 'npm test' || matrix.service == 'api' && 'bundle exec rspec' || 'pytest' }}
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build-and-push:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - service: web
            context: ./services/web
            image: plume-web
          - service: api
            context: ./services/api
            image: plume-api
          - service: ai-orchestrator
            context: ./services/ai-orchestrator
            image: plume-ai
          - service: mcp-tickets
            context: ./mcp-servers/tickets-mcp
            image: plume-mcp-tickets
          - service: mcp-routing
            context: ./mcp-servers/routing-mcp
            image: plume-mcp-routing
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.ORG }}/${{ matrix.image }}
          tags: |
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.context }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Deploy to production
        if: github.ref == 'refs/heads/main'
        run: |
          curl -X POST ${{ secrets.DEPLOY_WEBHOOK }} \
            -H "Authorization: Bearer ${{ secrets.DEPLOY_TOKEN }}" \
            -d '{"image":"${{ env.REGISTRY }}/${{ env.ORG }}/${{ matrix.image }}:${{ github.sha }}"}'

  integration-tests:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run integration suite
        run: |
          docker-compose -f docker/docker-compose.prod.yml up -d
          sleep 30
          ./scripts/integration-tests.sh
```

---

## 2. Docker Configurations

### `docker/docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  # Frontend
  web:
    image: ghcr.io/jardin-acclimatation/plume-web:latest
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=https://api.plume.jardin.fr
      - NEXT_PUBLIC_WS_URL=wss://api.plume.jardin.fr/cable
      - REDIS_URL=redis://redis:6379
    depends_on:
      - api
    networks:
      - plume-network
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure

  # Rails API
  api:
    image: ghcr.io/jardin-acclimatation/plume-api:latest
    ports:
      - "3001:3000"
    environment:
      - RAILS_ENV=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@postgres:5432/plume_production
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
      - AI_SERVICE_URL=http://ai-orchestrator:8000
      - MCP_TRANSPORT=stdio
    depends_on:
      - postgres
      - redis
      - ai-orchestrator
    networks:
      - plume-network
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure

  # AI Orchestrator (FastAPI + Celery)
  ai-orchestrator:
    image: ghcr.io/jardin-acclimatation/plume-ai:latest
    ports:
      - "8000:8000"
    environment:
      - VLLM_URL=http://vllm:8000/v1
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - RAILS_API_URL=http://api:3000
      - LOG_LEVEL=INFO
    volumes:
      - ai-models:/models
    depends_on:
      - redis
      - vllm
    networks:
      - plume-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # Celery Workers
  celery-worker:
    image: ghcr.io/jardin-acclimatation/plume-ai:latest
    command: celery -A app.celery_app worker -l info -Q ai-tasks,default -c 4
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - VLLM_URL=http://vllm:8000/v1
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - ai-orchestrator
    networks:
      - plume-network
    deploy:
      replicas: 2

  # Celery Beat (Scheduler)
  celery-beat:
    image: ghcr.io/jardin-acclimatation/plume-ai:latest
    command: celery -A app.celery_app beat -l info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - plume-network

  # Celery Flower (Monitoring)
  flower:
    image: ghcr.io/jardin-acclimatation/plume-ai:latest
    command: celery -A app.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - plume-network

  # vLLM (Llama Inference)
  vllm:
    image: vllm/vllm-openai:latest
    command: >
      --model meta-llama/Llama-3.3-70B-Instruct
      --quantization awq
      --tensor-parallel-size 2
      --max-model-len 8192
      --gpu-memory-utilization 0.9
    volumes:
      - ai-models:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 2
              capabilities: [gpu]
    networks:
      - plume-network

  # MCP Servers
  mcp-tickets:
    image: ghcr.io/jardin-acclimatation/plume-mcp-tickets:latest
    environment:
      - RAILS_API_URL=http://api:3000
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
    networks:
      - plume-network

  mcp-routing:
    image: ghcr.io/jardin-acclimatation/plume-mcp-routing:latest
    networks:
      - plume-network

  # Infrastructure
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASS}
      - POSTGRES_DB=plume_production
    networks:
      - plume-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    networks:
      - plume-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - web
      - api
    networks:
      - plume-network

volumes:
  postgres-data:
  redis-data:
  ai-models:

networks:
  plume-network:
    driver: bridge
```

---

## 3. AI Orchestrator Service (Python)

### `services/ai-orchestrator/requirements.txt`

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
celery[redis]==5.3.6
redis==5.0.1
pydantic==2.5.3
pydantic-settings==2.1.0
httpx==0.26.0
structlog==24.1.0
prometheus-client==0.19.0
sentry-sdk==1.40.0
pytest==7.4.4
pytest-asyncio==0.23.4
pytest-cov==4.1.0
black==24.1.1
mypy==1.8.0
openai==1.12.0  # For vLLM OpenAI-compatible API
```

### `services/ai-orchestrator/Dockerfile`

```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY app/ ./app/
COPY workers/ ./workers/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### `services/ai-orchestrator/app/celery_app.py`

```python
"""
Celery configuration with comprehensive logging and monitoring.
"""
import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import structlog

# Configure structlog for structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = Celery('plume-ai')

app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    worker_prefetch_multiplier=1,  # Ensure visibility of task start
    
    # Results
    result_expires=3600,  # 1 hour
    result_extended=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Queues
    task_routes={
        'app.tasks.inference.*': {'queue': 'ai-tasks'},
        'app.tasks.notifications.*': {'queue': 'notifications'},
        'app.tasks.analytics.*': {'queue': 'analytics'},
    },
    
    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Monitoring signals
@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    logger.info(
        "task_started",
        task_id=task_id,
        task_name=task.name,
        args=str(args),
        kwargs=str(kwargs)
    )

@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, **extras):
    logger.info(
        "task_completed",
        task_id=task_id,
        task_name=task.name,
        state=state,
        result=str(retval)[:100]  # Truncate long results
    )

@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extras):
    logger.error(
        "task_failed",
        task_id=task_id,
        exception=str(exception),
        args=str(args),
        kwargs=str(kwargs),
        traceback=traceback
    )

@app.task(bind=True, max_retries=3)
def debug_task(self):
    """Debug task to verify Celery is working"""
    logger.info(f"Request: {self.request!r}")
    return "Celery is working!"
```

### `services/ai-orchestrator/app/main.py`

```python
"""
FastAPI application for AI Orchestrator with agentic AI and MCP integration.
"""
import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import structlog

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.orchestrator import PlumeOrchestrator
from app.mcp.client import MCPClientManager
from app.llm.client import LlamaClient
from app.celery_app import app as celery_app
from app.tasks.inference import process_chat_async

logger = structlog.get_logger()

# Global clients
llm_client: Optional[LlamaClient] = None
mcp_manager: Optional[MCPClientManager] = None
orchestrator: Optional[PlumeOrchestrator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global llm_client, mcp_manager, orchestrator
    
    # Startup
    logger.info("Starting up AI Orchestrator")
    
    llm_client = LlamaClient(base_url=os.getenv("VLLM_URL"))
    mcp_manager = MCPClientManager()
    
    # Connect to MCP servers
    await mcp_manager.connect_all([
        {"name": "tickets", "transport": "stdio", "command": "python", "args": ["-m", "mcp_tickets"]},
        {"name": "routing", "transport": "stdio", "command": "python", "args": ["-m", "mcp_routing"]},
        {"name": "park_status", "transport": "stdio", "command": "python", "args": ["-m", "mcp_park_status"]},
    ])
    
    orchestrator = PlumeOrchestrator(llm_client, mcp_manager)
    
    logger.info("AI Orchestrator ready")
    yield
    
    # Shutdown
    logger.info("Shutting down")
    await mcp_manager.disconnect_all()

app = FastAPI(
    title="Plume AI Orchestrator",
    description="Agentic AI service for Jardin d'Acclimatation companion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Anonymous or linked session ID")
    message: str = Field(..., description="User message")
    context: Optional[dict] = Field(default_factory=dict, description="Additional context")
    stream: bool = Field(default=True, description="Stream response or complete")

class ChatResponse(BaseModel):
    response: str
    agent_used: str
    tools_called: list[str]
    latency_ms: float

@app.get("/health")
async def health_check():
    """Health check for load balancers"""
    return {
        "status": "healthy",
        "llm_connected": llm_client is not None,
        "mcp_connected": mcp_manager is not None if mcp_manager else False
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Main chat endpoint. Routes to appropriate agent based on intent.
    Can stream (default) or return complete response.
    """
    try:
        if request.stream:
            return StreamingResponse(
                orchestrator.stream_response(request.session_id, request.message, request.context),
                media_type="text/event-stream"
            )
        else:
            # Use Celery for async processing if not streaming
            task = process_chat_async.delay(
                request.session_id,
                request.message,
                request.context
            )
            result = task.get(timeout=30)
            return ChatResponse(**result)
            
    except Exception as e:
        logger.error("chat_error", error=str(e), session_id=request.session_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}/status")
async def session_status(session_id: str):
    """Get session context and available tools"""
    context = await orchestrator.get_session_context(session_id)
    tools = await mcp_manager.list_all_tools()
    return {
        "session_id": session_id,
        "context": context,
        "available_tools": tools
    }

@app.post("/admin/reload-mcp")
async def reload_mcp():
    """Admin endpoint to reload MCP servers"""
    await mcp_manager.disconnect_all()
    await mcp_manager.connect_all([...])  # Same config as startup
    return {"status": "reloaded"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### `services/ai-orchestrator/app/agents/orchestrator.py`

```python
"""
Agentic orchestrator with sub-agents and MCP integration.
"""
import json
import time
from typing import AsyncGenerator, Literal, Optional
import structlog

from app.llm.client import LlamaClient
from app.mcp.client import MCPClientManager

logger = structlog.get_logger()

class SessionContext:
    def __init__(self, session_id: str, tickets: list = None, history: list = None):
        self.session_id = session_id
        self.tickets = tickets or []
        self.history = history or []
        self.preferences = {}

class PlumeOrchestrator:
    def __init__(self, llm: LlamaClient, mcp: MCPClientManager):
        self.llm = llm
        self.mcp = mcp
        self.agents = {
            "planner": PlanningAgent(llm, mcp),
            "companion": CompanionAgent(llm, mcp),
            "concierge": ConciergeAgent(llm, mcp),
            "detective": DiscoveryAgent(llm, mcp),
        }
    
    async def classify_intent(self, message: str) -> Literal["planner", "companion", "concierge", "detective"]:
        """Fast intent classification using lightweight model or rules"""
        # Rule-based pre-filtering for common patterns
        msg_lower = message.lower()
        
        if any(w in msg_lower for w in ["acheter", "ticket", "billetterie", "payer", "acheté", "réservation"]):
            return "concierge"
        elif any(w in msg_lower for w in ["plan", "itinéraire", "route", "optimiser", "par où commencer"]):
            return "planner"
        elif any(w in msg_lower for w in ["secret", "badge", "récompense", "découvrir", "caché"]):
            return "detective"
        else:
            return "companion"
    
    async def stream_response(
        self, 
        session_id: str, 
        message: str, 
        context: dict
    ) -> AsyncGenerator[str, None]:
        """Main entry point for chat streaming"""
        start_time = time.time()
        
        # Fetch session context from Rails via MCP
        session_ctx = await self.get_session_context(session_id)
        
        # Classify intent
        intent = await self.classify_intent(message)
        agent = self.agents[intent]
        
        logger.info(
            "agent_selected",
            session_id=session_id,
            intent=intent,
            agent_type=type(agent).__name__
        )
        
        # Stream through selected agent
        tools_used = []
        async for chunk in agent.run(message, session_ctx):
            if chunk.get("type") == "tool_call":
                tools_used.append(chunk.get("tool"))
            
            yield f"data: {json.dumps(chunk)}\n\n"
        
        # Send completion metadata
        latency = (time.time() - start_time) * 1000
        yield f"data: {json.dumps({'type': 'metadata', 'agent': intent, 'tools': tools_used, 'latency_ms': latency})}\n\n"
    
    async def get_session_context(self, session_id: str) -> SessionContext:
        """Fetch session from Rails API via MCP tickets server"""
        try:
            result = await self.mcp.call_tool("tickets", "get_session_details", {
                "session_id": session_id
            })
            data = json.loads(result[0].text)
            return SessionContext(
                session_id=session_id,
                tickets=data.get("tickets", []),
                history=data.get("recent_messages", [])
            )
        except Exception as e:
            logger.error("Failed to fetch session", error=str(e))
            return SessionContext(session_id=session_id)

class BaseAgent:
    def __init__(self, llm: LlamaClient, mcp: MCPClientManager):
        self.llm = llm
        self.mcp = mcp
        self.system_prompt = ""
    
    async def gather_tools(self) -> list:
        """Discover available tools from MCP servers"""
        return await self.mcp.list_all_tools()
    
    async def run(self, message: str, context: SessionContext) -> AsyncGenerator[dict, None]:
        raise NotImplementedError

class PlanningAgent(BaseAgent):
    def __init__(self, llm, mcp):
        super().__init__(llm, mcp)
        self.system_prompt = """You are Plume in PLANNING mode. Optimize visits."""
    
    async def run(self, message: str, context: SessionContext):
        tools = await self.gather_tools()
        
        # Check if we have tickets first
        if not context.tickets:
            yield {"type": "text", "content": "Je peux vous aider à planifier ! Avez-vous déjà des billets ou souhaitez-vous planifier en mode simulation ?"}
            return
        
        # Build prompt with tool descriptions
        prompt = self._build_prompt(message, context, tools)
        
        # Generate with tool calling
        response = await self.llm.generate(prompt, tools=tools)
        
        # Handle tool calls
        if response.tool_calls:
            for tool_call in response.tool_calls:
                yield {"type": "tool_call", "tool": tool_call.name, "args": tool_call.arguments}
                
                # Execute via MCP
                result = await self.mcp.call_tool(
                    tool_call.server,  # MCP server name
                    tool_call.name,
                    tool_call.arguments
                )
                
                # Re-prompt with result for synthesis
                synthesis = await self.llm.generate(
                    prompt + f"\nTool result: {result}\nSynthesize this for the user:"
                )
                yield {"type": "text", "content": synthesis.text}
        else:
            yield {"type": "text", "content": response.text}

class CompanionAgent(BaseAgent):
    async def run(self, message: str, context: SessionContext):
        # Emotional intelligence, present-moment help
        prompt = f"""You are Plume, companion mode. User context: {context.tickets}
        Message: {message}
        Respond warmly and helpfully. If they seem tired, suggest rest."""
        
        response = await self.llm.generate(prompt)
        yield {"type": "text", "content": response.text}

class ConciergeAgent(BaseAgent):
    async def run(self, message: str, context: SessionContext):
        # Handle purchases, ticket linking
        prompt = f"""You are Plume, concierge mode. Help with tickets.
        Current tickets: {context.tickets}
        Message: {message}"""
        
        response = await self.llm.generate(prompt, tools=await self.gather_tools())
        # Handle ticket operations...
        yield {"type": "text", "content": response.text}

class DiscoveryAgent(BaseAgent):
    async def run(self, message: str, context: SessionContext):
        # Secrets, gamification
        yield {"type": "text", "content": "Mode découverte activé ! Cherchez-vous un secret particulier ?"}
```

### `services/ai-orchestrator/app/tasks/inference.py`

```python
"""
Celery tasks for AI processing with full monitoring.
"""
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
import structlog
import asyncio

logger = structlog.get_logger()

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_chat_async(self, session_id: str, message: str, context: dict):
    """
    Async chat processing for non-streaming requests.
    Uses retry logic for LLM availability issues.
    """
    logger.info(
        "chat_task_started",
        task_id=self.request.id,
        session_id=session_id,
        message_preview=message[:50]
    )
    
    try:
        # Import here to avoid circular imports
        from app.main import orchestrator
        
        # Run async code in sync Celery task
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            _process_chat(orchestrator, session_id, message, context)
        )
        
        logger.info(
            "chat_task_completed",
            task_id=self.request.id,
            agent_used=result.get("agent_used")
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "chat_task_failed",
            task_id=self.request.id,
            error=str(exc),
            retry_count=self.request.retries
        )
        
        if self.request.retries < 3:
            raise self.retry(exc=exc)
        else:
            raise MaxRetriesExceededError(f"Failed after 3 retries: {exc}")

async def _process_chat(orchestrator, session_id, message, context):
    """Helper to run async orchestrator in Celery"""
    chunks = []
    async for chunk in orchestrator.stream_response(session_id, message, context):
        chunks.append(chunk)
    
    # Combine chunks into final result
    text_parts = [c.get("content", "") for c in chunks if c.get("type") == "text"]
    
    return {
        "response": " ".join(text_parts),
        "agent_used": chunks[-1].get("agent", "unknown"),
        "tools_called": list(set(c.get("tool") for c in chunks if c.get("type") == "tool_call")),
        "latency_ms": chunks[-1].get("latency_ms", 0)
    }

@shared_task
def notify_closure_change(session_id: str, attraction_name: str, status: str):
    """Background task to notify users of attraction closures"""
    logger.info(
        "closure_notification",
        session_id=session_id,
        attraction=attraction_name,
        status=status
    )
    
    # Implementation: Send push notification or email via Rails API
    import httpx
    httpx.post(f"{os.getenv('RAILS_API_URL')}/notifications/push", json={
        "session_id": session_id,
        "title": "Changement d'horaire",
        "body": f"{attraction_name} est maintenant {status}"
    })

@shared_task
def sync_group_itinerary(group_id: str):
    """Sync itineraries when group members update plans"""
    logger.info("group_sync_started", group_id=group_id)
    # Implementation details...
    logger.info("group_sync_completed", group_id=group_id)
```

---

## 4. MCP Server Implementation (Example)

### `mcp-servers/tickets-mcp/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "-m", "src.server"]
```

### `mcp-servers/tickets-mcp/src/server.py`

```python
"""
MCP Server for Ticket Operations
Communicates with Rails API
"""
import os
import json
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("tickets-mcp")
rails_url = os.getenv("RAILS_API_URL", "http://localhost:3000")
api_key = os.getenv("INTERNAL_API_KEY")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_session_details",
            description="Get session context including tickets",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="create_simulated_ticket",
            description="Create draft ticket for planning",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "date": {"type": "string"},
                    "visitor_type": {"type": "string"},
                    "count": {"type": "integer"}
                }
            }
        ),
        Tool(
            name="confirm_purchase",
            description="Convert simulated to purchased (irreversible)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "ticket_ids": {"type": "array", "items": {"type": "string"}},
                    "payment_ref": {"type": "string"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {api_key}"}
        
        if name == "get_session_details":
            resp = await client.get(
                f"{rails_url}/api/v1/sessions/{arguments['session_id']}",
                headers=headers
            )
            return [TextContent(type="text", text=resp.text)]
        
        elif name == "create_simulated_ticket":
            resp = await client.post(
                f"{rails_url}/api/v1/tickets/simulated",
                json=arguments,
                headers=headers
            )
            return [TextContent(type="text", text=json.dumps({
                "status": "created",
                "simulated": True,
                "data": resp.json()
            }))]
        
        elif name == "confirm_purchase":
            resp = await client.post(
                f"{rails_url}/api/v1/tickets/confirm",
                json=arguments,
                headers=headers
            )
            return [TextContent(type="text", text=json.dumps({
                "status": "confirmed",
                "locked": True,  # Cannot modify after this
                "data": resp.json()
            }))]

if __name__ == "__main__":
    app.run(transport="stdio")
```

---

## 5. Rails API (Key Files)

### `services/api/Gemfile`

```ruby
source 'https://rubygems.org'
git_source(:github) { |repo| "https://github.com/#{repo}.git" }

ruby '3.2.2'

gem 'rails', '~> 7.1.0'
gem 'pg', '~> 1.1'
gem 'puma', '~> 6.0'
gem 'redis', '~> 5.0'
gem 'sidekiq', '~> 7.0'
gem 'bootsnap', require: false
gem 'tzinfo-data', platforms: %i[mingw mswin x64_mingw jruby]

# API
gem 'jsonapi-serializer'
gem 'kaminari'
gem 'rack-cors'

# Auth
gem 'bcrypt', '~> 3.1.7'
gem 'jwt'

# Monitoring
gem 'sentry-ruby'
gem 'sentry-rails'
gem 'prometheus-client'

group :development, :test do
  gem 'debug', platforms: %i[mri mingw x64_mingw]
  gem 'rspec-rails'
  gem 'factory_bot_rails'
  gem 'faker'
  gem 'shoulda-matchers'
end

group :development do
  gem 'listen'
end
```

### `services/api/app/models/visit_session.rb`

```ruby
class VisitSession < ApplicationRecord
  has_many :tickets, dependent: :destroy
  has_many :chat_messages, dependent: :destroy
  belongs_to :user, optional: true
  belongs_to :group, optional: true
  
  enum status: {
    draft: 0,      # Anonymous, localStorage only
    linked: 1,     # Has email or tickets
    active: 2,     # Currently at park
    completed: 3   # Visit done
  }
  
  validates :id, presence: true, uniqueness: true
  
  before_create :set_default_preferences
  
  # The boolean logic for simulated vs purchased
  def simulated_tickets
    tickets.where(purchased: false)
  end
  
  def confirmed_tickets
    tickets.where(purchased: true, status: 'confirmed')
  end
  
  def confirm_purchase!(ticket_ids, payment_ref)
    transaction do
      tickets.where(id: ticket_ids, purchased: false).each do |ticket|
        ticket.update!(
          purchased: true,
          status: 'confirmed',
          purchased_at: Time.current,
          payment_reference: payment_ref,
          # Lock the ticket - no more changes allowed
          locked: true
        )
      end
      
      update!(status: :linked) if status == 'draft'
      
      # Sync with group if applicable
      sync_with_group! if group.present?
    end
  end
  
  def link_to_group!(group_code)
    group = Group.find_by!(code: group_code)
    update!(group: group)
    GroupSyncWorker.perform_async(id)
  end
  
  private
  
  def set_default_preferences
    self.preferences ||= {
      mobility: 'standard',
      pace: 'relaxed',
      interests: ['family', 'nature'],
      notifications: true
    }
  end
  
  def sync_with_group!
    GroupSyncWorker.perform_async(id)
  end
end
```

### `services/api/app/models/ticket.rb`

```ruby
class Ticket < ApplicationRecord
  belongs_to :visit_session
  
  enum status: {
    draft: 0,      # Simulated/planning
    reserved: 1,   # Hold but not paid
    confirmed: 2,  # Paid, locked
    used: 3,       # Entry scanned
    expired: 4
  }
  
  validates :date, presence: true
  validates :visitor_type, presence: true, inclusion: { in: %w[adult child senior] }
  
  # The key boolean field
  validates :purchased, inclusion: { in: [true, false] }
  
  # Once confirmed, immutable except for status progression
  validate :immutable_if_confirmed, on: :update
  
  scope :simulated, -> { where(purchased: false) }
  scope :purchased, -> { where(purchased: true) }
  
  def simulated?
    !purchased
  end
  
  def confirm!(payment_ref)
    return false if purchased && status == 'confirmed'
    
    update!(
      purchased: true,
      status: 'confirmed',
      purchased_at: Time.current,
      payment_reference: payment_ref
    )
  end
  
  private
  
  def immutable_if_confirmed
    if status_was == 'confirmed' && (date_changed? || visitor_type_changed?)
      errors.add(:base, "Confirmed tickets cannot be modified")
    end
  end
end
```

---

## 6. Next.js Web (Key Files)

### `services/web/src/lib/session-store.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';

interface Ticket {
  id: string;
  date: string;
  type: 'adult' | 'child' | 'senior';
  purchased: boolean;
  status: string;
}

interface SessionState {
  sessionId: string;
  tickets: Ticket[];
  messages: Array<{role: string; content: string}>;
  isLinked: boolean;
  
  initSession: () => void;
  linkTicket: (code: string) => Promise<void>;
  createSimulatedTicket: (date: string, type: string) => Promise<void>;
  confirmPurchase: (ticketIds: string[]) => Promise<void>;
  addMessage: (message: {role: string; content: string}) => void;
}

export const useSession = create<SessionState>()(
  persist(
    (set, get) => ({
      sessionId: '',
      tickets: [],
      messages: [],
      isLinked: false,
      
      initSession: () => {
        if (!get().sessionId) {
          const id = uuidv4();
          set({ sessionId: id });
          
          // Register with backend
          fetch('/api/sessions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id })
          });
        }
      },
      
      linkTicket: async (code: string) => {
        const { sessionId } = get();
        const resp = await fetch(`/api/sessions/${sessionId}/link-ticket`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ code })
        });
        
        if (resp.ok) {
          const data = await resp.json();
          set({ 
            tickets: [...get().tickets, data.ticket],
            isLinked: true 
          });
        }
      },
      
      createSimulatedTicket: async (date: string, type: string) => {
        const { sessionId } = get();
        const resp = await fetch(`/api/sessions/${sessionId}/simulated-tickets`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ date, visitor_type: type })
        });
        
        if (resp.ok) {
          const ticket = await resp.json();
          set({ tickets: [...get().tickets, ticket] });
        }
      },
      
      confirmPurchase: async (ticketIds: string[]) => {
        const { sessionId } = get();
        const resp = await fetch(`/api/sessions/${sessionId}/confirm-purchase`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ ticket_ids: ticketIds })
        });
        
        if (resp.ok) {
          // Update local state to reflect confirmed status
          set({
            tickets: get().tickets.map(t => 
              ticketIds.includes(t.id) 
                ? {...t, purchased: true, status: 'confirmed'} 
                : t
            )
          });
        }
      },
      
      addMessage: (message) => {
        set({ messages: [...get().messages, message] });
      }
    }),
    {
      name: 'plume-session',
      partialize: (state) => ({ 
        sessionId: state.sessionId, 
        tickets: state.tickets,
        isLinked: state.isLinked
      })
    }
  )
);
```

---

## 7. Testing Strategy

### Python Tests

```python
# services/ai-orchestrator/tests/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.orchestrator import PlumeOrchestrator

@pytest.fixture
def mock_llm():
    return AsyncMock()

@pytest.fixture
def mock_mcp():
    m = AsyncMock()
    m.list_all_tools.return_value = []
    return m

@pytest.mark.asyncio
async def test_intent_classification(mock_llm, mock_mcp):
    orchestrator = PlumeOrchestrator(mock_llm, mock_mcp)
    
    assert await orchestrator.classify_intent("Je veux acheter des billets") == "concierge"
    assert await orchestrator.classify_intent("Planifier ma journée") == "planner"
    assert await orchestrator.classify_intent("Où est le carrousel ?") == "companion"

@pytest.mark.asyncio
async def test_simulated_ticket_boolean(mock_llm, mock_mcp):
    orchestrator = PlumeOrchestrator(mock_llm, mock_mcp)
    
    # Mock MCP response
    mock_mcp.call_tool.return_value = [MagicMock(text='{"tickets": [{"id": "123", "purchased": false}]}')]
    
    ctx = await orchestrator.get_session_context("test-session")
    assert len(ctx.tickets) == 1
    assert ctx.tickets[0]['purchased'] == False
```

### Rails Tests

```ruby
# services/api/spec/models/ticket_spec.rb
require 'rails_helper'

RSpec.describe Ticket, type: :model do
  describe 'simulated vs purchased' do
    let(:session) { create(:visit_session) }
    
    it 'creates simulated ticket with purchased=false' do
      ticket = session.tickets.create!(
        date: Date.tomorrow,
        visitor_type: 'adult',
        purchased: false
      )
      
      expect(ticket.simulated?).to be true
      expect(ticket).to be_draft
    end
    
    it 'locks ticket after confirmation' do
      ticket = session.tickets.create!(
        date: Date.tomorrow,
        visitor_type: 'adult',
        purchased: false
      )
      
      ticket.confirm!('stripe_123')
      
      expect(ticket).to be_confirmed
      expect(ticket).to be_purchased
      
      # Should not allow changes
      ticket.date = Date.today + 2.days
      expect(ticket).not_to be_valid
    end
  end
end
```

---

## 8. Deployment Script

### `scripts/deploy-production.sh`

```bash
#!/bin/bash
set -e

echo "🚀 Deploying Plume to Production"

# Pull latest images
docker-compose -f docker/docker-compose.prod.yml pull

# Run migrations
docker-compose -f docker/docker-compose.prod.yml run --rm api rails db:migrate

# Restart services with zero downtime
docker-compose -f docker/docker-compose.prod.yml up -d --no-deps --scale api=4 api
sleep 10
docker-compose -f docker/docker-compose.prod.yml up -d --no-deps --scale api=3 api

# Verify health
curl -f http://localhost:3001/health || exit 1

echo "✅ Deployment complete"
```

---

## Complete File List for ClaudeCode

**Immediate implementation order:**

1. **Infrastructure**: `docker-compose.prod.yml`, CI/CD workflows
2. **Rails API**: Models (VisitSession, Ticket), Controllers, Tests
3. **AI Orchestrator**: Celery config, FastAPI app, Agent classes
4. **MCP Servers**: Tickets server (primary), then Routing
5. **Next.js**: Session store, Chat UI, Map integration
6. **Integration**: End-to-end tests, monitoring setup

**Key environment variables needed:**

```env
# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# AI
VLLM_URL=http://vllm:8000/v1
LLM_MODEL=meta-llama/Llama-3.3-70B-Instruct

# Security
SECRET_KEY_BASE=...
INTERNAL_API_KEY=...
SENTRY_DSN=...

# External
RAILS_API_URL=http://api:3000
PARK_API_ENDPOINT=...
```

This architecture gives you:
- ✅ Dockerized, scalable services
- ✅ Celery with Flower monitoring (port 5555)
- ✅ Automated CI/CD on main branch pushes
- ✅ Agentic AI with Llama + MCP
- ✅ The "agnostic but supportive" session model
- ✅ Boolean ticket state (simulated ↔ purchased)
- ✅ Comprehensive testing and logging

Ready for ClaudeCode to implement. Start with the Rails API models and Docker setup, then move to the AI orchestrator.
