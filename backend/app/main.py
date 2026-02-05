# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.core.config import settings
from app.api import auth, config, chat, graph, conversations, actions, rules
from app.core.database import engine, Base, async_session
import app.models  # Implicitly registers models

# Import rule engine components
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.rule_engine import RuleEngine
from app.rule_engine.event_emitter import GraphEventEmitter
from app.services.rule_storage import RuleStorage
from app.core.neo4j_pool import get_neo4j_driver
from app.core.init_db import init_db

app = FastAPI(title="Knowledge Graph QA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()

    # Create event emitter early for dependency injection
    event_emitter = GraphEventEmitter()
    
    action_registry = ActionRegistry()
    action_executor = ActionExecutor(action_registry, event_emitter=event_emitter)
    rule_registry = RuleRegistry()

    # Get global Neo4j config from database
    async with async_session() as session:
        from app.models.neo4j_config import Neo4jConfig
        from sqlalchemy import select
        from app.core.security import decrypt_data

        result = await session.execute(select(Neo4jConfig).limit(1))
        db_config = result.scalar_one_or_none()

        neo4j_uri = settings.NEO4J_URI
        neo4j_user = settings.NEO4J_USERNAME
        neo4j_pass = settings.NEO4J_PASSWORD

        if db_config:
            neo4j_uri = decrypt_data(db_config.uri_encrypted)
            neo4j_user = decrypt_data(db_config.username_encrypted)
            neo4j_pass = decrypt_data(db_config.password_encrypted)

    # Get Neo4j driver for rule engine
    neo4j_driver = None
    if neo4j_uri:
        try:
            neo4j_driver = await get_neo4j_driver(
                uri=neo4j_uri, username=neo4j_user, password=neo4j_pass
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to initialize Neo4j driver: {e}")
    else:
        import logging

        logging.getLogger(__name__).warning(
            "Neo4j not configured, rule engine will start without Neo4j."
        )

    # event_emitter created earlier

    # Define a driver provider for RuleEngine resilience
    async def driver_provider():
        async with async_session() as session:
            from app.models.neo4j_config import Neo4jConfig
            from sqlalchemy import select
            from app.core.security import decrypt_data

            result = await session.execute(select(Neo4jConfig).limit(1))
            db_config = result.scalar_one_or_none()

            uri, user, pw = (
                settings.NEO4J_URI,
                settings.NEO4J_USERNAME,
                settings.NEO4J_PASSWORD,
            )
            if db_config:
                uri = decrypt_data(db_config.uri_encrypted)
                user = decrypt_data(db_config.username_encrypted)
                pw = decrypt_data(db_config.password_encrypted)

            if not uri:
                return None

            return await get_neo4j_driver(uri=uri, username=user, password=pw)

    # Create RuleEngine with all dependencies
    rule_engine = RuleEngine(
        action_registry, rule_registry, neo4j_driver, driver_provider=driver_provider
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
            except Exception:
                # Skip invalid rules
                pass

    # Load rules from database
    import logging

    logger = logging.getLogger(__name__)
    async with async_session() as session:
        from app.repositories.rule_repository import RuleRepository
        from sqlalchemy import select
        from app.models.rule import Rule

        repo = RuleRepository(session)
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
        from app.models.rule import ActionDefinition
        from app.rule_engine.models import ActionDef

        result = await session.execute(
            select(ActionDefinition).where(ActionDefinition.is_active == True)
        )
        db_actions = result.scalars().all()

        logger.info(f"Loading {len(db_actions)} actions from database")

        from app.rule_engine.parser import RuleParser

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

    # Store in app state for access
    app.state.action_registry = action_registry
    app.state.action_executor = action_executor
    app.state.rule_registry = rule_registry
    app.state.rule_engine = rule_engine
    app.state.rule_storage = rule_storage
    app.state.neo4j_driver = neo4j_driver
    app.state.event_emitter = event_emitter


@app.on_event("shutdown")
async def shutdown():
    from app.core.neo4j_pool import close_neo4j

    await close_neo4j()


app.include_router(auth.router)
app.include_router(config.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(conversations.router)
app.include_router(actions.router)
app.include_router(rules.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
