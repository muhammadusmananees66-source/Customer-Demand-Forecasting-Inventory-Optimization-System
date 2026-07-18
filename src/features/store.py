# """
# Feature Store - Feature storage and retrieval
# """

# import pandas as pd
# from typing import Dict, Any, List, Optional
# import structlog
# import redis
# import json
# import hashlib

# logger = structlog.get_logger()


# class FeatureStoreManager:
#     """Feature Store Manager for online and offline features"""

#     def __init__(self, config: Dict[str, Any]):
#         self.config = config
#         self.redis_host = config.get("redis_host", "localhost")
#         self.redis_port = config.get("redis_port", 6379)
#         self.redis_db = config.get("redis_db", 0)
#         self.redis_client = None
#         self._init_redis()

#     def _init_redis(self):
#         """Initialize Redis client"""
#         try:
#             self.redis_client = redis.Redis(
#                 host=self.redis_host,
#                 port=self.redis_port,
#                 db=self.redis_db,
#                 decode_responses=True
#             )
#             self.redis_client.ping()
#             logger.info("Redis client initialized")
#         except Exception as e:
#             logger.warning(f"Redis initialization failed: {e}")
#             self.redis_client = None

#     def _generate_cache_key(self, entity_rows: List[Dict], feature_names: List[str]) -> str:
#         """Generate cache key from entity rows and feature names"""
#         key_data = {
#             "entities": entity_rows,
#             "features": sorted(feature_names)
#         }
#         key_string = json.dumps(key_data, sort_keys=True)
#         return f"features:{hashlib.md5(key_string.encode()).hexdigest()}"

#     def get_online_features(self, entity_rows: List[Dict], feature_names: List[str]) -> pd.DataFrame:
#         """Get online features from Redis cache"""
#         if self.redis_client is None:
#             logger.warning("Redis not available, returning empty DataFrame")
#             return pd.DataFrame()

#         cache_key = self._generate_cache_key(entity_rows, feature_names)
#         cached = self.redis_client.get(cache_key)

#         if cached:
#             logger.debug("Features retrieved from Redis cache")
#             return pd.DataFrame(json.loads(cached))

#         # Generate features if not cached
#         results = []
#         for entity in entity_rows:
#             row = {}
#             for feature in feature_names:
#                 row[feature] = self._generate_mock_feature(feature, entity)
#             results.append(row)

#         df = pd.DataFrame(results)

#         # Cache for future
#         if self.redis_client:
#             self.redis_client.setex(cache_key, 3600, df.to_json())

#         return df

#     def _generate_mock_feature(self, feature: str, entity: Dict) -> float:
#         """Generate mock feature value"""
#         import random
#         return round(random.uniform(0, 100), 2)

#     def push_features(self, df: pd.DataFrame, feature_view_name: str):
#         """Push features to Redis cache"""
#         if self.redis_client is None:
#             logger.warning("Redis not available, cannot push features")
#             return

#         for _, row in df.iterrows():
#             key = f"feature:{feature_view_name}:{row.get('product_id', '')}"
#             self.redis_client.setex(key, 3600, row.to_json())

#         logger.info(f"Pushed {len(df)} rows to Redis cache for {feature_view_name}")

#     def get_historical_features(self, entity_df: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
#         """Get historical features for training"""
#         entity_rows = entity_df.to_dict('records')
#         return self.get_online_features(entity_rows, feature_names)


"""
Feature Store - Simplified for initial development
"""

from typing import Any

import pandas as pd
import structlog

logger = structlog.get_logger()


class FeatureStoreManager:
    """Simplified Feature Store Manager"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config: dict[str, Any] = config
        self.cache: dict[str, pd.DataFrame] = {}

    def get_online_features(
        self, entity_rows: list[dict], feature_names: list[str]
    ) -> pd.DataFrame:
        """Get online features"""
        results: list[dict] = []
        for _entity in entity_rows:
            row: dict[str, float] = {}
            for feature in feature_names:
                # In production, this would fetch from Redis/Feast
                row[feature] = 0.0  # Placeholder
            results.append(row)

        return pd.DataFrame(results)

    def push_features(self, df: pd.DataFrame, feature_view_name: str) -> None:
        """Push features to cache"""
        logger.info(f"Pushed {len(df)} rows to cache for {feature_view_name}")

    def get_historical_features(
        self, entity_df: pd.DataFrame, feature_names: list[str]
    ) -> pd.DataFrame:
        """Get historical features"""
        return self.get_online_features(entity_df.to_dict("records"), feature_names)
