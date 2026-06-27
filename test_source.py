"""
Test script for Hugging Face data source
"""

import asyncio
from datetime import datetime, timedelta
from src.data_sources.huggingface_source import HuggingFaceDemandSource

async def test_500_records():
    """Test loading 500 records"""
    print("\n" + "="*60)
    print("TEST: Loading 500 records")
    print("="*60)
    
    source = HuggingFaceDemandSource({'max_records': 500})
    df = await source.fetch_data(
        datetime.now() - timedelta(days=30),
        datetime.now()
    )
    print(f'✅ Loaded {len(df)} records')
    return df

async def test_data_quality():
    """Test data quality"""
    print("\n" + "="*60)
    print("TEST: Data Quality Check")
    print("="*60)
    
    source = HuggingFaceDemandSource({'max_records': 100})
    df = await source.fetch_data(
        datetime.now() - timedelta(days=30),
        datetime.now()
    )
    
    print(f'Total records: {len(df)}')
    print(f'Unique products: {df["product_id"].nunique()}')
    print(f'Avg price: ${df["price"].mean():.2f}')
    print(f'Total units sold: {df["units_sold"].sum()}')
    print('Sentiment distribution:')
    print(df['sentiment'].value_counts())
    
    return df

async def main():
    """Run all tests"""
    await test_500_records()
    await test_data_quality()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())