# Makefile for FastAPI + Angular project

# Variables
BACKEND_DIR=backend
FRONTEND_DIR=frontend

# Default target
.PHONY: all
all: install-backend install-frontend

# -------------------
# Backend (FastAPI)
# -------------------
.PHONY: install-backend
install-backend:
    cd $(BACKEND_DIR) && pip install -r requirements.txt

.PHONY: run-backend
run-backend:
    cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: test-backend
test-backend:
    cd $(BACKEND_DIR) && pytest --maxfail=1 --disable-warnings -q

.PHONY: lint-backend
lint-backend:
    cd $(BACKEND_DIR) && flake8 .

# -------------------
# Frontend (Angular)
# -------------------
.PHONY: install-frontend
install-frontend:
    cd $(FRONTEND_DIR) && npm ci

.PHONY: build-frontend
build-frontend:
    cd $(FRONTEND_DIR) && npm run build

.PHONY: run-frontend
run-frontend:
    cd $(FRONTEND_DIR) && npm start

.PHONY: test-frontend
test-frontend:
    cd $(FRONTEND_DIR) && npm test -- --watch=false --browsers=ChromeHeadless

# -------------------
# Utilities
# -------------------
.PHONY: clean
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    cd $(FRONTEND_DIR) && rm -rf node_modules dist
