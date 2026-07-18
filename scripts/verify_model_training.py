# #!/usr/bin/env python
# """
# Verify Model Training Module - Standalone script
# """

# import sys
# import os
# import pandas as pd
# import numpy as np
# from datetime import datetime, timedelta

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from src.models.trainer import ModelTrainer


# def create_sample_data():
#     """Create sample data for testing"""
#     dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
#     np.random.seed(42)
#     data = {
#         'date': dates,
#         'product_id': ['A'] * 100 + ['B'] * 100,
#         'feature_1': np.random.randn(200),
#         'feature_2': np.random.randn(200),
#         'feature_3': np.random.randn(200),
#         'quantity': np.random.randint(1, 100, 200),
#         'price': np.random.uniform(10, 100, 200),
#     }
#     df = pd.DataFrame(data)
#     y = df['quantity'].copy()
#     return df, y


# def verify_trainer():
#     """Verify ModelTrainer"""
#     print("\n📋 Testing ModelTrainer...")
    
#     config = {
#         'model_type': 'xgboost',
#         'hyperparameters': {
#             'n_estimators': 50,
#             'max_depth': 4,
#             'learning_rate': 0.1,
#         },
#         'date_col': 'date',
#         'distributed': False,
#         'mlflow_tracking_uri': 'http://localhost:5000',
#         'experiment_name': 'verify_experiment'
#     }
    
#     df, y = create_sample_data()
#     trainer = ModelTrainer(config)
    
#     # Train with MLflow patch
#     import mlflow
#     with mlflow.start_run():
#         metrics = trainer.train(df, y)
    
#     print(f"  Model type: {trainer.model_type}")
#     print(f"  Features: {len(trainer.feature_columns)}")
#     print(f"  Test RMSE: {metrics.get('test_rmse', 'N/A'):.4f}")
#     print(f"  Test R²: {metrics.get('test_r2', 'N/A'):.4f}")
    
#     # Test predictions
#     predictions = trainer.predict(df)
#     print(f"  Predictions shape: {predictions.shape}")
    
#     # Test save/load
#     import tempfile
#     import os
#     with tempfile.TemporaryDirectory() as tmpdir:
#         model_path = os.path.join(tmpdir, "model.pkl")
#         trainer.save_model(model_path)
#         new_trainer = ModelTrainer(config)
#         new_trainer.load_model(model_path)
#         new_predictions = new_trainer.predict(df)
        
#         assert len(predictions) == len(new_predictions)
#         print("  ✅ Save/Load successful")
    
#     print("✅ ModelTrainer works!")
#     return True


# def main():
#     """Main verification function"""
#     print("=" * 60)
#     print("🔍 VERIFYING MODEL TRAINING MODULE")
#     print("=" * 60)
    
#     try:
#         verify_trainer()
        
#         print("\n" + "=" * 60)
#         print("✅ ALL MODEL TRAINING VERIFICATIONS PASSED!")
#         print("=" * 60)
#         return True
        
#     except Exception as e:
#         print(f"\n❌ Verification failed: {e}")
#         import traceback
#         traceback.print_exc()
#         return False


# if __name__ == "__main__":
#     success = main()
#     sys.exit(0 if success else 1)























#!/usr/bin/env python
"""
Production-Grade Model Training Verification Script
Tests the ModelTrainer without hanging or external dependencies
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

# Set environment variables to prevent hanging
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///:memory:"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_data(n_samples: int = 200) -> tuple[pd.DataFrame, pd.Series]:
    """Create sample time-series data for testing"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=n_samples, freq='D')
    
    data = {
        'date': dates,
        'product_id': np.random.choice(['A', 'B', 'C'], n_samples),
        'feature_1': np.random.randn(n_samples),
        'feature_2': np.random.randn(n_samples),
        'feature_3': np.random.randn(n_samples),
        'feature_4': np.random.randn(n_samples),
        'feature_5': np.random.randn(n_samples),
        'price': np.random.uniform(10, 100, n_samples),
        'quantity': np.random.randint(1, 100, n_samples),
    }
    df = pd.DataFrame(data)
    y = df['quantity'].copy()
    return df, y


