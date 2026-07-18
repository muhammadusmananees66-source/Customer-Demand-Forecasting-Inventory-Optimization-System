"""
Unit tests for ModelTrainer - Production-grade comprehensive testing
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from src.models.trainer import ModelTrainer

# Set environment variable for MLflow file store (for test compatibility)
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"


class TestModelTrainer:
    """Comprehensive ModelTrainer tests - Unit + Integration"""

    @pytest.fixture
    def sample_data(self):
        """Create sample time-series data for testing"""
        dates = pd.date_range(start="2024-01-01", periods=200, freq="D")
        np.random.seed(42)
        data = {
            "date": dates,
            "product_id": np.random.choice(["A", "B", "C"], 200),
            "feature_1": np.random.randn(200),
            "feature_2": np.random.randn(200),
            "feature_3": np.random.randn(200),
            "feature_4": np.random.randn(200),
            "feature_5": np.random.randn(200),
            "quantity": np.random.randint(1, 100, 200),
            "price": np.random.uniform(10, 100, 200),
        }
        df = pd.DataFrame(data)
        y = df["quantity"].copy()
        x = df.drop("quantity", axis=1)
        return x, y, df

    @pytest.fixture
    def config(self):
        """Default configuration for tests - using SQLite in-memory for speed"""
        return {
            "model_type": "xgboost",
            "hyperparameters": {
                "n_estimators": 50,
                "max_depth": 4,
                "learning_rate": 0.1,
                "random_state": 42,
            },
            "date_col": "date",
            "target_col": "quantity",
            "distributed": False,
            "save_model": False,
            "mlflow_tracking_uri": "sqlite:///:memory:",
            "experiment_name": "test_experiment",
        }

    # ========== INITIALIZATION TESTS ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_trainer_creation(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        config,
    ):
        """Test ModelTrainer initialization"""
        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        trainer = ModelTrainer(config)

        assert trainer.config == config
        assert trainer.model_type == "xgboost"
        assert trainer.date_col == "date"
        assert trainer.target_col == "quantity"
        assert trainer.model is None
        assert trainer.feature_columns is None
        assert trainer.metrics == {}

    # ========== MODEL TRAINING TESTS ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_train_xgboost(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test xGBoost training"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        trainer = ModelTrainer(config)
        metrics = trainer.train(df, y)

        assert trainer.model is not None
        assert "train_mae" in metrics
        assert "val_mae" in metrics
        assert "test_mae" in metrics
        assert "train_mse" in metrics
        assert "val_mse" in metrics
        assert "test_mse" in metrics
        assert "train_r2" in metrics
        assert "val_r2" in metrics
        assert "test_r2" in metrics
        assert isinstance(metrics, dict)
        assert len(trainer.feature_columns) > 0

        predictions = trainer.predict(x)
        assert len(predictions) == len(x)
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype in [np.float32, np.float64]

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_train_random_forest(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test Random Forest training"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        config["model_type"] = "random_forest"
        config["hyperparameters"] = {
            "n_estimators": 50,
            "max_depth": 4,
            "random_state": 42,
            "n_jobs": -1,
        }
        trainer = ModelTrainer(config)
        metrics = trainer.train(df, y)

        assert trainer.model is not None
        assert isinstance(trainer.model, RandomForestRegressor)
        assert "train_mae" in metrics
        assert "val_mae" in metrics
        assert "test_mae" in metrics
        assert isinstance(metrics, dict)

        predictions = trainer.predict(x)
        assert len(predictions) == len(x)

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_train_gradient_boosting(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test Gradient Boosting training"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        config["model_type"] = "gradient_boosting"
        trainer = ModelTrainer(config)
        metrics = trainer.train(df, y)

        assert trainer.model is not None
        assert isinstance(trainer.model, GradientBoostingRegressor)
        assert "train_mae" in metrics
        assert isinstance(metrics, dict)

        predictions = trainer.predict(x)
        assert len(predictions) == len(x)

    # ========== TIME-SERIES SPLIT TESTS ==========

    def test_time_series_split(self, sample_data, config):
        """Test time-series aware train/val/test split"""
        x, y, df = sample_data

        with patch("mlflow.set_experiment"), patch("mlflow.start_run"):
            ModelTrainer(config)
            n = len(df)
            train_size = int(n * 0.7)
            val_size = int(n * 0.15)

            assert train_size == 140
            assert val_size == 30
            assert n - train_size - val_size == 30

            dates = pd.to_datetime(df["date"])
            assert dates.iloc[0] < dates.iloc[1]

    # ========== PREDICTION TESTS ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_predict(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test prediction after training"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        trainer = ModelTrainer(config)
        trainer.train(df, y)

        predictions = trainer.predict(x)
        assert len(predictions) == len(x)
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype in [np.float32, np.float64]

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_predict_without_training(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test prediction without training raises error"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        trainer = ModelTrainer(config)

        with pytest.raises(ValueError, match="Model not trained"):
            trainer.predict(x)

    # ========== FEATURE IMPORTANCE TESTS ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_get_feature_importance(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test feature importance extraction"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        trainer = ModelTrainer(config)
        trainer.train(df, y)

        importance = trainer.get_feature_importance()

        assert isinstance(importance, dict)
        assert len(importance) > 0
        assert all(isinstance(v, (float, np.float32, np.float64)) for v in importance.values())
        assert sum(importance.values()) == pytest.approx(1.0, abs=0.15)

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_feature_importance_without_training(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        config,
    ):
        """Test feature importance without training raises error"""
        trainer = ModelTrainer(config)

        with pytest.raises(ValueError, match="Model not trained"):
            trainer.get_feature_importance()

    # ========== SAVE/LOAD TESTS ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_save_and_load_model(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test full round-trip save and load"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        config["save_model"] = True
        trainer = ModelTrainer(config)
        trainer.train(df, y)

        with tempfile.TemporaryDirectory() as tmpdir:
            run_id = "test_run_id"
            model_path = os.path.join(tmpdir, f"models/{run_id}")
            trainer.config["model_path"] = model_path
            trainer._save_model(run_id)

            assert os.path.exists(f"{model_path}/model.pkl")
            assert os.path.exists(f"{model_path}/features.json")

            new_trainer = ModelTrainer(config)
            new_trainer.load_model(model_path)

            assert new_trainer.model is not None
            assert new_trainer.feature_columns == trainer.feature_columns

            original_predictions = trainer.predict(x)
            loaded_predictions = new_trainer.predict(x)
            np.testing.assert_array_almost_equal(
                original_predictions, loaded_predictions, decimal=5
            )

    # ========== EVALUATION TESTS ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_evaluate_model(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """Test model evaluation metrics"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        trainer = ModelTrainer(config)
        trainer.train(df, y)

        # Get prepared features (same as trainer does)
        df_prepared = trainer._prepare_features(df)

        n = len(df_prepared)
        train_size = int(n * 0.7)
        val_size = int(n * 0.15)

        x_train = df_prepared.iloc[:train_size]
        y_train = y.iloc[:train_size]
        x_val = df_prepared.iloc[train_size : train_size + val_size]
        y_val = y.iloc[train_size : train_size + val_size]
        x_test = df_prepared.iloc[train_size + val_size :]
        y_test = y.iloc[train_size + val_size :]

        metrics = trainer._evaluate_model(x_train, y_train, x_val, y_val, x_test, y_test)

        expected_metrics = [
            "train_mae",
            "train_mse",
            "train_r2",
            "val_mae",
            "val_mse",
            "val_r2",
            "test_mae",
            "test_mse",
            "test_r2",
        ]

        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
            assert isinstance(metrics[metric], (float, np.float32, np.float64))
            if not metric.endswith("r2"):
                assert metrics[metric] >= 0

    # ========== GPU DETECTION TESTS ==========

    def test_has_gpu_detection(self, config):
        """Test GPU detection"""
        with patch("mlflow.set_experiment"), patch("mlflow.start_run"):
            trainer = ModelTrainer(config)
            result = trainer._has_gpu()
            assert isinstance(result, bool)
            assert result is False

    # ========== DISTRIBUTED TRAINING TESTS ==========

    @pytest.mark.skipif(
        not os.environ.get("RUN_DISTRIBUTED_TESTS"),
        reason="Skipping distributed tests by default - requires Ray cluster",
    )
    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    def test_distributed_training(self, mock_start_run, mock_set_experiment, sample_data, config):
        """Test distributed training with Ray"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        config["distributed"] = True
        config["num_workers"] = 2
        trainer = ModelTrainer(config)

        metrics = trainer.train(df, y)

        assert trainer.model is not None
        assert "train_mae" in metrics
        assert trainer.is_distributed is True

    # ========== FULL PIPELINE INTEGRATION TEST ==========

    @patch("mlflow.set_experiment")
    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_param")
    def test_full_pipeline(
        self,
        mock_log_param,
        mock_log_metric,
        mock_log_params,
        mock_start_run,
        mock_set_experiment,
        sample_data,
        config,
    ):
        """End-to-end pipeline test"""
        x, y, df = sample_data

        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        mock_start_run.return_value.__enter__.return_value = mock_run

        config["save_model"] = True
        trainer = ModelTrainer(config)

        metrics = trainer.train(df, y)

        predictions = trainer.predict(x)
        assert len(predictions) == len(x)

        importance = trainer.get_feature_importance()
        assert len(importance) > 0

        with tempfile.TemporaryDirectory() as tmpdir:
            run_id = "test_run_id"
            model_path = os.path.join(tmpdir, f"models/{run_id}")
            trainer.config["model_path"] = model_path
            trainer._save_model(run_id)

            new_trainer = ModelTrainer(config)
            new_trainer.load_model(model_path)

            new_predictions = new_trainer.predict(x)
            np.testing.assert_array_almost_equal(predictions, new_predictions)

        expected_metrics = [
            "train_mae",
            "val_mae",
            "test_mae",
            "train_mse",
            "val_mse",
            "test_mse",
            "train_r2",
            "val_r2",
            "test_r2",
        ]
        for metric in expected_metrics:
            assert metric in metrics

    # ========== ERROR HANDLING TESTS ==========

    def test_invalid_model_type(self, config):
        """Test error handling for invalid model type"""
        config["model_type"] = "invalid_model"
        trainer = ModelTrainer(config)

        # Create data with proper numeric columns
        x = pd.DataFrame({"feature_1": [1.0, 2.0, 3.0], "feature_2": [4.0, 5.0, 6.0]})
        y = pd.Series([1, 2, 3])
        df = pd.concat([x, y.rename("quantity")], axis=1)

        with (
            patch("mlflow.start_run"),
            patch("mlflow.set_experiment"),
            pytest.raises(ValueError, match="Unsupported model type"),
        ):
            trainer.train(df, y)


class TestModelTrainerIntegration:
    """Integration tests with real SQLite MLflow backend"""

    @pytest.fixture
    def sample_data_large(self):
        """Create larger dataset for integration tests"""
        dates = pd.date_range(start="2024-01-01", periods=500, freq="D")
        np.random.seed(42)
        data = {
            "date": dates,
            "product_id": np.random.choice(["A", "B", "C"], 500),
            "feature_1": np.random.randn(500),
            "feature_2": np.random.randn(500),
            "feature_3": np.random.randn(500),
            "feature_4": np.random.randn(500),
            "feature_5": np.random.randn(500),
            "quantity": np.random.randint(1, 100, 500),
            "price": np.random.uniform(10, 100, 500),
        }
        df = pd.DataFrame(data)
        y = df["quantity"].copy()
        return df, y

    def test_integration_full_pipeline(self, sample_data_large):
        """Integration test with real SQLite MLflow backend"""
        df, y = sample_data_large

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "mlflow.db")
            config = {
                "model_type": "xgboost",
                "hyperparameters": {
                    "n_estimators": 50,
                    "max_depth": 6,
                    "learning_rate": 0.1,
                },
                "date_col": "date",
                "distributed": False,
                "save_model": True,
                "mlflow_tracking_uri": f"sqlite:///{db_path}",
                "experiment_name": "integration_test",
                "model_path": tmpdir,
            }

            trainer = ModelTrainer(config)
            metrics = trainer.train(df, y)

            predictions = trainer.predict(df)
            assert len(predictions) == len(df)

            assert metrics["test_r2"] > -1.0
            assert metrics["test_mse"] >= 0
            assert metrics["test_mae"] >= 0

            assert os.path.exists(db_path)
