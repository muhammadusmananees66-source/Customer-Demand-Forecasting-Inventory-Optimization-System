# Makefile
# ============================================================
# PRODUCTION-GRADE MAKEFILE WITH UV
# ============================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:

# ============================================================
# CONFIGURATION
# ============================================================
PYTHON_VERSION ?= 3.12
UV ?= uv
UV_SYNC_OPTS := --frozen
UV_SYNC_DEV_OPTS := --all-extras --dev --frozen

IMAGE_NAME ?= customer-demand-forecasting
IMAGE_TAG ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "local")
REGISTRY ?= ghcr.io/your-org
FULL_IMAGE := $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
LATEST_IMAGE := $(REGISTRY)/$(IMAGE_NAME):latest

COMPOSE ?= docker compose
COMPOSE_FILE ?= docker-compose.yml
COMPOSE_INTEG ?= docker-compose.integration.yml

K8S_NAMESPACE ?= demand-forecast
K8S_DIR ?= deploy/k8s

COV_MIN ?= 80

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# ============================================================
# HELP
# ============================================================
.PHONY: help
help: ## Show this help message
	@printf '\n${BLUE}🚀 Customer Demand Forecast - Production Makefile${NC}\n\n'
	@printf '${YELLOW}Usage:${NC} make <target>\n\n'
	@printf '${YELLOW}Targets:${NC}\n'
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-28s${NC} %s\n", $$1, $$2}'

# ============================================================
# ENVIRONMENT
# ============================================================
.PHONY: install
install: ## Install runtime dependencies (frozen)
	@printf '${BLUE}📦 Installing dependencies from lockfile...${NC}\n'
	$(UV) sync $(UV_SYNC_OPTS)
	@printf '${GREEN}✅ Dependencies installed${NC}\n'

.PHONY: install-dev
install-dev: ## Install development dependencies (frozen)
	@printf '${BLUE}📦 Installing development dependencies from lockfile...${NC}\n'
	$(UV) sync $(UV_SYNC_DEV_OPTS)
	pre-commit install || true
	@printf '${GREEN}✅ Development dependencies installed${NC}\n'

.PHONY: lock
lock: ## Update lockfile from pyproject.toml
	@printf '${BLUE}🔒 Updating lockfile...${NC}\n'
	$(UV) lock
	@printf '${GREEN}✅ Lockfile updated${NC}\n'

.PHONY: venv
venv: ## Create a virtual environment with uv
	@printf '${BLUE}🐍 Creating virtual environment...${NC}\n'
	$(UV) venv
	@printf '${GREEN}✅ Virtual environment created at .venv${NC}\n'
	@printf '${YELLOW}Run: source .venv/bin/activate${NC}\n'

# ============================================================
# CODE QUALITY
# ============================================================
.PHONY: lint
lint: ## Run linters (ruff, black, isort)
	@printf '${BLUE}🔍 Running linters...${NC}\n'
	$(UV) run ruff check src tests
	$(UV) run black --check src tests
	$(UV) run isort --check-only src tests
	@printf '${GREEN}✅ Linters passed${NC}\n'

.PHONY: format
format: ## Auto-format code
	@printf '${BLUE}🎨 Formatting code...${NC}\n'
	$(UV) run ruff check --fix src tests
	$(UV) run black src tests
	$(UV) run isort src tests
	@printf '${GREEN}✅ Code formatted${NC}\n'

.PHONY: typecheck
typecheck: ## Run mypy type checking
	@printf '${BLUE}🔍 Running type checking...${NC}\n'
	$(UV) run mypy src
	@printf '${GREEN}✅ Type checking passed${NC}\n'

.PHONY: security-scan
security-scan: ## Run security scans (bandit, safety)
	@printf '${BLUE}🔒 Running security scans...${NC}\n'
	$(UV) run bandit -r src -ll -x tests -f json -o bandit-report.json || true
	$(UV) run safety check --json > safety-report.json || true
	@printf '${GREEN}✅ Security scans complete${NC}\n'

.PHONY: check
check: lint typecheck security-scan ## Run all static checks

# ============================================================
# TESTING
# ============================================================
.PHONY: test-unit
test-unit: ## Run unit tests with coverage
	@printf '${BLUE}🧪 Running unit tests...${NC}\n'
	mkdir -p reports
	$(UV) run pytest tests/unit -v \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=$(COV_MIN) \
		--junitxml=reports/unit-junit.xml
	@printf '${GREEN}✅ Unit tests passed${NC}\n'

