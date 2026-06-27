# """
# Data Sources Layer - Hugging Face Integration
# """

# import asyncio
# from typing import Dict, List, Optional
# from datetime import datetime, timedelta
# import pandas as pd
# import numpy as np
# from datasets import load_dataset, concatenate_datasets, DatasetDict
# from abc import ABC, abstractmethod

# class DataSource(ABC):
#     @abstractmethod
#     async def fetch_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
#         pass

#     @abstractmethod
#     def validate_source(self) -> bool:
#         pass

# class HuggingFaceDemandSource(DataSource):
#     """Fetch demand forecasting datasets from Hugging Face"""

#     def __init__(self, config: Dict):
#         self.config = config
#         self.datasets = {}

#     async def fetch_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
#         """Fetch multiple datasets from Hugging Face"""

#         ## Load M5 Forecasting dataset
#         ## m5_dataset = load_dataset(
#         ##    "m5_forecasting",
#         ##     split="train",
#         ##     streaming=True
#         ## )

#         # Load Fashion Product dataset
#         fashion_dataset = load_dataset(
#             "ashraq/fashion-product-images-small",
#             split="train",
#             streaming=True
#         )

#         # Load Amazon Reviews dataset
#         reviews_dataset = load_dataset(
#             "amazon_reviews_multi",
#             "en",
#             split="train",
#             streaming=True
#         )

#         # Process and combine datasets
#         combined_data = []

#         # Process M5 data (demand forecasting specific)
#         ## async for item in self._process_m5_data(m5_dataset.take(10000)):
#         ##     combined_data.append(item)

#         # Process fashion data (product attributes)
#         async for item in self._process_fashion_data(fashion_dataset.take(5000)):
#             combined_data.append(item)

#         # Process reviews data (sentiment)
#         async for item in self._process_reviews_data(reviews_dataset.take(5000)):
#             combined_data.append(item)

#         df = pd.DataFrame(combined_data)
#         df['timestamp'] = pd.to_datetime(df['timestamp'])
#         df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]

#         return df

#     async def _process_m5_data(self, dataset):
#         """Process M5 forecasting dataset"""
#         for item in dataset:
#             yield {
#                 'source': 'm5_forecasting',
#                 'product_id': item.get('item_id', 'unknown'),
#                 'store_id': item.get('store_id', 'unknown'),
#                 'category': item.get('cat_id', 'unknown'),
#                 'timestamp': item.get('date', datetime.now()),
#                 'units_sold': item.get('demand', 0),
#                 'price': item.get('sell_price', 0),
#                 'promotion': item.get('promo_1', 0),
#                 'event_type': item.get('event_type_1', 'none')
#             }

#     async def _process_fashion_data(self, dataset):
#         """Process fashion product dataset"""
#         for item in dataset:
#             yield {
#                 'source': 'fashion_products',
#                 'product_id': item.get('id', 'unknown'),
#                 'product_name': item.get('productDisplayName', 'unknown'),
#                 'category': item.get('masterCategory', 'unknown'),
#                 'subcategory': item.get('subCategory', 'unknown'),
#                 'price': np.random.uniform(10, 500),
#                 'timestamp': datetime.now(),
#                 'units_sold': np.random.poisson(50)
#             }

#     async def _process_reviews_data(self, dataset):
#         """Process reviews dataset for sentiment"""
#         for item in dataset:
#             yield {
#                 'source': 'amazon_reviews',
#                 'product_id': item.get('product_id', 'unknown'),
#                 'review_text': item.get('review_body', ''),
#                 'rating': item.get('star_rating', 3),
#                 'helpful_votes': item.get('helpful_votes', 0),
#                 'timestamp': item.get('review_date', datetime.now())
#             }

#     def validate_source(self) -> bool:
#         """Validate data source connectivity"""
#         try:
#             test_dataset = load_dataset("amazon_reviews_multi","en", split="train", streaming=True)
#             next(iter(test_dataset.take(1)))
#             ##test_dataset = load_dataset("m5_forecasting", split="train", streaming=True)
#             ##next(iter(test_dataset.take(1)))
            
