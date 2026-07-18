#!/usr/bin/env python
"""
Verify Data Validation Module - Standalone script
"""

import sys
import tempfile
import pandas as pd
from src.data.validators import (
    ValidationResult,
    SchemaValidator,
    QualityValidator,
    DataValidator,
    ResultsStore
)


def verify_schema_validator():
    """Verify SchemaValidator"""
    print("\n📋 Testing SchemaValidator...")
    
    df = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"]
    })
    schema = {"col1": "int64", "col2": "object"}
    
    validator = SchemaValidator()
    result = validator.validate(df, schema)
    
    assert result.success is True
    assert len(result.errors) == 0
    print("✅ SchemaValidator works!")


def verify_quality_validator():
    """Verify QualityValidator"""
    print("\n📋 Testing QualityValidator...")
    
    df = pd.DataFrame({
        "col1": [1, 2, 3, 4, 5],
        "col2": [1.0, 2.0, 3.0, 4.0, 5.0]
    })
    
    validator = QualityValidator()
    result = validator.validate(df)
    
    assert result.success is True
    assert "row_count" in result.metadata
    assert result.metadata["row_count"] == 5
    print("✅ QualityValidator works!")


def verify_data_validator():
    """Verify DataValidator"""
    print("\n📋 Testing DataValidator...")
    
    config = {
        "schema": {"col1": "int64", "col2": "object"},
        "quality_thresholds": {"null_threshold": 0.05}
    }
    
    validator = DataValidator(config)
    df = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"]
    })
    
    result = validator.validate(df, "test_stage")
    
    assert result.success is True
    assert result.stage == "test_stage"
    assert len(result.errors) == 0
    print("✅ DataValidator works!")


def verify_results_store():
    """Verify ResultsStore"""
    print("\n📋 Testing ResultsStore...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ResultsStore(tmpdir)
        
        result = ValidationResult(
            success=True,
            stage="test_stage",
            errors=[],
            warnings=["warning1"],
            metadata={"key": "value"}
        )
        
        store.store(result)
        results = store.get_results(limit=10)
        
        assert len(results) == 1
        assert results[0].stage == "test_stage"
        print("✅ ResultsStore works!")


def main():
    """Main verification function"""
    print("=" * 60)
    print("🔍 VERIFYING DATA VALIDATION MODULE")
    print("=" * 60)
    
    try:
        verify_schema_validator()
        verify_quality_validator()
        verify_data_validator()
        verify_results_store()
        
        print("\n" + "=" * 60)
        print("✅ ALL VALIDATION VERIFICATIONS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)