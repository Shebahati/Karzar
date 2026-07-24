# Karzar — Industrial tools platform (monorepo)

**کارزار** is a B2B/B2C industrial tools commerce platform. This repository is a **monorepo**:

| Path | Role |
|------|------|
| `app/`, `alembic/`, `deploy/`, … | Backend API (FastAPI) |
| `frontend/Storefront/` | Customer shop (Next.js, `:3000`) |
| `frontend/admin-panel/` | Admin dashboard (Next.js, `:3001`) |
| `.github/workflows/` | CI + Deploy Staging / Production |

- **Repo:** [Shebahati/Karzar](https://github.com/Shebahati/Karzar)
- **Frontend collaborator deploy guide (FA):** [docs/COLLABORATOR_DEPLOY.md](docs/COLLABORATOR_DEPLOY.md)
- **Frontend app README:** [frontend/README.md](frontend/README.md)

Push/merge to `main` that touches `frontend/**` (or backend deploy paths) triggers **Deploy Staging** on the self-hosted VPS runner (sources are packaged on `ubuntu-latest` first). **Deploy Production** is manual-only (`workflow_dispatch` + typed confirm + Environment approval) because production is not on a separate host yet — see [docs/COLLABORATOR_DEPLOY.md](docs/COLLABORATOR_DEPLOY.md).

---

# Backend — Industrial Lathe Tools API

A modern, production-ready FastAPI application for managing industrial lathe tools inventory with comprehensive product management, stock control, and authentication.

## Features

- ✅ **Complete CRUD Operations**: Full product lifecycle management
- ✅ **Database Migrations**: Alembic for version-controlled schema changes
- ✅ **Async/Await**: SQLAlchemy 2.0 with async support
- ✅ **Authentication**: JWT-based API security
- ✅ **Validation**: Pydantic V2 with comprehensive validation
- ✅ **Error Handling**: Global exception handlers with proper HTTP status codes
- ✅ **Logging**: Structured logging for debugging and monitoring
- ✅ **Health Checks**: Kubernetes and Docker orchestration ready
- ✅ **Stock Management**: Real-time inventory tracking
- ✅ **Soft Deletes**: Non-destructive product removal
- ✅ **Advanced Filtering**: Search, categorization, and price range filtering
- ✅ **Pagination**: Efficient data retrieval with skip/limit
- ✅ **Docker Support**: Multi-stage Docker builds with security best practices
- ✅ **Testing**: Pytest integration with test fixtures

## Project Structure

```
Karzar/
├── frontend/                   # Next.js apps (see frontend/README.md)
│   ├── Storefront/             # Public shop
│   ├── admin-panel/            # Admin panel
│   └── README.md
├── .github/workflows/          # backend-ci, deploy-staging, deploy-production
├── docs/
│   └── COLLABORATOR_DEPLOY.md  # How FE collaborators push & deploy
├── alembic/                    # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/              # Migration files
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── api/                  # API routes and endpoints
│   │   ├── endpoints/
│   │   │   ├── auth.py       # OTP, login, refresh, step-up PIN
│   │   │   ├── product.py    # Products, stock, images
│   │   │   ├── category.py   # Category tree & spec templates
│   │   │   ├── brand.py      # Brand CRUD
│   │   │   ├── cart.py       # Session cart
│   │   │   ├── order.py      # Orders, tracking, admin workflow
│   │   │   ├── payment.py    # Payment init/verify/callback/refund
│   │   │   ├── storefront.py # Checkout, blog, contact, hero
│   │   │   ├── users.py      # Admin user management
│   │   │   └── cms.py        # CMS admin (blog, comments)
│   │   └── v1/               # API version 1 router
│   ├── core/                 # Core configurations
│   │   ├── config.py         # Environment configuration
│   │   ├── logging.py        # Logging setup
│   │   ├── security.py       # Security utilities (JWT, passwords)
│   ├── crud/                 # Database operations
│   │   └── product.py        # Product CRUD operations
│   ├── db/                   # Database setup
│   │   ├── database.py       # AsyncSession configuration
│   │   └── models/
│   │       ├── base.py       # SQLAlchemy declarative base
│   │       └── product.py    # Product model
│   ├── schemas/              # Pydantic models
│   │   ├── auth.py           # Authentication schemas
│   │   └── product.py        # Product schemas with validation
│   └── services/             # Business logic layer
│       └── product_service.py # Product business logic
├── docs/                       # Contract, ops, testing, seed guides
│   ├── API_CONTRACT.md
│   ├── API_CHANGELOG.md
│   ├── FRONTEND_INTEGRATION.md
│   ├── OPERATIONS.md
│   ├── SEED_IMPORT.md
│   └── TESTING.md
├── scripts/
│   └── setup-dev.sh            # Local dev bootstrap (venv + deps)
├── tests/                      # Test suite
│   ├── conftest.py
│   ├── test_product_endpoints.py
│   ├── test_category_tree.py
│   └── test_jsonb_filters.py
├── .env.example
├── .dockerignore
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt            # Production dependencies (Docker)
├── requirements-dev.txt        # Dev/test deps (includes requirements.txt)
└── README.md
```

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis 7+ (optional, for caching)
- Docker & Docker Compose (for containerized deployment)

## Installation

### Local Development Setup

**Quick start (recommended):**

```bash
git clone <repository-url>
cd karzar
./scripts/setup-dev.sh
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Manual setup:**

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd karzar
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```
   Use `requirements.txt` only when you do not need tests (e.g. minimal prod-like install).
   Docker images install `requirements.txt` only.

4. **Setup environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

2. **Run migrations in container**:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

3. **Access the application**:
   - API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/api/docs`
   - ReDoc: `http://localhost:8000/api/redoc`

## API Endpoints

Full interactive documentation: `/api/docs` (OpenAPI is always up to date).

### Error envelope (all error responses)

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Request validation failed",
  "details": [{ "field": "sku", "message": "already exists" }]
}
```

### Product Management

#### Create Product
```http
POST /api/v1/products/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "sku": "TOOL-001",
  "name": "Digital Caliper",
  "category_id": 1,
  "brand_id": 1,
  "base_price": 99.99,
  "stock_quantity": 50,
  "specifications": { "technical_specs": { "range": "0-150mm" } }
}
```

Returns full `ProductDetailResponse` (same shape as GET product).

#### List Products (PLP)
```http
GET /api/v1/products/?skip=0&limit=100&category_id=1&brand_id=1&search=caliper
GET /api/v1/products/?filters={"technical_specs.range":"0-150mm"}
GET /api/v1/products/?spec_technical_specs__range=0-150mm
```

Response:
```json
{
  "data": [{ "id": 1, "sku": "...", "name": "...", "thumbnail": null, "base_price": "99.99", "stock_status": "in_stock", "category": { "id": 1, "name": "..." }, "brand": { "id": 1, "name": "..." } }],
  "meta": { "total_count": 1, "skip": 0, "limit": 100, "has_next": false, "has_prev": false }
}
```

#### Get Product by ID / SKU (PDP)
```http
GET /api/v1/products/{product_id}
GET /api/v1/products/sku/{sku}
```

#### Update Product
```http
PUT /api/v1/products/{product_id}
```

#### Delete Product (Soft Delete) — requires step-up token
```http
DELETE /api/v1/products/{product_id}
Authorization: Bearer <access_token>
X-Step-Up-Token: <secure_token>
```

#### Restore Deleted Product — requires step-up token
```http
POST /api/v1/products/{product_id}/restore
```

### Categories

#### Category Tree (Mega Menu)
```http
GET /api/v1/categories/tree
```

Response: `{ "data": [ { "id": 1, "name": "...", "parent_id": null, "subcategories": [...] } ] }`

### Brands

```http
GET    /api/v1/brands/
POST   /api/v1/brands/              # super admin
PUT    /api/v1/brands/{id}          # super admin
DELETE /api/v1/brands/{id}          # super admin + X-Step-Up-Token
```

### Cart

```http
GET    /api/v1/cart/
POST   /api/v1/cart/items
PATCH  /api/v1/cart/items/{product_id}
DELETE /api/v1/cart/items/{product_id}
```

Cart merges into the authenticated user on login.

### Orders & tracking

```http
POST   /api/v1/checkout             # storefront — purchase (auth) or inquiry
GET    /api/v1/orders/me            # customer order history (auth)
GET    /api/v1/orders/track/{code}  # public tracking (no PII; includes items)
GET    /api/v1/orders               # admin list (page/page_size, filters)
GET    /api/v1/orders/{id}          # admin detail
PATCH  /api/v1/orders/{id}/status   # admin status update
POST   /api/v1/orders/{id}/quote    # inquiry quote (admin)
DELETE /api/v1/orders/{id}           # soft delete (admin + step-up)
```

### Payments

```http
POST /api/v1/payments/init          # start gateway session (auth)
GET  /api/v1/payments/callback      # public gateway redirect
POST /api/v1/payments/verify        # verify authority (callback-friendly)
POST /api/v1/payments/refund        # admin refund (mock/Zarinpal)
```

Purchase checkout returns `payment_url`; payment metadata is stored in `payment_authority` / `payment_ref_id` (not `order.note`).

### Storefront & CMS

```http
GET  /api/v1/blog/                  # article list
GET  /api/v1/blog/{slug}
GET  /api/v1/hero-slides/
POST /api/v1/contact
POST /api/v1/checkout
```

Admin CMS routes under `/api/v1/cms/` (blog, hero slides, product comments).

### Users (admin)

```http
GET   /api/v1/users?page=1&page_size=20&search=0912&sort=created_desc
PATCH /api/v1/users/{id}
```

### Stock Management

#### Get Stock Status
```http
GET /api/v1/products/{product_id}/stock
```

Response: `{ "product_id": 1, "sku": "...", "stock_quantity": "50", "stock_status": "in_stock" }`

#### Adjust Stock
```http
POST /api/v1/products/{product_id}/stock/adjust?quantity_delta=10
```

### Authentication

#### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{ "phone_number": "09123456789", "password": "securepass", "full_name": "User" }
```

