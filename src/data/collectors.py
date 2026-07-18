# """
# Data Collection - Multi-source with retries
# """

# import asyncio
# import json
# import logging
# import os
# from collections.abc import AsyncIterator
# from dataclasses import dataclass
# from datetime import datetime, timedelta
# from typing import Any

# import aiohttp
# import pandas as pd
# import structlog
# from tenacity import (
#     before_sleep_log,
#     retry,
#     retry_if_exception_type,
#     stop_after_attempt,
#     wait_exponential,
# )

# logger = structlog.get_logger()


# @dataclass
# class CollectorConfig:
#     name: str
#     source_type: str
#     config: dict[str, Any]
#     checkpoint_dir: str = "/tmp/checkpoints"
#     batch_size: int = 10000
#     retry_attempts: int = 3
#     timeout_seconds: int = 30


# class CheckpointManager:
#     def __init__(self, checkpoint_dir: str, collector_name: str):
#         self.checkpoint_dir = checkpoint_dir
#         self.collector_name = collector_name
#         self.checkpoint_file = f"{checkpoint_dir}/{collector_name}.json"
#         os.makedirs(checkpoint_dir, exist_ok=True)
#         self._checkpoints = self._load()

#     def _load(self) -> dict[str, Any]:
#         try:
#             with open(self.checkpoint_file) as f:
#                 return json.load(f)
#         except (FileNotFoundError, json.JSONDecodeError):
#             return {"last_processed": None, "processed_ids": [], "state": {}}

#     def save(self):
#         with open(self.checkpoint_file, "w") as f:
#             json.dump(self._checkpoints, f, default=str)

#     def get_last_processed(self) -> datetime | None:
#         if self._checkpoints.get("last_processed"):
#             try:
#                 return datetime.fromisoformat(self._checkpoints["last_processed"])
#             except (ValueError, TypeError):
#                 return None
#         return None

#     def update_last_processed(self, timestamp: datetime):
#         self._checkpoints["last_processed"] = timestamp.isoformat()
#         self.save()

#     def mark_processed(self, record_id: str):
#         if record_id not in self._checkpoints["processed_ids"]:
#             self._checkpoints["processed_ids"].append(record_id)
#             if len(self._checkpoints["processed_ids"]) > 100000:
#                 self._checkpoints["processed_ids"] = self._checkpoints["processed_ids"][-50000:]
#             self.save()

#     def is_processed(self, record_id: str) -> bool:
#         return record_id in self._checkpoints["processed_ids"]


# class BaseCollector:
#     def __init__(self, config: CollectorConfig):
#         self.config = config
#         self.checkpoint = CheckpointManager(config.checkpoint_dir, config.name)
#         self._session: Optional[aiohttp.ClientSession] = None

#     async def get_session(self) -> aiohttp.ClientSession:
#         if self._session is None:
#             timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
#             self._session = aiohttp.ClientSession(timeout=timeout)
#         return self._session

#     async def close(self):
#         if self._session:
#             await self._session.close()
#             self._session: Optional[aiohttp.ClientSession] = None

#     @retry(
#         stop=stop_after_attempt(3),
#         wait=wait_exponential(multiplier=1, min=2, max=30),
#         retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
#         before_sleep=before_sleep_log(logger, logging.WARNING),
#     )
#     async def fetch_json(self, url: str, **kwargs) -> dict[str, Any]:
#         session = await self.get_session()
#         async with session.get(url, **kwargs) as response:
#             response.raise_for_status()
#             return await response.json()


# class SalesAPICollector(BaseCollector):
#     async def collect(
#         self, start_date: datetime | None = None, end_date: datetime | None = None
#     ) -> AsyncIterator[pd.DataFrame]:
#         cfg = self.config.config
#         base_url = cfg.get("base_url")
#         api_key = cfg.get("api_key")
#         endpoint = cfg.get("endpoint", "/sales")
#         page_size = cfg.get("page_size", 1000)

#         if start_date is None:
#             start_date = self.checkpoint.get_last_processed() or datetime.now() - timedelta(days=7)
#         if end_date is None:
#             end_date = datetime.now()

#         headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

#         page = 0
#         has_more = True

#         while has_more:
#             params = {
#                 "start_date": start_date.strftime("%Y-%m-%d"),
#                 "end_date": end_date.strftime("%Y-%m-%d"),
#                 "limit": page_size,
#                 "offset": page * page_size,
#             }