#             return True
#         except Exception as e:
#             print(f"Data source validation failed: {e}")
#             return False

# class WeatherAPISource(DataSource):
#     """Fetch weather data from API"""

#     def __init__(self, api_key: str):
#         self.api_key = api_key
#         self.base_url = "https://api.openweathermap.org/data/2.5"

#     async def fetch_data(self, location: str) -> pd.DataFrame:
#         async with aiohttp.ClientSession() as session:
#             url = f"{self.base_url}/forecast?q={location}&appid={self.api_key}"
#             async with session.get(url) as response:
#                 data = await response.json()
#                 return self._process_weather_data(data)

#     def validate_source(self) -> bool:
#         return bool(self.api_key)

# class SocialMediaSource(DataSource):
#     """Fetch social media trends"""

#     def __init__(self, bearer_token: str):
#         self.bearer_token = bearer_token
#         self.base_url = "https://api.twitter.com/2"

#     async def fetch_data(self, keywords: List[str]) -> pd.DataFrame:
#         # Twitter API v2 implementation
#         pass

#     def validate_source(self) -> bool:
#         return bool(self.bearer_token)
    



















# """
# Data Sources Layer - Hugging Face Integration
# """

# import logging
# from abc import ABC, abstractmethod
# from datetime import datetime, timedelta
# from typing import Any, Dict, Optional

# import aiohttp
# import numpy as np
# import pandas as pd
# from datasets import load_dataset

# logger = logging.getLogger(__name__)


# # ==========================================================
# # Base Data Source
# # ==========================================================
# class DataSource(ABC):
#     @abstractmethod
#     async def fetch_data(
#         self,
#         start_date: datetime,
#         end_date: datetime,
#     ) -> pd.DataFrame:
#         pass

#     @abstractmethod
#     def validate_source(self) -> bool:
#         pass


# # ==========================================================
# # Hugging Face Demand Source
# # ==========================================================
# class HuggingFaceDemandSource(DataSource):
#     """
#     Generates synthetic demand forecasting data from a
#     Hugging Face product dataset.
#     """

#     def __init__(self, config: Dict[str, Any]) -> None:
#         self.config = config
#         self.max_records = config.get("max_records", 5000)

#     async def fetch_data(
#         self,
#         start_date: datetime,
#         end_date: datetime,
#     ) -> pd.DataFrame:

#         try:
#             dataset = load_dataset(
#                 "ashraq/fashion-product-images-small",
#                 split="train",
#                 streaming=False,
#             )

#             n_records = min(
#                 self.max_records,
#                 len(dataset),
#             )

#             rows = []

#             for item in dataset.select(range(n_records)):
#                 days_ago = int(
#                     np.random.randint(0, 365)
#                 )

#                 timestamp = (
#                     datetime.now()
#                     - timedelta(days=days_ago)
#                 )

#                 rows.append(
#                     {
#                         "source": "fashion_products",
#                         "product_id": str(
#                             item.get("id", "unknown")
#                         ),
#                         "product_name": item.get(
#                             "productDisplayName",
#                             "unknown",
#                         ),
#                         "category": item.get(
#                             "masterCategory",
#                             "unknown",
#                         ),
#                         "subcategory": item.get(
#                             "subCategory",
#                             "unknown",
#                         ),
#                         "store_id": (
#                             f"store_{np.random.randint(1,11)}"
#                         ),
#                         "price": round(
#                             np.random.uniform(10, 500),
#                             2,
#                         ),
#                         "units_sold": int(
#                             np.random.poisson(50)
#                         ),
#                         "promotion": int(
#                             np.random.choice(
#                                 [0, 1],
#                                 p=[0.8, 0.2],
#                             )
#                         ),
#                         "event_type": np.random.choice(
#                             [
#                                 "none",
#                                 "holiday",
#                                 "weekend",
#                                 "sale",
#                             ]
#                         ),
#                         "timestamp": timestamp,
#                     }
#                 )

#             df = pd.DataFrame(rows)

#             if df.empty:
#                 return df

#             df["timestamp"] = pd.to_datetime(
#                 df["timestamp"],
#                 errors="coerce",
#             )

