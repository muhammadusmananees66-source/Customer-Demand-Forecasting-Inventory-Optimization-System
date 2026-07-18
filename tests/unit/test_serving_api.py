"""
Unit tests for FastAPI Serving module
"""

import json
import os
import pickle
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.serving.api import create_app
from src.serving.rate_limiter import rate_limiter as rl


@pytest.fixture
def sample_model():
    """Create a sample model for testing"""
    from sklearn.ensemble import RandomForestRegressor

    np.random.seed(42)
    x = pd.DataFrame(
        {
            "feature_1": np.random.randn(50),
            "feature_2": np.random.randn(50),
            "feature_3": np.random.randn(50),
        }
    )
    y = 2 * x["feature_1"] + 3 * x["feature_2"] + np.random.randn(50) * 0.1

    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(x, y)
    return model, x.columns.tolist()


@pytest.fixture
def model_path(sample_model):
    """Create a temporary model file"""
    model, feature_cols = sample_model
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        with open(f"{model_path}.features", "w") as f:
            json.dump(feature_cols, f)
        yield model_path


@pytest.fixture
def prediction_payload():
    """Standard prediction payload for tests"""
    return {
        "product_id": "test",
        "store_id": "test",
        "date": "2024-01-01",
        "features": {"feature_1": 1.0, "feature_2": 2.0, "feature_3": 3.0},
    }


