"""
Unit tests for Feature Engineering module
"""

import numpy as np
import pandas as pd
import pytest

from src.features.engineering import FeatureEngineer, FeatureSelector


class TestFeatureEngineer:
    """Test FeatureEngineer class"""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        np.random.seed(42)  # For reproducible tests
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        data = {
            "date": dates,
            "product_id": ["A"] * 50 + ["B"] * 50,
            "quantity": np.random.randint(1, 100, 100),
            "price": np.random.uniform(10, 100, 100),
            "store_id": ["store1"] * 50 + ["store2"] * 50,
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def config(self):
        """Default configuration"""
        return {
            "time_features": True,
            "lag_features": [1, 7],
            "rolling_windows": [7, 14],
            "group_by": ["product_id"],
            "target": "quantity",
            "date_col": "date",
        }

    def test_feature_engineer_creation(self, config):
        """Test FeatureEngineer initialization"""
        engineer = FeatureEngineer(config)
        assert engineer.config == config
        assert engineer.time_features is True
        assert engineer.lag_features == [1, 7]
        assert engineer.rolling_windows == [7, 14]
        assert engineer.group_by == ["product_id"]
        assert engineer.target == "quantity"
        assert engineer.date_col == "date"
        assert engineer.scaler is None
        assert engineer.encoder is None

    def test_create_features(self, sample_data, config):
        """Test full feature creation pipeline"""
        engineer = FeatureEngineer(config)
        result = engineer.create_features(sample_data)

        # Check that more columns were added
        assert len(result.columns) > len(sample_data.columns)

        # Check time features
        assert "day_of_week" in result.columns
        assert "month" in result.columns
        assert "is_weekend" in result.columns

        # Check lag features
        assert "quantity_lag_1" in result.columns
        assert "quantity_lag_7" in result.columns

        # Check rolling features
        assert "quantity_roll_mean_7" in result.columns
        assert "quantity_roll_mean_14" in result.columns

        # Check interaction features
        assert "revenue" in result.columns
        assert "log_quantity" in result.columns

    def test_add_time_features(self, sample_data, config):
        """Test time feature creation"""
        engineer = FeatureEngineer(config)
        result = engineer._add_time_features(sample_data)

        assert "day_of_week" in result.columns
        assert "month" in result.columns
        assert "quarter" in result.columns
        assert "year" in result.columns
        assert "is_weekend" in result.columns
        assert "days_until_holiday" in result.columns

    def test_add_lag_features(self, sample_data, config):
        """Test lag feature creation"""
        engineer = FeatureEngineer(config)
        # Sort data first
        sample_data = sample_data.sort_values("date")
        result = engineer._add_lag_features(sample_data)

        assert "quantity_lag_1" in result.columns
        assert "quantity_lag_7" in result.columns
        assert "price_lag_1" in result.columns
        assert "price_lag_7" in result.columns

        # Check that lag values are NaN for first rows
        assert result["quantity_lag_1"].iloc[0] is None or pd.isna(result["quantity_lag_1"].iloc[0])

    def test_add_rolling_features(self, sample_data, config):
        """Test rolling feature creation"""
        engineer = FeatureEngineer(config)
        sample_data = sample_data.sort_values("date")
        result = engineer._add_rolling_features(sample_data)

        assert "quantity_roll_mean_7" in result.columns
        assert "quantity_roll_std_7" in result.columns
        assert "quantity_roll_min_7" in result.columns
        assert "quantity_roll_max_7" in result.columns
        assert "price_roll_mean_7" in result.columns

    def test_add_aggregation_features(self, sample_data, config):
        """Test aggregation feature creation"""
        engineer = FeatureEngineer(config)
        result = engineer._add_aggregation_features(sample_data)

        assert "quantity_mean" in result.columns
        assert "quantity_std" in result.columns
        assert "quantity_min" in result.columns
        assert "quantity_max" in result.columns
        assert "price_mean" in result.columns
        assert "store_id_nunique" in result.columns

    def test_add_interaction_features(self, sample_data, config):
        """Test interaction feature creation"""
        engineer = FeatureEngineer(config)
        sample_data = sample_data.sort_values("date")
        result = engineer._add_interaction_features(sample_data)

        assert "revenue" in result.columns
        assert "log_quantity" in result.columns
        assert "log_price" in result.columns
        assert "log_revenue" in result.columns

    def test_add_seasonal_features(self, sample_data, config):
        """Test seasonal feature creation"""
        engineer = FeatureEngineer(config)
        result = engineer._add_seasonal_features(sample_data)

        assert "month_sin" in result.columns
        assert "month_cos" in result.columns
        assert "day_of_week_sin" in result.columns
        assert "day_of_week_cos" in result.columns

    def test_encode_categorical(self, sample_data, config):
        """Test categorical encoding"""
        engineer = FeatureEngineer(config)
        result = engineer._encode_categorical(sample_data)

        # Check that categorical columns are encoded
        # Note: 'product_id' is in group_by, so it won't be encoded
        # But 'store_id' should be encoded
        assert "product_id" in result.columns, "product_id should remain (it's in group_by)"
        assert "store_id" not in result.columns, "store_id should be encoded"
        assert "store_id_store1" in result.columns, "store_id_store1 one-hot column should exist"
        assert "store_id_store2" in result.columns, "store_id_store2 one-hot column should exist"

        # Verify one-hot encoding values are binary (0 or 1)
        assert (
            result["store_id_store1"].isin([0, 1]).all()
        ), "One-hot values should be binary (0 or 1)"

        # Check that each row has exactly one store_id flag
        store_cols = ["store_id_store1", "store_id_store2"]
        row_sums = result[store_cols].sum(axis=1)
        assert (row_sums == 1).all(), "Each row should have exactly one store flag"

        # Check that row count remains the same
        assert len(result) == len(sample_data), "Number of rows should remain unchanged"

    def test_scale_features(self, sample_data, config):
        """Test feature scaling"""
        engineer = FeatureEngineer(config)

        # First add some features so we have features to scale (not just target)
        sample_data_with_features = engineer._add_time_features(sample_data)
        sample_data_with_features = engineer._add_interaction_features(sample_data_with_features)

        result = engineer._scale_features(sample_data_with_features)

        # Get numerical columns that were scaled (excluding group_by columns)
        exclude_cols = config["group_by"] + [config["date_col"]]
        numerical_cols = result.select_dtypes(include=[np.number]).columns.tolist()
        scaled_cols = [col for col in numerical_cols if col not in exclude_cols]

        # Check that we have at least one feature column to test
        assert len(scaled_cols) > 0, "No feature columns to test scaling"

        # Test scaling on the first feature column
        test_col = scaled_cols[0]
        # Mean should be approximately 0 after scaling
        assert (
            abs(result[test_col].mean()) < 1e-10
        ), f"Mean of {test_col} should be 0, got {result[test_col].mean()}"
        # Std should be approximately 1
        assert (
            abs(result[test_col].std() - 1) < 0.1
        ), f"Std of {test_col} should be 1, got {result[test_col].std()}"

        # Verify the scaler was fitted and stored
        assert engineer.scaler is not None, "Scaler should be fitted and stored"


class TestFeatureSelector:
    """Test FeatureSelector class"""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        np.random.seed(42)
        x = pd.DataFrame(
            {
                "feature_1": np.random.randn(100),
                "feature_2": np.random.randn(100),
                "feature_3": np.random.randn(100),
                "feature_4": np.random.randn(100),
            }
        )
        y = pd.Series(2 * x["feature_1"] + 3 * x["feature_2"] + np.random.randn(100) * 0.1)
        return x, y

    def test_feature_selector_creation(self):
        """Test FeatureSelector initialization"""
        config = {"method": "importance", "num_features": 2}
        selector = FeatureSelector(config)
        assert selector.config == config
        assert selector.method == "importance"
        assert selector.num_features == 2

    def test_importance_based_selection(self, sample_data):
        """Test importance-based feature selection"""
        x, y = sample_data
        config = {"method": "importance", "num_features": 2}
        selector = FeatureSelector(config)
        selected = selector.select_features(x, y)

        assert len(selected) == 2
        assert "feature_1" in selected or "feature_2" in selected

    def test_rfe_selection(self, sample_data):
        """Test RFE-based feature selection"""
        x, y = sample_data
        config = {"method": "rfe", "num_features": 2}
        selector = FeatureSelector(config)
        selected = selector.select_features(x, y)

        assert len(selected) == 2

    def test_correlation_selection(self, sample_data):
        """Test correlation-based feature selection"""
        x, y = sample_data
        config = {"method": "correlation", "num_features": 2}
        selector = FeatureSelector(config)
        selected = selector.select_features(x, y)

        assert len(selected) == 2
