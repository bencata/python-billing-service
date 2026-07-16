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

    # 4. List transactions
    response = await client.get(f"/customers/{customer_id}/transactions")
    assert response.status_code == 200
    txs = response.json()
    assert len(txs) == 1
    assert txs[0]["id"] == tx["id"]
    assert float(txs[0]["amount"]) == 100.50