#             df = df.dropna(
#                 subset=["timestamp"]
#             )

#             df = df[
#                 (df["timestamp"] >= start_date)
#                 & (df["timestamp"] <= end_date)
#             ]

#             logger.info(
#                 "Loaded %s records.",
#                 len(df),
#             )

#             return df.reset_index(drop=True)

#         except Exception:
#             logger.exception(
#                 "Failed to fetch data."
#             )
#             return pd.DataFrame()

#     def validate_source(self) -> bool:
#         try:
#             dataset = load_dataset(
#                 "ashraq/fashion-product-images-small",
#                 split="train",
#                 streaming=False,
#             )

#             _ = dataset[0]

#             logger.info(
#                 "Hugging Face validation successful."
#             )

#             return True

#         except Exception:
#             logger.exception(
#                 "Validation failed."
#             )
#             return False


# # ==========================================================
# # Weather API Source
# # ==========================================================
# class WeatherAPISource(DataSource):
#     def __init__(
#         self,
#         api_key: str,
#         location: str = "London",
#     ) -> None:
#         self.api_key = api_key
#         self.location = location
#         self.base_url = (
#             "https://api.openweathermap.org/data/2.5"
#         )
#         self._session: Optional[
#             aiohttp.ClientSession
#         ] = None

#     async def fetch_data(
#         self,
#         start_date: datetime,
#         end_date: datetime,
#     ) -> pd.DataFrame:

#         if not self.api_key:
#             return pd.DataFrame()

#         try:
#             if self._session is None:
#                 self._session = (
#                     aiohttp.ClientSession()
#                 )

#             url = (
#                 f"{self.base_url}/forecast"
#                 f"?q={self.location}"
#                 f"&appid={self.api_key}"
#                 f"&units=metric"
#             )

#             async with self._session.get(
#                 url
#             ) as response:

#                 if response.status != 200:
#                     logger.error(
#                         "Weather API returned %s",
#                         response.status,
#                     )
#                     return pd.DataFrame()

#                 data = (
#                     await response.json()
#                 )

#             df = self._process_weather_data(
#                 data
#             )

#             if df.empty:
#                 return df

#             df["timestamp"] = pd.to_datetime(
#                 df["timestamp"]
#             )

#             df = df[
#                 (df["timestamp"] >= start_date)
#                 & (df["timestamp"] <= end_date)
#             ]

#             return df

#         except Exception:
#             logger.exception(
#                 "Weather fetch failed."
#             )
#             return pd.DataFrame()

#     def _process_weather_data(
#         self,
#         data: Dict[str, Any],
#     ) -> pd.DataFrame:

#         if "list" not in data:
#             return pd.DataFrame()

#         rows = []

#         for item in data["list"]:
#             rows.append(
#                 {
#                     "timestamp": datetime.fromtimestamp(
#                         item["dt"]
#                     ),
#                     "temperature": item["main"][
#                         "temp"
#                     ],
#                     "humidity": item["main"][
#                         "humidity"
#                     ],
#                     "pressure": item["main"][
#                         "pressure"
#                     ],
#                     "wind_speed": item.get(
#                         "wind",
#                         {},
#                     ).get(
#                         "speed",
#                         0,
#                     ),
#                     "weather": item[
#                         "weather"
#                     ][0]["main"],
#                     "location": data.get(
#                         "city",
#                         {},
#                     ).get(
#                         "name",
#                         self.location,
#                     ),
#                 }
#             )

#         return pd.DataFrame(rows)

#     def validate_source(self) -> bool:
#         return bool(self.api_key)

#     async def close(self) -> None:
#         if self._session:
#             await self._session.close()
#             self._session = None


# # ==========================================================
# # Social Media Source Placeholder
# # ==========================================================
# class SocialMediaSource(DataSource):
#     def __init__(
#         self,
#         bearer_token: str,
#     ) -> None:
#         self.bearer_token = bearer_token

#     async def fetch_data(
#         self,
#         start_date: datetime,
#         end_date: datetime,
#     ) -> pd.DataFrame:
#         raise NotImplementedError(
#             "SocialMediaSource is not implemented."
#         )

