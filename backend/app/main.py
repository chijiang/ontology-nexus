# backend/app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.api import (
    auth,
    config,
    chat,
    graph,
    conversations,
    actions,
    rules,
    data_products,
    data_mappings,
    users,
    roles,
)
from app.core.database import engine, Base, async_session, get_db
import app.models  # Implicitly registers models

# Import rule engine components
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.rule_engine import RuleEngine
from app.rule_engine.event_emitter import GraphEventEmitter
from app.rule_engine.parser import RuleParser
from app.rule_engine.models import ActionDef
from app.services.rule_storage import RuleStorage
from app.services.permission_service import init_permission_service
from app.core.init_db import init_db
from app.repositories.rule_repository import RuleRepository
from app.models.rule import Rule, ActionDefinition

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Startup ===
    await init_db()

    # Create event emitter early for dependency injection
    event_emitter = GraphEventEmitter()

    action_registry = ActionRegistry()
    action_executor = ActionExecutor(action_registry, event_emitter=event_emitter)
    rule_registry = RuleRegistry()

    # Create RuleEngine with database session provider
    rule_engine = RuleEngine(
        action_registry,
        rule_registry,
        db_session=None,
        session_provider=async_session,
    )

    # Connect event emitter to rule engine
    event_emitter.subscribe(rule_engine.on_event)

    # Initialize rule storage
    rules_dir = Path(__file__).parent.parent / "rules"
    rules_dir.mkdir(exist_ok=True)
    rule_storage = RuleStorage(rules_dir)

    # Load any existing rules from file storage
    for rule_data in rule_storage.list_rules():
        rule_details = rule_storage.load_rule(rule_data["name"])
        if rule_details:
            try:
                rule_registry.load_from_dsl(rule_details["dsl_content"])
            except Exception as e:
                logger.warning("Failed to load rule '%s' from file storage: %s", rule_data["name"], e)

    # Load rules from database
    async with async_session() as session:
        result = await session.execute(select(Rule).where(Rule.is_active == True))
        db_rules = result.scalars().all()

        logger.info(f"Loading {len(db_rules)} rules from database")

        for db_rule in db_rules:
            try:
                rule_registry.load_from_dsl(db_rule.dsl_content)
                logger.info(f"Loaded rule '{db_rule.name}' from database")
            except Exception as e:
                logger.warning(f"Failed to load rule '{db_rule.name}': {e}")

    logger.info(f"Rule registry has {len(rule_registry)} rules loaded")

    # Load actions from database
    async with async_session() as session:
        result = await session.execute(
            select(ActionDefinition).where(ActionDefinition.is_active == True)
        )
        db_actions = result.scalars().all()

        logger.info(f"Loading {len(db_actions)} actions from database")

        parser = RuleParser()
        for db_action in db_actions:
            try:
                parsed = parser.parse(db_action.dsl_content)
                for item in parsed:
                    if isinstance(item, ActionDef):
                        action_registry.register(item)
                logger.info(f"Loaded action '{db_action.name}' from database")
            except Exception as e:
                logger.warning(f"Failed to load action '{db_action.name}': {e}")

    # Initialize API modules
    actions.init_actions_api(action_registry, action_executor)
    rules.init_rules_api(rule_registry, rule_storage)
    init_permission_service(action_registry)

    # Store in app state for access
    app.state.action_registry = action_registry
    app.state.action_executor = action_executor
    app.state.rule_registry = rule_registry
    app.state.rule_engine = rule_engine
    app.state.rule_storage = rule_storage
    app.state.event_emitter = event_emitter

    yield

    # === Shutdown ===
    await engine.dispose()
    logger.info("Database engine disposed")


app = FastAPI(title="Knowledge Graph QA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(conversations.router)
app.include_router(actions.router)
app.include_router(rules.router)
app.include_router(data_products.router)
app.include_router(data_mappings.router)
app.include_router(users.router)
app.include_router(roles.router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": "database unreachable"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
