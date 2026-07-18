# """
# Model Trainer - Production-grade ML training with XGBoost, RandomForest, and distributed training
# """

# import json
# import pickle
# from pathlib import Path
# from typing import Any

# import mlflow
# import numpy as np
# import pandas as pd
# import ray
# import structlog
# import xgboost as xgb
# from ray import train as ray_train
# from ray.train import RunConfig, ScalingConfig
# from ray.train.torch import TorchTrainer
# from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# from sklearn.preprocessing import LabelEncoder

# # Try importing torch for GPU support
# try:
#     import torch
# except ImportError:
#     torch = None

# logger = structlog.get_logger()


# class ModelTrainer:
#     """Production-grade model trainer with MLflow tracking and distributed training support"""

#     def __init__(self, config: dict[str, Any]):
#         self.config = config
#         self.model_type = config.get("model_type", "xgboost")
#         self.date_col = config.get("date_col", "date")
#         self.target_col = config.get("target_col", "quantity")
#         self.hyperparameters = config.get("hyperparameters", {})
#         self.model: Any | None = None
#         self.feature_columns: list[str] | None = None
#         self.metrics: dict[str, float] = {}
#         self.label_encoders: dict[str, LabelEncoder] = {}  # For categorical encoding
#         self.is_distributed = config.get("distributed", False)

#         # Initialize MLflow
#         try:
#             mlflow.set_tracking_uri(config.get("mlflow_tracking_uri", "file:./mlruns"))
#             mlflow.set_experiment(config.get("experiment_name", "customer_demand"))
#         except Exception as e:
#             logger.warning(f"MLflow initialization failed: {e}")

#     def _prepare_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
#         """
#         Prepare features for model training - handle non-numeric columns

#         Args:
#             df: Input DataFrame
#             fit: If True, fit encoders; if False, use existing encoders

#         Returns:
#             DataFrame with only numeric features
#         """
#         df = df.copy()

#         # Drop date column if it exists (already used for splitting)
#         if self.date_col in df.columns:
#             df = df.drop(columns=[self.date_col])

#         # Handle categorical variables - convert to numeric
#         categorical_cols = df.select_dtypes(include=["object", "category"]).columns

#         for col in categorical_cols:
#             if fit:
#                 # Fit new encoder
#                 encoder = LabelEncoder()
#                 # Handle NaN values
#                 df[col] = df[col].fillna("unknown")
#                 df[col] = encoder.fit_transform(df[col].astype(str))
#                 self.label_encoders[col] = encoder
#             else:
#                 # Use existing encoder
#                 if col in self.label_encoders:
#                     encoder = self.label_encoders[col]
#                     # Handle unseen categories
#                     df[col] = df[col].fillna("unknown").astype(str)
#                     # Transform, mapping unseen to 0 - fix for B023
#                     known_classes = set(encoder.classes_)
#                     df[col] = df[col].apply(
#                         lambda x, enc=encoder, known=known_classes: (
#                             enc.transform([x])[0] if x in known else 0
#                         )
#                     )
#                 else:
#                     # Fallback: drop column if no encoder
#                     logger.warning(f"No encoder found for column {col}, dropping")
#                     df = df.drop(columns=[col])

#         # Ensure all columns are numeric
#         numeric_cols = df.select_dtypes(include=[np.number]).columns
#         df = df[numeric_cols]

#         # Handle any remaining NaN values
#         df = df.fillna(0)

#         return df

#     def train(self, df: pd.DataFrame, y: pd.Series) -> dict[str, float]:
#         """
#         Train the model with time-series aware split

#         Args:
#             df: Feature DataFrame
#             y: Target Series

#         Returns:
#             dict: Training metrics
#         """
#         # Sort by date if available
#         if self.date_col in df.columns:
#             df = df.sort_values(self.date_col)
#             y = y.loc[df.index]

#         # Prepare features (convert non-numeric columns)
#         df_prepared = self._prepare_features(df, fit=True)

#         # Update feature columns
#         self.feature_columns = df_prepared.columns.tolist()

#         n = len(df_prepared)
#         train_size = int(n * 0.7)
#         val_size = int(n * 0.15)

#         x_train = df_prepared.iloc[:train_size]
#         y_train = y.iloc[:train_size]
#         x_val = df_prepared.iloc[train_size : train_size + val_size]
#         y_val = y.iloc[train_size : train_size + val_size]
#         x_test = df_prepared.iloc[train_size + val_size :]
#         y_test = y.iloc[train_size + val_size :]