.PHONY: test-integration
test-integration: ## Run integration tests
	@printf '${BLUE}🧪 Running integration tests...${NC}\n'
	mkdir -p reports
	INTEGRATION_TESTS=1 $(UV) run pytest tests/integration -v -m integration \
		--junitxml=reports/integration-junit.xml
	@printf '${GREEN}✅ Integration tests passed${NC}\n'

.PHONY: test-integration-up
test-integration-up: ## Start integration dependencies
	@printf '${BLUE}🐳 Starting integration services...${NC}\n'
	$(COMPOSE) -f $(COMPOSE_INTEG) up -d
	./scripts/wait_for_services.sh
	@printf '${GREEN}✅ Integration services started${NC}\n'

.PHONY: test-integration-down
test-integration-down: ## Stop integration dependencies
	@printf '${BLUE}🐳 Stopping integration services...${NC}\n'
	$(COMPOSE) -f $(COMPOSE_INTEG) down -v
	@printf '${GREEN}✅ Integration services stopped${NC}\n'

.PHONY: test-integration-full
test-integration-full: test-integration-up test-integration test-integration-down ## Full integration test lifecycle

.PHONY: test
test: test-unit ## Alias: unit tests only

.PHONY: test-all
test-all: test-unit test-integration-full ## Unit + integration tests

.PHONY: test-cov
test-cov: ## Run tests with HTML coverage report
	@printf '${BLUE}📊 Running tests with coverage...${NC}\n'
	$(UV) run pytest tests/ -v \
		--cov=src \
		--cov-report=html \
		--cov-report=term-missing
	@printf '${GREEN}✅ Coverage report: htmlcov/index.html${NC}\n'

# ============================================================
# APPLICATION
# ============================================================
.PHONY: run-api
run-api: ## Run the FastAPI serving app locally
	@printf '${BLUE}🚀 Starting API server...${NC}\n'
	$(UV) run uvicorn src.serving.api:create_app \
		--factory \
		--reload \
		--host 0.0.0.0 \
		--port 8000

.PHONY: train
train: ## Run the training pipeline
	@printf '${BLUE}📊 Running training pipeline...${NC}\n'
	$(UV) run python -m src.models.trainer

.PHONY: verify
verify: ## Run verification scripts
	@printf '${BLUE}🔍 Running verification scripts...${NC}\n'
	$(UV) run python scripts/verify_business_requirements.py
	$(UV) run python scripts/verify_validator.py
	$(UV) run python scripts/verify_features.py
	$(UV) run python scripts/verify_data_collection.py
	$(UV) run python scripts/verify_inference.py
	$(UV) run python scripts/verify_model_training.py
	@printf '${GREEN}✅ All verifications passed${NC}\n'

# ============================================================
# DOCKER
# ============================================================
.PHONY: docker-build
docker-build: ## Build the production image
	@printf '${BLUE}🐳 Building Docker image...${NC}\n'
	docker build \
		--build-arg BUILD_SHA=$(IMAGE_TAG) \
		-t $(FULL_IMAGE) \
		-t $(LATEST_IMAGE) \
		-t $(IMAGE_NAME):local .
	@printf '${GREEN}✅ Image built: $(FULL_IMAGE)${NC}\n'

.PHONY: docker-run
docker-run: ## Run the built image locally
	@printf '${BLUE}🐳 Running Docker container...${NC}\n'
	docker run --rm -it -p 8000:8000 \
		-e MLFLOW_TRACKING_URI=http://host.docker.internal:5000 \
		-e REDIS_HOST=host.docker.internal \
		$(IMAGE_NAME):local

.PHONY: docker-push
docker-push: ## Push image to registry
	@printf '${BLUE}🐳 Pushing image to registry...${NC}\n'
	docker push $(FULL_IMAGE)
	docker push $(LATEST_IMAGE)
	@printf '${GREEN}✅ Image pushed${NC}\n'

.PHONY: docker-scan
docker-scan: ## Scan the built image for vulnerabilities
	@printf '${BLUE}🔒 Scanning image for vulnerabilities...${NC}\n'
	trivy image --severity HIGH,CRITICAL $(IMAGE_NAME):local