#             try:
#                 data = await self.fetch_json(
#                     f"{base_url}{endpoint}", headers=headers, params=params
#                 )
#                 records = data.get("data", [])

#                 if records:
#                     df = pd.DataFrame(records)
#                     for col in ["date", "timestamp", "created_at"]:
#                         if col in df.columns:
#                             df[col] = pd.to_datetime(df[col])

#                     if "id" in df.columns:
#                         df = df[~df["id"].apply(self.checkpoint.is_processed)]

#                     if not df.empty:
#                         if "date" in df.columns:
#                             self.checkpoint.update_last_processed(df["date"].max())
#                         if "id" in df.columns:
#                             for record_id in df["id"]:
#                                 self.checkpoint.mark_processed(str(record_id))
#                         yield df

#                 has_more = data.get("has_more", False)
#                 page += 1

#             except Exception as e:
#                 logger.error(f"Collection error for {self.config.name}: {e}")
#                 break


# class KafkaCollector(BaseCollector):
#     def setup_consumer(self):
#         from confluent_kafka import Consumer

#         cfg = self.config.config
#         consumer_config = {
#             "bootstrap.servers": cfg.get("bootstrap_servers", "localhost:9092"),
#             "group.id": cfg.get("group_id", f"demand-forecasting-{self.config.name}"),
#             "auto.offset.reset": "earliest",
#             "enable.auto.commit": False,
#             "max.poll.interval.ms": 300000,
#             "session.timeout.ms": 45000,
#         }
#         self.consumer = Consumer(consumer_config)
#         self.consumer.subscribe([cfg.get("topic")])

#     async def collect(self) -> AsyncIterator[pd.DataFrame]:
#         self.setup_consumer()
#         try:
#             while True:
#                 messages = self.consumer.consume(num_messages=self.config.batch_size, timeout=1.0)
#                 if not messages:
#                     await asyncio.sleep(0.1)
#                     continue

#                 records = []
#                 for msg in messages:
#                     try:
#                         record = json.loads(msg.value().decode("utf-8"))
#                         record["_partition"] = msg.partition()
#                         record["_offset"] = msg.offset()
#                         records.append(record)
#                     except json.JSONDecodeError:
#                         continue

#                 if records:
#                     df = pd.DataFrame(records)
#                     yield df
#                     self.consumer.store_offsets()
#                     self.consumer.commit()

#         except Exception as e:
#             logger.error(f"Kafka consumer error: {e}")
#             raise
#         finally:
#             if self.consumer:
#                 self.consumer.close()


# class HuggingFaceCollector(BaseCollector):
#     async def collect(self, dataset_name: str, split: str = "train") -> AsyncIterator[pd.DataFrame]:
#         try:
#             from datasets import load_dataset

#             dataset = load_dataset(dataset_name, split=split, streaming=True)
#             batch = []
#             for item in dataset:
#                 batch.append(item)
#                 if len(batch) >= self.config.batch_size:
#                     df = pd.DataFrame(batch)
#                     yield df
#                     batch = []
#             if batch:
#                 yield pd.DataFrame(batch)
#         except Exception as e:
#             logger.error(f"Hugging Face error: {e}")
#             raise


# class S3Collector(BaseCollector):
#     async def collect(self, bucket: str, prefix: str) -> AsyncIterator[pd.DataFrame]:
#         import boto3

#         s3_client = boto3.client("s3")
#         objects = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
#         processed_files = set(self.checkpoint._checkpoints.get("processed_files", []))

#         for obj in objects.get("Contents", []):
#             key = obj["Key"]
#             if key in processed_files or not key.endswith(".parquet"):
#                 continue

#             try:
#                 response = s3_client.get_object(Bucket=bucket, Key=key)
#                 df = pd.read_parquet(response["Body"])
#                 df["_source_file"] = key
#                 df["_ingestion_timestamp"] = datetime.now()
#                 yield df

#                 processed_files.add(key)
#                 self.checkpoint._checkpoints["processed_files"] = list(processed_files)
#                 self.checkpoint.save()

#             except Exception as e:
#                 logger.error(f"S3 error for {key}: {e}")


# class DataCollectionOrchestrator:
#     def __init__(self, config: dict[str, Any]):
#         self.config = config
#         self.collectors: List[BaseCollector] = []
#         self._init_collectors()

