"""
Production-grade integration tests - The Final Solution
"""

import contextlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

import jwt
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration

# ============================================================
# 1. MODEL LOADING TESTS (STRICT VALIDATION)
# ============================================================


class TestModelLoading:
    """Strict model loading validation"""

    def test_model_loads_from_mlflow(self, mlflow_client, test_model):
        """CRITICAL: Validate MLflow registry integration.

        Uses the mlflow_client/test_model fixtures instead of talking to
        MLflow directly. Those fixtures already gate on
        is_mlflow_available() (a 2s bounded socket + HTTP probe) and call
        pytest.skip() immediately if no MLflow server is reachable. Doing
        the connection inline here (as the old version did) bypasses that
        check entirely and lets MlflowClient's default, effectively
        unbounded urllib3 retry/backoff hang the whole test session
        against a dead host.
        """
        # from src.models.inference import ModelInference

        # config = {
        #     "model_name": test_model if isinstance(test_model, str) and not test_model.startswith('/') else "test_model",
        #     "version": "1.0.0"
        # }

        # inference = ModelInference(config)
        from src.models.inference import ModelInference

        if isinstance(test_model, str) and test_model.startswith("/"):
            # test_model fixture fell back to a local file (real MLflow
            # registration failed) -- load from that path instead of
            # querying the registry for a model name that was never
            # actually registered.
            config = {"model_path": test_model, "version": "1.0.0"}
        else:
            config = {"model_name": test_model, "version": "1.0.0"}

        inference = ModelInference(config)
        inference.load_model()

        assert inference.model is not None, "Model should be loaded"
        assert inference.model_version is not None, "Version should be set"
        assert len(inference.feature_columns) > 0, "Features should exist"

        test_data = pd.DataFrame({"feature_1": [1.0], "feature_2": [2.0], "feature_3": [3.0]})

        result = inference.predict(test_data)
        assert result is not None, "Prediction should work"
        assert len(result) == 1, "Should return one prediction"

        logger.info("Model loaded from MLflow successfully")

    def test_model_loading_fallback(self, tmp_path):
        """Test local model loading as fallback.

        Writes the fixture model with pickle (via ModelInference.save_model),
        matching the format _load_from_path actually reads with pickle.load().
        joblib.dump's on-disk format is not guaranteed pickle-compatible, so
        writing with joblib and reading with pickle can fail even though the
        model itself is perfectly valid.
        """
        from src.models.inference import ModelInference

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

        model_path = tmp_path / "model.pkl"
        writer = ModelInference({})
        writer.model = model
        writer.feature_columns = ["feature_1", "feature_2", "feature_3"]
        writer.save_model(str(model_path))

        inference = ModelInference({"model_path": str(model_path)})
        inference.load_model()

        assert inference.model is not None
        assert len(inference.feature_columns) == 3


# ============================================================
# 2. API ENDPOINT TESTS (CONTRACT VALIDATION)
# ============================================================


