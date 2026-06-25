"""
MLflow Registry Layer - Model Versioning, Staging, Production Promotion
"""

import mlflow
import mlflow.sklearn
import mlflow.pytorch
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from datetime import datetime
from typing import Dict, List, Optional
import json
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Complete model registry with MLflow"""

    def __init__(self, tracking_uri: str = "http://mlflow:5000", registry_uri: str = None):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient(tracking_uri)
        self.experiment_name = "demand_forecasting"

        # Create experiment if not exists
        try:
            self.experiment_id = mlflow.create_experiment(self.experiment_name)
        except:
            self.experiment_id = mlflow.get_experiment_by_name(self.experiment_name).experiment_id

        mlflow.set_experiment(self.experiment_name)

    def log_model(self, model, model_name: str, metrics: Dict, params: Dict,
                  artifacts: Dict = None, tags: Dict = None):
        """Log model to MLflow"""

        with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            # Log parameters
            for key, value in params.items():
                mlflow.log_param(key, value)

            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)

            # Log tags
            if tags:
                for key, value in tags.items():
                    mlflow.set_tag(key, value)

            # Log artifacts
            if artifacts:
                for name, path in artifacts.items():
                    mlflow.log_artifact(path, artifact_path=name)

            # Log model
            if isinstance(model, torch.nn.Module):
                mlflow.pytorch.log_model(model, model_name)
            else:
                mlflow.sklearn.log_model(model, model_name)

            run_id = mlflow.active_run().info.run_id

            # Register model
            model_uri = f"runs:/{run_id}/{model_name}"
            registered_model = mlflow.register_model(model_uri, model_name)

            return run_id, registered_model.version

    def transition_model_stage(self, model_name: str, version: str, stage: str):
        """Transition model to different stage (Staging, Production, Archived)"""

        stages = ['Staging', 'Production', 'Archived']
        if stage not in stages:
            raise ValueError(f"Stage must be one of {stages}")

        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=True
        )

        logger.info(f"✅ Model {model_name} v{version} transitioned to {stage}")

    def get_production_model(self, model_name: str):
        """Get the current production model"""

        model_version = self.client.get_latest_versions(model_name, stages=["Production"])

        if not model_version:
            raise ValueError(f"No production model found for {model_name}")

        model_uri = f"models:/{model_name}/Production"
        model = mlflow.sklearn.load_model(model_uri)

        return model, model_version[0].version

    def compare_models(self, model_name: str) -> pd.DataFrame:
        """Compare all versions of a model"""

        versions = self.client.search_model_versions(f"name='{model_name}'")

        comparisons = []
        for version in versions:
            run = self.client.get_run(version.run_id)

            comparisons.append({
                'version': version.version,
                'stage': version.current_stage,
                'created_at': version.creation_timestamp,
                'metrics': run.data.metrics,
                'params': run.data.params,
                'run_id': version.run_id
            })

        return pd.DataFrame(comparisons)

    def promote_candidate(self, model_name: str, metric_name: str = 'mae',
                          direction: str = 'min'):
        """Automatically promote best performing model"""

        versions = self.client.search_model_versions(f"name='{model_name}'")

        best_version = None
        best_metric = float('inf') if direction == 'min' else -float('inf')

        for version in versions:
            run = self.client.get_run(version.run_id)
            metric_value = run.data.metrics.get(metric_name)

            if metric_value:
                if direction == 'min' and metric_value < best_metric:
                    best_metric = metric_value
                    best_version = version
                elif direction == 'max' and metric_value > best_metric:
                    best_metric = metric_value
                    best_version = version

        if best_version and best_version.current_stage != 'Production':
            self.transition_model_stage(
                model_name,
                best_version.version,
                'Production'
            )

            logger.info(f"✅ Promoted version {best_version.version} to production (MAE: {best_metric:.4f})")

    def create_model_ensemble(self, model_names: List[str], weights: List[float]):
        """Create ensemble from registered models"""

        models = []
        for name in model_names:
            model, _ = self.get_production_model(name)
            models.append(model)

        class EnsembleModel:
            def __init__(self, models, weights):
                self.models = models
                self.weights = weights

            def predict(self, X):
                predictions = np.array([model.predict(X) for model in self.models])
                return np.average(predictions, axis=0, weights=self.weights)

        ensemble = EnsembleModel(models, weights)

        # Log ensemble as model
        with mlflow.start_run(run_name="ensemble_model"):
            mlflow.sklearn.log_model(ensemble, "ensemble")

            # Log ensemble composition
            ensemble_info = {
                'models': model_names,
                'weights': weights,
                'created_at': datetime.now().isoformat()
            }
            mlflow.log_dict(ensemble_info, "ensemble_info.json")

        return ensemble