def test_model_trainer_basic():
    """Test basic ModelTrainer functionality"""
    logger.info("=" * 60)
    logger.info("Testing ModelTrainer - Basic Functionality")
    logger.info("=" * 60)
    
    from src.models.trainer import ModelTrainer
    
    # Create config with in-memory SQLite
    config = {
        'model_type': 'xgboost',
        'hyperparameters': {
            'n_estimators': 10,  # Small for quick test
            'max_depth': 3,
            'learning_rate': 0.1,
            'random_state': 42,
        },
        'date_col': 'date',
        'target_col': 'quantity',
        'distributed': False,
        'save_model': False,
        'mlflow_tracking_uri': 'sqlite:///:memory:',
        'experiment_name': 'verification_test'
    }
    
    # Create sample data
    df, y = create_sample_data(100)
    
    # Test with mocked MLflow
    with patch('mlflow.set_experiment'), patch('mlflow.start_run'), \
         patch('mlflow.log_params'), patch('mlflow.log_metric'), patch('mlflow.log_param'):
        
        logger.info("📋 Initializing ModelTrainer...")
        trainer = ModelTrainer(config)
        
        logger.info("📊 Training model...")
        metrics = trainer.train(df, y)
        
        logger.info("✅ Training completed!")
        logger.info(f"📈 Metrics: {metrics}")
        
        # Test prediction
        logger.info("🔮 Making predictions...")
        predictions = trainer.predict(df)
        
        # Test feature importance
        logger.info("📊 Getting feature importance...")
        importance = trainer.get_feature_importance()
        
        # Assertions
        assert trainer.model is not None, "Model should not be None"
        assert len(predictions) == len(df), "Predictions should match data length"
        assert len(importance) > 0, "Feature importance should not be empty"
        assert 'train_mae' in metrics, "Training metrics missing"
        assert 'test_mae' in metrics, "Test metrics missing"
        assert 'train_r2' in metrics, "R2 metrics missing"
        
        logger.info("✅ All basic tests passed!")
        return True


def test_model_trainer_random_forest():
    """Test ModelTrainer with Random Forest"""
    logger.info("=" * 60)
    logger.info("Testing ModelTrainer - Random Forest")
    logger.info("=" * 60)
    
    from src.models.trainer import ModelTrainer
    
    config = {
        'model_type': 'random_forest',
        'hyperparameters': {
            'n_estimators': 10,
            'max_depth': 4,
            'random_state': 42,
            'n_jobs': -1,
        },
        'date_col': 'date',
        'target_col': 'quantity',
        'distributed': False,
        'save_model': False,
        'mlflow_tracking_uri': 'sqlite:///:memory:',
        'experiment_name': 'verification_test_rf'
    }
    
    df, y = create_sample_data(100)
    
    with patch('mlflow.set_experiment'), patch('mlflow.start_run'), \
         patch('mlflow.log_params'), patch('mlflow.log_metric'), patch('mlflow.log_param'):
        
        logger.info("📋 Initializing Random Forest trainer...")
        trainer = ModelTrainer(config)
        
        logger.info("📊 Training Random Forest...")
        metrics = trainer.train(df, y)
        
        logger.info("✅ Training completed!")
        logger.info(f"📈 Metrics: {metrics}")
        
        # Test prediction
        predictions = trainer.predict(df)
        
        # Assertions
        assert trainer.model is not None
        assert len(predictions) == len(df)
        assert 'train_mae' in metrics
        assert 'test_mae' in metrics
        
        logger.info("✅ Random Forest tests passed!")
        return True


def test_model_trainer_save_load():
    """Test ModelTrainer save and load functionality"""
    logger.info("=" * 60)
    logger.info("Testing ModelTrainer - Save and Load")
    logger.info("=" * 60)
    
    from src.models.trainer import ModelTrainer
    
    config = {
        'model_type': 'xgboost',
        'hyperparameters': {
            'n_estimators': 10,
            'max_depth': 3,
            'learning_rate': 0.1,
            'random_state': 42,
        },
        'date_col': 'date',
        'target_col': 'quantity',
        'distributed': False,
        'save_model': True,
        'mlflow_tracking_uri': 'sqlite:///:memory:',
        'experiment_name': 'verification_test_save'
    }
    
    df, y = create_sample_data(100)
    
    with patch('mlflow.set_experiment'), patch('mlflow.start_run'), \
         patch('mlflow.log_params'), patch('mlflow.log_metric'), patch('mlflow.log_param'):
        
        # Mock MLflow run_id
        mock_run = MagicMock()
        mock_run.info.run_id = "test_run_id"
        
        with patch('mlflow.start_run') as mock_start_run:
            mock_start_run.return_value.__enter__.return_value = mock_run
            
            logger.info("📋 Training model for save test...")
            trainer = ModelTrainer(config)
            trainer.train(df, y)
            
            # Save to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                run_id = "test_run_id"
                model_path = os.path.join(tmpdir, f"models/{run_id}")
                trainer.config['model_path'] = model_path
                
                logger.info(f"💾 Saving model to {model_path}...")
                trainer._save_model(run_id)
                
                # Verify files exist
                assert os.path.exists(f"{model_path}/model.pkl"), "Model file not saved"
                assert os.path.exists(f"{model_path}/features.json"), "Features file not saved"
                logger.info("✅ Files saved successfully")
                
                # Load model
                logger.info("📂 Loading model...")
                new_trainer = ModelTrainer(config)
                new_trainer.load_model(model_path)
                
                # Verify loaded model works
                assert new_trainer.model is not None
                assert new_trainer.feature_columns == trainer.feature_columns
                
                # Test predictions match
                original_predictions = trainer.predict(df)
                loaded_predictions = new_trainer.predict(df)
                np.testing.assert_array_almost_equal(
                    original_predictions,
                    loaded_predictions,
                    decimal=5
                )
                logger.info("✅ Predictions match after load!")
                
        logger.info("✅ Save/Load tests passed!")
        return True