#         logger.info(
#             f"Time-series split: train={len(x_train)}, val={len(x_val)}, test={len(x_test)}"
#         )

#         # Train model
#         use_distributed = self.config.get("distributed", False)
#         if use_distributed:
#             self.model = self._train_distributed(x_train, y_train, x_val, y_val)
#         else:
#             self.model = self._train_model(x_train, y_train)

#         # Evaluate
#         metrics = self._evaluate_model(x_train, y_train, x_val, y_val, x_test, y_test)
#         self.metrics = metrics

#         # Log to MLflow
#         try:
#             with mlflow.start_run(nested=True) as run:
#                 mlflow.log_params(self.config.get("hyperparameters", {}))
#                 mlflow.log_param("model_type", self.model_type)
#                 mlflow.log_param("train_size", len(x_train))
#                 mlflow.log_param("val_size", len(x_val))
#                 mlflow.log_param("test_size", len(x_test))
#                 mlflow.log_param("feature_columns", str(self.feature_columns))

#                 for name, value in metrics.items():
#                     mlflow.log_metric(name, value)

#                 # Save model
#                 if self.config.get("save_model", True):
#                     self._save_model(run.info.run_id)
#         except Exception as e:
#             logger.warning(f"Could not log to MLflow: {e}")

#         return metrics

#     def _train_model(self, x_train: pd.DataFrame, y_train: pd.Series) -> Any:
#         """Train a single model"""
#         params = self.config.get("hyperparameters", {})

#         if self.model_type == "xgboost":
#             # Use CPU for Codespaces
#             params.setdefault("n_estimators", 100)
#             params.setdefault("learning_rate", 0.1)
#             params.setdefault("max_depth", 6)
#             params.setdefault("random_state", 42)

#             # Check for GPU
#             if self._has_gpu():
#                 params["device"] = "cuda"
#             else:
#                 params["device"] = "cpu"

#             model = xgb.XGBRegressor(**params)
#             model.fit(x_train, y_train)

#         elif self.model_type == "random_forest":
#             params.setdefault("n_estimators", 100)
#             params.setdefault("max_depth", 10)
#             params.setdefault("random_state", 42)
#             params.setdefault("n_jobs", -1)
#             model = RandomForestRegressor(**params)
#             model.fit(x_train, y_train)

#         elif self.model_type == "gradient_boosting":
#             params.setdefault("n_estimators", 100)
#             params.setdefault("learning_rate", 0.1)
#             params.setdefault("max_depth", 5)
#             params.setdefault("random_state", 42)
#             model = GradientBoostingRegressor(**params)
#             model.fit(x_train, y_train)

#         else:
#             raise ValueError(f"Unsupported model type: {self.model_type}")

#         return model

#     def _train_distributed(
#         self, x_train: pd.DataFrame, y_train: pd.Series, x_val: pd.DataFrame, y_val: pd.Series
#     ) -> Any:
#         """Train model using Ray for distributed training"""
#         if not ray.is_initialized():
#             ray.init()

#         # Prepare data for distributed training
#         train_data = pd.concat([x_train, y_train.rename("target")], axis=1)
#         val_data = pd.concat([x_val, y_val.rename("target")], axis=1)

#         train_dataset = ray.data.from_pandas(train_data)
#         val_dataset = ray.data.from_pandas(val_data)

#         config = {
#             "model_type": self.model_type,
#             "hyperparameters": self.hyperparameters,
#             "num_workers": self.config.get("num_workers", 2),
#             "use_gpu": self._has_gpu(),
#         }

#         def train_func(config: dict[str, Any]) -> dict[str, float]:
#             import xgboost as xgb

#             # Get data
#             train_df = ray_train.get_dataset_shard("train")
#             val_df = ray_train.get_dataset_shard("val")

#             train_df = train_df.to_pandas()
#             val_df = val_df.to_pandas()

#             x_train_local = train_df.drop(columns=["target"])
#             y_train_local = train_df["target"]
#             x_val_local = val_df.drop(columns=["target"])
#             y_val_local = val_df["target"]

#             model = xgb.XGBRegressor(
#                 n_estimators=config["hyperparameters"].get("n_estimators", 100),
#                 learning_rate=config["hyperparameters"].get("learning_rate", 0.1),
#                 max_depth=config["hyperparameters"].get("max_depth", 6),
#                 random_state=42,
#                 device="cuda" if config.get("use_gpu", False) else "cpu",
#             )
#             model.fit(x_train_local, y_train_local)