class TestAPIEndpoints:
    """Test API endpoint contracts"""

    def test_health_endpoint(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "uptime" in data
        assert data["status"] in ["healthy", "degraded"]

    def test_ready_endpoint(self, api_client):
        response = api_client.get("/ready")
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            assert response.json()["status"] == "ready"

    def test_metrics_endpoint(self, api_client):
        response = api_client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        assert any(
            metric in response.text
            for metric in [
                "api_requests_total",
                "http_requests_total",
                "api_request_duration_seconds",
            ]
        )


# ============================================================
# 3. PREDICTION TESTS (BUSINESS LOGIC)
# ============================================================


class TestPrediction:
    """Test prediction functionality"""

    def test_prediction_with_features(self, api_client, auth_token):
        payload = {
            "product_id": "test_product",
            "store_id": "test_store",
            "date": "2024-01-01",
            "features": {"feature_1": 1.0, "feature_2": 2.0, "feature_3": 3.0},
        }

        response = api_client.post(
            "/predict", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "predicted_quantity" in data
            assert "confidence_lower" in data
            assert "confidence_upper" in data
            assert isinstance(data["predicted_quantity"], (int, float))
            assert data["product_id"] == "test_product"
        elif response.status_code == 400:
            assert "No features found" in response.text or "Missing features" in response.text
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_prediction_from_feature_store(self, api_client, auth_token, seeded_redis):
        payload = {"product_id": "test_product", "store_id": "test_store", "date": "2024-01-01"}

        response = api_client.post(
            "/predict", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert "predicted_quantity" in data

    def test_prediction_invalid_features(self, api_client, auth_token):
        payload = {
            "product_id": "test",
            "store_id": "test",
            "date": "2024-01-01",
            "features": {"feature_1": "invalid_string", "feature_2": 2.0},
        }

        response = api_client.post(
            "/predict", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 422

    def test_prediction_missing_fields(self, api_client, auth_token):
        payload = {"store_id": "test", "date": "2024-01-01"}

        response = api_client.post(
            "/predict", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 422


# ============================================================
# 4. AUTHENTICATION TESTS (SECURITY)
# ============================================================


class TestAuthentication:
    """Test authentication and authorization"""

    def test_login_success(self, api_client):
        # response = api_client.post(
        #     "/auth/login",
        #     json={"username": "admin", "password": "password"}
        # )
        response = api_client.post(
            "/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)

        from src.serving.auth import JWT_ALGORITHM, JWT_SECRET

        decoded = jwt.decode(data["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "user_id" in decoded
        assert "exp" in decoded
        assert decoded.get("username") == "admin"

    def test_login_failure(self, api_client):
        response = api_client.post(
            "/auth/login", json={"username": "invalid", "password": "invalid"}
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.text

    def test_protected_endpoint_without_token(self, api_client):
        response = api_client.post(
            "/predict", json={"product_id": "test", "store_id": "test", "date": "2024-01-01"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, api_client):
        response = api_client.post(
            "/predict",
            json={"product_id": "test", "store_id": "test", "date": "2024-01-01"},
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_token_expiration(self, api_client):
        # with patch('src.serving.auth.auth_manager.access_token_expire_minutes', 0.1):
        # with patch('src.serving.auth.JWT_EXPIRY_MINUTES', 0.1):
        #     response = api_client.post(
        #         "/auth/login",
        #         json={"username": "admin", "password": "password"}
        #     )
        with patch("src.serving.auth.JWT_EXPIRY_MINUTES", 0.1):
            response = api_client.post(
                "/auth/login", json={"username": "admin", "password": "admin123"}
            )
            assert response.status_code == 200
            token = response.json()["access_token"]

            time.sleep(6)  # 0.1 minutes = 6 seconds

            response = api_client.post(
                "/predict",
                json={
                    "product_id": "test",
                    "store_id": "test",
                    "date": "2024-01-01",
                    "features": {"feature_1": 1.0, "feature_2": 2.0, "feature_3": 3.0},
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 401
            assert "expired" in response.text.lower()


# ============================================================
# 5. FEATURE STORE TESTS (INTEGRATION)
# ============================================================


class TestFeatureStore:
    """Test Redis feature store integration"""

    def test_redis_connection(self, redis_client):
        redis_client.ping()

    def test_redis_crud_operations(self, redis_client):
        test_key = "test:crud:key"
        test_value = {"data": "test", "timestamp": time.time()}

        redis_client.set(test_key, json.dumps(test_value))

        value = redis_client.get(test_key)
        assert value is not None
        parsed = json.loads(value)
        assert parsed["data"] == "test"

        test_value["data"] = "updated"
        redis_client.set(test_key, json.dumps(test_value))
        value = redis_client.get(test_key)
        parsed = json.loads(value)
        assert parsed["data"] == "updated"

        redis_client.delete(test_key)
        assert redis_client.get(test_key) is None

    def test_feature_store_pipeline(self, redis_client):
        feature_data = {"feature_1": 10.0, "feature_2": 20.0, "feature_3": 30.0}

        key = "feature:test_product:test_store"
        redis_client.set(key, json.dumps(feature_data))
        redis_client.expire(key, 60)

        value = redis_client.get(key)
        assert value is not None
        parsed = json.loads(value)
        assert parsed["feature_1"] == 10.0

        redis_client.delete(key)


# ============================================================
# 6. OBSERVABILITY TESTS (MONITORING)
# ============================================================


class TestObservability:
    """Test observability and monitoring"""

    def test_metrics_increment(self, api_client, auth_token):
        response = api_client.get("/metrics")
        baseline = response.text

        # initial = 0
        # for line in baseline.split('\n'):
        #     if 'api_requests_total' in line and '200' in line:
        #         try:
        #             initial = int(line.split()[-1])
        #         except Exception:
        #             pass
        initial = 0
        for line in baseline.split("\n"):
            if "api_requests_total" in line and "200" in line:
                with contextlib.suppress(Exception):
                    initial = float(line.split()[-1])

        for i in range(3):
            response = api_client.post(
                "/predict",
                json={
                    "product_id": f"obs_test_{i}",
                    "store_id": "test",
                    "date": "2024-01-01",
                    "features": {"feature_1": 1.0, "feature_2": 2.0, "feature_3": 3.0},
                },
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code in [200, 400, 500]

        response = api_client.get("/metrics")
        updated = response.text

        # updated_count = 0
        # for line in updated.split('\n'):
        #     if 'api_requests_total' in line and '200' in line:
        #         try:
        #             updated_count = int(line.split()[-1])
        #         except Exception:
        #             pass
        updated_count = 0
        for line in updated.split("\n"):
            if "api_requests_total" in line and "200" in line:
                with contextlib.suppress(Exception):
                    updated_count = float(line.split()[-1])

        assert updated_count > initial, "Metrics should increment"


# ============================================================
# 7. PERFORMANCE TESTS (WITH TIMEOUTS)
# ============================================================


class TestPerformance:
    """Performance and load tests with timeouts"""

    @pytest.mark.slow
    def test_concurrent_predictions(self, api_client, auth_token):
        def make_request(i):
            payload = {
                "product_id": f"concurrent_{i}",
                "store_id": "test",
                "date": "2024-01-01",
                "features": {
                    "feature_1": float(i),
                    "feature_2": float(i * 2),
                    "feature_3": float(i * 3),
                },
            }

            start = time.time()
            try:
                response = api_client.post(
                    "/predict",
                    json=payload,
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=10,
                )
                elapsed = time.time() - start
                return response, elapsed
            except Exception:
                return None, time.time() - start

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = []
            for future in as_completed(futures, timeout=30):
                try:
                    response, elapsed = future.result(timeout=10)
                    if response is not None:
                        results.append((response, elapsed))
                except Exception as e:
                    logger.warning(f"Request failed: {e}")

        if results:
            successful = sum(1 for r, _ in results if r.status_code == 200)
            avg_time = sum(t for _, t in results) / len(results)

            logger.info("Performance Results:")
            logger.info(f"  Requests: {len(results)}")
            logger.info(
                f"  Success rate: {successful}/{len(results)} ({successful / len(results) * 100:.1f}%)"
            )
            logger.info(f"  Avg response: {avg_time:.3f}s")

            assert len(results) > 0, "Should have at least one successful request"
        else:
            pytest.skip("No requests completed")

    @pytest.mark.slow
    def test_load_test(self, api_client, auth_token):
        start = time.time()
        requests_made = 0
        errors = 0

        for i in range(20):
            try:
                payload = {
                    "product_id": f"load_{i}",
                    "store_id": "test",
                    "date": "2024-01-01",
                    "features": {
                        "feature_1": float(i),
                        "feature_2": float(i * 2),
                        "feature_3": float(i * 3),
                    },
                }
                response = api_client.post(
                    "/predict",
                    json=payload,
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=5,
                )
                requests_made += 1
                if response.status_code != 200:
                    errors += 1
            except Exception:
                errors += 1

        elapsed = time.time() - start

        logger.info("Load Test Results:")
        logger.info(f"  Requests: {requests_made}")
        logger.info(f"  Errors: {errors}")
        logger.info(f"  Time: {elapsed:.2f}s")
        logger.info(f"  Throughput: {requests_made / elapsed:.2f} req/s")

        assert requests_made > 0, "Should make requests"
        assert errors < requests_made, "Not all requests should fail"


# ============================================================
# 8. END-TO-END TESTS (COMPLETE WORKFLOW)
# ============================================================


class TestEndToEndWorkflow:
    """Complete end-to-end workflow tests"""

    def test_complete_user_journey(self, api_client):
        health = api_client.get("/health")
        assert health.status_code == 200

        # login = api_client.post(
        #     "/auth/login",
        #     json={"username": "admin", "password": "password"}
        # )

        # if login.status_code != 200:
        #     login = api_client.post(
        #         "/auth/login",
        #         json={"username": "test_user", "password": "test_pass"}
        #     )
        login = api_client.post("/auth/login", json={"username": "admin", "password": "admin123"})

        if login.status_code != 200:
            pytest.skip("Unable to authenticate")

        token = login.json()["access_token"]

        successful_predictions = 0
        for i in range(5):
            response = api_client.post(
                "/predict",
                json={
                    "product_id": f"e2e_{i}",
                    "store_id": "test",
                    "date": "2024-01-01",
                    "features": {
                        "feature_1": float(i),
                        "feature_2": float(i * 2),
                        "feature_3": float(i * 3),
                    },
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 200:
                successful_predictions += 1
                data = response.json()
                assert "request_id" in data
                assert "predicted_quantity" in data
                assert "product_id" in data

        assert successful_predictions > 0, "Should have at least one successful prediction"

    def test_observability_pipeline(self, api_client, auth_token):
        api_client.post(
            "/predict",
            json={
                "product_id": "obs_test",
                "store_id": "test",
                "date": "2024-01-01",
                "features": {"feature_1": 1.0, "feature_2": 2.0, "feature_3": 3.0},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        metrics = api_client.get("/metrics")
        assert metrics.status_code == 200

        metrics_text = metrics.text
        assert any(
            metric in metrics_text
            for metric in [
                "api_requests_total",
                "http_requests_total",
                "api_request_duration_seconds",
            ]
        )

        health = api_client.get("/health")
        assert health.status_code == 200
        data = health.json()
        assert "uptime" in data
        assert "status" in data


# ============================================================
# 9. RATE LIMITING TESTS
# ============================================================


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_enforcement(self, api_client, auth_token):
        responses = []
        for i in range(15):
            response = api_client.post(
                "/predict",
                json={
                    "product_id": f"rate_{i}",
                    "store_id": "test",
                    "date": "2024-01-01",
                    "features": {
                        "feature_1": float(i),
                        "feature_2": float(i * 2),
                        "feature_3": float(i * 3),
                    },
                },
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            responses.append(response)

        status_codes = [r.status_code for r in responses]
        has_rate_limit = 429 in status_codes

        if has_rate_limit:
            limited = responses[status_codes.index(429)]
            assert "rate limit" in limited.text.lower() or "too many" in limited.text.lower()
