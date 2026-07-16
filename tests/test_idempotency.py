import pytest
from httpx import AsyncClient

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

    # 2. First usage event
    headers = {"Idempotency-Key": "first-unique-key"}
    payload = {"customer_id": cust_id, "product_id": prod_id, "quantity": "1"}
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 200
    tx1 = res.json()
    assert float(tx1["amount"]) == -5.00
    assert float(tx1["remaining_balance"]) == 5.00

    # 3. Duplicate usage event (same key, same payload) -> should return cached response
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 200
    tx2 = res.json()
    assert tx1["transaction_id"] == tx2["transaction_id"]
    assert float(tx2["remaining_balance"]) == 5.00

    # Verify balance is still 5.00 (not double charged)
    res = await client.get(f"/customers/{cust_id}/balance")
    assert float(res.json()["balance"]) == 5.00

    # 4. Conflicting usage event (same key, different payload) -> should reject
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

    # Customer has 0 balance, so this usage event will fail due to insufficient funds
    headers = {"Idempotency-Key": "failing-key"}
    payload = {"customer_id": cust_id, "product_id": prod_id, "quantity": "1"}
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Insufficient funds" in res.json()["detail"]

    # Now, add 150.00 credit to customer
    await client.post(f"/customers/{cust_id}/credit", json={"amount": "150.00"})

    # Retry the exact same request with the same idempotency key. It should now succeed!
    res = await client.post("/usage", json=payload, headers=headers)
    assert res.status_code == 200
    tx = res.json()
    assert float(tx["amount"]) == -100.00
    assert float(tx["remaining_balance"]) == 50.00