def test_model_trainer_gradient_boosting():
    """Test ModelTrainer with Gradient Boosting"""
    logger.info("=" * 60)
    logger.info("Testing ModelTrainer - Gradient Boosting")
    logger.info("=" * 60)
    
    from src.models.trainer import ModelTrainer
    
    config = {
        'model_type': 'gradient_boosting',
        'hyperparameters': {
            'n_estimators': 10,
            'max_depth': 3,
            'learning_rate': 0.1,
            'random_state': 42,
        },
        'date_col': 'date',
        'target_col': 'quantity',
        'distributed': False,
        'save_model': False,
        'mlflow_tracking_uri': 'sqlite:///:memory:',
        'experiment_name': 'verification_test_gb'
    }
    
    df, y = create_sample_data(100)
    
    with patch('mlflow.set_experiment'), patch('mlflow.start_run'), \
         patch('mlflow.log_params'), patch('mlflow.log_metric'), patch('mlflow.log_param'):
        
        logger.info("📋 Initializing Gradient Boosting trainer...")
        trainer = ModelTrainer(config)
        
        logger.info("📊 Training Gradient Boosting...")
        metrics = trainer.train(df, y)
        
        logger.info("✅ Training completed!")
        logger.info(f"📈 Metrics: {metrics}")
        
        # Test prediction
        predictions = trainer.predict(df)
        
        # Assertions
        assert trainer.model is not None
        assert len(predictions) == len(df)
        assert 'train_mae' in metrics
        assert 'test_mae' in metrics
        
        logger.info("✅ Gradient Boosting tests passed!")
        return True


def test_error_handling():
    """Test ModelTrainer error handling"""
    logger.info("=" * 60)
    logger.info("Testing ModelTrainer - Error Handling")
    logger.info("=" * 60)
    
    from src.models.trainer import ModelTrainer
    
    # Test invalid model type
    config = {
        'model_type': 'invalid_model',
        'hyperparameters': {},
        'date_col': 'date',
        'target_col': 'quantity',
        'mlflow_tracking_uri': 'sqlite:///:memory:',
        'experiment_name': 'error_test'
    }
    
    df, y = create_sample_data(10)
    
    with patch('mlflow.set_experiment'), patch('mlflow.start_run'):
        trainer = ModelTrainer(config)
        
        try:
            trainer.train(df, y)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unsupported model type" in str(e)
            logger.info("✅ Invalid model type caught correctly")
    
    # Test predict without training
    config['model_type'] = 'xgboost'
    with patch('mlflow.set_experiment'), patch('mlflow.start_run'):
        trainer = ModelTrainer(config)
        
        try:
            trainer.predict(df)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Model not trained" in str(e)
            logger.info("✅ Predict without training caught correctly")
    
    logger.info("✅ Error handling tests passed!")
    return True


def main():
    """Run all verification tests"""
    logger.info("=" * 60)
    logger.info("🔍 PRODUCTION-GRADE MODEL TRAINING VERIFICATION")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        ("Basic XGBoost Training", test_model_trainer_basic),
        ("Random Forest Training", test_model_trainer_random_forest),
        ("Gradient Boosting Training", test_model_trainer_gradient_boosting),
        ("Save/Load Functionality", test_model_trainer_save_load),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                logger.info(f"✅ {name}: PASSED")
            else:
                failed += 1
                logger.info(f"❌ {name}: FAILED")
        except Exception as e:
            failed += 1
            logger.info(f"❌ {name}: FAILED with error: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 VERIFICATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Passed: {passed}/{len(tests)}")
    logger.info(f"❌ Failed: {failed}/{len(tests)}")
    logger.info("")
    
    if failed == 0:
        logger.info("🎉 All tests passed! ModelTrainer is production-ready!")
        return 0
    else:
        logger.warning("⚠️ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())