#     def _init_collectors(self):
#         for source_config in self.config.get("sources", []):
#             collector_config = CollectorConfig(
#                 name=source_config.get("name"),
#                 source_type=source_config.get("type"),
#                 config=source_config,
#                 checkpoint_dir=self.config.get("checkpoint_dir", "/tmp/checkpoints"),
#                 batch_size=self.config.get("batch_size", 10000),
#             )

#             if source_config.get("type") == "api":
#                 self.collectors.append(SalesAPICollector(collector_config))
#             elif source_config.get("type") == "kafka":
#                 self.collectors.append(KafkaCollector(collector_config))
#             elif source_config.get("type") == "huggingface":
#                 self.collectors.append(HuggingFaceCollector(collector_config))
#             elif source_config.get("type") == "s3":
#                 self.collectors.append(S3Collector(collector_config))

#     async def collect_all(self) -> AsyncIterator[pd.DataFrame]:
#         for collector in self.collectors:
#             try:
#                 if isinstance(collector, (SalesAPICollector, KafkaCollector)):
#                     async for df in collector.collect():
#                         yield df
#                 elif isinstance(collector, HuggingFaceCollector):
#                     async for df in collector.collect(
#                         dataset_name=self.config.get("huggingface_dataset"),
#                         split=self.config.get("split", "train"),
#                     ):
#                         yield df
#                 elif isinstance(collector, S3Collector):
#                     async for df in collector.collect(
#                         bucket=self.config.get("s3_bucket"), prefix=self.config.get("s3_prefix")
#                     ):
#                         yield df
#             except Exception as e:
#                 logger.error(f"Error collecting from {collector.config.name}: {e}")


# """
# Data Collection - Multi-source with retries
# """

# import asyncio
# import json
# import logging
# import os
# from collections.abc import AsyncIterator
# from dataclasses import dataclass
# from datetime import datetime, timedelta
# from typing import Any, Optional, List

# import aiohttp
# import pandas as pd
# import structlog
# from tenacity import (
#     before_sleep_log,
#     retry,
#     retry_if_exception_type,
#     stop_after_attempt,
#     wait_exponential,
# )

# logger = structlog.get_logger()


# @dataclass
# class CollectorConfig:
#     name: str
#     source_type: str
#     config: dict[str, Any]
#     checkpoint_dir: str = "/tmp/checkpoints"
#     batch_size: int = 10000
#     retry_attempts: int = 3
#     timeout_seconds: int = 30


# class CheckpointManager:
#     def __init__(self, checkpoint_dir: str, collector_name: str) -> None:
#         self.checkpoint_dir = checkpoint_dir
#         self.collector_name = collector_name
#         self.checkpoint_file = f"{checkpoint_dir}/{collector_name}.json"
#         os.makedirs(checkpoint_dir, exist_ok=True)
#         self._checkpoints = self._load()

#     def _load(self) -> dict[str, Any]:
#         try:
#             with open(self.checkpoint_file) as f:
#                 return json.load(f)  # type: ignore[no-any-return]
#         except (FileNotFoundError, json.JSONDecodeError):
#             return {"last_processed": None, "processed_ids": [], "state": {}}

#     def save(self) -> None:
#         with open(self.checkpoint_file, "w") as f:
#             json.dump(self._checkpoints, f, default=str)

#     def get_last_processed(self) -> datetime | None:
#         if self._checkpoints.get("last_processed"):
#             try:
#                 return datetime.fromisoformat(self._checkpoints["last_processed"])
#             except (ValueError, TypeError):
#                 return None
#         return None

#     def update_last_processed(self, timestamp: datetime) -> None:
#         self._checkpoints["last_processed"] = timestamp.isoformat()
#         self.save()

#     def mark_processed(self, record_id: str) -> None:
#         if record_id not in self._checkpoints["processed_ids"]:
#             self._checkpoints["processed_ids"].append(record_id)
#             if len(self._checkpoints["processed_ids"]) > 100000:
#                 self._checkpoints["processed_ids"] = self._checkpoints["processed_ids"][-50000:]
#             self.save()

#     def is_processed(self, record_id: str) -> bool:
#         return record_id in self._checkpoints["processed_ids"]


