# .PHONY: help setup data-ingestion data-lake validation preprocessing \
#         feature-store training evaluation mlflow-registry docker-build \
#         k8s-deploy monitoring drift-detection retraining full-pipeline

# # Variables
# PYTHON := python3
# KAFKA_HOST := localhost:9092
# REDIS_HOST := localhost
# MLFLOW_HOST := localhost:5000
# KUBE_NAMESPACE := demand-forecast-prod

# # Colors
# GREEN := \033[0;32m
# YELLOW := \033[1;33m
# BLUE := \033[0;34m
# NC := \033[0m

# help: ## Show all commands
# 	@printf '${BLUE}Demand Forecasting MLOps Pipeline${NC}\n'
# 	@printf '${YELLOW}Complete pipeline stages:${NC}\n\n'
# 	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-25s${NC} %s\n", $$1, $$2}'

# # Stage 1: Data Sources
# data-sources: ## Fetch data from Hugging Face and other sources
# 	@printf '${YELLOW}[1/14] Fetching data sources...${NC}\n'
# 	$(PYTHON) src/data_sources/huggingface_source.py
# # 	$(PYTHON) src/data_sources/sales_api.py
# # 	$(PYTHON) src/data_sources/weather_api.py
# 	@printf '${GREEN}✅ Data sources fetched${NC}\n'

# # Stage 2: Ingestion Layer
# ingestion: ## Ingest data through Kafka/Spark
# 	@printf '${YELLOW}[2/14] Starting data ingestion...${NC}\n'
# 	docker-compose up -d kafka zookeeper
# 	sleep 10
# 	$(PYTHON) src/ingestion/kafka_producer.py
# 	$(PYTHON) src/ingestion/spark_streaming.py
# 	@printf '${GREEN}✅ Data ingestion complete${NC}\n'

# # Stage 3: Data Lake Storage
# data-lake: ## Store data in data lake (S3/MinIO)
# 	@printf '${YELLOW}[3/14] Storing data in lake...${NC}\n'
# 	docker-compose up -d minio
# 	$(PYTHON) src/data_lake/s3_storage.py --zone raw
# 	$(PYTHON) src/data_lake/data_versioning.py --version v1.0
# 	@printf '${GREEN}✅ Data stored in lake${NC}\n'

# # Stage 4: Validation & EDA
# validation: ## Run data validation and exploratory analysis
# 	@printf '${YELLOW}[4/14] Validating data...${NC}\n'
# 	$(PYTHON) src/validation/data_quality.py
# 	$(PYTHON) src/validation/schema_validation.py
# 	$(PYTHON) src/validation/exploratory_analysis.py
# 	$(PYTHON) src/validation/statistical_tests.py
# 	@printf '${GREEN}✅ Validation complete${NC}\n'

# # Stage 5: Preprocessing
# preprocessing: ## Clean and preprocess data
# 	@printf '${YELLOW}[5/14] Preprocessing data...${NC}\n'
# 	$(PYTHON) src/preprocessing/data_cleaner.py
# 	$(PYTHON) src/preprocessing/outlier_handler.py
# 	$(PYTHON) src/preprocessing/missing_value_imputer.py
# 	$(PYTHON) src/preprocessing/data_normalizer.py
# 	@printf '${GREEN}✅ Preprocessing complete${NC}\n'

# # Stage 6: Feature Store
# feature-store: ## Create and update feature store
# 	@printf '${YELLOW}[6/14] Building feature store...${NC}\n'
# 	docker-compose up -d redis
# 	$(PYTHON) src/feature_store/redis_store.py --init
# 	$(PYTHON) src/feature_store/feature_registry.py
# 	$(PYTHON) src/feature_store/online_features.py
# 	$(PYTHON) src/feature_store/offline_features.py
# 	@printf '${GREEN}✅ Feature store ready${NC}\n'

