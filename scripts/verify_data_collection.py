#!/usr/bin/env python
"""
Verify Data Collection Module - Standalone script
"""

import sys
import asyncio
import tempfile
from datetime import datetime, timedelta
from src.data.collectors import (
    CollectorConfig,
    CheckpointManager,
    SalesAPICollector,
    DataCollectionOrchestrator
)


async def verify_checkpoint_manager():
    """Verify CheckpointManager"""
    print("\n📋 Testing CheckpointManager...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(tmpdir, "test_collector")
        
        # Test save/load
        manager._checkpoints["last_processed"] = datetime.now().isoformat()
        manager._checkpoints["processed_ids"] = ["id1", "id2"]
        manager.save()
        
        # Test load
        new_manager = CheckpointManager(tmpdir, "test_collector")
        assert new_manager._checkpoints["processed_ids"] == ["id1", "id2"]
        
        # Test mark_processed
        manager.mark_processed("id3")
        assert manager.is_processed("id3") is True
        
        print("✅ CheckpointManager works!")


async def verify_collector_config():
    """Verify CollectorConfig"""
    print("\n📋 Testing CollectorConfig...")
    
    config = CollectorConfig(
        name="test_collector",
        source_type="api",
        config={"base_url": "https://api.example.com"}
    )
    
    assert config.name == "test_collector"
    assert config.source_type == "api"
    assert config.config["base_url"] == "https://api.example.com"
    
    print("✅ CollectorConfig works!")


async def verify_orchestrator():
    """Verify DataCollectionOrchestrator"""
    print("\n📋 Testing DataCollectionOrchestrator...")
    
    config = {
        "sources": [
            {
                "name": "api_source",
                "type": "api",
                "base_url": "https://api.example.com",
                "api_key": "test_key"
            }
        ]
    }
    
    orchestrator = DataCollectionOrchestrator(config)
    assert len(orchestrator.collectors) == 1
    assert orchestrator.collectors[0].config.name == "api_source"
    
    print("✅ DataCollectionOrchestrator works!")


async def main():
    """Main verification function"""
    print("=" * 60)
    print("🔍 VERIFYING DATA COLLECTION MODULE")
    print("=" * 60)
    
    try:
        await verify_collector_config()
        await verify_checkpoint_manager()
        await verify_orchestrator()
        
        print("\n" + "=" * 60)
        print("✅ ALL DATA COLLECTION VERIFICATIONS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)