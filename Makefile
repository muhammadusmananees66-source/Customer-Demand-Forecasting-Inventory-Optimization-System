.PHONY: help setup data-ingestion data-lake validation preprocessing \
        feature-store training evaluation mlflow-registry docker-build \
        k8s-deploy monitoring drift-detection retraining full-pipeline

# Variables
PYTHON := python3
KAFKA_HOST := localhost:9092
REDIS_HOST := localhost
MLFLOW_HOST := localhost:5000
KUBE_NAMESPACE := demand-forecast-prod

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

help: ## Show all commands
	@printf '${BLUE}Demand Forecasting MLOps Pipeline${NC}\n'
	@printf '${YELLOW}Complete pipeline stages:${NC}\n\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-25s${NC} %s\n", $$1, $$2}'

# Stage 1: Data Sources
data-sources: ## Fetch data from Hugging Face and other sources
	@printf '${YELLOW}[1/14] Fetching data sources...${NC}\n'
	$(PYTHON) src/data_sources/huggingface_source.py
	$(PYTHON) src/data_sources/sales_api.py
	$(PYTHON) src/data_sources/weather_api.py
	@printf '${GREEN}✅ Data sources fetched${NC}\n'

# Stage 2: Ingestion Layer
ingestion: ## Ingest data through Kafka/Spark
	@printf '${YELLOW}[2/14] Starting data ingestion...${NC}\n'
	docker-compose up -d kafka zookeeper
	sleep 10
	$(PYTHON) src/ingestion/kafka_producer.py
	$(PYTHON) src/ingestion/spark_streaming.py
	@printf '${GREEN}✅ Data ingestion complete${NC}\n'

# Stage 3: Data Lake Storage
data-lake: ## Store data in data lake (S3/MinIO)
	@printf '${YELLOW}[3/14] Storing data in lake...${NC}\n'
	docker-compose up -d minio
	$(PYTHON) src/data_lake/s3_storage.py --zone raw
	$(PYTHON) src/data_lake/data_versioning.py --version v1.0
	@printf '${GREEN}✅ Data stored in lake${NC}\n'

# Stage 4: Validation & EDA
validation: ## Run data validation and exploratory analysis
	@printf '${YELLOW}[4/14] Validating data...${NC}\n'
	$(PYTHON) src/validation/data_quality.py
	$(PYTHON) src/validation/schema_validation.py
	$(PYTHON) src/validation/exploratory_analysis.py
	$(PYTHON) src/validation/statistical_tests.py
	@printf '${GREEN}✅ Validation complete${NC}\n'

# Stage 5: Preprocessing
preprocessing: ## Clean and preprocess data
	@printf '${YELLOW}[5/14] Preprocessing data...${NC}\n'
	$(PYTHON) src/preprocessing/data_cleaner.py
	$(PYTHON) src/preprocessing/outlier_handler.py
	$(PYTHON) src/preprocessing/missing_value_imputer.py
	$(PYTHON) src/preprocessing/data_normalizer.py
	@printf '${GREEN}✅ Preprocessing complete${NC}\n'

# Stage 6: Feature Store
feature-store: ## Create and update feature store
	@printf '${YELLOW}[6/14] Building feature store...${NC}\n'
	docker-compose up -d redis
	$(PYTHON) src/feature_store/redis_store.py --init
	$(PYTHON) src/feature_store/feature_registry.py
	$(PYTHON) src/feature_store/online_features.py
	$(PYTHON) src/feature_store/offline_features.py
	@printf '${GREEN}✅ Feature store ready${NC}\n'

# Stage 7: Training Pipeline
training: ## Train models (distributed/Kubeflow)
	@printf '${YELLOW}[7/14] Training models...${NC}\n'
	$(PYTHON) src/training/distributed_training.py --mode train
	$(PYTHON) src/training/kubeflow_pipeline.py
	$(PYTHON) src/training/ray_trainer.py
	@printf '${GREEN}✅ Training complete${NC}\n'

# Stage 8: Evaluation & Tuning
evaluation: ## Evaluate models and tune hyperparameters
	@printf '${YELLOW}[8/14] Evaluating models...${NC}\n'
	$(PYTHON) src/evaluation/model_metrics.py
	$(PYTHON) src/evaluation/hyperparameter_tuning.py --trials 100
	$(PYTHON) src/evaluation/ablation_study.py
	$(PYTHON) src/evaluation/model_comparison.py
	@printf '${GREEN}✅ Evaluation complete${NC}\n'

# Stage 9: MLflow Registry
mlflow-registry: ## Register models in MLflow
	@printf '${YELLOW}[9/14] Registering models...${NC}\n'
	docker-compose up -d mlflow postgres minio
	sleep 10
	$(PYTHON) src/mlflow_registry/model_registry.py --register
	$(PYTHON) src/mlflow_registry/experiment_tracking.py
	$(PYTHON) src/mlflow_registry/model_versioning.py
	$(PYTHON) src/mlflow_registry/model_staging.py --stage production
	@printf '${GREEN}✅ Models registered${NC}\n'