# # Stage 7: Training Pipeline
# training: ## Train models (distributed/Kubeflow)
# 	@printf '${YELLOW}[7/14] Training models...${NC}\n'
# 	$(PYTHON) src/training/distributed_training.py --mode train
# 	$(PYTHON) src/training/kubeflow_pipeline.py
# 	$(PYTHON) src/training/ray_trainer.py
# 	@printf '${GREEN}✅ Training complete${NC}\n'

# # Stage 8: Evaluation & Tuning
# evaluation: ## Evaluate models and tune hyperparameters
# 	@printf '${YELLOW}[8/14] Evaluating models...${NC}\n'
# 	$(PYTHON) src/evaluation/model_metrics.py
# 	$(PYTHON) src/evaluation/hyperparameter_tuning.py --trials 100
# 	$(PYTHON) src/evaluation/ablation_study.py
# 	$(PYTHON) src/evaluation/model_comparison.py
# 	@printf '${GREEN}✅ Evaluation complete${NC}\n'

# # Stage 9: MLflow Registry
# mlflow-registry: ## Register models in MLflow
# 	@printf '${YELLOW}[9/14] Registering models...${NC}\n'
# 	docker-compose up -d mlflow postgres minio
# 	sleep 10
# 	$(PYTHON) src/mlflow_registry/model_registry.py --register
# 	$(PYTHON) src/mlflow_registry/experiment_tracking.py
# 	$(PYTHON) src/mlflow_registry/model_versioning.py
# 	$(PYTHON) src/mlflow_registry/model_staging.py --stage production
# 	@printf '${GREEN}✅ Models registered${NC}\n'

# # Stage 10: Docker Packaging
# docker-build: ## Build Docker containers
# 	@printf '${YELLOW}[10/14] Building Docker images...${NC}\n'
# 	docker build -f deployments/docker/Dockerfile.api -t demand-forecast/api:latest .
# 	docker build -f deployments/docker/Dockerfile.trainer -t demand-forecast/trainer:latest .
# 	docker build -f deployments/docker/Dockerfile.feature_store -t demand-forecast/feature-store:latest .
# 	docker build -f deployments/docker/Dockerfile.monitoring -t demand-forecast/monitoring:latest .
# 	@printf '${GREEN}✅ Docker images built${NC}\n'

# # Stage 11: Kubernetes Deployment
# k8s-deploy: ## Deploy to Kubernetes cluster
# 	@printf '${YELLOW}[11/14] Deploying to Kubernetes...${NC}\n'
# 	kubectl create namespace $(KUBE_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
# 	kubectl apply -f deployments/kubernetes/configmap.yaml
# 	kubectl apply -f deployments/kubernetes/secrets.yaml
# 	kubectl apply -f deployments/kubernetes/kafka.yaml
# 	kubectl apply -f deployments/kubernetes/spark.yaml
# 	kubectl apply -f deployments/kubernetes/mlflow.yaml
# 	kubectl apply -f deployments/kubernetes/model_serving.yaml
# 	kubectl apply -f deployments/kubernetes/ingress.yaml
# 	kubectl apply -f deployments/kubernetes/hpa.yaml
# 	kubectl rollout status deployment/model-serving -n $(KUBE_NAMESPACE)
# 	@printf '${GREEN}✅ Deployment complete${NC}\n'

# # Stage 12: Monitoring Layer
# monitoring: ## Setup monitoring (Prometheus/Grafana)
# 	@printf '${YELLOW}[12/14] Setting up monitoring...${NC}\n'
# 	kubectl apply -f deployments/kubernetes/monitoring.yaml
# 	$(PYTHON) src/monitoring/prometheus_metrics.py
# 	$(PYTHON) src/monitoring/grafana_dashboards.py
# 	$(PYTHON) src/monitoring/performance_monitor.py
# 	$(PYTHON) src/monitoring/alert_manager.py --setup
# 	@printf '${GREEN}✅ Monitoring configured${NC}\n'