#             from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

#             y_pred = model.predict(x_val_local)
#             return {
#                 "mse": mean_squared_error(y_val_local, y_pred),
#                 "mae": mean_absolute_error(y_val_local, y_pred),
#                 "r2": r2_score(y_val_local, y_pred),
#             }

#         trainer = TorchTrainer(
#             train_func,
#             scaling_config=ScalingConfig(
#                 num_workers=config["num_workers"],
#                 use_gpu=config["use_gpu"],
#             ),
#             run_config=RunConfig(
#                 name="xgboost_distributed",
#                 storage_path=self.config.get("ray_storage_path", "/tmp/ray_results"),
#             ),
#             datasets={"train": train_dataset, "val": val_dataset},
#         )

#         result = trainer.fit()
#         best_checkpoint = result.checkpoint
#         model_path = best_checkpoint.get_path("model.pkl")

#         with open(model_path, "rb") as f:
#             model = pickle.load(f)

#         return model

#     def _evaluate_model(
#         self,
#         x_train: pd.DataFrame,
#         y_train: pd.Series,
#         x_val: pd.DataFrame,
#         y_val: pd.Series,
#         x_test: pd.DataFrame,
#         y_test: pd.Series,
#     ) -> dict[str, float]:
#         """Evaluate model on train, validation, and test sets"""
#         from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

#         if self.model is None:
#             raise ValueError("Model is None. Cannot evaluate.")

#         metrics: dict[str, float] = {}

#         for name, x_data, y_data in [
#             ("train", x_train, y_train),
#             ("val", x_val, y_val),
#             ("test", x_test, y_test),
#         ]:
#             if len(x_data) == 0:
#                 continue

#             y_pred = self.model.predict(x_data)
#             mse = mean_squared_error(y_data, y_pred)
#             mae = mean_absolute_error(y_data, y_pred)
#             r2 = r2_score(y_data, y_pred)

#             metrics[f"{name}_mse"] = float(mse)
#             metrics[f"{name}_mae"] = float(mae)
#             metrics[f"{name}_r2"] = float(r2)

#         return metrics

#     def _save_model(self, run_id: str) -> None:
#         """Save model and feature columns"""
#         path = self.config.get("model_path", f"models/{run_id}")
#         Path(path).mkdir(parents=True, exist_ok=True)

#         # Save model
#         with open(f"{path}/model.pkl", "wb") as f:
#             pickle.dump(self.model, f)

#         # Save feature columns
#         with open(f"{path}/features.json", "w") as f:
#             json.dump(self.feature_columns, f)

#         # Save label encoders
#         with open(f"{path}/encoders.pkl", "wb") as f:
#             pickle.dump(self.label_encoders, f)

#         logger.info(f"Model saved to {path}")

#     def _has_gpu(self) -> bool:
#         """Check if GPU is available"""
#         return torch is not None and torch.cuda.is_available()

#     def predict(self, x: pd.DataFrame) -> np.ndarray:
#         """Make predictions with trained model"""
#         if self.model is None:
#             raise ValueError("Model not trained. Call train() first.")

#         # Prepare features using existing encoders
#         x_prepared = self._prepare_features(x, fit=False)

#         # Ensure we have all required columns
#         if self.feature_columns is not None:
#             for col in self.feature_columns:
#                 if col not in x_prepared.columns:
#                     x_prepared[col] = 0
#             x_prepared = x_prepared[self.feature_columns]

#         return self.model.predict(x_prepared)

#     def load_model(self, path: str) -> None:
#         """Load a saved model"""
#         try:
#             with open(f"{path}/model.pkl", "rb") as f:
#                 self.model = pickle.load(f)

#             with open(f"{path}/features.json") as f:
#                 self.feature_columns = json.load(f)

#             # Load label encoders if they exist
#             encoders_path = f"{path}/encoders.pkl"
#             if Path(encoders_path).exists():
#                 with open(encoders_path, "rb") as f:
#                     self.label_encoders = pickle.load(f)

#             logger.info(f"Model loaded from {path}")
#         except FileNotFoundError as e:
#             logger.error(f"Model not found at {path}: {e}")
#             raise
#         except Exception as e:
#             logger.error(f"Error loading model: {e}")
#             raise

#     def get_feature_importance(self) -> dict[str, float]:
#         """Get feature importance from trained model"""
#         if self.model is None:
#             raise ValueError("Model not trained. Call train() first.")