# Stage 10: Docker Packaging
docker-build: ## Build Docker containers
	@printf '${YELLOW}[10/14] Building Docker images...${NC}\n'
	docker build -f deployments/docker/Dockerfile.api -t demand-forecast/api:latest .
	docker build -f deployments/docker/Dockerfile.trainer -t demand-forecast/trainer:latest .
	docker build -f deployments/docker/Dockerfile.feature_store -t demand-forecast/feature-store:latest .
	docker build -f deployments/docker/Dockerfile.monitoring -t demand-forecast/monitoring:latest .
	@printf '${GREEN}✅ Docker images built${NC}\n'

# Stage 11: Kubernetes Deployment
k8s-deploy: ## Deploy to Kubernetes cluster
	@printf '${YELLOW}[11/14] Deploying to Kubernetes...${NC}\n'
	kubectl create namespace $(KUBE_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f deployments/kubernetes/configmap.yaml
	kubectl apply -f deployments/kubernetes/secrets.yaml
	kubectl apply -f deployments/kubernetes/kafka.yaml
	kubectl apply -f deployments/kubernetes/spark.yaml
	kubectl apply -f deployments/kubernetes/mlflow.yaml
	kubectl apply -f deployments/kubernetes/model_serving.yaml
	kubectl apply -f deployments/kubernetes/ingress.yaml
	kubectl apply -f deployments/kubernetes/hpa.yaml
	kubectl rollout status deployment/model-serving -n $(KUBE_NAMESPACE)
	@printf '${GREEN}✅ Deployment complete${NC}\n'

# Stage 12: Monitoring Layer
monitoring: ## Setup monitoring (Prometheus/Grafana)
	@printf '${YELLOW}[12/14] Setting up monitoring...${NC}\n'
	kubectl apply -f deployments/kubernetes/monitoring.yaml
	$(PYTHON) src/monitoring/prometheus_metrics.py
	$(PYTHON) src/monitoring/grafana_dashboards.py
	$(PYTHON) src/monitoring/performance_monitor.py
	$(PYTHON) src/monitoring/alert_manager.py --setup
	@printf '${GREEN}✅ Monitoring configured${NC}\n'

# Stage 13: Drift Detection
drift-detection: ## Setup drift detection
	@printf '${YELLOW}[13/14] Configuring drift detection...${NC}\n'
	$(PYTHON) src/drift_detection/data_drift.py --continuous
	$(PYTHON) src/drift_detection/concept_drift.py
	$(PYTHON) src/drift_detection/model_drift.py
	$(PYTHON) src/drift_detection/drift_alert.py --setup
	@printf '${GREEN}✅ Drift detection configured${NC}\n'

# Stage 14: Retraining Pipeline
retraining: ## Setup automated retraining
	@printf '${YELLOW}[14/14] Configuring retraining pipeline...${NC}\n'
	$(PYTHON) src/retraining/trigger_manager.py --setup
	$(PYTHON) src/retraining/pipeline_trigger.py
	$(PYTHON) src/retraining/model_updater.py
	$(PYTHON) src/retraining/a_b_testing.py --setup
	@printf '${GREEN}✅ Retraining pipeline configured${NC}\n'

# Complete Pipeline
full-pipeline: data-sources ingestion data-lake validation preprocessing \
                feature-store training evaluation mlflow-registry \
                docker-build k8s-deploy monitoring drift-detection retraining
	@printf '${GREEN}🎉 Complete MLOps pipeline executed successfully!${NC}\n'
	@printf '${BLUE}Access services:${NC}\n'
	@printf '  - API: http://localhost:8000\n'
	@printf '  - Dashboard: http://localhost:8501\n'
	@printf '  - MLflow: http://localhost:5000\n'
	@printf '  - Grafana: http://localhost:3000\n'
	@printf '  - Prometheus: http://localhost:9090\n'

# Quick Commands
quick-start: | setup data-sources ingestion data-lake validation preprocessing feature-store training
	@printf '${GREEN}Quick start complete!${NC}\n'

quick-deploy: | docker-build k8s-deploy
	@printf '${GREEN}Quick deploy complete!${NC}\n'

# Utility Commands
setup: ## Setup environment
	@printf '${YELLOW}Setting up environment...${NC}\n'
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	mkdir -p data/{raw,processed,features} models logs reports
	cp .env.example .env
	@printf '${GREEN}Setup complete${NC}\n'

clean: ## Clean all artifacts
	@printf '${YELLOW}Cleaning...${NC}\n'
	rm -rf venv data/* models/* logs/* reports/*
	docker-compose down -v
	kubectl delete namespace $(KUBE_NAMESPACE)
	@printf '${GREEN}Clean complete${NC}\n'

status: ## Check pipeline status
	@printf '${BLUE}Checking pipeline status...${NC}\n'
	@printf '${YELLOW}Kafka:${NC} ' && curl -s http://localhost:9092 || echo "Not running"
	@printf '${YELLOW}MLflow:${NC} ' && curl -s http://localhost:5000 || echo "Not running"
	@printf '${YELLOW}Kubernetes:${NC} ' && kubectl get pods -n $(KUBE_NAMESPACE) 2>/dev/null || echo "Not running"
	@printf '${YELLOW}Prometheus:${NC} ' && curl -s http://localhost:9090 || echo "Not running"

logs-api: ## View API logs
	kubectl logs -f deployment/model-serving -n $(KUBE_NAMESPACE) -c api

logs-monitoring: ## View monitoring logs
	kubectl logs -f deployment/prometheus -n $(KUBE_NAMESPACE)