# # Stage 13: Drift Detection
# drift-detection: ## Setup drift detection
# 	@printf '${YELLOW}[13/14] Configuring drift detection...${NC}\n'
# 	$(PYTHON) src/drift_detection/data_drift.py --continuous
# 	$(PYTHON) src/drift_detection/concept_drift.py
# 	$(PYTHON) src/drift_detection/model_drift.py
# 	$(PYTHON) src/drift_detection/drift_alert.py --setup
# 	@printf '${GREEN}✅ Drift detection configured${NC}\n'

# # Stage 14: Retraining Pipeline
# retraining: ## Setup automated retraining
# 	@printf '${YELLOW}[14/14] Configuring retraining pipeline...${NC}\n'
# 	$(PYTHON) src/retraining/trigger_manager.py --setup
# 	$(PYTHON) src/retraining/pipeline_trigger.py
# 	$(PYTHON) src/retraining/model_updater.py
# 	$(PYTHON) src/retraining/a_b_testing.py --setup
# 	@printf '${GREEN}✅ Retraining pipeline configured${NC}\n'

# # Complete Pipeline
# full-pipeline: data-sources ingestion data-lake validation preprocessing \
#                 feature-store training evaluation mlflow-registry \
#                 docker-build k8s-deploy monitoring drift-detection retraining
# 	@printf '${GREEN}🎉 Complete MLOps pipeline executed successfully!${NC}\n'
# 	@printf '${BLUE}Access services:${NC}\n'
# 	@printf '  - API: http://localhost:8000\n'
# 	@printf '  - Dashboard: http://localhost:8501\n'
# 	@printf '  - MLflow: http://localhost:5000\n'
# 	@printf '  - Grafana: http://localhost:3000\n'
# 	@printf '  - Prometheus: http://localhost:9090\n'

# # Quick Commands
# quick-start: | setup data-sources ingestion data-lake validation preprocessing feature-store training
# 	@printf '${GREEN}Quick start complete!${NC}\n'

# quick-deploy: | docker-build k8s-deploy
# 	@printf '${GREEN}Quick deploy complete!${NC}\n'

# # Utility Commands
# setup: ## Setup environment
# 	@printf '${YELLOW}Setting up environment...${NC}\n'
# 	python -m venv venv
# 	. venv/bin/activate && pip install -r requirements.txt
# 	mkdir -p data/{raw,processed,features} models logs reports
# 	cp .env.example .env
# 	@printf '${GREEN}Setup complete${NC}\n'

# clean: ## Clean all artifacts
# 	@printf '${YELLOW}Cleaning...${NC}\n'
# 	rm -rf venv data/* models/* logs/* reports/*
# 	docker-compose down -v
# 	kubectl delete namespace $(KUBE_NAMESPACE)
# 	@printf '${GREEN}Clean complete${NC}\n'

# status: ## Check pipeline status
# 	@printf '${BLUE}Checking pipeline status...${NC}\n'
# 	@printf '${YELLOW}Kafka:${NC} ' && curl -s http://localhost:9092 || echo "Not running"
# 	@printf '${YELLOW}MLflow:${NC} ' && curl -s http://localhost:5000 || echo "Not running"
# 	@printf '${YELLOW}Kubernetes:${NC} ' && kubectl get pods -n $(KUBE_NAMESPACE) 2>/dev/null || echo "Not running"
# 	@printf '${YELLOW}Prometheus:${NC} ' && curl -s http://localhost:9090 || echo "Not running"

# logs-api: ## View API logs
# 	kubectl logs -f deployment/model-serving -n $(KUBE_NAMESPACE) -c api

# logs-monitoring: ## View monitoring logs
# 	kubectl logs -f deployment/prometheus -n $(KUBE_NAMESPACE)








# ============================================================================
# Customer Demand Forecasting & Inventory Optimization System
# Complete MLOps Pipeline Makefile
# ============================================================================

.PHONY: help setup data-sources ingestion data-lake validation preprocessing \
        feature-store training evaluation mlflow-registry docker-build \
        k8s-deploy monitoring drift-detection retraining full-pipeline \
        clean status logs-api logs-monitoring quick-start quick-deploy \
        test lint format coverage serve

