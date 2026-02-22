# Marketplace Architecture

## Goal
Design marketplace architecture, describe it with a C4 Container diagram, and run service in Docker that returns 200 OK on `/health`.

---

## Requirements
Marketplace should provide:
- Personalized product feed
- Seller catalog management
- User management (buyers and sellers)
- Order placement
- Payment accounting
- Notifications about order statuses

---

## Domains and responsibilities
Below are the main marketplace domains and what each domain is responsible for:

1) **Users / Identity**
- Registration/authentication (conceptually), roles (buyer/seller), user profiles

2) **Catalog**
- Product cards, categories, attributes, seller’s product management

3) **Feed / Recommendations**
- Product feed generation

4) **Orders**
- Creating orders, storing order items, tracking order statuses

5) **Payments**
- Payment accounting and payment statuses

6) **Notifications**
- Sending notifications to users about order/payment status changes

---

## Architecture options

### Option A: Domain microservices
**Containers**
- **API Gateway** — single entry point for clients
- **User Service** + User DB
- **Catalog Service** + Catalog DB
- **Feed Service** + Feed DB/Cache
- **Order Service** + Order DB
- **Payment Service** + Payment DB
- **Notification Service** + Notification DB

**Domain &rarr; Service mapping**
- Users/Identity &rarr; **User Service**
- Catalog &rarr; **Catalog Service**
- Feed/Recommendations &rarr; **Feed Service**
- Orders &rarr; **Order Service**
- Payments &rarr; **Payment Service**
- Notifications &rarr; **Notification Service**

### Option B: Simplified decomposition
**Containers**
- API Gateway
- **Core Service** (Users + Catalog + Orders) + Core DB
- Feed Service + Feed DB/Cache
- Payment Service + Payment DB
- Notification Service + Notification DB

**Domain &rarr; Service mapping**
- Users + Catalog + Orders &rarr; **Core Service**
- Feed &rarr; **Feed Service**
- Payments &rarr; **Payment Service**
- Notifications &rarr; **Notification Service**

---

## Data ownership
**Rule:** each service owns its data storage. **No shared databases**.

Option A data ownership:
- **User Service** owns: `users`, `roles`, `profiles`
- **Catalog Service** owns: `products`, `categories`, `attributes`, `seller_product_settings`
- **Feed Service** owns: `user_events`, `feed_cache`
- **Order Service** owns: `orders`, `order_items`, `order_status_history`
- **Payment Service** owns: `payments`, `payment_transactions`
- **Notification Service** owns: `templates`, `notification_log` / `outbox`

---

## Trade-offs

### Option A
**Pros**
- Clear domain boundaries (high cohesion)
- Independent scaling (feed/catalog/orders can scale separately)
- Independent deployments per domain
- Stronger data ownership boundaries (no shared DB)

**Cons**
- More infrastructure complexity (many services + DBs + broker)
- More network calls and operational overhead (monitoring, tracing, deployment)
- Consistency across services is harder (often eventual consistency)

### Option B
**Pros**
- Simpler operations and deployment (fewer services)
- Fewer network calls, easier debugging
- Easier to keep strong consistency inside Core (if business logic existed)

**Cons**
- Core grows into a “big service” (lower flexibility for teams)
- Harder to scale different parts independently
- Harder to split later (risk of monolith-like coupling)

---

## Final decision
**Chosen architecture: Option A**

**Why**
- Marketplace domains are naturally separable
- Different parts will have different load patterns
- Clear data ownership is required
- Async events are a natural fit for order/payment status propagation and notifications

## C4 Container diagram (LikeC4)
File: `Diagram/Diagram.likec4`

```bash
npx likec4@latest start
```

## Run in Docker

```bash
cd Service
docker compose up --build
curl -i http://localhost:8080/health
```

## Stop Docker
```bash
docker compose down
```