# class BaseCollector:
#     def __init__(self, config: CollectorConfig) -> None:
#         self.config = config
#         self.checkpoint = CheckpointManager(config.checkpoint_dir, config.name)
#         self._session: Optional[aiohttp.ClientSession] = None

#     async def get_session(self) -> Optional[aiohttp.ClientSession]:
#         if self._session is None:
#             timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
#             self._session = aiohttp.ClientSession(timeout=timeout)
#         return self._session

#     async def close(self) -> None:
#         if self._session:
#             await self._session.close()
#             self._session = None

#     @retry(
#         stop=stop_after_attempt(3),
#         wait=wait_exponential(multiplier=1, min=2, max=30),
#         retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
#         before_sleep=before_sleep_log(logger, logging.WARNING),
#     )
#     async def fetch_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
#         session = await self.get_session()
#         if session is None:
#             raise RuntimeError("HTTP session not initialized")
#         async with session.get(url, **kwargs) as response:
#             response.raise_for_status()
#             return await response.json()  # type: ignore[no-any-return]


# class SalesAPICollector(BaseCollector):
#     async def collect(
#         self, start_date: datetime | None = None, end_date: datetime | None = None
#     ) -> AsyncIterator[pd.DataFrame]:
#         cfg = self.config.config
#         base_url: str = cfg.get("base_url", "")
#         api_key: Optional[str] = cfg.get("api_key")
#         endpoint: str = cfg.get("endpoint", "/sales")
#         page_size: int = cfg.get("page_size", 1000)

#         if start_date is None:
#             start_date = self.checkpoint.get_last_processed() or datetime.now() - timedelta(days=7)
#         if end_date is None:
#             end_date = datetime.now()

#         headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

#         page = 0
#         has_more = True

#         while has_more:
#             params = {
#                 "start_date": start_date.strftime("%Y-%m-%d"),
#                 "end_date": end_date.strftime("%Y-%m-%d"),
#                 "limit": page_size,
#                 "offset": page * page_size,
#             }

#             try:
#                 data = await self.fetch_json(
#                     f"{base_url}{endpoint}", headers=headers, params=params
#                 )
#                 records = data.get("data", [])

#                 if records:
#                     df = pd.DataFrame(records)
#                     for col in ["date", "timestamp", "created_at"]:
#                         if col in df.columns:
#                             df[col] = pd.to_datetime(df[col])

#                     if "id" in df.columns:
#                         df = df[~df["id"].apply(self.checkpoint.is_processed)]

#                     if not df.empty:
#                         if "date" in df.columns:
#                             self.checkpoint.update_last_processed(df["date"].max())
#                         if "id" in df.columns:
#                             for record_id in df["id"]:
#                                 self.checkpoint.mark_processed(str(record_id))
#                         yield df

#                 has_more = data.get("has_more", False)
#                 page += 1

#             except Exception as e:
#                 logger.error(f"Collection error for {self.config.name}: {e}")
#                 break


# class KafkaCollector(BaseCollector):
#     def __init__(self, config: CollectorConfig) -> None:
#         super().__init__(config)
#         self.consumer = None

#     def setup_consumer(self) -> None:
#         from confluent_kafka import Consumer

#         cfg = self.config.config
#         consumer_config = {
#             "bootstrap.servers": cfg.get("bootstrap_servers", "localhost:9092"),
#             "group.id": cfg.get("group_id", f"demand-forecasting-{self.config.name}"),
#             "auto.offset.reset": "earliest",
#             "enable.auto.commit": False,
#             "max.poll.interval.ms": 300000,
#             "session.timeout.ms": 45000,
#         }
#         self.consumer = Consumer(consumer_config)
#         topic: str = cfg.get("topic", "")
#         self.consumer.subscribe([topic])

#     async def collect(self) -> AsyncIterator[pd.DataFrame]:
#         self.setup_consumer()
#         try:
#             while True:
#                 if self.consumer is None:
#                     raise RuntimeError("Kafka consumer not initialized")
#                 messages = self.consumer.consume(num_messages=self.config.batch_size, timeout=1.0)
#                 if not messages:
#                     await asyncio.sleep(0.1)
#                     continue

#                 records = []
#                 for msg in messages:
#                     try:
#                         value = msg.value()
#                         if value is not None:
#                             record = json.loads(value.decode("utf-8"))
#                             record["_partition"] = msg.partition()
#                             record["_offset"] = msg.offset()
#                             records.append(record)
#                     except (json.JSONDecodeError, AttributeError):
#                         continue