# ============================================================================
# Variables
# ============================================================================
PYTHON := python3
UV := uv
KAFKA_HOST := localhost:9092
REDIS_HOST := localhost
MLFLOW_HOST := localhost:5000
KUBE_NAMESPACE := demand-forecast-prod
DOCKER_REGISTRY := ghcr.io
DOCKER_IMAGE_NAME := $(shell echo $(USER) | tr '[:upper:]' '[:lower:]')/demand-forecast

# ============================================================================
# Colors for output
# ============================================================================
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

# ============================================================================
# Help & Documentation
# ============================================================================
help: ## Show all available commands
	@printf '${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}\n'
	@printf '${BLUE}║  Customer Demand Forecasting - MLOps Pipeline                ║${NC}\n'
	@printf '${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n'
	@printf '\n${YELLOW}📋 Available Commands:${NC}\n\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-25s${NC} %s\n", $$1, $$2}'
	@printf '\n${YELLOW}Example Workflow:${NC}\n'
	@printf '  ${GREEN}make setup${NC}               → Setup environment\n'
	@printf '  ${GREEN}make data-sources${NC}        → Fetch data\n'
	@printf '  ${GREEN}make training${NC}            → Train models\n'
	@printf '  ${GREEN}make serve${NC}               → Start API server\n'

# ============================================================================
# Setup & Environment
# ============================================================================
setup: ## Setup environment with uv
	@printf '${YELLOW}📦 Setting up environment...${NC}\n'
	@if command -v uv &> /dev/null; then \
		echo "Using uv for dependency management..."; \
		uv sync; \
	else \
		echo "uv not found, installing..."; \
		pip install uv; \
		uv sync; \
	fi
	@mkdir -p data/{raw,processed,features} models logs reports
	@mkdir -p deployments/kubernetes/overlays/{staging,production}
	@if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || echo "⚠️  .env.example not found, create .env manually"; fi
	@printf '${GREEN}✅ Setup complete!${NC}\n'
	@printf '${BLUE}Next steps:${NC}\n'
	@printf '  1. Update .env file with your credentials\n'
	@printf '  2. Run ${GREEN}make data-sources${NC} to fetch data\n'
	@printf '  3. Run ${GREEN}make training${NC} to train models\n'

# ============================================================================
# Code Quality
# ============================================================================
lint: ## Run linters (ruff, mypy)
	@printf '${YELLOW}🔍 Running linters...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run ruff check src/ tests/; \
		uv run mypy src/ --ignore-missing-imports --no-error-summary || true; \
	else \
		ruff check src/ tests/; \
		mypy src/ --ignore-missing-imports --no-error-summary || true; \
	fi
	@printf '${GREEN}✅ Linting complete!${NC}\n'

format: ## Format code with ruff
	@printf '${YELLOW}🎨 Formatting code...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run ruff format src/ tests/; \
		uv run ruff check --fix src/ tests/; \
	else \
		ruff format src/ tests/; \
		ruff check --fix src/ tests/; \
	fi
	@printf '${GREEN}✅ Formatting complete!${NC}\n'

# ============================================================================
# Testing
# ============================================================================
test: ## Run all tests
	@printf '${YELLOW}🧪 Running all tests...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run pytest tests/ -v --tb=short; \
	else \
		pytest tests/ -v --tb=short; \
	fi

test-unit: ## Run unit tests only
	@printf '${YELLOW}🧪 Running unit tests...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run pytest tests/unit/ -v; \
	else \
		pytest tests/unit/ -v; \
	fi

test-integration: ## Run integration tests
	@printf '${YELLOW}🧪 Running integration tests...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run pytest tests/integration/ -v; \
	else \
		pytest tests/integration/ -v; \
	fi

coverage: ## Run tests with coverage report
	@printf '${YELLOW}📊 Running tests with coverage...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run pytest tests/ --cov=src --cov-report=html --cov-report=term; \
	else \
		pytest tests/ --cov=src --cov-report=html --cov-report=term; \
	fi
	@printf '${GREEN}📊 Coverage report generated in htmlcov/index.html${NC}\n'