#### Login (OAuth2 form)
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=09123456789&password=securepass
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Step-Up PIN (destructive admin actions)
```http
POST /api/v1/auth/verify-pin
Authorization: Bearer <access_token>
Content-Type: application/json

{ "pin": "your-admin-pin" }
```

Response:
```json
{
  "secure_token": "eyJ...",
  "token_type": "step_up",
  "expires_in": 300
}
```

### System Endpoints

#### Health Check
```http
GET /health
```

#### Readiness Check
```http
GET /ready
```

#### API Info
```http
GET /api/v1
```

## Testing

Requires dev dependencies (`pip install -r requirements-dev.txt`). See [docs/TESTING.md](docs/TESTING.md) for CI, markers, and Postgres/Redis integration.

```bash
pytest

# Coverage gate (matches CI, minimum 62%)
pytest --cov=app --cov-fail-under=62

# Lint (also run in CI)
ruff check app tests
mypy app

# Pre-commit (optional local hook)
pre-commit install && pre-commit run --all-files
```

GitHub Actions (`backend-ci.yml`) runs lint + tests with Postgres and Redis on every push to `main`.

## Database Migrations

### Create a new migration
```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback last migration
```bash
alembic downgrade -1
```

### View migration history
```bash
alembic current
alembic history
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Contract index when Swagger is disabled in prod |
| [docs/API_CHANGELOG.md](docs/API_CHANGELOG.md) | API v1 versioning and release notes |
| [docs/FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md) | Storefront integration guide |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Deploy, backup, rollback, incidents |
| [docs/SEED_IMPORT.md](docs/SEED_IMPORT.md) | Catalog seed/import pipeline |
| [docs/BACKEND_CHANGES.md](docs/BACKEND_CHANGES.md) | Recent backend deltas for frontend |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Codebase map (no SQLAdmin; Next.js admin panel) |
| [docs/FRONTEND_IMPLEMENTATION_GUIDE.md](docs/FRONTEND_IMPLEMENTATION_GUIDE.md) | FE/BE parity guide |
| [docs/GO_LIVE_EXECUTION_PLAN.md](docs/GO_LIVE_EXECUTION_PLAN.md) | Launch checklist |

