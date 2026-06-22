# Karzar - Industrial Lathe Tools API

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
karzar/
├── alembic/                    # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/              # Migration files
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── api/                  # API routes and endpoints
│   │   ├── endpoints/
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   └── product.py    # Product management endpoints
│   │   └── v1/               # API version 1
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
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest configuration and fixtures
│   └── test_product_endpoints.py # Endpoint tests
├── .env.example              # Environment template
├── .dockerignore
├── .gitignore
├── alembic.ini              # Alembic configuration
├── docker-compose.yml       # Docker Compose orchestration
├── Dockerfile               # Multi-stage Docker build
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Redis 7+ (optional, for caching)
- Docker & Docker Compose (for containerized deployment)

## Installation

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd karzar
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

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

Run the test suite:

```bash
# Install test dependencies (included in requirements.txt)
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_product_endpoints.py

# Run with verbose output
pytest -v
```

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

**Last Updated**: 2026-06-16  
**Version**: 1.0.0