#                 if records:
#                     df = pd.DataFrame(records)
#                     yield df
#                     if self.consumer is not None:
#                         self.consumer.store_offsets()
#                         self.consumer.commit()

#         except Exception as e:
#             logger.error(f"Kafka consumer error: {e}")
#             raise
#         finally:
#             if self.consumer:
#                 self.consumer.close()


# class HuggingFaceCollector(BaseCollector):
#     async def collect(self, dataset_name: str, split: str = "train") -> AsyncIterator[pd.DataFrame]:
#         try:
#             from datasets import load_dataset

#             dataset = load_dataset(dataset_name, split=split, streaming=True)
#             batch = []
#             for item in dataset:
#                 batch.append(item)
#                 if len(batch) >= self.config.batch_size:
#                     df = pd.DataFrame(batch)
#                     yield df
#                     batch = []
#             if batch:
#                 yield pd.DataFrame(batch)
#         except Exception as e:
#             logger.error(f"Hugging Face error: {e}")
#             raise


# class S3Collector(BaseCollector):
#     async def collect(self, bucket: str, prefix: str) -> AsyncIterator[pd.DataFrame]:
#         import boto3

#         s3_client = boto3.client("s3")
#         objects = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
#         processed_files = set(self.checkpoint._checkpoints.get("processed_files", []))

#         for obj in objects.get("Contents", []):
#             key = obj["Key"]
#             if key in processed_files or not key.endswith(".parquet"):
#                 continue

#             try:
#                 response = s3_client.get_object(Bucket=bucket, Key=key)
#                 df = pd.read_parquet(response["Body"])
#                 df["_source_file"] = key
#                 df["_ingestion_timestamp"] = datetime.now()
#                 yield df

#                 processed_files.add(key)
#                 self.checkpoint._checkpoints["processed_files"] = list(processed_files)
#                 self.checkpoint.save()

#             except Exception as e:
#                 logger.error(f"S3 error for {key}: {e}")


# class DataCollectionOrchestrator:
#     def __init__(self, config: dict[str, Any]) -> None:
#         self.config = config
#         self.collectors: List[BaseCollector] = []
#         self._init_collectors()

#     def _init_collectors(self) -> None:
#         for source_config in self.config.get("sources", []):
#             collector_config = CollectorConfig(
#                 name=source_config.get("name", ""),
#                 source_type=source_config.get("type", ""),
#                 config=source_config,
#                 checkpoint_dir=self.config.get("checkpoint_dir", "/tmp/checkpoints"),
#                 batch_size=self.config.get("batch_size", 10000),
#             )

#             source_type = source_config.get("type", "")
#             if source_type == "api":
#                 self.collectors.append(SalesAPICollector(collector_config))
#             elif source_type == "kafka":
#                 self.collectors.append(KafkaCollector(collector_config))
#             elif source_type == "huggingface":
#                 self.collectors.append(HuggingFaceCollector(collector_config))
#             elif source_type == "s3":
#                 self.collectors.append(S3Collector(collector_config))

#     async def collect_all(self) -> AsyncIterator[pd.DataFrame]:
#         for collector in self.collectors:
#             try:
#                 if isinstance(collector, (SalesAPICollector, KafkaCollector)):
#                     async for df in collector.collect():
#                         yield df
#                 elif isinstance(collector, HuggingFaceCollector):
#                     huggingface_dataset: str = self.config.get("huggingface_dataset", "")
#                     split: str = self.config.get("split", "train")
#                     async for df in collector.collect(
#                         dataset_name=huggingface_dataset,
#                         split=split,
#                     ):
#                         yield df
#                 elif isinstance(collector, S3Collector):
#                     s3_bucket: str = self.config.get("s3_bucket", "")
#                     s3_prefix: str = self.config.get("s3_prefix", "")
#                     async for df in collector.collect(
#                         bucket=s3_bucket,
#                         prefix=s3_prefix,
#                     ):
#                         yield df
#             except Exception as e:
#                 logger.error(f"Error collecting from {collector.config.name}: {e}")


