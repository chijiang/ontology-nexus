# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.core.config import settings
from app.api import auth, config, chat, graph, conversations, actions, rules
from app.core.database import engine, Base
import app.models  # Implicitly registers models

# Import rule engine components
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.rule_engine import RuleEngine
from app.services.rule_storage import RuleStorage

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize rule engine components
    action_registry = ActionRegistry()
    action_executor = ActionExecutor(action_registry)
    rule_registry = RuleRegistry()
    rule_engine = RuleEngine(rule_registry)

    # Initialize rule storage
    rules_dir = Path(__file__).parent.parent / "rules"
    rules_dir.mkdir(exist_ok=True)
    rule_storage = RuleStorage(rules_dir)

    # Load any existing rules from storage
    for rule_data in rule_storage.list_rules():
        rule_details = rule_storage.load_rule(rule_data["name"])
        if rule_details:
            try:
                rule_registry.load_from_file(rule_details["dsl_content"])
            except Exception:
                # Skip invalid rules
                pass

    # Initialize API modules
    actions.init_actions_api(action_registry, action_executor)
    rules.init_rules_api(rule_registry, rule_storage)

    # Store in app state for access
    app.state.action_registry = action_registry
    app.state.action_executor = action_executor
    app.state.rule_registry = rule_registry
    app.state.rule_engine = rule_engine
    app.state.rule_storage = rule_storage


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
