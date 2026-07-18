#!/usr/bin/env python
"""
Verify Model Inference Module - Standalone script
"""

import sys
import os
import pickle
import json
import tempfile
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.inference import ModelInference


def create_sample_model():
    """Create a sample model for testing"""
    np.random.seed(42)
    X = pd.DataFrame({
        'feature_1': np.random.randn(100),
        'feature_2': np.random.randn(100),
        'feature_3': np.random.randn(100),
    })
    y = 2 * X['feature_1'] + 3 * X['feature_2'] + np.random.randn(100) * 0.1
    
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X, y)
    return model, X.columns.tolist()


def verify_inference():
    """Verify ModelInference"""
    print("\n📋 Testing ModelInference...")
    
    config = {
        'version': '1.0.0',
        'model_name': 'verify_model',
        'mlflow_tracking_uri': 'http://localhost:5000',
    }
    
    inference = ModelInference(config)
    model, feature_cols = create_sample_model()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        
        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        with open(f"{model_path}.features", 'w') as f:
            json.dump(feature_cols, f)
        
        # Load model
        inference.load_model(path=model_path)
        print(f"  Model loaded: version={inference.model_version}")
        print(f"  Features: {len(inference.feature_columns)}")
        
        # Test prediction
        X_test = pd.DataFrame({
            'feature_1': np.random.randn(10),
            'feature_2': np.random.randn(10),
            'feature_3': np.random.randn(10),
        })
        
        predictions = inference.predict(X_test)
        print(f"  Predictions shape: {predictions.shape}")
        
        # Test confidence intervals
        result = inference.predict_with_confidence(X_test)
        print(f"  Confidence intervals: lower={result['confidence_lower'][0]:.2f}, upper={result['confidence_upper'][0]:.2f}")
        
        # Test model info
        info = inference.get_model_info()
        print(f"  Model info: {info['model_name']} v{info['model_version']}")
    
    print("✅ ModelInference works!")
    return True


def main():
    """Main verification function"""
    print("=" * 60)
    print("🔍 VERIFYING MODEL INFERENCE MODULE")
    print("=" * 60)
    
    try:
        verify_inference()
        
        print("\n" + "=" * 60)
        print("✅ ALL INFERENCE VERIFICATIONS PASSED!")
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