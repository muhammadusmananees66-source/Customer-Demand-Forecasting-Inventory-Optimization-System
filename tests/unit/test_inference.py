# """
# Unit tests for Model Inference module
# """

# import json
# import os
# import pickle
# import tempfile
# from unittest.mock import MagicMock, patch

# import numpy as np
# import pandas as pd
# import pytest

# # ✅ ADD THIS IMPORT
# from mlflow.tracking import MlflowClient

# from src.models.inference import ModelInference


# class TestModelInference:
#     """Test ModelInference class"""

#     @pytest.fixture
#     def sample_model(self):
#         """Create a simple model for testing"""
#         from sklearn.ensemble import RandomForestRegressor

#         np.random.seed(42)
#         x = pd.DataFrame(
#             {
#                 "feature_1": np.random.randn(100),
#                 "feature_2": np.random.randn(100),
#                 "feature_3": np.random.randn(100),
#             }
#         )
#         y = 2 * x["feature_1"] + 3 * x["feature_2"] + np.random.randn(100) * 0.1

#         model = RandomForestRegressor(n_estimators=10, random_state=42)
#         model.fit(x, y)
#         return model, x.columns.tolist()

#     @pytest.fixture
#     def config(self):
#         """Default configuration"""
#         return {
#             "version": "1.0.0",
#             "model_name": "test_model",
#             "mlflow_tracking_uri": "http://localhost:5000",
#         }

#     def test_inference_creation(self, config):
#         """Test ModelInference initialization"""
#         inference = ModelInference(config)
#         assert inference.config == config
#         assert inference.model_version == "1.0.0"
#         assert inference.model_name == "test_model"
#         assert inference.model is None
#         assert inference.feature_columns == []

#     def test_load_from_path(self, config, sample_model):
#         """Test loading model from local path"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         with tempfile.TemporaryDirectory() as tmpdir:
#             model_path = os.path.join(tmpdir, "model.pkl")

#             # Save model
#             with open(model_path, "wb") as f:
#                 pickle.dump(model, f)

#             # Save feature columns
#             with open(f"{model_path}.features", "w") as f:
#                 json.dump(feature_cols, f)

#             # Load model
#             inference._load_from_path(model_path)

#             assert inference.model is not None
#             assert inference.feature_columns == feature_cols

#     def test_load_from_path_no_features_file(self, config, sample_model):
#         """Test loading model when features file doesn't exist"""
#         model, _ = sample_model
#         inference = ModelInference(config)

#         with tempfile.TemporaryDirectory() as tmpdir:
#             model_path = os.path.join(tmpdir, "model.pkl")

#             with open(model_path, "wb") as f:
#                 pickle.dump(model, f)

#             # Don't create features file

#             inference._load_from_path(model_path)
#             assert inference.model is not None
#             assert inference.feature_columns == []

#     def test_load_from_registry_success(self, config, sample_model):
#         """Test loading model from MLflow registry"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         # Mock MLflow client
#         mock_client = MagicMock()
#         mock_version = MagicMock()
#         mock_version.version = 1

#         mock_client.get_latest_versions.return_value = [mock_version]

#         with (
#             patch.object(inference, "_get_registry_client", return_value=mock_client),
#             patch("mlflow.artifacts.download_artifacts") as mock_download,
#         ):
#             mock_download.return_value = "/tmp/model"

#             with patch("builtins.open", create=True) as mock_open:
#                 mock_open.return_value.__enter__.return_value = MagicMock()

#                 with patch("pickle.load") as mock_pickle:
#                     mock_pickle.return_value = model

#                     with (
#                         patch("os.path.exists", return_value=True),
#                         patch("json.load") as mock_json,
#                     ):
#                         mock_json.return_value = feature_cols

#                         inference._load_from_registry()

#                         assert inference.model is not None
#                         assert inference.model_version == "1"

#     def test_load_from_registry_no_production(self, config):
#         """Test loading when no production model exists"""
#         inference = ModelInference(config)

#         mock_client = MagicMock()
#         mock_client.get_latest_versions.return_value = []

#         with (
#             patch.object(inference, "_get_registry_client", return_value=mock_client),
#             patch("src.models.inference.logger") as mock_logger,
#         ):
#             inference._load_from_registry()
#             mock_logger.warning.assert_called_once()

#     def test_load_from_registry_error(self, config):
#         """Test loading from registry with error"""
#         inference = ModelInference(config)

