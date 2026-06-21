"""
Feature Store Layer - Online/Offline Feature Serving
"""

import redis
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import hashlib

class FeatureStore:
    """Complete feature store with online and offline capabilities"""

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            health_check_interval=30
        )
        self.feature_registry = {}
        self._initialize_registry()

    def _initialize_registry(self):
        """Initialize feature registry with metadata"""

        self.feature_registry = {
            # Product features
            'product_category': {'type': 'static', 'ttl': 86400*365, 'entity': 'product'},
            'product_base_price': {'type': 'static', 'ttl': 86400*365, 'entity': 'product'},
            'product_brand': {'type': 'static', 'ttl': 86400*365, 'entity': 'product'},

            # Time series features
            'sales_lag_7d': {'type': 'time_series', 'ttl': 86400*30, 'entity': 'product_store'},
            'sales_lag_28d': {'type': 'time_series', 'ttl': 86400*30, 'entity': 'product_store'},
            'sales_rolling_mean_7d': {'type': 'window', 'ttl': 86400*30, 'entity': 'product_store'},
            'sales_rolling_mean_30d': {'type': 'window', 'ttl': 86400*30, 'entity': 'product_store'},

            # Derived features
            'price_elasticity': {'type': 'derived', 'ttl': 86400*7, 'entity': 'product'},
            'demand_volatility': {'type': 'derived', 'ttl': 86400*7, 'entity': 'product_store'},
            'inventory_turnover': {'type': 'derived', 'ttl': 86400*1, 'entity': 'product_store'},
            'stockout_risk': {'type': 'derived', 'ttl': 86400*1, 'entity': 'product_store'},

            # Real-time features
            'current_inventory': {'type': 'online', 'ttl': 3600, 'entity': 'product_store'},
            'current_price': {'type': 'online', 'ttl': 3600, 'entity': 'product'},
            'competitor_price': {'type': 'online', 'ttl': 3600, 'entity': 'product'},
            'weather_condition': {'type': 'online', 'ttl': 3600, 'entity': 'location'},
            'holiday_flag': {'type': 'online', 'ttl': 86400, 'entity': 'date'},
        }

    def _get_key(self, feature_name: str, entity_id: str) -> str:
        """Generate Redis key for feature"""
        return f"feature:{feature_name}:{entity_id}"

    def register_feature(self, name: str, feature_type: str, ttl: int, entity: str):
        """Register new feature"""
        self.feature_registry[name] = {
            'type': feature_type,
            'ttl': ttl,
            'entity': entity
        }

    def set_feature(self, feature_name: str, entity_id: str, value: Any,
                    timestamp: datetime = None):
        """Set feature value in store"""

        if feature_name not in self.feature_registry:
            raise ValueError(f"Feature {feature_name} not registered")

        key = self._get_key(feature_name, entity_id)
        ttl = self.feature_registry[feature_name]['ttl']

        # Store value with metadata
        value_dict = {
            'value': value,
            'timestamp': (timestamp or datetime.now()).isoformat(),
            'feature_name': feature_name,
            'entity_id': entity_id
        }

        self.redis_client.setex(
            key,
            ttl,
            json.dumps(value_dict, default=str)
        )

        # Add to entity index
        entity_key = f"entity:{self.feature_registry[feature_name]['entity']}:{entity_id}"
        self.redis_client.sadd(entity_key, feature_name)
        self.redis_client.expire(entity_key, ttl)

    def get_feature(self, feature_name: str, entity_id: str,
                    default: Any = None) -> Optional[Any]:
        """Get feature value"""

        key = self._get_key(feature_name, entity_id)
        value_json = self.redis_client.get(key)

        if value_json:
            value_dict = json.loads(value_json)
            return value_dict['value']
        return default

    def get_features_batch(self, feature_names: List[str], entity_id: str) -> Dict[str, Any]:
        """Get multiple features for an entity"""

        features = {}
        for feature_name in feature_names:
            value = self.get_feature(feature_name, entity_id)
            if value is not None:
                features[feature_name] = value
        return features

    def get_entity_features(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Get all features for an entity"""

        entity_key = f"entity:{entity_type}:{entity_id}"
        feature_names = self.redis_client.smembers(entity_key)

        features = {}
        for feature_name in feature_names:
            value = self.get_feature(feature_name, entity_id)
            if value is not None:
                features[feature_name] = value

        return features

    def compute_derived_features(self, product_id: str, store_id: str,
                                 sales_history: List[float]) -> Dict[str, float]:
        """Compute derived features on the fly"""

        entity_id = f"{product_id}_{store_id}"
        derived_features = {}

        if len(sales_history) > 7:
            # Price elasticity
            # Simplified calculation - would need price data in production
            derived_features['demand_volatility'] = np.std(sales_history) / np.mean(sales_history)

            # Trend
            recent_avg = np.mean(sales_history[-7:])
            previous_avg = np.mean(sales_history[-14:-7])
            derived_features['sales_trend'] = (recent_avg - previous_avg) / previous_avg if previous_avg > 0 else 0

            # Seasonality
            if len(sales_history) > 28:
                weekly_pattern = []
                for i in range(7):
                    weekly_pattern.append(np.mean(sales_history[i::7]))
                derived_features['peak_day'] = np.argmax(weekly_pattern)

        # Store derived features
        for name, value in derived_features.items():
            self.set_feature(name, entity_id, value)

        return derived_features

    def get_feature_vector(self, product_id: str, store_id: str,
                          timestamp: datetime = None) -> np.ndarray:
        """Get complete feature vector for model inference"""

        entity_id = f"{product_id}_{store_id}"

        # Get all features
        features = self.get_entity_features('product_store', entity_id)

        # Add time-based features
        now = timestamp or datetime.now()
        features['hour'] = now.hour
        features['day_of_week'] = now.weekday()
        features['day_of_month'] = now.day
        features['month'] = now.month
        features['is_weekend'] = 1 if now.weekday() >= 5 else 0

        # Convert to vector
        feature_names = sorted(features.keys())
        feature_vector = np.array([float(features[name]) for name in feature_names])

        return feature_vector, feature_names

    def batch_update_offline_features(self, feature_df: pd.DataFrame,
                                      entity_columns: List[str]):
        """Batch update offline features"""

        for _, row in feature_df.iterrows():
            entity_id = '_'.join([str(row[col]) for col in entity_columns])

            for col in feature_df.columns:
                if col not in entity_columns and col in self.feature_registry:
                    self.set_feature(col, entity_id, row[col])

        print(f"✅ Batch updated {len(feature_df)} records")

    def get_training_data(self, entity_ids: List[str], start_date: datetime,
                          end_date: datetime) -> pd.DataFrame:
        """Get historical features for training"""

        training_data = []

        for entity_id in entity_ids:
            # Get features for time range
            # In production, would query from offline storage
            features = self.get_entity_features('product_store', entity_id)
            features['entity_id'] = entity_id
            training_data.append(features)

        return pd.DataFrame(training_data)