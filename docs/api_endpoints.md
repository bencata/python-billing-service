# Usage-Based Billing Service: API Documentation

This document documents the API endpoints implemented in Phase 1 of the home assignment.

All request and response payloads use JSON formatting. Prices, quantities, and balances use high-precision decimals represented as strings in JSON payloads to avoid floating-point inaccuracies.

---

## Customers API

### 1. Create Customer
Creates a new customer record with a default balance of `0.0000`.

- **Method**: `POST`
- **Path**: `/customers`
- **Request Body**:
  ```json
  {
    "name": "Eyal"
  }
  ```
- **Response** (HTTP 201 Created):
  ```json
  {
    "name": "Eyal",
    "id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
    "balance": "0.0000"
  }
  ```

### 2. Retrieve Customer
Retrieves customer details including their current prepaid balance.

- **Method**: `GET`
- **Path**: `/customers/{customer_id}`
- **Response** (HTTP 200 OK):
  ```json
  {
    "name": "Eyal",
    "id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
    "balance": "0.0000"
  }
  ```
- **Error Response** (HTTP 404 Not Found):
  ```json
  {
    "detail": "Customer not found"
  }
  ```

### 3. Retrieve Customer Balance
A fast helper endpoint to retrieve just a customer's balance.

- **Method**: `GET`
- **Path**: `/customers/{customer_id}/balance`
- **Response** (HTTP 200 OK):
  ```json
  {
    "customer_id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
    "balance": "0.0000"
  }
  ```

### 4. Add Credit to Customer Balance
Adds credit to a customer's prepaid balance. This operation atomically updates the customer's balance and records a positive transaction in the ledger.

- **Method**: `POST`
- **Path**: `/customers/{customer_id}/credit`
- **Request Body**:
  ```json
  {
    "amount": "100.5000"
  }
  ```
- **Response** (HTTP 200 OK):
  ```json
  {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "customer_id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
    "amount": "100.5000",
    "product_id": null,
    "quantity": null,
    "unit_price_at_time": null,
    "created_at": "2026-07-16T14:40:00.000Z"
  }
  ```

### 5. List Customer Transactions
Lists a paginated history of all credit and charge transactions for a customer, sorted by creation date descending.

- **Method**: `GET`
- **Path**: `/customers/{customer_id}/transactions`
- **Query Parameters**:
  - `limit` (Integer, Optional, Default: 20, Max: 100): Maximum records to return.
  - `offset` (Integer, Optional, Default: 0): Records to skip.
- **Response** (HTTP 200 OK):
  ```json
  [
    {
      "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "customer_id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
      "amount": "100.5000",
      "product_id": null,
      "quantity": null,
      "unit_price_at_time": null,
      "created_at": "2026-07-16T14:40:00.000Z"
    }
  ]
  ```

---

## Products API

### 1. Create Product
Creates a new billing product with a fixed price per unit.

- **Method**: `POST`
- **Path**: `/products`
- **Request Body**:
  ```json
  {
    "name": "Database Hosting",
    "price_per_unit": "0.0500"
  }
  ```
- **Response** (HTTP 201 Created):
  ```json
  {
    "name": "Database Hosting",
    "price_per_unit": "0.0500",
    "id": "a0a39217-dd37-4ae6-b56e-91787f802d80"
  }
  ```

### 2. Retrieve Product
Retrieves product details.

- **Method**: `GET`
- **Path**: `/products/{product_id}`
- **Response** (HTTP 200 OK):
  ```json
  {
    "name": "Database Hosting",
    "price_per_unit": "0.0500",
    "id": "a0a39217-dd37-4ae6-b56e-91787f802d80"
  }
  ```

---

## Usage Ingestion API

### 1. Report Usage (Synchronous Ingestion)
Accepts a usage event and charges the customer balance synchronously. Enforces transaction serialization to protect against overdrafts, and guarantees request idempotency using the `Idempotency-Key` header.

- **Method**: `POST`
- **Path**: `/usage`
- **Headers**:
  - `Idempotency-Key` (String, Required): A unique caller-provided identifier for deduplication.
- **Request Body**:
  ```json
  {
    "customer_id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
    "product_id": "a0a39217-dd37-4ae6-b56e-91787f802d80",
    "quantity": "2.5000"
  }
  ```
- **Response** (HTTP 200 OK):
  ```json
  {
    "transaction_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
    "customer_id": "495b63bb-b75c-4feb-ba0d-31eaf80c0dc9",
    "amount": "-0.1250",
    "remaining_balance": "100.3750",
    "product_id": "a0a39217-dd37-4ae6-b56e-91787f802d80",
    "quantity": "2.5000",
    "unit_price": "0.0500"
  }
  ```
- **Error Responses**:
  - **HTTP 400 Bad Request** (e.g., Insufficient funds or payload hash mismatch for the idempotency key):
    ```json
    {
      "detail": "Insufficient funds. Required: 0.1250, Available: 0.0000"
    }
    ```
  - **HTTP 409 Conflict** (The request is currently being processed concurrently):
    ```json
    {
      "detail": "Request is already processing."
    }
    ```

