import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_and_get_customer(client: AsyncClient):
    # 1. Create customer
    response = await client.post("/customers", json={"name": "Alice"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Alice"
    assert float(data["balance"]) == 0.0

    customer_id = data["id"]

    # 2. Get customer
    response = await client.get(f"/customers/{customer_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer_id
    assert data["name"] == "Alice"

@pytest.mark.asyncio
async def test_get_nonexistent_customer(client: AsyncClient):
    response = await client.get("/customers/non-existent-id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_and_get_product(client: AsyncClient):
    # 1. Create product
    response = await client.post("/products", json={"name": "Compute Unit", "price_per_unit": "0.0015"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Compute Unit"
    assert float(data["price_per_unit"]) == 0.0015

    product_id = data["id"]

    # 2. Get product
    response = await client.get(f"/products/{product_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == "Compute Unit"
    assert float(data["price_per_unit"]) == 0.0015

@pytest.mark.asyncio
async def test_add_credit_and_list_transactions(client: AsyncClient):
    # 1. Create customer
    response = await client.post("/customers", json={"name": "Bob"})
    assert response.status_code == 201
    customer = response.json()
    customer_id = customer["id"]

    # 2. Add credit
    response = await client.post(f"/customers/{customer_id}/credit", json={"amount": "100.50"})
    assert response.status_code == 200
    tx = response.json()
    assert tx["customer_id"] == customer_id
    assert float(tx["amount"]) == 100.50
    assert tx["product_id"] is None

    # 3. Retrieve balance
    response = await client.get(f"/customers/{customer_id}/balance")
    assert response.status_code == 200
    balance_data = response.json()
    assert balance_data["customer_id"] == customer_id
    assert float(balance_data["balance"]) == 100.50

    # 4. List transactions and verify cursor-based pagination
    # Add a second credit transaction
    await client.post(f"/customers/{customer_id}/credit", json={"amount": "50.00"})

    # Fetch first page with limit 1
    response = await client.get(f"/customers/{customer_id}/transactions?limit=1")
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1["items"]) == 1
    assert float(page1["items"][0]["amount"]) == 50.00
    assert page1["next_cursor"] is not None

    cursor = page1["next_cursor"]

    # Fetch second page using the cursor
    response = await client.get(f"/customers/{customer_id}/transactions?limit=1&cursor={cursor}")
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2["items"]) == 1
    assert float(page2["items"][0]["amount"]) == 100.50
    assert page2["next_cursor"] is None