"""
Data Collection - Multi-source with retries
"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import pandas as pd
import structlog
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()


@dataclass
class CollectorConfig:
    name: str
    source_type: str
    config: dict[str, Any]
    checkpoint_dir: str = "/tmp/checkpoints"
    batch_size: int = 10000
    retry_attempts: int = 3
    timeout_seconds: int = 30


class CheckpointManager:
    def __init__(self, checkpoint_dir: str, collector_name: str) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.collector_name = collector_name
        self.checkpoint_file = f"{checkpoint_dir}/{collector_name}.json"
        os.makedirs(checkpoint_dir, exist_ok=True)
        self._checkpoints = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.checkpoint_file) as f:
                return json.load(f)  # type: ignore[no-any-return]
        except (FileNotFoundError, json.JSONDecodeError):
            return {"last_processed": None, "processed_ids": [], "state": {}}

    def save(self) -> None:
        with open(self.checkpoint_file, "w") as f:
            json.dump(self._checkpoints, f, default=str)

    def get_last_processed(self) -> datetime | None:
        if self._checkpoints.get("last_processed"):
            try:
                return datetime.fromisoformat(self._checkpoints["last_processed"])
            except (ValueError, TypeError):
                return None
        return None

    def update_last_processed(self, timestamp: datetime) -> None:
        self._checkpoints["last_processed"] = timestamp.isoformat()
        self.save()

    def mark_processed(self, record_id: str) -> None:
        if record_id not in self._checkpoints["processed_ids"]:
            self._checkpoints["processed_ids"].append(record_id)
            if len(self._checkpoints["processed_ids"]) > 100000:
                self._checkpoints["processed_ids"] = self._checkpoints["processed_ids"][-50000:]
            self.save()

    def is_processed(self, record_id: str) -> bool:
        return record_id in self._checkpoints["processed_ids"]


class BaseCollector:
    def __init__(self, config: CollectorConfig) -> None:
        self.config = config
        self.checkpoint = CheckpointManager(config.checkpoint_dir, config.name)
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession | None:
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def fetch_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        session = await self.get_session()
        if session is None:
            raise RuntimeError("HTTP session not initialized")
        async with session.get(url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()  # type: ignore[no-any-return]


class SalesAPICollector(BaseCollector):
    async def collect(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> AsyncIterator[pd.DataFrame]:
        cfg = self.config.config
        base_url: str = cfg.get("base_url", "")
        api_key: str | None = cfg.get("api_key")
        endpoint: str = cfg.get("endpoint", "/sales")
        page_size: int = cfg.get("page_size", 1000)

        if start_date is None:
            start_date = self.checkpoint.get_last_processed() or datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        page = 0
        has_more = True

        while has_more:
            params = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "limit": page_size,
                "offset": page * page_size,
            }

            try:
                data = await self.fetch_json(
                    f"{base_url}{endpoint}", headers=headers, params=params
                )
                records = data.get("data", [])

                if records:
                    df = pd.DataFrame(records)
                    for col in ["date", "timestamp", "created_at"]:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col])

                    if "id" in df.columns:
                        df = df[~df["id"].apply(self.checkpoint.is_processed)]

                    if not df.empty:
                        if "date" in df.columns:
                            self.checkpoint.update_last_processed(df["date"].max())
                        if "id" in df.columns:
                            for record_id in df["id"]:
                                self.checkpoint.mark_processed(str(record_id))
                        yield df

                has_more = data.get("has_more", False)
                page += 1

            except Exception as e:
                logger.error(f"Collection error for {self.config.name}: {e}")
                break


class KafkaCollector(BaseCollector):
    def __init__(self, config: CollectorConfig) -> None:
        super().__init__(config)
        self.consumer: Any | None = None

    def setup_consumer(self) -> None:
        # Import inside method to avoid hard dependency
        try:
            from confluent_kafka import Consumer  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("confluent_kafka not installed, Kafka collector unavailable")
            return

        cfg = self.config.config
        consumer_config = {
            "bootstrap.servers": cfg.get("bootstrap_servers", "localhost:9092"),
            "group.id": cfg.get("group_id", f"demand-forecasting-{self.config.name}"),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 45000,
        }

        # Create consumer and subscribe in one step
        consumer = Consumer(consumer_config)
        topic: str = cfg.get("topic", "")
        consumer.subscribe([topic])
        self.consumer = consumer

    async def collect(self) -> AsyncIterator[pd.DataFrame]:
        self.setup_consumer()

        if self.consumer is None:
            logger.warning("Kafka consumer not initialized, skipping collection")
            return

        try:
            while True:
                messages = self.consumer.consume(num_messages=self.config.batch_size, timeout=1.0)
                if not messages:
                    await asyncio.sleep(0.1)
                    continue

                records = []
                for msg in messages:
                    try:
                        value = msg.value()
                        if value is not None:
                            record = json.loads(value.decode("utf-8"))
                            record["_partition"] = msg.partition()
                            record["_offset"] = msg.offset()
                            records.append(record)
                    except (json.JSONDecodeError, AttributeError):
                        continue

                if records:
                    df = pd.DataFrame(records)
                    yield df
                    if self.consumer is not None:
                        self.consumer.store_offsets()
                        self.consumer.commit()

        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
        finally:
            if self.consumer:
                self.consumer.close()


class HuggingFaceCollector(BaseCollector):
    async def collect(self, dataset_name: str, split: str = "train") -> AsyncIterator[pd.DataFrame]:
        try:
            from datasets import load_dataset  # type: ignore[import-not-found]

            dataset = load_dataset(dataset_name, split=split, streaming=True)
            batch = []
            for item in dataset:
                batch.append(item)
                if len(batch) >= self.config.batch_size:
                    df = pd.DataFrame(batch)
                    yield df
                    batch = []
            if batch:
                yield pd.DataFrame(batch)
        except ImportError:
            logger.warning("datasets library not installed, HuggingFace collector unavailable")
            raise
        except Exception as e:
            logger.error(f"Hugging Face error: {e}")
            raise


class S3Collector(BaseCollector):
    async def collect(self, bucket: str, prefix: str) -> AsyncIterator[pd.DataFrame]:
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("boto3 not installed, S3 collector unavailable")
            return

        s3_client = boto3.client("s3")
        objects = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        processed_files = set(self.checkpoint._checkpoints.get("processed_files", []))

        for obj in objects.get("Contents", []):
            key = obj["Key"]
            if key in processed_files or not key.endswith(".parquet"):
                continue

            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                df = pd.read_parquet(response["Body"])
                df["_source_file"] = key
                df["_ingestion_timestamp"] = datetime.now()
                yield df

                processed_files.add(key)
                self.checkpoint._checkpoints["processed_files"] = list(processed_files)
                self.checkpoint.save()

            except Exception as e:
                logger.error(f"S3 error for {key}: {e}")


class DataCollectionOrchestrator:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.collectors: list[BaseCollector] = []
        self._init_collectors()

    def _init_collectors(self) -> None:
        for source_config in self.config.get("sources", []):
            collector_config = CollectorConfig(
                name=source_config.get("name", ""),
                source_type=source_config.get("type", ""),
                config=source_config,
                checkpoint_dir=self.config.get("checkpoint_dir", "/tmp/checkpoints"),
                batch_size=self.config.get("batch_size", 10000),
            )

            source_type = source_config.get("type", "")
            if source_type == "api":
                self.collectors.append(SalesAPICollector(collector_config))
            elif source_type == "kafka":
                self.collectors.append(KafkaCollector(collector_config))
            elif source_type == "huggingface":
                self.collectors.append(HuggingFaceCollector(collector_config))
            elif source_type == "s3":
                self.collectors.append(S3Collector(collector_config))

    async def collect_all(self) -> AsyncIterator[pd.DataFrame]:
        for collector in self.collectors:
            try:
                if isinstance(collector, (SalesAPICollector, KafkaCollector)):
                    async for df in collector.collect():
                        yield df
                elif isinstance(collector, HuggingFaceCollector):
                    huggingface_dataset: str = self.config.get("huggingface_dataset", "")
                    split: str = self.config.get("split", "train")
                    async for df in collector.collect(
                        dataset_name=huggingface_dataset,
                        split=split,
                    ):
                        yield df
                elif isinstance(collector, S3Collector):
                    s3_bucket: str = self.config.get("s3_bucket", "")
                    s3_prefix: str = self.config.get("s3_prefix", "")
                    async for df in collector.collect(
                        bucket=s3_bucket,
                        prefix=s3_prefix,
                    ):
                        yield df
            except Exception as e:
                logger.error(f"Error collecting from {collector.config.name}: {e}")
