import asyncio
import pytest
from httpx import AsyncClient

async def wait_for_balance(client: AsyncClient, customer_id: str, expected_balance: float, timeout: float = 3.0) -> None:
    steps = int(timeout / 0.1)
    for _ in range(steps):
        await asyncio.sleep(0.1)
        res = await client.get(f"/customers/{customer_id}/balance")
        assert res.status_code == 200
        if float(res.json()["balance"]) == expected_balance:
            return
    res = await client.get(f"/customers/{customer_id}/balance")
    raise AssertionError(f"Balance did not reach {expected_balance}. Current: {res.json()['balance']}")

@pytest.mark.asyncio
async def test_idempotency_workflow(client: AsyncClient):
    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Idempotency Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Storage GB", "price_per_unit": "5.00"})
    prod = res.json()
    prod_id = prod["id"]

    # Add 10 USD credit
    await client.post(f"/customers/{cust_id}/credit", json={"amount": "10.00"})

    # 2. First usage event (asynchronous ingestion)
    headers = {"Idempotency-Key": "first-unique-key"}
    payload = {"customer_id": cust_id, "product_id": prod_id, "quantity": "1"}
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 202
    assert res.json()["status"] == "accepted"

    # Wait for processing to complete
    await wait_for_balance(client, cust_id, 5.00)

    # 3. Duplicate usage event (same key, same payload) -> should return HTTP 200 and cached response
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 200
    tx2 = res.json()
    assert float(tx2["remaining_balance"]) == 5.00

    # Verify balance is still 5.00 (not double charged)
    res = await client.get(f"/customers/{cust_id}/balance")
    assert float(res.json()["balance"]) == 5.00

    # 4. Conflicting usage event (same key, different payload) -> should reject with HTTP 400
    payload_conflicting = {"customer_id": cust_id, "product_id": prod_id, "quantity": "2"}
    res = await client.post("/usage", json=payload_conflicting, headers=headers)
    assert res.status_code == 400
    assert "Idempotency key conflict" in res.json()["detail"]

@pytest.mark.asyncio
async def test_failed_request_retry_is_allowed(client: AsyncClient):
    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Retry Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Heavy Compute", "price_per_unit": "100.00"})
    prod = res.json()
    prod_id = prod["id"]

    # Customer has 0 balance. Usage request will be accepted (202), but the background worker will fail it due to insufficient funds.
    headers = {"Idempotency-Key": "failing-key"}
    payload = {"customer_id": cust_id, "product_id": prod_id, "quantity": "1"}
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 202

    # Wait to let the worker process it and mark it FAILED in the DB
    await asyncio.sleep(0.8)

    # Verify key status is cached as failed by retrying payload or checking DB.
    # In this state, balance is still 0
    res = await client.get(f"/customers/{cust_id}/balance")
    assert float(res.json()["balance"]) == 0.00

    # Now, add 150.00 credit to customer
    await client.post(f"/customers/{cust_id}/credit", json={"amount": "150.00"})

    # Retry the exact same request with the same idempotency key. It should now succeed!
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 202

    # Wait for processing to complete
    await wait_for_balance(client, cust_id, 50.00)


@pytest.mark.asyncio
async def test_process_usage_sync_rollback_bug(client: AsyncClient):
    from decimal import Decimal
    from fastapi import HTTPException
    from app.database import AsyncSessionLocal
    from app.services.billing import BillingService
    from app.repositories.idempotency import IdempotencyRepository

    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Sync Rollback Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Sync Rollback Product", "price_per_unit": "100.00"})
    prod = res.json()
    prod_id = prod["id"]

    # Customer has 0 balance. Calling process_usage_sync directly should raise HTTP 400 (Insufficient funds)
    async with AsyncSessionLocal() as session:
        billing_service = BillingService(session)
        with pytest.raises(HTTPException) as exc_info:
            await billing_service.process_usage_sync(
                idempotency_key="sync-rollback-key",
                request_path="/usage",
                payload_hash="some-hash",
                customer_id=cust_id,
                product_id=prod_id,
                quantity=Decimal("1.00")
            )
        assert exc_info.value.status_code == 400
        assert "Insufficient funds" in exc_info.value.detail

    # Verify that the idempotency key was successfully committed with FAILED status
    async with AsyncSessionLocal() as session:
        idemp_repo = IdempotencyRepository(session)
        ik = await idemp_repo.get("sync-rollback-key")
        assert ik is not None, "Idempotency key was not saved in the database!"
        assert ik.status == "FAILED", f"Expected status FAILED, got {ik.status}"