# ============================================================================
# Stage 1: Data Sources
# ============================================================================
data-sources: ## Fetch data from Hugging Face and other sources
	@printf '${YELLOW}[1/14] Fetching data sources...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/data_sources/huggingface_source.py; \
	else \
		python src/data_sources/huggingface_source.py; \
	fi
	@printf '${GREEN}✅ Data sources fetched${NC}\n'

# ============================================================================
# Stage 2: Ingestion Layer
# ============================================================================
ingestion: ## Ingest data through Kafka/Spark
	@printf '${YELLOW}[2/14] Starting data ingestion...${NC}\n'
	docker-compose up -d kafka zookeeper 2>/dev/null || echo "⚠️  Docker services not found"
	sleep 10
	@if command -v uv &> /dev/null; then \
		uv run python src/ingestion/kafka_streaming.py; \
	else \
		python src/ingestion/kafka_streaming.py; \
	fi
	@printf '${GREEN}✅ Data ingestion complete${NC}\n'

# ============================================================================
# Stage 3: Data Lake Storage
# ============================================================================
data-lake: ## Store data in data lake (S3/MinIO)
	@printf '${YELLOW}[3/14] Storing data in lake...${NC}\n'
	docker-compose up -d minio 2>/dev/null || echo "⚠️  Docker services not found"
	@if command -v uv &> /dev/null; then \
		uv run python src/data_lake/data_lake_manager.py; \
	else \
		python src/data_lake/data_lake_manager.py; \
	fi
	@printf '${GREEN}✅ Data stored in lake${NC}\n'

# ============================================================================
# Stage 4: Validation & EDA
# ============================================================================
validation: ## Run data validation and exploratory analysis
	@printf '${YELLOW}[4/14] Validating data...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/validation/data_validation.py; \
	else \
		python src/validation/data_validation.py; \
	fi
	@printf '${GREEN}✅ Validation complete${NC}\n'

# ============================================================================
# Stage 5: Preprocessing
# ============================================================================
preprocessing: ## Clean and preprocess data
	@printf '${YELLOW}[5/14] Preprocessing data...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/preprocessing/preprocessing_pipeline.py; \
	else \
		python src/preprocessing/preprocessing_pipeline.py; \
	fi
	@printf '${GREEN}✅ Preprocessing complete${NC}\n'

# ============================================================================
# Stage 6: Feature Store
# ============================================================================
feature-store: ## Create and update feature store
	@printf '${YELLOW}[6/14] Building feature store...${NC}\n'
	docker-compose up -d redis 2>/dev/null || echo "⚠️  Docker services not found"
	@if command -v uv &> /dev/null; then \
		uv run python src/feature_store/feature_store.py; \
	else \
		python src/feature_store/feature_store.py; \
	fi
	@printf '${GREEN}✅ Feature store ready${NC}\n'

# ============================================================================
# Stage 7: Training Pipeline
# ============================================================================
training: ## Train models (distributed/Kubeflow)
	@printf '${YELLOW}[7/14] Training models...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/training/training_pipeline.py; \
	else \
		python src/training/training_pipeline.py; \
	fi
	@printf '${GREEN}✅ Training complete${NC}\n'

# ============================================================================
# Stage 8: Evaluation & Tuning
# ============================================================================
evaluation: ## Evaluate models and tune hyperparameters
	@printf '${YELLOW}[8/14] Evaluating models...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/evaluation/model_evaluation.py; \
	else \
		python src/evaluation/model_evaluation.py; \
	fi
	@printf '${GREEN}✅ Evaluation complete${NC}\n'

# ============================================================================
# Stage 9: MLflow Registry
# ============================================================================
mlflow-registry: ## Register models in MLflow
	@printf '${YELLOW}[9/14] Registering models...${NC}\n'
	docker-compose up -d mlflow postgres minio 2>/dev/null || echo "⚠️  Docker services not found"
	sleep 10
	@if command -v uv &> /dev/null; then \
		uv run python src/mlflow_registry/model_registry.py; \
	else \
		python src/mlflow_registry/model_registry.py; \
	fi
	@printf '${GREEN}✅ Models registered${NC}\n'

