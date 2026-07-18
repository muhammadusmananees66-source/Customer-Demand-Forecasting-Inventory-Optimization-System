# """
# Production FastAPI - Complete with auth, rate limiting, and observability
# Production-Grade ML Serving API
# """

# import os
# import uuid
# from datetime import datetime
# from typing import Any

# import structlog
# from fastapi import Depends, FastAPI, HTTPException, Response
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
# from prometheus_client import Counter, Gauge, Histogram, generate_latest
# from pydantic import BaseModel, Field

# from src.features.store import FeatureStoreManager
# from src.models.inference import ModelInference
# from src.serving.auth import auth_manager
# from src.serving.dependencies import get_current_user
# from src.serving.rate_limiter import rate_limiter

# logger = structlog.get_logger()
# security: HTTPBearer = HTTPBearer()

# # Prometheus metrics
# REQUEST_COUNT = Counter(
#     "api_requests_total", "Total API requests", ["method", "endpoint", "status"]
# )
# REQUEST_LATENCY = Histogram(
#     "api_request_duration_seconds", "Request latency", ["method", "endpoint"]
# )
# ACTIVE_REQUESTS = Gauge("api_active_requests", "Active API requests")


# # ============================================================================
# # Request/Response Models
# # ============================================================================


# class LoginRequest(BaseModel):
#     """Login request model"""

#     username: str
#     password: str


# class TokenResponse(BaseModel):
#     """JWT token response"""

#     access_token: str
#     token_type: str = "bearer"
#     expires_in: int


# class PredictionRequest(BaseModel):
#     """Prediction request model"""

#     product_id: str
#     store_id: str
#     date: str
#     features: dict[str, float] = Field(
#         default_factory=dict, description="Additional feature values"
#     )


# class PredictionResponse(BaseModel):
#     """Prediction response model"""

#     request_id: str
#     product_id: str
#     predicted_quantity: float
#     confidence_lower: float
#     confidence_upper: float
#     model_version: str
#     timestamp: datetime


# # ============================================================================
# # Application Factory
# # ============================================================================


# def create_app(config: dict[str, Any] | None = None) -> FastAPI:
#     """
#     Create FastAPI application with:
#     - JWT authentication
#     - Rate limiting
#     - Prometheus metrics
#     - MLflow model registry integration
#     - Redis feature store
#     """
#     config = config or {}
#     startup_time: datetime = datetime.now()

#     # Initialize model inference
#     inference = ModelInference(config.get("model", {}))
#     model_path = config.get("model", {}).get("model_path")

#     if model_path and os.path.exists(model_path):
#         inference.load_model(model_path)
#     else:
#         inference.load_model()

#     model_version: str = inference.model_version
#     feature_store: FeatureStoreManager = FeatureStoreManager(config.get("feature_store", {}))

#     # Create FastAPI app
#     app = FastAPI(
#         title="Demand Forecasting API",
#         description="Production demand forecasting service with MLflow, Redis, and Prometheus",
#         version="1.0.0",
#         docs_url="/docs",
#         redoc_url="/redoc",
#     )

#     # CORS middleware
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=config.get("cors_origins", ["https://*.company.com"]),
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

#     # ========================================================================
#     # Health & Readiness Endpoints
#     # ========================================================================

#     @app.get("/health")
#     async def health() -> dict[str, Any]:
#         """Health check endpoint for liveness probe"""
#         return {
#             "status": "healthy",
#             "model_version": model_version,
#             "model_loaded": inference.model is not None,
#             "uptime": (datetime.now() - startup_time).total_seconds(),
#         }

#     @app.get("/ready")
#     async def ready() -> dict[str, Any]:
#         """Readiness check endpoint for readiness probe"""
#         if inference.model is None:
#             raise HTTPException(status_code=503, detail="Model not loaded")
#         return {"status": "ready", "model_version": model_version}

#     # ========================================================================
#     # Authentication Endpoints
#     # ========================================================================

#     @app.post("/auth/login", response_model=TokenResponse)
#     async def login(request: LoginRequest) -> TokenResponse:
#         """Authenticate user and return JWT token"""
#         user_data = auth_manager.authenticate(request.username, request.password)
#         if not user_data:
#             raise HTTPException(status_code=401, detail="Invalid credentials")
#         token = auth_manager.create_token(user_data)
#         return TokenResponse(access_token=token, expires_in=3600)

#     # ========================================================================
#     # Metrics Endpoint
#     # ========================================================================

#     @app.get("/metrics")
#     async def metrics() -> Response:
#         """Prometheus metrics endpoint"""
#         return Response(content=generate_latest(), media_type="text/plain")

#     # ========================================================================
#     # Prediction Endpoint
#     # ========================================================================

#     @app.post("/predict", response_model=PredictionResponse)
#     async def predict(
#         request: PredictionRequest,
#         credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
#         user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
#         _: bool = Depends(rate_limiter),  # noqa: B008
#     ) -> PredictionResponse:
#         """
#         Make demand prediction with authentication and rate limiting.

#         - ✅ JWT Authentication required
#         - ✅ Rate limiting (100 requests/minute)
#         - ✅ Prometheus metrics
#         - ✅ Confidence intervals
#         """
#         ACTIVE_REQUESTS.inc()
#         start_time: datetime = datetime.now()