#     def validate_source(self) -> bool:
#         return bool(
#             self.bearer_token
#         )   










"""
Data Sources Layer - Hugging Face Integration
"""

import logging
import platform
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Generator

import aiohttp
import numpy as np
import pandas as pd
from datasets import load_dataset

logger = logging.getLogger(__name__)


# ==========================================================
# Helper: Check if running on Windows
# ==========================================================
def is_windows() -> bool:
    """Check if running on Windows OS."""
    return platform.system() == "Windows"


def should_use_streaming() -> bool:
    """
    Determine if streaming should be used.
    Returns False on Windows to avoid DLL issues.
    """
    # Disable streaming on Windows
    if is_windows():
        return False
    
    # Also disable if torch import fails
    try:
        import torch
        return True
    except ImportError:
        return False
    except OSError:
        return False


# ==========================================================
# Base Data Source
# ==========================================================
class DataSource(ABC):
    @abstractmethod
    async def fetch_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def validate_source(self) -> bool:
        pass


# ==========================================================
# Hugging Face Demand Source
# ==========================================================
class HuggingFaceDemandSource(DataSource):
    """
    Fetch demand forecasting datasets from Hugging Face.
    Automatically handles Windows compatibility.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.max_records = config.get("max_records", 5000)
        # ✅ Auto-detect if streaming should be used
        self.use_streaming = config.get(
            "use_streaming",
            should_use_streaming()
        )
        logger.info(
            "HuggingFaceDemandSource initialized: streaming=%s, max_records=%s",
            self.use_streaming,
            self.max_records,
        )

    async def fetch_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        Fetch multiple datasets from Hugging Face.
        Uses streaming on Linux/Mac, falls back to eager loading on Windows.
        """
        try:
            combined_data = []

            if self.use_streaming:
                # ✅ Streaming mode (Linux/Mac)
                logger.info("Using streaming mode for datasets")
                
                fashion_dataset = load_dataset(
                    "ashraq/fashion-product-images-small",
                    split="train",
                    streaming=True,
                )

                reviews_dataset = load_dataset(
                    "imdb",
                    split="train",
                    streaming=True,
                )

                # Process fashion data (streaming) - ✅ use async for
                count = 0
                async for item in self._process_fashion_data_async(
                    fashion_dataset.take(self.max_records)
                ):
                    combined_data.append(item)
                    count += 1
                    if count >= self.max_records:
                        break

                # Process reviews data (streaming) - ✅ use async for
                count = 0
                async for item in self._process_reviews_data_async(
                    reviews_dataset.take(self.max_records)
                ):
                    combined_data.append(item)
                    count += 1
                    if count >= self.max_records:
                        break

            else:
                # ✅ Eager loading mode (Windows fallback)
                logger.info("Using eager loading mode (Windows fallback)")
                
                # Load limited records directly
                fashion_dataset = load_dataset(
                    "ashraq/fashion-product-images-small",
                    split=f"train[:{self.max_records}]",
                )

                reviews_dataset = load_dataset(
                    "imdb",
                    split=f"train[:{self.max_records}]",
                )

                # Process fashion data (eager) - ✅ use regular for loop
                for item in self._process_fashion_data_sync(fashion_dataset):
                    combined_data.append(item)

                # Process reviews data (eager) - ✅ use regular for loop
                for item in self._process_reviews_data_sync(reviews_dataset):
                    combined_data.append(item)

            if not combined_data:
                logger.warning("No data fetched from Hugging Face")
                return pd.DataFrame()

            df = pd.DataFrame(combined_data)

            df["timestamp"] = pd.to_datetime(
                df["timestamp"],
                errors="coerce",
            )

            df = df.dropna(subset=["timestamp"])

            df = df[
                (df["timestamp"] >= start_date)
                & (df["timestamp"] <= end_date)
            ]

            logger.info("Loaded %s records from Hugging Face.", len(df))
            return df.reset_index(drop=True)

        except Exception as e:
            logger.exception("Failed to fetch Hugging Face data: %s", e)
            return pd.DataFrame()

    # ✅ Async version for streaming mode
    async def _process_fashion_data_async(self, dataset):
        """Process fashion product dataset (async/streaming)."""
        for item in dataset:
            days_ago = int(np.random.randint(0, 365))
            timestamp = datetime.now() - timedelta(days=days_ago)

            yield {
                "source": "fashion_products",
                "product_id": str(item.get("id", "unknown")),
                "product_name": item.get("productDisplayName", "unknown"),
                "category": item.get("masterCategory", "unknown"),
                "subcategory": item.get("subCategory", "unknown"),
                "store_id": f"store_{np.random.randint(1, 11)}",
                "price": round(np.random.uniform(10, 500), 2),
                "units_sold": int(np.random.poisson(50)),
                "promotion": int(np.random.choice([0, 1], p=[0.8, 0.2])),
                "event_type": np.random.choice(
                    ["none", "holiday", "weekend", "sale"]
                ),
                "timestamp": timestamp,
            }

    # ✅ Sync version for eager loading mode
    def _process_fashion_data_sync(self, dataset):
        """Process fashion product dataset (sync/eager)."""
        for item in dataset:
            days_ago = int(np.random.randint(0, 365))
            timestamp = datetime.now() - timedelta(days=days_ago)

            yield {
                "source": "fashion_products",
                "product_id": str(item.get("id", "unknown")),
                "product_name": item.get("productDisplayName", "unknown"),
                "category": item.get("masterCategory", "unknown"),
                "subcategory": item.get("subCategory", "unknown"),
                "store_id": f"store_{np.random.randint(1, 11)}",
                "price": round(np.random.uniform(10, 500), 2),
                "units_sold": int(np.random.poisson(50)),
                "promotion": int(np.random.choice([0, 1], p=[0.8, 0.2])),
                "event_type": np.random.choice(
                    ["none", "holiday", "weekend", "sale"]
                ),
                "timestamp": timestamp,
            }

    # ✅ Async version for streaming mode
    async def _process_reviews_data_async(self, dataset):
        """Process IMDB reviews dataset (async/streaming)."""
        for item in dataset:
            days_ago = int(np.random.randint(0, 365))
            timestamp = datetime.now() - timedelta(days=days_ago)

            yield {
                "source": "imdb_reviews",
                "product_id": f"movie_{np.random.randint(1, 10000)}",
                "review_text": item.get("text", ""),
                "sentiment": item.get("label", 0),  # 0=negative, 1=positive
                "helpful_votes": int(np.random.poisson(5)),
                "timestamp": timestamp,
            }

    # ✅ Sync version for eager loading mode
    def _process_reviews_data_sync(self, dataset):
        """Process IMDB reviews dataset (sync/eager)."""
        for item in dataset:
            days_ago = int(np.random.randint(0, 365))
            timestamp = datetime.now() - timedelta(days=days_ago)

            yield {
                "source": "imdb_reviews",
                "product_id": f"movie_{np.random.randint(1, 10000)}",
                "review_text": item.get("text", ""),
                "sentiment": item.get("label", 0),  # 0=negative, 1=positive
                "helpful_votes": int(np.random.poisson(5)),
                "timestamp": timestamp,
            }

    def validate_source(self) -> bool:
        """
        Validate data source connectivity.
        Handles Windows DLL issues gracefully.
        """
        try:
            if self.use_streaming:
                # Try streaming validation
                test_dataset = load_dataset(
                    "imdb",
                    split="train",
                    streaming=True,
                )
                next(iter(test_dataset.take(1)))
                logger.info("Hugging Face source validation successful (streaming).")
                return True
            else:
                # Try eager loading validation (Windows fallback)
                test_dataset = load_dataset(
                    "imdb",
                    split="train[:1]",
                )
                _ = test_dataset[0]
                logger.info("Hugging Face source validation successful (eager).")
                return True

        except OSError as e:
            if "WinError 1114" in str(e) or "c10.dll" in str(e):
                logger.warning(
                    "Windows DLL issue detected. Attempting fallback validation."
                )
                try:
                    # Fallback: Try without streaming
                    fallback_dataset = load_dataset(
                        "imdb",
                        split="train[:1]",
                    )
                    _ = fallback_dataset[0]
                    logger.info("Validation successful via fallback method.")
                    return True
                except Exception as fallback_error:
                    logger.exception("Fallback validation failed: %s", fallback_error)
                    return False
            logger.exception("Validation failed: %s", e)
            return False

        except Exception as e:
            logger.exception("Validation failed: %s", e)
            return False


