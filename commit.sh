#!/bin/bash
# Git commit script for Karzar project
# This script commits all changes in logical groups

set -e  # Exit on error

echo "🔄 Starting git commit workflow..."
cd /home/moahmmad/Projects/Karzar

# 1. Configuration & Templates
echo "📋 Step 1: Committing configuration files..."
git add .env.example pytest.ini .dockerignore .gitignore
git commit -m "chore: add environment templates and configuration files"

# 2. Docker & Deployment
echo "🐳 Step 2: Committing Docker configuration..."
git add Dockerfile docker-compose.yml
git commit -m "chore: enhance Docker multi-stage build and orchestration"

# 3. Dependencies
echo "📦 Step 3: Committing dependency updates..."
git add requirements.txt
git commit -m "feat: add testing, security, and authentication dependencies"

# 4. Core Infrastructure
echo "⚙️  Step 4: Committing core infrastructure..."
git add app/core/ app/__init__.py app/crud/__init__.py app/db/__init__.py app/schemas/__init__.py app/services/__init__.py app/api/__init__.py
git commit -m "feat: implement logging, security, configuration, and package structure"

# 5. Database Layer
echo "🗄️  Step 5: Committing database changes..."
git add app/db/models/ alembic/versions/
git commit -m "feat: redesign Product model with UUID keys, timestamps, and soft deletes"

# 6. API & CRUD
echo "🛣️  Step 6: Committing API endpoints and CRUD..."
git add app/schemas/ app/api/ app/crud/product.py
git commit -m "feat: create comprehensive REST API endpoints, schemas, and CRUD operations"

# 7. Business Logic
echo "💼 Step 7: Committing business logic..."
git add app/services/
git commit -m "feat: implement ProductService with advanced business logic"

# 8. Application Entry
echo "🚀 Step 8: Committing application setup..."
git add app/main.py
git commit -m "feat: configure FastAPI with health checks, error handling, and routers"

# 9. Testing
echo "🧪 Step 9: Committing test suite..."
git add tests/
git commit -m "test: add pytest configuration and comprehensive endpoint tests"

# 10. Documentation
echo "📖 Step 10: Committing documentation..."
git add README.md
git commit -m "docs: add comprehensive API documentation and project guide"

echo ""
echo "✅ All commits completed successfully!"
echo ""
echo "📊 Commit History:"
git log --oneline -15

echo ""
echo "📝 Repository Status:"
git status

echo ""
echo "🏷️  Consider tagging this version:"
echo "  git tag -a v1.0.0 -m 'Complete project refactor with full CRUD and authentication'"
echo "  git push origin main"
echo "  git push origin v1.0.0"
