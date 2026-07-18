# """
# Model Inference - Complete with MLflow registry
# """


# import json
# import os
# import pickle
# from typing import Any

# import mlflow
# import numpy as np
# import pandas as pd
# import structlog
# from mlflow.tracking import MlflowClient

# logger = structlog.get_logger()


# class ModelInference:
#     def __init__(self, config: dict[str, Any]):
#         self.config = config
#         self.model = None
#         self.feature_columns = []
#         self.model_version = config.get("version", "1.0.0")
#         self.model_name = config.get("model_name", "customer_demand_model")
#         self.mlflow_tracking_uri = config.get("mlflow_tracking_uri", "http://localhost:5000")
#         self.model_path = config.get("model_path")
#         self._registry_client = None

#     def _get_registry_client(self):
#         if self._registry_client is None:
#             mlflow.set_tracking_uri(self.mlflow_tracking_uri)
#             self._registry_client = MlflowClient()
#         return self._registry_client

#     def load_model(self, path: str | None = None):
#         if path:
#             self._load_from_path(path)
#         else:
#             self._load_from_registry()
#         logger.info(f"Model loaded: version={self.model_version}, features={len(self.feature_columns)}")

#     def _load_from_path(self, path: str):
#         with open(path, 'rb') as f:
#             self.model = pickle.load(f)
#         features_path = f"{path}.features"
#         if os.path.exists(features_path):
#             with open(features_path) as f:
#                 self.feature_columns = json.load(f)

#     def _load_from_registry(self):
#         client = self._get_registry_client()
#         try:
#             versions = client.get_latest_versions(self.model_name, stages=["Production"])
#             if not versions:
#                 logger.warning(f"No production model found for {self.model_name}")
#                 return

#             prod_version = versions[0]
#             self.model_version = prod_version.version
#             model_uri = f"models:/{self.model_name}/{prod_version.version}"
#             local_path = mlflow.artifacts.download_artifacts(model_uri)

#             model_file = os.path.join(local_path, "model.pkl")
#             with open(model_file, 'rb') as f:
#                 self.model = pickle.load(f)

#             features_file = os.path.join(local_path, "model.pkl.features")
#             if os.path.exists(features_file):
#                 with open(features_file) as f:
#                     self.feature_columns = json.load(f)

#             logger.info(f"Model loaded from registry: {self.model_name} v{self.model_version}")

#         except Exception as e:
#             logger.error(f"Failed to load model from registry: {e}")
#             raise

#     def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
#         if self.model is None:
#             raise ValueError("Model not loaded")

#         if isinstance(x, pd.DataFrame) and self.feature_columns:
#             missing = set(self.feature_columns) - set(x.columns)
#             if missing:
#                 raise ValueError(f"Missing features: {missing}")
#             x = x[self.feature_columns]

#         predictions = self.model.predict(x)
#         logger.debug(f"Prediction complete: {len(predictions)} samples")
#         return predictions

#     def predict_with_confidence(self, x: pd.DataFrame) -> dict[str, np.ndarray]:
#         predictions = self.predict(x)
#         return {
#             "predictions": predictions,
#             "confidence_lower": predictions * 0.85,
#             "confidence_upper": predictions * 1.15
#         }

#     def get_model_info(self) -> dict[str, Any]:
#         return {
#             "model_name": self.model_name,
#             "model_version": self.model_version,
#             "feature_columns": self.feature_columns,
#             "feature_count": len(self.feature_columns)
#         }


# """
# Model Inference - Complete with MLflow registry
# """

# import json
# import os
# import pickle
# from typing import Any

# import mlflow
# import numpy as np
# import pandas as pd
# import structlog
# from mlflow.tracking import MlflowClient

# logger = structlog.get_logger()


# class ModelInference:
#     """Production model inference with MLflow registry integration"""

#     def __init__(self, config: dict[str, Any]) -> None:
#         """
#         Initialize ModelInference with configuration.

#         Args:
#             config: Configuration dictionary containing:
#                 - version: Model version string
#                 - model_name: Name of the model in MLflow registry
#                 - mlflow_tracking_uri: MLflow tracking URI
#                 - model_path: Local path to model file (optional)
#         """
#         self.config: dict[str, Any] = config
#         self.model: Any | None = None
#         self.feature_columns: list[str] = []
#         self.model_version: str = config.get("version", "1.0.0")
#         self.model_name: str = config.get("model_name", "customer_demand_model")
#         self.mlflow_tracking_uri: str = config.get("mlflow_tracking_uri", "http://localhost:5000")
#         self.model_path: str | None = config.get("model_path")
#         self._registry_client: MlflowClient | None = None