#         if self.feature_columns is None:
#             raise ValueError("Feature columns not set. Train the model first.")

#         if hasattr(self.model, "feature_importances_"):
#             importance = self.model.feature_importances_
#         elif hasattr(self.model, "coef_"):
#             importance = np.abs(self.model.coef_)
#         else:
#             raise ValueError(f"Model {self.model_type} does not support feature importance")

#         # Ensure we have the right number of features
#         if len(importance) != len(self.feature_columns):
#             # Truncate or pad as needed
#             if len(importance) < len(self.feature_columns):
#                 # Pad with zeros
#                 importance = list(importance) + [0] * (len(self.feature_columns) - len(importance))
#             else:
#                 # Truncate
#                 importance = importance[: len(self.feature_columns)]

#         return dict(zip(self.feature_columns, importance, strict=False))


"""
Model Trainer - Production-grade ML training with XGBoost, RandomForest, and distributed training
"""

import json
import pickle
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import ray
import structlog
import xgboost as xgb
from ray import train as ray_train
from ray.train import RunConfig, ScalingConfig
from ray.train.torch import TorchTrainer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

# Try importing torch for GPU support
try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

logger = structlog.get_logger()


class ModelTrainer:
    """Production-grade model trainer with MLflow tracking and distributed training support"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.model_type = config.get("model_type", "xgboost")
        self.date_col = config.get("date_col", "date")
        self.target_col = config.get("target_col", "quantity")
        self.hyperparameters = config.get("hyperparameters", {})
        self.model: Any | None = None
        self.feature_columns: list[str] | None = None
        self.metrics: dict[str, float] = {}
        self.label_encoders: dict[str, LabelEncoder] = {}  # For categorical encoding
        self.is_distributed = config.get("distributed", False)

        # Initialize MLflow
        try:
            mlflow.set_tracking_uri(config.get("mlflow_tracking_uri", "file:./mlruns"))
            mlflow.set_experiment(config.get("experiment_name", "customer_demand"))
        except Exception as e:
            logger.warning(f"MLflow initialization failed: {e}")

    def _prepare_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Prepare features for model training - handle non-numeric columns

        Args:
            df: Input DataFrame
            fit: If True, fit encoders; if False, use existing encoders

        Returns:
            DataFrame with only numeric features
        """
        df = df.copy()

        # Drop date column if it exists (already used for splitting)
        if self.date_col in df.columns:
            df = df.drop(columns=[self.date_col])

        # Handle categorical variables - convert to numeric
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns

        for col in categorical_cols:
            if fit:
                # Fit new encoder
                encoder = LabelEncoder()
                # Handle NaN values
                df[col] = df[col].fillna("unknown")
                df[col] = encoder.fit_transform(df[col].astype(str))
                self.label_encoders[col] = encoder
            else:
                # Use existing encoder
                if col in self.label_encoders:
                    encoder = self.label_encoders[col]
                    # Handle unseen categories
                    df[col] = df[col].fillna("unknown").astype(str)
                    # Transform, mapping unseen to 0 - fix for B023
                    known_classes = set(encoder.classes_)
                    df[col] = df[col].apply(
                        lambda x, enc=encoder, known=known_classes: (
                            enc.transform([x])[0] if x in known else 0
                        )
                    )
                else:
                    # Fallback: drop column if no encoder
                    logger.warning(f"No encoder found for column {col}, dropping")
                    df = df.drop(columns=[col])

        # Ensure all columns are numeric
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df = df[numeric_cols]

        # Handle any remaining NaN values
        df = df.fillna(0)

        return df

    def train(self, df: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """
        Train the model with time-series aware split

        Args:
            df: Feature DataFrame
            y: Target Series

        Returns:
            dict: Training metrics
        """
        # Sort by date if available
        if self.date_col in df.columns:
            df = df.sort_values(self.date_col)
            y = y.loc[df.index]

        # Prepare features (convert non-numeric columns)
        df_prepared = self._prepare_features(df, fit=True)

        # Update feature columns
        self.feature_columns = df_prepared.columns.tolist()

        n = len(df_prepared)
        train_size = int(n * 0.7)
        val_size = int(n * 0.15)

        x_train = df_prepared.iloc[:train_size]
        y_train = y.iloc[:train_size]
        x_val = df_prepared.iloc[train_size : train_size + val_size]
        y_val = y.iloc[train_size : train_size + val_size]
        x_test = df_prepared.iloc[train_size + val_size :]
        y_test = y.iloc[train_size + val_size :]

        logger.info(
            f"Time-series split: train={len(x_train)}, val={len(x_val)}, test={len(x_test)}"
        )

        # Train model
        use_distributed = self.config.get("distributed", False)
        if use_distributed:
            self.model = self._train_distributed(x_train, y_train, x_val, y_val)
        else:
            self.model = self._train_model(x_train, y_train)

        # Evaluate
        metrics = self._evaluate_model(x_train, y_train, x_val, y_val, x_test, y_test)
        self.metrics = metrics

        # Log to MLflow
        try:
            with mlflow.start_run(nested=True) as run:
                mlflow.log_params(self.config.get("hyperparameters", {}))
                mlflow.log_param("model_type", self.model_type)
                mlflow.log_param("train_size", len(x_train))
                mlflow.log_param("val_size", len(x_val))
                mlflow.log_param("test_size", len(x_test))
                mlflow.log_param("feature_columns", str(self.feature_columns))

                for name, value in metrics.items():
                    mlflow.log_metric(name, value)

                # Save model
                if self.config.get("save_model", True):
                    self._save_model(run.info.run_id)
        except Exception as e:
            logger.warning(f"Could not log to MLflow: {e}")

        return metrics

    def _train_model(self, x_train: pd.DataFrame, y_train: pd.Series) -> Any:
        """Train a single model"""
        params = self.config.get("hyperparameters", {})

        if self.model_type == "xgboost":
            # Use CPU for Codespaces
            params.setdefault("n_estimators", 100)
            params.setdefault("learning_rate", 0.1)
            params.setdefault("max_depth", 6)
            params.setdefault("random_state", 42)

            # Check for GPU
            if self._has_gpu():
                params["device"] = "cuda"
            else:
                params["device"] = "cpu"

            model = xgb.XGBRegressor(**params)
            model.fit(x_train, y_train)

        elif self.model_type == "random_forest":
            params.setdefault("n_estimators", 100)
            params.setdefault("max_depth", 10)
            params.setdefault("random_state", 42)
            params.setdefault("n_jobs", -1)
            model = RandomForestRegressor(**params)
            model.fit(x_train, y_train)

        elif self.model_type == "gradient_boosting":
            params.setdefault("n_estimators", 100)
            params.setdefault("learning_rate", 0.1)
            params.setdefault("max_depth", 5)
            params.setdefault("random_state", 42)
            model = GradientBoostingRegressor(**params)
            model.fit(x_train, y_train)

        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        return model

    def _train_distributed(
        self, x_train: pd.DataFrame, y_train: pd.Series, x_val: pd.DataFrame, y_val: pd.Series
    ) -> Any:
        """Train model using Ray for distributed training"""
        if not ray.is_initialized():
            ray.init()

        # Prepare data for distributed training
        train_data = pd.concat([x_train, y_train.rename("target")], axis=1)
        val_data = pd.concat([x_val, y_val.rename("target")], axis=1)

        train_dataset = ray.data.from_pandas(train_data)
        val_dataset = ray.data.from_pandas(val_data)

        config = {
            "model_type": self.model_type,
            "hyperparameters": self.hyperparameters,
            "num_workers": self.config.get("num_workers", 2),
            "use_gpu": self._has_gpu(),
        }

        def train_func(config: dict[str, Any]) -> dict[str, float]:
            import xgboost as xgb

            # Get data
            train_df = ray_train.get_dataset_shard("train")
            val_df = ray_train.get_dataset_shard("val")

            train_df = train_df.to_pandas()
            val_df = val_df.to_pandas()

            x_train_local = train_df.drop(columns=["target"])
            y_train_local = train_df["target"]
            x_val_local = val_df.drop(columns=["target"])
            y_val_local = val_df["target"]

            model = xgb.XGBRegressor(
                n_estimators=config["hyperparameters"].get("n_estimators", 100),
                learning_rate=config["hyperparameters"].get("learning_rate", 0.1),
                max_depth=config["hyperparameters"].get("max_depth", 6),
                random_state=42,
                device="cuda" if config.get("use_gpu", False) else "cpu",
            )
            model.fit(x_train_local, y_train_local)

            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

            y_pred = model.predict(x_val_local)
            return {
                "mse": mean_squared_error(y_val_local, y_pred),
                "mae": mean_absolute_error(y_val_local, y_pred),
                "r2": r2_score(y_val_local, y_pred),
            }

        trainer = TorchTrainer(
            train_func,  # type: ignore[arg-type]
            scaling_config=ScalingConfig(
                num_workers=config["num_workers"],
                use_gpu=config["use_gpu"],
            ),
            run_config=RunConfig(
                name="xgboost_distributed",
                storage_path=self.config.get("ray_storage_path", "/tmp/ray_results"),
            ),
            datasets={"train": train_dataset, "val": val_dataset},
        )

        # Fixed: Properly handle the training result
        training_result = trainer.fit()

        # Extract model from checkpoint with proper type handling
        if training_result.checkpoint is not None:
            best_checkpoint = training_result.checkpoint
            # Use the correct method to get model path
            # The checkpoint may be a Checkpoint object with a path property
            if hasattr(best_checkpoint, "get_path"):
                model_path = best_checkpoint.get_path("model.pkl")
            else:
                # Fallback: use the checkpoint's path attribute
                model_path = f"{best_checkpoint}/model.pkl"
        else:
            raise RuntimeError("No checkpoint found from training run")

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        return model

    def _evaluate_model(
        self,
        x_train: pd.DataFrame,
        y_train: pd.Series,
        x_val: pd.DataFrame,
        y_val: pd.Series,
        x_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> dict[str, float]:
        """Evaluate model on train, validation, and test sets"""
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        if self.model is None:
            raise ValueError("Model is None. Cannot evaluate.")

        metrics: dict[str, float] = {}

        for name, x_data, y_data in [
            ("train", x_train, y_train),
            ("val", x_val, y_val),
            ("test", x_test, y_test),
        ]:
            if len(x_data) == 0:
                continue

            y_pred = self.model.predict(x_data)
            mse = mean_squared_error(y_data, y_pred)
            mae = mean_absolute_error(y_data, y_pred)
            r2 = r2_score(y_data, y_pred)

            metrics[f"{name}_mse"] = float(mse)
            metrics[f"{name}_mae"] = float(mae)
            metrics[f"{name}_r2"] = float(r2)

        return metrics

    def _save_model(self, run_id: str) -> None:
        """Save model and feature columns"""
        path = self.config.get("model_path", f"models/{run_id}")
        Path(path).mkdir(parents=True, exist_ok=True)

        # Save model
        with open(f"{path}/model.pkl", "wb") as f:
            pickle.dump(self.model, f)

        # Save feature columns
        with open(f"{path}/features.json", "w") as f:
            json.dump(self.feature_columns, f)

        # Save label encoders
        with open(f"{path}/encoders.pkl", "wb") as f:
            pickle.dump(self.label_encoders, f)

        logger.info(f"Model saved to {path}")

    def _has_gpu(self) -> bool:
        """Check if GPU is available"""
        return torch is not None and torch.cuda.is_available()

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        """Make predictions with trained model"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Prepare features using existing encoders
        x_prepared = self._prepare_features(x, fit=False)

        # Ensure we have all required columns
        if self.feature_columns is not None:
            for col in self.feature_columns:
                if col not in x_prepared.columns:
                    x_prepared[col] = 0
            x_prepared = x_prepared[self.feature_columns]

        result: np.ndarray = self.model.predict(x_prepared)
        return result

    def load_model(self, path: str) -> None:
        """Load a saved model"""
        try:
            with open(f"{path}/model.pkl", "rb") as f:
                self.model = pickle.load(f)

            with open(f"{path}/features.json") as f:
                self.feature_columns = json.load(f)

            # Load label encoders if they exist
            encoders_path = f"{path}/encoders.pkl"
            if Path(encoders_path).exists():
                with open(encoders_path, "rb") as f:
                    self.label_encoders = pickle.load(f)

            logger.info(f"Model loaded from {path}")
        except FileNotFoundError as e:
            logger.error(f"Model not found at {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance from trained model"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        if self.feature_columns is None:
            raise ValueError("Feature columns not set. Train the model first.")

        if hasattr(self.model, "feature_importances_"):
            importance = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            importance = np.abs(self.model.coef_)
        else:
            raise ValueError(f"Model {self.model_type} does not support feature importance")

        # Ensure we have the right number of features
        if len(importance) != len(self.feature_columns):
            # Truncate or pad as needed
            if len(importance) < len(self.feature_columns):
                # Pad with zeros
                importance = list(importance) + [0] * (len(self.feature_columns) - len(importance))
            else:
                # Truncate
                importance = importance[: len(self.feature_columns)]

        return dict(zip(self.feature_columns, importance, strict=False))