# ============================================================
# LOCAL STACK
# ============================================================
.PHONY: compose-up
compose-up: ## Start full local stack
	@printf '${BLUE}🐳 Starting local stack...${NC}\n'
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build
	@printf '${GREEN}✅ Local stack started${NC}\n'
	@printf '${YELLOW}API:        http://localhost:8000/docs${NC}\n'
	@printf '${YELLOW}MLflow:     http://localhost:5000${NC}\n'
	@printf '${YELLOW}Prometheus: http://localhost:9090${NC}\n'
	@printf '${YELLOW}Grafana:    http://localhost:3000 (admin/admin)${NC}\n'

.PHONY: compose-down
compose-down: ## Stop local stack
	@printf '${BLUE}🐳 Stopping local stack...${NC}\n'
	$(COMPOSE) -f $(COMPOSE_FILE) down -v
	@printf '${GREEN}✅ Local stack stopped${NC}\n'

.PHONY: compose-logs
compose-logs: ## Tail logs from local stack
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f --tail=200

# ============================================================
# KUBERNETES
# ============================================================
.PHONY: k8s-deploy
k8s-deploy: ## Deploy to Kubernetes
	@test -n "$(IMAGE)" || (echo "Usage: make k8s-deploy IMAGE=$(FULL_IMAGE)"; exit 1)
	@printf '${BLUE}☸️ Deploying to Kubernetes...${NC}\n'
	kubectl create namespace $(K8S_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	sed 's#__IMAGE__#$(IMAGE)#g' $(K8S_DIR)/deployment.yaml | kubectl apply -n $(K8S_NAMESPACE) -f -
	kubectl apply -n $(K8S_NAMESPACE) -f $(K8S_DIR)/service.yaml
	kubectl apply -n $(K8S_NAMESPACE) -f $(K8S_DIR)/hpa.yaml
	kubectl rollout status deployment/demand-forecast-api -n $(K8S_NAMESPACE) --timeout=180s
	@printf '${GREEN}✅ Deployment complete${NC}\n'

.PHONY: k8s-rollback
k8s-rollback: ## Rollback Kubernetes deployment
	@printf '${BLUE}⏪ Rolling back deployment...${NC}\n'
	kubectl rollout undo deployment/demand-forecast-api -n $(K8S_NAMESPACE)
	kubectl rollout status deployment/demand-forecast-api -n $(K8S_NAMESPACE) --timeout=120s
	@printf '${GREEN}✅ Rollback complete${NC}\n'

.PHONY: k8s-smoke-test
k8s-smoke-test: ## Run smoke tests on deployed service
	@test -n "$(HOST)" || (echo "Usage: make k8s-smoke-test HOST=https://api.example.com"; exit 1)
	@printf '${BLUE}🧪 Running smoke tests...${NC}\n'
	$(UV) run python scripts/smoke_test.py --host $(HOST)

# ============================================================
# MONITORING
# ============================================================
.PHONY: monitoring-up
monitoring-up: ## Start monitoring stack
	@printf '${BLUE}📊 Starting monitoring stack...${NC}\n'
	docker compose -f docker-compose.monitoring.yml up -d
	@printf '${GREEN}✅ Monitoring stack started${NC}\n'

.PHONY: monitoring-down
monitoring-down: ## Stop monitoring stack
	@printf '${BLUE}📊 Stopping monitoring stack...${NC}\n'
	docker compose -f docker-compose.monitoring.yml down -v
	@printf '${GREEN}✅ Monitoring stack stopped${NC}\n'

# ============================================================
# CLEANUP
# ============================================================
.PHONY: clean
clean: ## Clean build artifacts
	@printf '${BLUE}🧹 Cleaning artifacts...${NC}\n'
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov reports coverage.xml
	rm -rf dist build *.egg-info
	rm -rf bandit-report.json safety-report.json trivy-results.sarif
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	@printf '${GREEN}✅ Cleanup complete${NC}\n'

.PHONY: clean-all
clean-all: clean ## Clean everything including virtual environment
	@printf '${BLUE}🧹 Cleaning everything...${NC}\n'
	rm -rf .venv/
	rm -rf .uv/
	@printf '${GREEN}✅ Everything cleaned${NC}\n'

# ============================================================
# CI PIPELINE (Used by GitHub Actions)
# ============================================================
.PHONY: ci
ci: install-dev check test-all ## Full CI pipeline
	@printf '${GREEN}✅ CI pipeline completed successfully${NC}\n'

# ============================================================
# VERSION
# ============================================================
.PHONY: version
version: ## Show version information
	@printf '${BLUE}📌 Version: ${IMAGE_TAG}${NC}\n'
	@printf '${BLUE}📌 Build: $(shell date -u +%Y-%m-%dT%H:%M:%SZ)${NC}\n'