#     def _get_registry_client(self) -> MlflowClient:
#         """Get or create MLflow registry client."""
#         if self._registry_client is None:
#             mlflow.set_tracking_uri(self.mlflow_tracking_uri)
#             self._registry_client = MlflowClient()
#         return self._registry_client

#     def load_model(self, path: str | None = None) -> None:
#         """
#         Load model from path or MLflow registry.

#         Args:
#             path: Optional local path to model file. If not provided,
#                  loads from MLflow registry (production stage).
#         """
#         if path:
#             self._load_from_path(path)
#         else:
#             self._load_from_registry()
#         logger.info(
#             f"Model loaded: version={self.model_version}, " f"features={len(self.feature_columns)}"
#         )

#     def _load_from_path(self, path: str) -> None:
#         """Load model from local path."""
#         with open(path, "rb") as f:
#             self.model = pickle.load(f)

#         features_path: str = f"{path}.features"
#         if os.path.exists(features_path):
#             with open(features_path) as f:
#                 self.feature_columns = json.load(f)

#     def _load_from_registry(self) -> None:
#         """Load model from MLflow registry (production stage)."""
#         client: MlflowClient = self._get_registry_client()

#         try:
#             versions = client.get_latest_versions(self.model_name, stages=["Production"])
#             if not versions:
#                 logger.warning(f"No production model found for {self.model_name}")
#                 return

#             prod_version = versions[0]
#             self.model_version = str(prod_version.version)
#             model_uri: str = f"models:/{self.model_name}/{prod_version.version}"
#             local_path: str = mlflow.artifacts.download_artifacts(model_uri)

#             model_file: str = os.path.join(local_path, "model.pkl")
#             with open(model_file, "rb") as f:
#                 self.model = pickle.load(f)

#             features_file: str = os.path.join(local_path, "model.pkl.features")
#             if os.path.exists(features_file):
#                 with open(features_file) as f:
#                     self.feature_columns = json.load(f)

#             logger.info(f"Model loaded from registry: {self.model_name} " f"v{self.model_version}")

#         except Exception as e:
#             logger.error(f"Failed to load model from registry: {e}")
#             raise

#     def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
#         """
#         Make predictions using the loaded model.

#         Args:
#             x: Input features as DataFrame or numpy array.

#         Returns:
#             numpy array of predictions.

#         Raises:
#             ValueError: If model is not loaded or features are missing.
#         """
#         if self.model is None:
#             raise ValueError("Model not loaded")

#         if isinstance(x, pd.DataFrame) and self.feature_columns:
#             missing = set(self.feature_columns) - set(x.columns)
#             if missing:
#                 raise ValueError(f"Missing features: {missing}")
#             x = x[self.feature_columns]

#         predictions: np.ndarray = self.model.predict(x)
#         logger.debug(f"Prediction complete: {len(predictions)} samples")
#         return predictions

#     def predict_with_confidence(self, x: pd.DataFrame) -> dict[str, np.ndarray]:
#         """
#         Make predictions with confidence intervals.

#         Args:
#             x: Input features as DataFrame.

#         Returns:
#             Dictionary with 'predictions', 'confidence_lower', 'confidence_upper'.
#         """
#         predictions: np.ndarray = self.predict(x)
#         return {
#             "predictions": predictions,
#             "confidence_lower": predictions * 0.85,
#             "confidence_upper": predictions * 1.15,
#         }

#     def get_model_info(self) -> dict[str, Any]:
#         """
#         Get model information.

#         Returns:
#             Dictionary with model metadata.
#         """
#         return {
#             "model_name": self.model_name,
#             "model_version": self.model_version,
#             "feature_columns": self.feature_columns,
#             "feature_count": len(self.feature_columns),
#         }

#     def save_model(self, path: str) -> None:
#         """
#         Save model and feature columns to disk.

#         Args:
#             path: Path to save model file.
#         """
#         import json
#         import pickle
#         from pathlib import Path

#         Path(path).parent.mkdir(parents=True, exist_ok=True)
#         with open(path, "wb") as f:
#             pickle.dump(self.model, f)
#         with open(f"{path}.features", "w") as f:
#             json.dump(self.feature_columns, f)


"""
Model Inference - Complete with MLflow registry
"""

import json
import os
import pickle
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import structlog
from mlflow.tracking import MlflowClient

logger = structlog.get_logger()


