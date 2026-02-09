import asyncio
import logging
from sqlalchemy import text
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.context import EvaluationContext
from app.rule_engine.parser import RuleParser
from app.core.database import async_session

logging.basicConfig(level=logging.INFO)


async def test_condition(db, poname, condition_ast):
    res = await db.execute(
        text(f"SELECT id, name, properties FROM graph_entities WHERE name = '{poname}'")
    )
    po = res.first()
    if not po:
        print(f"PO {poname} not found")
        return None

    poid, poname, poprops = po
    entity = {**poprops, "id": poid, "name": poname, "__type__": "PurchaseOrder"}
    context = EvaluationContext(entity=entity, old_values={}, session=db)
    evaluator = ExpressionEvaluator(context)
    return await evaluator.evaluate(condition_ast)


async def verify():
    parser = RuleParser()
    dsl = """
    ACTION PurchaseOrder.openPO {
        PRECONDITION checkSupplier: NOT EXISTS(this -[orderedFrom]-> s:Supplier WHERE s.status != "Active")
            ON_FAILURE: "Fail"
        EFFECT { SET this.status = "Open"; }
    }
    """
    actions = parser.parse(dsl)
    condition = actions[0].preconditions[0].condition

    async with async_session() as db:
        # 1. PO-0017 (OfficePro Supplies)
        print("\n--- Testing PO-0017 (Blacklisted supplier) ---")
        # Ensure OfficePro Supplies is Blacklisted
        await db.execute(
            text(
                "UPDATE graph_entities SET properties = properties || '{\"status\": \"Blacklisted\"}'::jsonb WHERE name = 'OfficePro Supplies'"
            )
        )
        await db.commit()
        res = await test_condition(db, "PO-0017", condition)
        print(f"PO-0017 result: {res}")
        assert res is False, "PO-0017 should FAIL precondition"

        # 2. PO-0017 with ACTIVE supplier
        print("\n--- Testing PO-0017 with ACTIVE supplier ---")
        await db.execute(
            text(
                "UPDATE graph_entities SET properties = properties || '{\"status\": \"Active\"}'::jsonb WHERE name = 'OfficePro Supplies'"
            )
        )
        await db.commit()
        res = await test_condition(db, "PO-0017", condition)
        print(f"PO-0017 result (Active): {res}")
        assert res is True, "PO-0017 should PASS precondition with active supplier"

    print("\nALL TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(verify())
