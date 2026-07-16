import asyncio
import pytest
from httpx import AsyncClient
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.outbox import OutboxEvent
from app.models.idempotency import IdempotencyKey

@pytest.mark.asyncio
async def test_asynchronous_outbox_pipeline(client: AsyncClient):
    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Async Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Server Unit", "price_per_unit": "0.10"})
    prod = res.json()
    prod_id = prod["id"]

    # Credit 20.00 USD
    await client.post(f"/customers/{cust_id}/credit", json={"amount": "20.00"})

    # 2. Report Usage (Asynchronous Outbox Ingestion)
    headers = {"Idempotency-Key": "async-key-1"}
    payload = {"customer_id": cust_id, "product_id": prod_id, "quantity": "50"}  # Charge: 5.00 USD
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 202
    assert res.json()["status"] == "accepted"

    # 3. Wait for background outbox publisher loop to pick up and process the event
    # We will poll every 0.1 seconds up to 3 seconds
    success = False
    for _ in range(30):
        await asyncio.sleep(0.1)
        res = await client.get(f"/customers/{cust_id}/balance")
        assert res.status_code == 200, f"Error getting balance: {res.status_code} - {res.json()}"
        if float(res.json()["balance"]) == 15.00:
            success = True
            break

    assert success, "Asynchronous outbox processing did not complete within the timeout period."

    # 4. Verify Database State
    async with AsyncSessionLocal() as session:
        # Verify Outbox event status updated to PUBLISHED
        outbox_res = await session.execute(select(OutboxEvent))
        events = outbox_res.scalars().all()
        assert len(events) == 1
        assert events[0].status == "PUBLISHED"

        # Verify Idempotency status updated to SUCCESS and response body cached
        idemp_res = await session.execute(select(IdempotencyKey))
        keys = idemp_res.scalars().all()
        assert len(keys) == 1
        assert keys[0].status == "SUCCESS"
        assert float(keys[0].response_body["remaining_balance"]) == 15.00
        assert keys[0].response_body["transaction_id"] is not None

    # 5. Subsequent duplicate request with same idempotency key should return HTTP 200 and cached response
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert float(data["remaining_balance"]) == 15.00
    assert data["customer_id"] == cust_id

@pytest.mark.asyncio
async def test_outbox_publisher_resilience(client: AsyncClient):
    from unittest.mock import patch

    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Resilient Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Resilient Unit", "price_per_unit": "10.00"})
    prod = res.json()
    prod_id = prod["id"]

    await client.post(f"/customers/{cust_id}/credit", json={"amount": "100.00"})

    # 2. Mock Celery dispatch to fail once, then succeed
    from app.services.outbox_publisher import process_usage_task
    
    original_delay = process_usage_task.delay
    call_count = 0

    def mock_delay(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Celery connection error (simulated)")
        return original_delay(*args, **kwargs)

    with patch("app.services.outbox_publisher.process_usage_task.delay", side_effect=mock_delay):
        # Report usage
        headers = {"Idempotency-Key": "resilience-key"}
        payload = {"customer_id": cust_id, "product_id": prod_id, "quantity": "1"}
        res = await client.post("/usage", json=payload, headers=headers)
        assert res.status_code == 202

        # Poll balance. It should fail on first iteration, then succeed on the next iteration
        success = False
        for _ in range(30):
            await asyncio.sleep(0.1)
            res = await client.get(f"/customers/{cust_id}/balance")
            if float(res.json()["balance"]) == 90.00:
                success = True
                break

        assert success, "Outbox publisher did not recover and publish the event after transient failure."
        assert call_count >= 2