Interactive OpenAPI: `/api/docs` when `ENABLE_API_DOCS=true`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | - | PostgreSQL username |
| `POSTGRES_PASSWORD` | - | PostgreSQL password |
| `POSTGRES_SERVER` | db | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | karzar_db | Database name |
| `REDIS_HOST` | redis | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `SECRET_KEY` | - | JWT secret key (change in production!) |
| `DEBUG` | False | Enable debug mode |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT token expiration (seconds returned as `expires_in = minutes × 60`) |
| `ADMIN_STEP_UP_PIN` | - | Admin PIN for destructive actions (min 6 chars; weak values rejected when `DEBUG=False`) |
| `STEP_UP_TOKEN_EXPIRE_MINUTES` | 5 | Step-up token lifetime in minutes |

## Architecture

### Layered Architecture

```
┌─────────────────────────────────┐
│  API Routes (Endpoints)         │ ← FastAPI route handlers
├─────────────────────────────────┤
│  Services (Business Logic)      │ ← Domain logic, validations
├─────────────────────────────────┤
│  CRUD Operations                │ ← Database queries
├─────────────────────────────────┤
│  SQLAlchemy Models              │ ← ORM entities
├─────────────────────────────────┤
│  Database (PostgreSQL)          │ ← Data persistence
└─────────────────────────────────┘
```

### Key Components

- **Models**: SQLAlchemy declarative models representing database tables
- **Schemas**: Pydantic models for request/response validation
- **CRUD**: Database operations (Create, Read, Update, Delete)
- **Services**: Business logic layer processing domain operations
- **Endpoints**: FastAPI routes exposing API functionality

## Security

- ✅ Step-up authentication for destructive admin actions (PIN + `X-Step-Up-Token`)
- ✅ Standardized error envelope (`error_code`, `message`, `details`)
- ✅ Password hashing with bcrypt
- ✅ Non-root Docker user
- ✅ Environment-based secrets (never committed)
- ✅ Input validation and sanitization
- ✅ SQL injection protection (parameterized queries)
- ✅ Comprehensive error handling (no stack traces to client)

## Performance

- ✅ Async/await for non-blocking I/O
- ✅ Connection pooling (20 connections, 10 overflow)
- ✅ Database query indexing on frequently searched columns
- ✅ Pagination to prevent large result sets
- ✅ Soft deletes to avoid actual row deletion overhead

## Monitoring

- Health check endpoint for load balancer integration
- Readiness check for orchestration readiness
- Structured logging with timestamps and severity levels
- Request/response logging in endpoints

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please create an issue in the repository.

---

**Last Updated**: 2026-07-12  
**Version**: 1.0.0 (API v1)
