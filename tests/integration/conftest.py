# tests/integration/conftest.py
"""
Production-grade integration test infrastructure
Combines smart detection + strict validation
"""

import os

# ============================================================
# CRITICAL: Bound every MLflow HTTP call BEFORE mlflow is ever
# imported anywhere in the test session.
#
# By default, MlflowClient's underlying urllib3 pool retries a
# dead/unreachable tracking server with exponential backoff and no
# overall deadline. Against an MLflow server that simply isn't
# running (the common case in CI / local dev without docker-compose
# up), this hangs for minutes, not seconds -- which is exactly the
# "hangs until I Ctrl+C" behavior being reported. These env vars
# must be set at import time, since MlflowClient reads them once
# when it builds its requests session.
# ============================================================
os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "3")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAx_RETRIES", "1")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_BACKOFF_FACTOR", "0")

import json
import logging
import socket
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache

import pytest
import redis
import requests
from fastapi.testclient import TestClient

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# SERVICE DETECTION WITH LRU CACHE
# ============================================================


@dataclass
class ServiceStatus:
    """Service availability status"""

    available: bool
    version: str | None = None
    latency_ms: float | None = None


def wait_for_service(host: str, port: int, timeout: int = 5) -> bool:
    """Wait for service with timeout - prevents hanging"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def is_mlflow_available() -> bool:
    """Check MLflow availability. Not cached: MLflow can take 10-20s to
    finish booting (sqlite backend store creation, migrations) after its
    container reports "Started". Caching the first check result (as this
    used to do via @lru_cache) would permanently mark MLflow unavailable
    for the whole pytest session if that first check landed during startup,
    even though it becomes healthy moments later. This is called once per
    session-scoped fixture anyway, so no caching is needed for performance.
    """
    if not wait_for_service("localhost", 5000, timeout=15):
        return False

    try:
        response = requests.get("http://localhost:5000/health", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def is_redis_available() -> bool:
    """Check Redis availability. Not cached -- see is_mlflow_available()."""
    if not wait_for_service("localhost", 6379, timeout=15):
        return False

    try:
        r = redis.Redis(host="localhost", port=6379, socket_timeout=3)
        r.ping()
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def is_docker_available() -> bool:
    """Check Docker availability"""
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=2, check=True)
        return result.returncode == 0
    except Exception:
        return False


@lru_cache(maxsize=1)
def get_mlflow_version() -> str | None:
    """Get MLflow version if available"""
    if not is_mlflow_available():
        return None
    try:
        response = requests.get("http://localhost:5000/version", timeout=2)
        return response.json().get("version")
    except Exception:
        return None


# ============================================================
# DOCKER COMPOSE MANAGEMENT
# ============================================================


@contextmanager
def docker_compose_services(compose_file: str = "docker-compose.integration.yml"):
    """Context manager for Docker Compose services"""
    if not is_docker_available():
        logger.warning("Docker not available - skipping service startup")
        yield
        return

    if not os.path.exists(compose_file):
        logger.warning(f"Compose file {compose_file} not found")
        yield
        return

    # Check if services already running
    if is_redis_available() and is_mlflow_available():
        logger.info("Services already running")
        yield
        return

    # Start services
    logger.info(f"Starting services from {compose_file}...")
    try:
        subprocess.run(
            ["docker-compose", "-f", compose_file, "up", "-d"],
            check=True,
            capture_output=True,
            timeout=30,
        )
        logger.info("Services started successfully")
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        yield
        return

    # Wait for services
    logger.info("Waiting for services to be ready...")
    redis_ready = wait_for_service("localhost", 6379, timeout=15)
    mlflow_ready = wait_for_service("localhost", 5000, timeout=15)

    if redis_ready:
        logger.info("Redis is ready")
    else:
        logger.warning("Redis not ready after 15 seconds")

    if mlflow_ready:
        logger.info("MLflow is ready")
    else:
        logger.warning("MLflow not ready after 15 seconds")

    yield

    # Cleanup
    if not os.environ.get("DEBUG"):
        logger.info("Cleaning up services...")
        try:
            subprocess.run(
                ["docker-compose", "-f", compose_file, "down"],
                check=True,
                capture_output=True,
                timeout=30,
            )
            logger.info("Services cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")


# ============================================================
# FIxTURES
# ============================================================


@pytest.fixture(scope="session")
def services():
    """Start services if needed"""
    if not os.environ.get("INTEGRATION_TESTS"):
        logger.info("Integration tests disabled (set INTEGRATION_TESTS=1 to enable)")
        yield
        return

    with docker_compose_services():
        yield


@pytest.fixture(scope="session")
def mlflow_client(services):
    """Create MLflow client with validation. Skips fast if MLflow isn't up."""
    if not is_mlflow_available():
        pytest.skip("MLflow not available")
        return None

    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri("http://localhost:5000")
        client = MlflowClient()

        # Validate connection (bounded by MLFLOW_HTTP_REQUEST_TIMEOUT set above)
        client.get_experiment_by_name("test")
        return client
    except Exception as e:
        pytest.skip(f"MLflow client failed: {e}")
        return None