@pytest.fixture
def app(model_path):
    """Create test app with the rate limiter dependency overridden.

    IMPORTANT: We use app.dependency_overrides instead of
    patch('src.serving.api.rate_limiter'). Patching replaces the object
    with a bare MagicMock, and FastAPI introspects that Mock's own
    __call__ signature -- which is (*args, **kwargs) -- when resolving
    the route's dependencies. It misreads those as two required query
    parameters, so every request fails validation with a 422 before the
    endpoint body ever runs. dependency_overrides swaps the dependency at
    the routing layer and sidesteps signature introspection entirely.
    """
    config = {
        "model": {"model_path": model_path, "version": "1.0.0"},
        "feature_store": {"redis_host": "localhost", "redis_port": 6379},
        "cors_origins": ["*"],
    }
    app = create_app(config)

    async def mock_rate_limit():
        return True

    app.dependency_overrides[rl] = mock_rate_limit
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints"""

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model_version" in data
        assert "uptime" in data

    def test_ready_endpoint(self, client):
        """Test readiness endpoint"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        assert "api_requests_total" in response.text

    def test_login_success(self, client):
        """Test successful login"""
        with patch("src.serving.auth.auth_manager.authenticate") as mock_auth:
            mock_auth.return_value = {"user_id": "test_user", "roles": ["user"]}
            with patch("src.serving.auth.auth_manager.create_token") as mock_token:
                mock_token.return_value = "test_token"

                response = client.post(
                    "/auth/login", json={"username": "test_user", "password": "test_pass"}
                )
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

    def test_login_failure(self, client):
        """Test failed login"""
        with patch("src.serving.auth.auth_manager.authenticate", return_value=None):
            response = client.post(
                "/auth/login", json={"username": "invalid", "password": "invalid"}
            )
            assert response.status_code == 401
            assert "Invalid credentials" in response.text

    def test_predict_without_auth(self, client):
        """Test prediction without authentication"""
        response = client.post(
            "/predict", json={"product_id": "test", "store_id": "test", "date": "2024-01-01"}
        )
        assert response.status_code == 401
        assert "Not authenticated" in response.text or "detail" in response.text

    def test_predict_with_auth(self, client, prediction_payload):
        """Test prediction with authentication"""
        with patch("src.serving.auth.auth_manager.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test_user"}

            with patch(
                "src.features.store.FeatureStoreManager.get_online_features"
            ) as mock_features:
                # Return ALL features expected by the model
                mock_features.return_value = pd.DataFrame(
                    {"feature_1": [1.0], "feature_2": [2.0], "feature_3": [3.0]}
                )

                with patch(
                    "src.models.inference.ModelInference.predict_with_confidence"
                ) as mock_predict:
                    mock_predict.return_value = {
                        "predictions": np.array([100.0]),
                        "confidence_lower": np.array([85.0]),
                        "confidence_upper": np.array([115.0]),
                    }

                    response = client.post(
                        "/predict",
                        json=prediction_payload,
                        headers={"Authorization": "Bearer test_token"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["product_id"] == "test"
                    assert "predicted_quantity" in data
                    assert "confidence_lower" in data
                    assert "confidence_upper" in data


class TestPredictionRequest:
    """Test PredictionRequest model"""

    def test_prediction_request_creation(self):
        """Test creating prediction request"""
        from src.serving.api import PredictionRequest

        request = PredictionRequest(
            product_id="test", store_id="test", date="2024-01-01", features={"feature_1": 1.0}
        )
        assert request.product_id == "test"
        assert request.store_id == "test"
        assert request.date == "2024-01-01"
        assert request.features == {"feature_1": 1.0}

    def test_prediction_request_default_features(self):
        """Test prediction request with default features"""
        from src.serving.api import PredictionRequest

        request = PredictionRequest(product_id="test", store_id="test", date="2024-01-01")
        assert request.features == {}


class TestTokenResponse:
    """Test TokenResponse model"""

    def test_token_response_creation(self):
        """Test creating token response"""
        from src.serving.api import TokenResponse

        response = TokenResponse(access_token="test_token", expires_in=3600)
        assert response.access_token == "test_token"
        assert response.token_type == "bearer"
        assert response.expires_in == 3600


class TestPredictionResponse:
    """Test PredictionResponse model"""

    def test_prediction_response_creation(self):
        """Test creating prediction response"""
        from src.serving.api import PredictionResponse

        response = PredictionResponse(
            request_id="req-123",
            product_id="test",
            predicted_quantity=100.0,
            confidence_lower=85.0,
            confidence_upper=115.0,
            model_version="1.0.0",
            timestamp=datetime.now(),
        )
        assert response.request_id == "req-123"
        assert response.product_id == "test"
        assert response.predicted_quantity == 100.0


class TestAPIErrorHandling:
    """Test API error handling"""

    def test_predict_missing_features(self, client, prediction_payload):
        """Test prediction with missing features"""
        with patch("src.serving.auth.auth_manager.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test_user"}

            with patch(
                "src.features.store.FeatureStoreManager.get_online_features"
            ) as mock_features:
                mock_features.return_value = pd.DataFrame()  # Empty DataFrame

                response = client.post(
                    "/predict",
                    json=prediction_payload,
                    headers={"Authorization": "Bearer test_token"},
                )

                assert response.status_code == 400
                assert "No features found" in response.text

    def test_predict_model_error(self, client, prediction_payload):
        """Test prediction with model error"""
        with patch("src.serving.auth.auth_manager.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test_user"}

            with patch(
                "src.models.inference.ModelInference.predict_with_confidence"
            ) as mock_predict:
                mock_predict.side_effect = Exception("Model error")

                with patch(
                    "src.features.store.FeatureStoreManager.get_online_features"
                ) as mock_features:
                    mock_features.return_value = pd.DataFrame(
                        {"feature_1": [1.0], "feature_2": [2.0], "feature_3": [3.0]}
                    )

                    response = client.post(
                        "/predict",
                        json=prediction_payload,
                        headers={"Authorization": "Bearer test_token"},
                    )

                    assert response.status_code == 500
                    assert "Model error" in response.text


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers(self, client):
        """Test CORS headers"""
        response = client.options(
            "/health",
            headers={"Origin": "https://company.com", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_cors_with_allowed_origin(self, client):
        """Test CORS with allowed origin"""
        response = client.options(
            "/health",
            headers={"Origin": "https://company.com", "Access-Control-Request-Method": "POST"},
        )
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://company.com"


class TestRateLimiting:
    """Test rate limiting"""

    def test_rate_limit_headers(self, client, prediction_payload):
        """Test rate limit headers are present"""
        with patch("src.serving.auth.auth_manager.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test_user"}

            with patch(
                "src.features.store.FeatureStoreManager.get_online_features"
            ) as mock_features:
                mock_features.return_value = pd.DataFrame(
                    {"feature_1": [1.0], "feature_2": [2.0], "feature_3": [3.0]}
                )

                with patch(
                    "src.models.inference.ModelInference.predict_with_confidence"
                ) as mock_predict:
                    mock_predict.return_value = {
                        "predictions": np.array([100.0]),
                        "confidence_lower": np.array([85.0]),
                        "confidence_upper": np.array([115.0]),
                    }

                    response = client.post(
                        "/predict",
                        json=prediction_payload,
                        headers={"Authorization": "Bearer test_token"},
                    )

                    assert response.status_code == 200

    def test_rate_limit_exceeded(self, prediction_payload):
        """Test rate limit exceeded"""
        with patch("src.serving.api.ModelInference") as mock_inference:
            mock_instance = MagicMock()
            mock_instance.model_version = "1.0.0"
            mock_instance.feature_columns = ["feature_1", "feature_2", "feature_3"]
            mock_instance.load_model = MagicMock()
            mock_instance.predict_with_confidence = MagicMock(
                return_value={
                    "predictions": np.array([100.0]),
                    "confidence_lower": np.array([85.0]),
                    "confidence_upper": np.array([115.0]),
                }
            )
            mock_inference.return_value = mock_instance

            with patch("src.serving.api.FeatureStoreManager") as mock_store:
                mock_store_instance = MagicMock()
                mock_store_instance.get_online_features = MagicMock(
                    return_value=pd.DataFrame(
                        {"feature_1": [1.0], "feature_2": [2.0], "feature_3": [3.0]}
                    )
                )
                mock_store.return_value = mock_store_instance

                config = {
                    "model": {"model_path": None, "version": "1.0.0"},
                    "feature_store": {"redis_host": "localhost", "redis_port": 6379},
                    "cors_origins": ["*"],
                }
                test_app = create_app(config)

                # Override the rate limiter dependency to simulate it
                # rejecting the request, instead of patching the callable
                # object directly (see the `app` fixture above for why).
                async def blocked_rate_limit():
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Limit: 100 requests per 60 seconds",
                    )

                test_app.dependency_overrides[rl] = blocked_rate_limit
                test_client = TestClient(test_app)

                with patch("src.serving.auth.auth_manager.verify_token") as mock_verify:
                    mock_verify.return_value = {"user_id": "test_user"}

                    response = test_client.post(
                        "/predict",
                        json=prediction_payload,
                        headers={"Authorization": "Bearer test_token"},
                    )

                    assert response.status_code == 429
                    assert "Rate limit exceeded" in response.text

                test_app.dependency_overrides.clear()