class ModelInference:
    """Production model inference with MLflow registry integration"""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize ModelInference with configuration.

        Args:
            config: Configuration dictionary containing:
                - version: Model version string
                - model_name: Name of the model in MLflow registry
                - mlflow_tracking_uri: MLflow tracking URI
                - model_path: Local path to model file (optional)
        """
        self.config: dict[str, Any] = config
        self.model: Any | None = None
        self.feature_columns: list[str] = []
        self.model_version: str = config.get("version", "1.0.0")
        self.model_name: str = config.get("model_name", "customer_demand_model")
        self.mlflow_tracking_uri: str = config.get("mlflow_tracking_uri", "http://localhost:5000")
        self.model_path: str | None = config.get("model_path")
        self._registry_client: MlflowClient | None = None

    def _get_registry_client(self) -> MlflowClient:
        """Get or create MLflow registry client."""
        if self._registry_client is None:
            mlflow.set_tracking_uri(self.mlflow_tracking_uri)
            self._registry_client = MlflowClient()
        return self._registry_client

    def load_model(self, path: str | None = None) -> None:
        """
        Load model from path or MLflow registry.

        Args:
            path: Optional local path to model file. If not provided,
                 falls back to the `model_path` set in config. If neither
                 is available, loads from MLflow registry (production stage).

        NOTE: Previously this only checked the `path` argument and ignored
        `self.model_path` (set from config["model_path"] in __init__)
        whenever load_model() was called with no argument. That silently
        sent every no-argument call to the MLflow registry even when a
        local model_path was configured, which is why
        test_model_loading_fallback (and anything else relying on
        config-only model_path) was hitting MLflow over the network
        instead of loading the local file.
        """
        resolved_path: str | None = path or self.model_path
        if resolved_path:
            self._load_from_path(resolved_path)
        else:
            self._load_from_registry()
        logger.info(
            f"Model loaded: version={self.model_version}, features={len(self.feature_columns)}"
        )

    def _load_from_path(self, path: str) -> None:
        """Load model from local path."""
        with open(path, "rb") as f:
            self.model = pickle.load(f)

        features_path: str = f"{path}.features"
        if os.path.exists(features_path):
            with open(features_path) as f:
                self.feature_columns = json.load(f)

    def _load_from_registry(self) -> None:
        """Load model from MLflow registry (production stage)."""
        client: MlflowClient = self._get_registry_client()

        try:
            versions = client.get_latest_versions(self.model_name, stages=["Production"])
            if not versions:
                logger.warning(f"No production model found for {self.model_name}")
                return

            prod_version = versions[0]
            self.model_version = str(prod_version.version)
            model_uri: str = f"models:/{self.model_name}/{prod_version.version}"
            local_path: str = mlflow.artifacts.download_artifacts(model_uri)

            model_file: str = os.path.join(local_path, "model.pkl")
            with open(model_file, "rb") as f:
                self.model = pickle.load(f)

            features_file: str = os.path.join(local_path, "model.pkl.features")
            if os.path.exists(features_file):
                with open(features_file) as f:
                    self.feature_columns = json.load(f)

            logger.info(f"Model loaded from registry: {self.model_name} v{self.model_version}")

        except Exception as e:
            logger.error(f"Failed to load model from registry: {e}")
            raise

    def predict(self, x: pd.DataFrame | np.ndarray) -> np.ndarray:
        """
        Make predictions using the loaded model.

        Args:
            x: Input features as DataFrame or numpy array.

        Returns:
            numpy array of predictions.

        Raises:
            ValueError: If model is not loaded or features are missing.
        """
        if self.model is None:
            raise ValueError("Model not loaded")

        if isinstance(x, pd.DataFrame) and self.feature_columns:
            missing = set(self.feature_columns) - set(x.columns)
            if missing:
                raise ValueError(f"Missing features: {missing}")
            x = x[self.feature_columns]

        predictions: np.ndarray = self.model.predict(x)
        logger.debug(f"Prediction complete: {len(predictions)} samples")
        return predictions

    def predict_with_confidence(self, x: pd.DataFrame) -> dict[str, np.ndarray]:
        """
        Make predictions with confidence intervals.

        Args:
            x: Input features as DataFrame.

        Returns:
            Dictionary with 'predictions', 'confidence_lower', 'confidence_upper'.
        """
        predictions: np.ndarray = self.predict(x)
        return {
            "predictions": predictions,
            "confidence_lower": predictions * 0.85,
            "confidence_upper": predictions * 1.15,
        }

    def get_model_info(self) -> dict[str, Any]:
        """
        Get model information.

        Returns:
            Dictionary with model metadata.
        """
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_columns": self.feature_columns,
            "feature_count": len(self.feature_columns),
        }

    def save_model(self, path: str) -> None:
        """
        Save model and feature columns to disk.

        Args:
            path: Path to save model file.
        """
        import json
        import pickle
        from pathlib import Path

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        with open(f"{path}.features", "w") as f:
            json.dump(self.feature_columns, f)
