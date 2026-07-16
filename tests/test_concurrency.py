import asyncio
import pytest
from httpx import AsyncClient
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.idempotency import IdempotencyKey

@pytest.mark.asyncio
async def test_concurrent_billing_prevents_overdraft(client: AsyncClient):
    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Concurrent Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Compute Hour", "price_per_unit": "10.00"})
    prod = res.json()
    prod_id = prod["id"]

    # Credit 25.00 USD
    await client.post(f"/customers/{cust_id}/credit", json={"amount": "25.00"})

    # 2. Fire 3 concurrent usage reports of 10.00 USD (Total = 30.00 USD, which exceeds 25.00 USD balance)
    # We must use different idempotency keys for each request
    keys = ["concur-key-1", "concur-key-2", "concur-key-3"]
    payloads = [{"customer_id": cust_id, "product_id": prod_id, "quantity": "1"} for _ in range(3)]

    # Gather the requests (all should be accepted with HTTP 202)
    tasks = [
        client.post("/usage", json=p, headers={"Idempotency-Key": k})
        for p, k in zip(payloads, keys)
    ]
    responses = await asyncio.gather(*tasks)

    for r in responses:
        assert r.status_code == 202

    # 3. Wait for background outbox publisher loop and worker to process all 3 tasks
    # We poll every 0.1 seconds up to 3 seconds until balance reaches 5.00 USD
    success = False
    for _ in range(30):
        await asyncio.sleep(0.1)
        res = await client.get(f"/customers/{cust_id}/balance")
        assert res.status_code == 200
        if float(res.json()["balance"]) == 5.00:
            success = True
            break

    assert success, "Concurrent billing events were not fully processed or double-charged."

    # 4. Verify Idempotency records: two must be SUCCESS, one must be FAILED
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key.in_(keys))
        )
        keys_in_db = result.scalars().all()
        assert len(keys_in_db) == 3

        success_count = sum(1 for k in keys_in_db if k.status == "SUCCESS")
        failed_count = sum(1 for k in keys_in_db if k.status == "FAILED")

        assert success_count == 2
        assert failed_count == 1