# ============================================================================
# Stage 10: Docker Packaging
# ============================================================================
docker-build: ## Build Docker containers
	@printf '${YELLOW}[10/14] Building Docker images...${NC}\n'
	docker build -f deployments/docker/Dockerfile.api -t $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/api:latest .
	docker build -f deployments/docker/Dockerfile.trainer -t $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/trainer:latest .
	docker tag $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/api:latest $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/api:$(shell git rev-parse --short HEAD)
	docker tag $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/trainer:latest $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/trainer:$(shell git rev-parse --short HEAD)
	@printf '${GREEN}✅ Docker images built${NC}\n'

docker-push: ## Push Docker images to registry
	@printf '${YELLOW}📤 Pushing Docker images...${NC}\n'
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/api:latest
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/api:$(shell git rev-parse --short HEAD)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/trainer:latest
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME)/trainer:$(shell git rev-parse --short HEAD)
	@printf '${GREEN}✅ Images pushed${NC}\n'

# ============================================================================
# Stage 11: Kubernetes Deployment
# ============================================================================
k8s-deploy: ## Deploy to Kubernetes cluster
	@printf '${YELLOW}[11/14] Deploying to Kubernetes...${NC}\n'
	@if command -v kubectl &> /dev/null; then \
		kubectl create namespace $(KUBE_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true; \
		kubectl apply -f deployments/kubernetes/ -n $(KUBE_NAMESPACE) 2>/dev/null || echo "⚠️  Kubernetes manifests not found"; \
	else \
		echo "⚠️  kubectl not found, skipping Kubernetes deployment"; \
	fi
	@printf '${GREEN}✅ Deployment complete${NC}\n'

k8s-status: ## Check Kubernetes deployment status
	@printf '${YELLOW}☸️  Kubernetes status:${NC}\n'
	kubectl get all -n $(KUBE_NAMESPACE)
	kubectl get pods -n $(KUBE_NAMESPACE)
	kubectl get services -n $(KUBE_NAMESPACE)
	kubectl get ingress -n $(KUBE_NAMESPACE)

k8s-logs: ## View Kubernetes logs
	@printf '${YELLOW}📝 Kubernetes logs:${NC}\n'
	kubectl logs -f -l app=model-serving -n $(KUBE_NAMESPACE) || kubectl logs -f -l app=demand-forecast -n $(KUBE_NAMESPACE)

k8s-delete: ## Delete Kubernetes deployment
	@printf '${YELLOW}🗑️  Deleting Kubernetes resources...${NC}\n'
	kubectl delete namespace $(KUBE_NAMESPACE) 2>/dev/null || true
	@printf '${GREEN}✅ Kubernetes resources deleted${NC}\n'

# ============================================================================
# Stage 12: Monitoring Layer
# ============================================================================
monitoring: ## Setup monitoring (Prometheus/Grafana)
	@printf '${YELLOW}[12/14] Setting up monitoring...${NC}\n'
	kubectl apply -f deployments/kubernetes/monitoring/ -n $(KUBE_NAMESPACE) 2>/dev/null || echo "⚠️  Monitoring manifests not found"
	@if command -v uv &> /dev/null; then \
		uv run python src/monitoring/prometheus_metrics.py; \
	else \
		python src/monitoring/prometheus_metrics.py; \
	fi
	@printf '${GREEN}✅ Monitoring configured${NC}\n'

# ============================================================================
# Stage 13: Drift Detection
# ============================================================================
drift-detection: ## Setup drift detection
	@printf '${YELLOW}[13/14] Configuring drift detection...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/drift_detection/data_drift.py; \
	else \
		python src/drift_detection/data_drift.py; \
	fi
	@printf '${GREEN}✅ Drift detection configured${NC}\n'

# ============================================================================
# Stage 14: Retraining Pipeline
# ============================================================================
retraining: ## Setup automated retraining
	@printf '${YELLOW}[14/14] Configuring retraining pipeline...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python src/retraining/trigger_manager.py; \
	else \
		python src/retraining/trigger_manager.py; \
	fi
	@printf '${GREEN}✅ Retraining pipeline configured${NC}\n'

# ============================================================================
# Complete Pipelines
# ============================================================================
full-pipeline: data-sources ingestion data-lake validation preprocessing \
                feature-store training evaluation mlflow-registry \
                docker-build k8s-deploy monitoring drift-detection retraining
	@printf '${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}\n'
	@printf '${GREEN}║  🎉 Complete MLOps pipeline executed successfully!             ║${NC}\n'
	@printf '${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}\n'
	@printf '\n${BLUE}📊 Access Services:${NC}\n'
	@printf '  🌐 API: http://localhost:8000\n'
	@printf '  📊 Dashboard: http://localhost:8501\n'
	@printf '  🧪 MLflow: http://localhost:5000\n'
	@printf '  📈 Grafana: http://localhost:3000\n'
	@printf '  🔥 Prometheus: http://localhost:9090\n'

quick-start: setup data-sources ingestion data-lake validation preprocessing feature-store training
	@printf '${GREEN}✅ Quick start complete!${NC}\n'
	@printf '${BLUE}Run ${GREEN}make serve${BLUE} to start the API server${NC}\n'

quick-deploy: docker-build k8s-deploy
	@printf '${GREEN}✅ Quick deploy complete!${NC}\n'

# ============================================================================
# Serving & API
# ============================================================================
serve: ## Start model serving API
	@printf '${YELLOW}🚀 Starting model serving API...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run uvicorn src.serving.api:app --host 0.0.0.0 --port 8000 --reload; \
	else \
		uvicorn src.serving.api:app --host 0.0.0.0 --port 8000 --reload; \
	fi

serve-prod: ## Start production model serving API
	@printf '${YELLOW}🚀 Starting production API...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run gunicorn src.serving.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000; \
	else \
		gunicorn src.serving.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000; \
	fi

# ============================================================================
# Docker Compose (Local Development)
# ============================================================================
docker-up: ## Start all Docker services
	@printf '${YELLOW}🐳 Starting Docker services...${NC}\n'
	docker-compose up -d
	@sleep 5
	@printf '${GREEN}✅ Docker services started${NC}\n'
	@printf '${BLUE}Services:${NC}\n'
	@printf '  - API: http://localhost:8000\n'
	@printf '  - MLflow: http://localhost:5000\n'
	@printf '  - Kafka: localhost:9092\n'
	@printf '  - Redis: localhost:6379\n'

docker-down: ## Stop all Docker services
	@printf '${YELLOW}🐳 Stopping Docker services...${NC}\n'
	docker-compose down
	@printf '${GREEN}✅ Docker services stopped${NC}\n'

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-ps: ## Show Docker services status
	docker-compose ps

docker-clean: ## Clean Docker resources
	@printf '${YELLOW}🧹 Cleaning Docker resources...${NC}\n'
	docker-compose down -v
	docker system prune -f
	@printf '${GREEN}✅ Docker resources cleaned${NC}\n'

# ============================================================================
# Utility Commands
# ============================================================================
clean: ## Clean all artifacts and cache
	@printf '${YELLOW}🧹 Cleaning all artifacts...${NC}\n'
	rm -rf venv 2>/dev/null || true
	rm -rf data/raw/* data/processed/* data/features/* 2>/dev/null || true
	rm -rf models/* 2>/dev/null || true
	rm -rf logs/* 2>/dev/null || true
	rm -rf reports/* 2>/dev/null || true
	rm -rf htmlcov .pytest_cache .ruff_cache .mypy_cache 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@printf '${GREEN}✅ Clean complete!${NC}\n'

status: ## Check pipeline and service status
	@printf '${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}\n'
	@printf '${BLUE}║  📊 Pipeline Status                                            ║${NC}\n'
	@printf '${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n'
	@printf '\n${YELLOW}🐍 Python:${NC} '
	@python --version
	@printf '\n${YELLOW}📦 Dependencies:${NC}\n'
	@pip list 2>/dev/null | grep -E "(pandas|numpy|scikit-learn|torch|mlflow)" | head -5 || echo "  Not installed"
	@printf '\n${YELLOW}🐳 Docker Services:${NC}\n'
	@docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "  Docker not running"
	@printf '\n${YELLOW}☸️  Kubernetes:${NC}\n'
	@kubectl get pods -n $(KUBE_NAMESPACE) 2>/dev/null | head -5 || echo "  Kubernetes not configured"
	@printf '\n${YELLOW}📂 Data:${NC}\n'
	@ls -la data/ 2>/dev/null | head -5 || echo "  No data directory"
	@printf '\n${YELLOW}🧠 Models:${NC}\n'
	@ls -la models/ 2>/dev/null | head -5 || echo "  No models directory"
	@printf '\n${GREEN}✅ Status check complete!${NC}\n'

logs-api: ## View API logs
	@printf '${YELLOW}📝 API logs:${NC}\n'
	kubectl logs -f deployment/model-serving -n $(KUBE_NAMESPACE) -c api 2>/dev/null || \
	kubectl logs -f deployment/demand-forecast-api -n $(KUBE_NAMESPACE) 2>/dev/null || \
	echo "⚠️  No API deployment found"

logs-monitoring: ## View monitoring logs
	@printf '${YELLOW}📝 Monitoring logs:${NC}\n'
	kubectl logs -f deployment/prometheus -n $(KUBE_NAMESPACE) 2>/dev/null || \
	echo "⚠️  No monitoring deployment found"

logs-all: ## View all logs (API + Monitoring)
	@printf '${YELLOW}📝 All logs:${NC}\n'
	kubectl logs -f -l app=model-serving -n $(KUBE_NAMESPACE) 2>/dev/null || \
	kubectl logs -f -l app=demand-forecast -n $(KUBE_NAMESPACE) 2>/dev/null || \
	echo "⚠️  No logs found"

# ============================================================================
# Development & Debugging
# ============================================================================
dev: ## Start development environment
	@printf '${YELLOW}🚀 Starting development environment...${NC}\n'
	@make docker-up
	@make serve

debug: ## Run in debug mode with increased logging
	@printf '${YELLOW}🐛 Debug mode enabled...${NC}\n'
	@export LOG_LEVEL=DEBUG
	@export PYTHONDEBUG=1
	@make serve

shell: ## Open Python shell with project context
	@printf '${YELLOW}🐍 Opening Python shell...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run python; \
	else \
		python; \
	fi

notebook: ## Start Jupyter notebook
	@printf '${YELLOW}📓 Starting Jupyter notebook...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run jupyter notebook --ip=0.0.0.0 --port=8888 --allow-root; \
	else \
		jupyter notebook --ip=0.0.0.0 --port=8888 --allow-root; \
	fi

# ============================================================================
# Git Commands
# ============================================================================
git-status: ## Show git status
	git status

git-push: ## Push to remote with current branch
	git push origin $(shell git branch --show-current)

git-pull: ## Pull from remote with current branch
	git pull origin $(shell git branch --show-current)

# ============================================================================
# Database & Storage
# ============================================================================
db-migrate: ## Run database migrations
	@printf '${YELLOW}🗄️  Running database migrations...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run alembic upgrade head; \
	else \
		alembic upgrade head; \
	fi
	@printf '${GREEN}✅ Migrations complete${NC}\n'

db-rollback: ## Rollback last migration
	@printf '${YELLOW}🗄️  Rolling back migration...${NC}\n'
	@if command -v uv &> /dev/null; then \
		uv run alembic downgrade -1; \
	else \
		alembic downgrade -1; \
	fi
	@printf '${GREEN}✅ Rollback complete${NC}\n'

# ============================================================================
# Default target (show help)
# ============================================================================
.DEFAULT_GOAL := help