# ==========================================================
# Weather API Source
# ==========================================================
class WeatherAPISource(DataSource):
    """Fetch weather data from OpenWeather API."""

    def __init__(
        self,
        api_key: str,
        location: str = "London",
    ) -> None:
        self.api_key = api_key
        self.location = location
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self._session: Optional[aiohttp.ClientSession] = None

    async def fetch_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Fetch weather data with date filtering."""
        
        if not self.api_key:
            logger.warning("No API key provided for Weather API")
            return pd.DataFrame()

        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()

            url = (
                f"{self.base_url}/forecast"
                f"?q={self.location}"
                f"&appid={self.api_key}"
                f"&units=metric"
            )

            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.error(
                        "Weather API returned status %s",
                        response.status,
                    )
                    return pd.DataFrame()

                data = await response.json()

            df = self._process_weather_data(data)

            if df.empty:
                return df

            df["timestamp"] = pd.to_datetime(df["timestamp"])

            df = df[
                (df["timestamp"] >= start_date)
                & (df["timestamp"] <= end_date)
            ]

            logger.info("Fetched %s weather records.", len(df))
            return df

        except aiohttp.ClientError as e:
            logger.exception("Network error fetching weather: %s", e)
            return pd.DataFrame()
        except Exception as e:
            logger.exception("Weather fetch failed: %s", e)
            return pd.DataFrame()

    def _process_weather_data(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Process OpenWeather API response into DataFrame."""
        if "list" not in data:
            return pd.DataFrame()

        rows = []
        for item in data["list"]:
            rows.append({
                "timestamp": datetime.fromtimestamp(item["dt"]),
                "temperature": item["main"]["temp"],
                "feels_like": item["main"].get("feels_like", 0),
                "humidity": item["main"]["humidity"],
                "pressure": item["main"]["pressure"],
                "wind_speed": item.get("wind", {}).get("speed", 0),
                "weather_main": item["weather"][0]["main"],
                "weather_description": item["weather"][0]["description"],
                "clouds": item.get("clouds", {}).get("all", 0),
                "rain": item.get("rain", {}).get("3h", 0),
                "location": data.get("city", {}).get("name", self.location),
            })

        return pd.DataFrame(rows)

    def validate_source(self) -> bool:
        """Validate API key."""
        return bool(self.api_key)

    async def close(self) -> None:
        """Clean up HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None


# ==========================================================
# Social Media Source
# ==========================================================
class SocialMediaSource(DataSource):
    """Fetch social media trends (placeholder)."""

    def __init__(self, bearer_token: str) -> None:
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"

    async def fetch_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Not implemented yet."""
        raise NotImplementedError(
            "SocialMediaSource is not implemented yet."
        )

    def validate_source(self) -> bool:
        """Validate bearer token."""
        return bool(self.bearer_token)


# ==========================================================
# Example Usage
# ==========================================================
async def main():
    """Example usage of data sources."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("\n" + "=" * 60)
    print(f"Testing Hugging Face Source on {platform.system()}")
    print(f"Streaming mode: {should_use_streaming()}")
    print("=" * 60)

    config = {"max_records": 100}
    hf_source = HuggingFaceDemandSource(config)

    if hf_source.validate_source():
        now = datetime.now()
        df = await hf_source.fetch_data(
            start_date=now - timedelta(days=30),
            end_date=now,
        )
        print(f"✅ Fetched {len(df)} records")
        print(f"✅ DataFrame shape: {df.shape}")
        print(f"✅ Columns: {df.columns.tolist()}")
        if not df.empty:
            print("\n📊 First 5 rows:")
            print(df.head())
    else:
        print("❌ Validation failed")

    print("\n" + "=" * 60)
    print("✅ Test completed")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())