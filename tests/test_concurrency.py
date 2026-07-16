import asyncio
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_concurrent_billing_prevents_overdraft(client: AsyncClient):
    # 1. Setup Customer and Product
    res = await client.post("/customers", json={"name": "Concurrent Customer"})
    cust = res.json()
    cust_id = cust["id"]

    res = await client.post("/products", json={"name": "Compute Hour", "price_per_unit": "10.00"})
    prod = res.json()
    prod_id = prod["id"]

    # Credit 25.00
    await client.post(f"/customers/{cust_id}/credit", json={"amount": "25.00"})

    # 2. Fire 3 concurrent usage reports of 10.00 USD (Total = 30.00 USD, which exceeds 25.00 USD balance)
    # We must use different idempotency keys for each request
    keys = ["concur-key-1", "concur-key-2", "concur-key-3"]
    payloads = [{"customer_id": cust_id, "product_id": prod_id, "quantity": "1"} for _ in range(3)]

    # Gather the requests
    tasks = [
        client.post("/usage", json=p, headers={"Idempotency-Key": k})
        for p, k in zip(payloads, keys)
    ]
    responses = await asyncio.gather(*tasks)

    # 3. Analyze responses
    success_count = 0
    insufficient_funds_count = 0

    for r in responses:
        if r.status_code == 200:
            success_count += 1
        elif r.status_code == 400 and "Insufficient funds" in r.json().get("detail", ""):
            insufficient_funds_count += 1

    # 4. Verify invariants
    assert success_count == 2
    assert insufficient_funds_count == 1

    # Final balance check: must be exactly 5.00 (25.00 - 2 * 10.00)
    res = await client.get(f"/customers/{cust_id}/balance")
    assert float(res.json()["balance"]) == 5.00
