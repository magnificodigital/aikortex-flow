import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.gateway.config import get_gateway_config
from app.gateway.deps import langgraph_runtime
from app.gateway.routers import (
    agents,
    artifacts,
    assistants_compat,
    channels,
    mcp,
    memory,
    models,
    runs,
    skills,
    suggestions,
    thread_runs,
    threads,
    uploads,
)
from deerflow.config.app_config import get_app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""

    # Load config and check necessary environment variables at startup
    try:
        get_app_config()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration during gateway startup: {e}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from e
    config = get_gateway_config()
    logger.info(f"Starting API Gateway on {config.host}:{config.port}")

    # Initialize LangGraph runtime components (StreamBridge, RunManager, checkpointer, store)
    async with langgraph_runtime(app):
        logger.info("LangGraph runtime initialised")

        # Start IM channel service if any channels are configured
        try:
            from app.channels.service import start_channel_service

            channel_service = await start_channel_service()
            logger.info("Channel service started: %s", channel_service.get_status())
        except Exception:
            logger.exception("No IM channels configured or channel service failed to start")

        yield

        # Stop channel service on shutdown
        try:
            from app.channels.service import stop_channel_service

            await stop_channel_service()
        except Exception:
            logger.exception("Failed to stop channel service")

    logger.info("Shutting down API Gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """

    app = FastAPI(
        title="Aikortex Flow Engine",
        description="""
## Aikortex Flow Engine

Motor de agentes de IA da plataforma Aikortex, baseado em LangGraph com capacidades avançadas de execução.

### Funcionalidades

- **Modelos**: Consulte e gerencie os modelos de IA disponíveis
- **MCP**: Gerencie configurações de servidores Model Context Protocol
- **Memória**: Acesse e gerencie memória global para conversas personalizadas
- **Skills**: Consulte e gerencie skills e seus status
- **Artefatos**: Acesse artefatos e arquivos gerados por threads
- **Monitoramento**: Endpoints de health check do sistema

### Arquitetura

Requisições LangGraph são tratadas pelo proxy reverso nginx.
Este gateway fornece endpoints customizados para modelos, MCP, skills e artefatos.
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "models",
                "description": "Operações para consultar modelos de IA disponíveis e suas configurações",
            },
            {
                "name": "mcp",
                "description": "Gerenciar configurações de servidores Model Context Protocol (MCP)",
            },
            {
                "name": "memory",
                "description": "Acessar e gerenciar memória global para conversas personalizadas",
            },
            {
                "name": "skills",
                "description": "Gerenciar skills e suas configurações",
            },
            {
                "name": "artifacts",
                "description": "Acessar e baixar artefatos e arquivos gerados por threads",
            },
            {
                "name": "uploads",
                "description": "Upload e gerenciamento de arquivos de usuário para threads",
            },
            {
                "name": "threads",
                "description": "Gerenciar dados de filesystem local por thread",
            },
            {
                "name": "agents",
                "description": "Criar e gerenciar agentes customizados com config e prompts por agente",
            },
            {
                "name": "suggestions",
                "description": "Gerar sugestões de perguntas de acompanhamento para conversas",
            },
            {
                "name": "channels",
                "description": "Gerenciar integrações de canais (Feishu, Slack, Telegram)",
            },
            {
                "name": "assistants-compat",
                "description": "API de assistants compatível com LangGraph Platform (stub)",
            },
            {
                "name": "runs",
                "description": "Ciclo de vida de runs compatível com LangGraph Platform (criar, stream, cancelar)",
            },
            {
                "name": "health",
                "description": "Endpoints de health check e status do sistema",
            },
        ],
    )

    # CORS is handled by nginx - no need for FastAPI middleware

    # Include routers
    app.include_router(models.router)
    app.include_router(mcp.router)
    app.include_router(memory.router)
    app.include_router(skills.router)
    app.include_router(artifacts.router)
    app.include_router(uploads.router)
    app.include_router(threads.router)
    app.include_router(agents.router)
    app.include_router(suggestions.router)
    app.include_router(channels.router)
    app.include_router(assistants_compat.router)
    app.include_router(thread_runs.router)
    app.include_router(runs.router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint.

        Returns:
            Service health status information.
        """
        return {"status": "healthy", "service": "aikortex-flow-engine"}

    return app


# Create app instance for uvicorn
app = create_app()