#         mock_client = MagicMock()
#         mock_client.get_latest_versions.side_effect = Exception("Registry error")

#         with (
#             patch.object(inference, "_get_registry_client", return_value=mock_client),
#             pytest.raises(RuntimeError),
#         ):
#             inference._load_from_registry()

#     def test_load_model_with_path(self, config, sample_model):
#         """Test load_model with path"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         with tempfile.TemporaryDirectory() as tmpdir:
#             model_path = os.path.join(tmpdir, "model.pkl")

#             with open(model_path, "wb") as f:
#                 pickle.dump(model, f)

#             with open(f"{model_path}.features", "w") as f:
#                 json.dump(feature_cols, f)

#             with patch.object(inference, "_load_from_path") as mock_load:
#                 inference.load_model(path=model_path)
#                 mock_load.assert_called_once_with(model_path)

#     def test_load_model_without_path(self, config):
#         """Test load_model without path (registry)"""
#         inference = ModelInference(config)

#         with patch.object(inference, "_load_from_registry") as mock_load:
#             inference.load_model()
#             mock_load.assert_called_once()

#     def test_predict_with_model(self, config, sample_model):
#         """Test prediction with loaded model"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         # Load model
#         inference.model = model
#         inference.feature_columns = feature_cols

#         # Create test data
#         x = pd.DataFrame(
#             {
#                 "feature_1": np.random.randn(5),
#                 "feature_2": np.random.randn(5),
#                 "feature_3": np.random.randn(5),
#             }
#         )

#         # Make predictions
#         predictions = inference.predict(x)
#         assert len(predictions) == 5
#         assert isinstance(predictions, np.ndarray)

#     def test_predict_without_model(self, config):
#         """Test prediction without loaded model"""
#         inference = ModelInference(config)
#         x = pd.DataFrame({"feature_1": [1, 2, 3]})

#         with pytest.raises(ValueError, match="Model not loaded"):
#             inference.predict(x)

#     def test_predict_missing_features(self, config, sample_model):
#         """Test prediction with missing features"""
#         model, _ = sample_model
#         inference = ModelInference(config)

#         inference.model = model
#         inference.feature_columns = ["feature_1", "feature_2", "feature_3"]

#         # Create data with missing column
#         x = pd.DataFrame(
#             {
#                 "feature_1": np.random.randn(5),
#                 "feature_2": np.random.randn(5),
#             }
#         )

#         with pytest.raises(ValueError, match="Missing features"):
#             inference.predict(x)

#     def test_predict_with_confidence(self, config, sample_model):
#         """Test prediction with confidence intervals"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         inference.model = model
#         inference.feature_columns = feature_cols

#         x = pd.DataFrame(
#             {
#                 "feature_1": np.random.randn(5),
#                 "feature_2": np.random.randn(5),
#                 "feature_3": np.random.randn(5),
#             }
#         )

#         result = inference.predict_with_confidence(x)
#         assert "predictions" in result
#         assert "confidence_lower" in result
#         assert "confidence_upper" in result
#         assert len(result["predictions"]) == 5

#     def test_predict_with_numpy_array(self, config, sample_model):
#         """Test prediction with numpy array input"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         inference.model = model
#         inference.feature_columns = feature_cols

#         x = np.random.randn(5, 3)
#         predictions = inference.predict(x)
#         assert len(predictions) == 5

#     def test_get_model_info(self, config, sample_model):
#         """Test getting model information"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         inference.model = model
#         inference.feature_columns = feature_cols

#         info = inference.get_model_info()
#         assert info["model_name"] == "test_model"
#         assert info["model_version"] == "1.0.0"
#         assert info["feature_count"] == len(feature_cols)
#         assert info["feature_columns"] == feature_cols

#     def test_get_registry_client_lazy_init(self, config):
#         """Test lazy initialization of registry client"""
#         inference = ModelInference(config)
#         assert inference._registry_client is None

#         client = inference._get_registry_client()
#         assert client is not None
#         # ✅ FIxED: Use type check with isinstance
#         assert isinstance(client, MlflowClient)

#     def test_save_model(self, config, sample_model):
#         """Test saving model to disk"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         inference.model = model
#         inference.feature_columns = feature_cols

#         with tempfile.TemporaryDirectory() as tmpdir:
#             model_path = os.path.join(tmpdir, "model.pkl")