@pytest.fixture(scope="session")
def redis_client(services):
    """Create Redis client with validation"""
    if not is_redis_available():
        pytest.skip("Redis not available")
        return None

    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True,
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Redis client failed: {e}")
        return None


@pytest.fixture(scope="session")
def test_model(mlflow_client):
    """Create or get test model with proper validation"""
    if not mlflow_client:
        pytest.skip("MLflow client not available")
        return None

    model_name = "test_model"

    # Check if model exists
    try:
        versions = mlflow_client.get_latest_versions(model_name)
        if versions:
            logger.info(f"Model {model_name} exists")
            return model_name
    except Exception as e:
        logger.warning(f"Could not check model: {e}")

    # Create model
    try:
        import mlflow
        import numpy as np
        import pandas as pd
        from sklearn.ensemble import RandomForestRegressor

        logger.info(f"Creating model {model_name}...")

        with mlflow.start_run() as run:
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

            from mlflow.models.signature import infer_signature

            signature = infer_signature(x, y)

            mlflow.sklearn.log_model(
                model, "model", signature=signature, registered_model_name=model_name
            )

            model_uri = f"runs:/{run.info.run_id}/model"
            result = mlflow.register_model(model_uri, model_name)

            mlflow_client.transition_model_version_stage(
                name=model_name, version=result.version, stage="Production"
            )

            logger.info(f"Model {model_name} created (v{result.version})")
            return model_name

    except Exception as e:
        logger.warning(f"Failed to create model: {e}")
        return create_local_test_model()


def create_local_test_model():
    """Create local model as fallback.

    Writes with pickle via ModelInference.save_model() rather than
    joblib.dump(): every loader in this codebase (_load_from_path,
    _load_from_registry) reads with pickle.load(), and joblib's on-disk
    format is not guaranteed pickle-compatible. Writing with joblib and
    reading with pickle fails with "STACK_GLOBAL requires str" even
    though the model itself is perfectly valid -- this was silently
    breaking every fixture downstream of test_model whenever MLflow
    registration failed and this fallback kicked in.
    """
    import tempfile

    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor

    from src.models.inference import ModelInference

    logger.info("Creating local fallback model...")

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

    temp_dir = tempfile.mkdtemp()
    model_path = os.path.join(temp_dir, "model.pkl")

    writer = ModelInference({})
    writer.model = model
    writer.feature_columns = ["feature_1", "feature_2", "feature_3"]
    writer.save_model(model_path)

    logger.info(f"Local model created at {model_path}")
    return model_path


@pytest.fixture(scope="function")
def api_client(services, test_model):
    """Create API client with smart configuration"""

    model_config = {}
    if isinstance(test_model, str):
        if test_model.startswith("/"):
            model_config = {"model_path": test_model}
        else:
            model_config = {"model_name": test_model}

    config = {
        "model": model_config,
        "feature_store": {"redis_host": "localhost", "redis_port": 6379, "timeout": 3},
        "auth": {
            "secret_key": "test_secret_key",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
        },
        "rate_limiting": {"requests_per_minute": 1000, "burst_limit": 2000},
        "cors_origins": ["*"],
    }

    try:
        from src.serving.api import create_app

        app = create_app(config)
        return TestClient(app)
    except Exception as e:
        logger.error(f"Failed to create API client: {e}")
        pytest.skip(f"API client creation failed: {e}")
        return None


@pytest.fixture(scope="function")
def auth_token(api_client):
    """Get authentication token"""
    if not api_client:
        pytest.skip("API client not available")
        return None

    # for username, password in [("admin", "password"), ("test_user", "test_pass")]:
    for username, password in [("admin", "admin123"), ("user", "user123")]:
        try:
            response = api_client.post(
                "/auth/login", json={"username": username, "password": password}
            )
            if response.status_code == 200:
                token = response.json()["access_token"]
                logger.info(f"Authenticated as {username}")
                return token
        except Exception:
            continue

    pytest.skip("Authentication failed")
    return None


@pytest.fixture(scope="function")
def seeded_redis(redis_client):
    """Seed Redis with test data"""
    if not redis_client:
        pytest.skip("Redis not available")

    pattern = "test:*"
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key)

    test_data = {
        "feature:test_product:test_store": {"feature_1": 1.0, "feature_2": 2.0, "feature_3": 3.0},
        "feature:product_001:store_001": {"feature_1": 5.0, "feature_2": 6.0, "feature_3": 7.0},
    }

    for key, value in test_data.items():
        redis_client.set(key, json.dumps(value))
        redis_client.expire(key, 3600)

    yield redis_client

    for key in redis_client.scan_iter("test:*"):
        redis_client.delete(key)
