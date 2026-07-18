#!/usr/bin/env python
"""
Verify Feature Engineering Module - Standalone script
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features.engineering import FeatureEngineer, FeatureSelector


def verify_feature_engineer():
    """Verify FeatureEngineer"""
    print("\n📋 Testing FeatureEngineer...")
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'date': dates,
        'product_id': ['A'] * 50 + ['B'] * 50,
        'quantity': np.random.randint(1, 100, 100),
        'price': np.random.uniform(10, 100, 100),
        'store_id': ['store1'] * 50 + ['store2'] * 50,
    })
    
    config = {
        'time_features': True,
        'lag_features': [1, 7, 14],
        'rolling_windows': [7, 14, 30],
        'group_by': ['product_id'],
        'target': 'quantity',
        'date_col': 'date'
    }
    
    engineer = FeatureEngineer(config)
    result = engineer.create_features(data)
    
    print(f"  Original columns: {len(data.columns)}")
    print(f"  New columns: {len(result.columns)}")
    print(f"  Features created: {len(result.columns) - len(data.columns)}")
    
    # Check for expected features
    expected_features = [
        'day_of_week', 'month', 'is_weekend',
        'quantity_lag_1', 'quantity_lag_7',
        'quantity_roll_mean_7', 'quantity_roll_mean_14',
        'revenue', 'log_quantity',
        'month_sin', 'day_of_week_sin'
    ]
    
    for feature in expected_features:
        assert feature in result.columns, f"Missing feature: {feature}"
    
    print("✅ All expected features created!")
    return True


def verify_feature_selector():
    """Verify FeatureSelector"""
    print("\n📋 Testing FeatureSelector...")
    
    # Create sample data
    X = pd.DataFrame({
        'feature_1': np.random.randn(100),
        'feature_2': np.random.randn(100),
        'feature_3': np.random.randn(100),
        'feature_4': np.random.randn(100),
    })
    y = pd.Series(2 * X['feature_1'] + 3 * X['feature_2'] + np.random.randn(100) * 0.1)
    
    config = {'method': 'importance', 'num_features': 2}
    selector = FeatureSelector(config)
    selected = selector.select_features(X, y)
    
    print(f"  Selected features: {selected}")
    assert len(selected) == 2
    assert 'feature_1' in selected or 'feature_2' in selected
    
    print("✅ Feature selection works!")
    return True


def main():
    """Main verification function"""
    print("=" * 60)
    print("🔍 VERIFYING FEATURE ENGINEERING MODULE")
    print("=" * 60)
    
    try:
        verify_feature_engineer()
        verify_feature_selector()
        
        print("\n" + "=" * 60)
        print("✅ ALL FEATURE ENGINEERING VERIFICATIONS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)