#         try:
#             # Get features from feature store
#             entity_rows = [{"product_id": request.product_id, "store_id": request.store_id}]
#             feature_names = inference.feature_columns
#             features = feature_store.get_online_features(entity_rows, feature_names)

#             if features.empty:
#                 raise HTTPException(status_code=400, detail="No features found")

#             # Make prediction
#             result = inference.predict_with_confidence(features)
#             prediction = float(result["predictions"][0])
#             confidence_lower = float(result["confidence_lower"][0])
#             confidence_upper = float(result["confidence_upper"][0])

#             # Build response
#             response = PredictionResponse(
#                 request_id=str(uuid.uuid4()),
#                 product_id=request.product_id,
#                 predicted_quantity=prediction,
#                 confidence_lower=confidence_lower,
#                 confidence_upper=confidence_upper,
#                 model_version=model_version,
#                 timestamp=datetime.now(),
#             )

#             # Record metrics
#             REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="200").inc()
#             REQUEST_LATENCY.labels(method="POST", endpoint="/predict").observe(
#                 (datetime.now() - start_time).total_seconds()
#             )

#             return response

#         except HTTPException:
#             REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="401").inc()
#             raise
#         except Exception as e:
#             REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="500").inc()
#             logger.error(f"Prediction failed: {e}", exc_info=True)
#             # ✅ Preserve original traceback for debugging
#             raise HTTPException(status_code=500, detail=str(e)) from e
#         finally:
#             ACTIVE_REQUESTS.dec()

#     return app


"""
Production FastAPI - Complete with auth, rate limiting, and observability
Production-Grade ML Serving API
"""

import os
import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

from src.features.store import FeatureStoreManager
from src.models.inference import ModelInference
from src.serving.auth import auth_manager
from src.serving.dependencies import get_current_user
from src.serving.rate_limiter import rate_limiter

logger = structlog.get_logger()
security: HTTPBearer = HTTPBearer()

REQUEST_COUNT = Counter(
    "api_requests_total", "Total API requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds", "Request latency", ["method", "endpoint"]
)
ACTIVE_REQUESTS = Gauge("api_active_requests", "Active API requests")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PredictionRequest(BaseModel):
    product_id: str
    store_id: str
    date: str
    features: dict[str, float] = Field(
        default_factory=dict, description="Additional feature values"
    )


class PredictionResponse(BaseModel):
    request_id: str
    product_id: str
    predicted_quantity: float
    confidence_lower: float
    confidence_upper: float
    model_version: str
    timestamp: datetime


def create_app(config: dict[str, Any] | None = None) -> FastAPI:
    config = config or {}
    startup_time: datetime = datetime.now()

    inference = ModelInference(config.get("model", {}))
    model_path = config.get("model", {}).get("model_path") or os.getenv("MODEL_PATH")

    if model_path and os.path.exists(model_path):
        inference.load_model(model_path)
    else:
        inference.load_model()

    model_version: str = inference.model_version
    feature_store: FeatureStoreManager = FeatureStoreManager(config.get("feature_store", {}))

    app = FastAPI(
        title="Demand Forecasting API",
        description="Production demand forecasting service with MLflow, Redis, and Prometheus",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("cors_origins", ["https://*.company.com"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "healthy",
            "model_version": model_version,
            "model_loaded": inference.model is not None,
            "uptime": (datetime.now() - startup_time).total_seconds(),
        }

    @app.get("/ready")
    async def ready() -> dict[str, Any]:
        if inference.model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        return {"status": "ready", "model_version": model_version}

    @app.post("/auth/login", response_model=TokenResponse)
    async def login(request: LoginRequest) -> TokenResponse:
        user_data = auth_manager.authenticate(request.username, request.password)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = auth_manager.create_token(user_data)
        return TokenResponse(access_token=token, expires_in=3600)

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type="text/plain")

    @app.post("/predict", response_model=PredictionResponse)
    async def predict(
        request: PredictionRequest,
        credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
        user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
        _: bool = Depends(rate_limiter),  # noqa: B008
    ) -> PredictionResponse:
        ACTIVE_REQUESTS.inc()
        start_time: datetime = datetime.now()

        try:
            entity_rows = [{"product_id": request.product_id, "store_id": request.store_id}]
            feature_names = inference.feature_columns
            features = feature_store.get_online_features(entity_rows, feature_names)

            if features.empty:
                raise HTTPException(status_code=400, detail="No features found")

            result = inference.predict_with_confidence(features)
            prediction = float(result["predictions"][0])
            confidence_lower = float(result["confidence_lower"][0])
            confidence_upper = float(result["confidence_upper"][0])

            response = PredictionResponse(
                request_id=str(uuid.uuid4()),
                product_id=request.product_id,
                predicted_quantity=prediction,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                model_version=model_version,
                timestamp=datetime.now(),
            )

            REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="200").inc()
            REQUEST_LATENCY.labels(method="POST", endpoint="/predict").observe(
                (datetime.now() - start_time).total_seconds()
            )

            return response

        except HTTPException:
            REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="401").inc()
            raise
        except Exception as e:
            REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="500").inc()
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
        finally:
            ACTIVE_REQUESTS.dec()

    return app