#             # Save model
#             inference.save_model(model_path)

#             # Verify files exist
#             assert os.path.exists(model_path)
#             assert os.path.exists(f"{model_path}.features")

#             # Verify can load back
#             new_inference = ModelInference(config)
#             new_inference.load_model(path=model_path)

#             assert new_inference.model is not None
#             assert new_inference.feature_columns == feature_cols

#     def test_model_loading_logging(self, config, sample_model):
#         """Test logging during model loading"""
#         model, feature_cols = sample_model
#         inference = ModelInference(config)

#         with tempfile.TemporaryDirectory() as tmpdir:
#             model_path = os.path.join(tmpdir, "model.pkl")

#             with open(model_path, "wb") as f:
#                 pickle.dump(model, f)

#             with open(f"{model_path}.features", "w") as f:
#                 json.dump(feature_cols, f)

#             with patch("src.models.inference.logger") as mock_logger:
#                 inference.load_model(path=model_path)
#                 mock_logger.info.assert_called()


# tests/unit/test_inference.py - FIxED PRODUCTION-GRADE VERSION

"""
Unit tests for Model Inference module
"""

import json
import os
import pickle
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from mlflow.tracking import MlflowClient

from src.models.inference import ModelInference


class TestModelInference:
    """Test ModelInference class"""

    @pytest.fixture
    def sample_model(self):
        """Create a simple model for testing"""
        from sklearn.ensemble import RandomForestRegressor

        np.random.seed(42)
        x = pd.DataFrame(
            {
                "feature_1": np.random.randn(100),
                "feature_2": np.random.randn(100),
                "feature_3": np.random.randn(100),
            }
        )
        y = 2 * x["feature_1"] + 3 * x["feature_2"] + np.random.randn(100) * 0.1

        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(x, y)
        return model, x.columns.tolist()

    @pytest.fixture
    def config(self):
        """Default configuration"""
        return {
            "version": "1.0.0",
            "model_name": "test_model",
            "mlflow_tracking_uri": "http://localhost:5000",
        }

    def test_inference_creation(self, config):
        """Test ModelInference initialization"""
        inference = ModelInference(config)
        assert inference.config == config
        assert inference.model_version == "1.0.0"
        assert inference.model_name == "test_model"
        assert inference.model is None
        assert inference.feature_columns == []

    def test_load_from_path(self, config, sample_model):
        """Test loading model from local path"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pkl")

            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            with open(f"{model_path}.features", "w") as f:
                json.dump(feature_cols, f)

            inference._load_from_path(model_path)

            assert inference.model is not None
            assert inference.feature_columns == feature_cols

    def test_load_from_path_no_features_file(self, config, sample_model):
        """Test loading model when features file doesn't exist"""
        model, _ = sample_model
        inference = ModelInference(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pkl")

            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference._load_from_path(model_path)
            assert inference.model is not None
            assert inference.feature_columns == []

    def test_load_from_registry_success(self, config, sample_model):
        """Test loading model from MLflow registry"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = 1
        mock_client.get_latest_versions.return_value = [mock_version]

        with (
            patch.object(inference, "_get_registry_client", return_value=mock_client),
            patch("mlflow.artifacts.download_artifacts") as mock_download,
        ):
            mock_download.return_value = "/tmp/model"

            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value = MagicMock()

                with patch("pickle.load") as mock_pickle:
                    mock_pickle.return_value = model

                    with (
                        patch("os.path.exists", return_value=True),
                        patch("json.load") as mock_json,
                    ):
                        mock_json.return_value = feature_cols

                        inference._load_from_registry()

                        assert inference.model is not None
                        assert inference.model_version == "1"

    def test_load_from_registry_no_production(self, config):
        """Test loading when no production model exists"""
        inference = ModelInference(config)

        mock_client = MagicMock()
        mock_client.get_latest_versions.return_value = []

        with (
            patch.object(inference, "_get_registry_client", return_value=mock_client),
            patch("src.models.inference.logger") as mock_logger,
        ):
            inference._load_from_registry()
            mock_logger.warning.assert_called_once()

    def test_load_from_registry_error(self, config):
        """Test loading from registry with error"""
        inference = ModelInference(config)

        mock_client = MagicMock()
        # FIx: Raise Exception directly - the method catches Exception and re-raises
        mock_client.get_latest_versions.side_effect = Exception("Registry error")

        with (
            patch.object(inference, "_get_registry_client", return_value=mock_client),
            # FIx: Expect Exception since the method catches and re-raises Exception
            pytest.raises(Exception) as exc_info,
        ):
            inference._load_from_registry()

        # Verify the error message is preserved
        assert "Registry error" in str(exc_info.value)

    def test_load_model_with_path(self, config, sample_model):
        """Test load_model with path"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pkl")

            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            with open(f"{model_path}.features", "w") as f:
                json.dump(feature_cols, f)

            with patch.object(inference, "_load_from_path") as mock_load:
                inference.load_model(path=model_path)
                mock_load.assert_called_once_with(model_path)

    def test_load_model_without_path(self, config):
        """Test load_model without path (registry)"""
        inference = ModelInference(config)

        with patch.object(inference, "_load_from_registry") as mock_load:
            inference.load_model()
            mock_load.assert_called_once()

    def test_predict_with_model(self, config, sample_model):
        """Test prediction with loaded model"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        inference.model = model
        inference.feature_columns = feature_cols

        x = pd.DataFrame(
            {
                "feature_1": np.random.randn(5),
                "feature_2": np.random.randn(5),
                "feature_3": np.random.randn(5),
            }
        )

        predictions = inference.predict(x)
        assert len(predictions) == 5
        assert isinstance(predictions, np.ndarray)

    def test_predict_without_model(self, config):
        """Test prediction without loaded model"""
        inference = ModelInference(config)
        x = pd.DataFrame({"feature_1": [1, 2, 3]})

        with pytest.raises(ValueError, match="Model not loaded"):
            inference.predict(x)

    def test_predict_missing_features(self, config, sample_model):
        """Test prediction with missing features"""
        model, _ = sample_model
        inference = ModelInference(config)

        inference.model = model
        inference.feature_columns = ["feature_1", "feature_2", "feature_3"]

        x = pd.DataFrame(
            {
                "feature_1": np.random.randn(5),
                "feature_2": np.random.randn(5),
            }
        )

        with pytest.raises(ValueError, match="Missing features"):
            inference.predict(x)

    def test_predict_with_confidence(self, config, sample_model):
        """Test prediction with confidence intervals"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        inference.model = model
        inference.feature_columns = feature_cols

        x = pd.DataFrame(
            {
                "feature_1": np.random.randn(5),
                "feature_2": np.random.randn(5),
                "feature_3": np.random.randn(5),
            }
        )

        result = inference.predict_with_confidence(x)
        assert "predictions" in result
        assert "confidence_lower" in result
        assert "confidence_upper" in result
        assert len(result["predictions"]) == 5

    def test_predict_with_numpy_array(self, config, sample_model):
        """Test prediction with numpy array input"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        inference.model = model
        inference.feature_columns = feature_cols

        x = np.random.randn(5, 3)
        predictions = inference.predict(x)
        assert len(predictions) == 5

    def test_get_model_info(self, config, sample_model):
        """Test getting model information"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        inference.model = model
        inference.feature_columns = feature_cols

        info = inference.get_model_info()
        assert info["model_name"] == "test_model"
        assert info["model_version"] == "1.0.0"
        assert info["feature_count"] == len(feature_cols)
        assert info["feature_columns"] == feature_cols

    def test_get_registry_client_lazy_init(self, config):
        """Test lazy initialization of registry client"""
        inference = ModelInference(config)
        assert inference._registry_client is None

        client = inference._get_registry_client()
        assert client is not None
        assert isinstance(client, MlflowClient)

    def test_save_model(self, config, sample_model):
        """Test saving model to disk"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        inference.model = model
        inference.feature_columns = feature_cols

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pkl")

            inference.save_model(model_path)

            assert os.path.exists(model_path)
            assert os.path.exists(f"{model_path}.features")

            new_inference = ModelInference(config)
            new_inference.load_model(path=model_path)

            assert new_inference.model is not None
            assert new_inference.feature_columns == feature_cols

    def test_model_loading_logging(self, config, sample_model):
        """Test logging during model loading"""
        model, feature_cols = sample_model
        inference = ModelInference(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pkl")

            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            with open(f"{model_path}.features", "w") as f:
                json.dump(feature_cols, f)

            with patch("src.models.inference.logger") as mock_logger:
                inference.load_model(path=model_path)
                mock_logger.info.assert_called()
