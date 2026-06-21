"""
Ingestion Layer - Kafka Streaming
"""

import asyncio
import json
from kafka import KafkaProducer, KafkaConsumer
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaIngestionLayer:
    """Complete Kafka-based data ingestion"""

    def __init__(self, bootstrap_servers: List[str] = ['localhost:9092']):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumers = {}
        self.topics = {
            'sales': 'demand.sales.raw',
            'inventory': 'demand.inventory.raw',
            'weather': 'demand.weather.raw',
            'social': 'demand.social.raw',
            'reviews': 'demand.reviews.raw'
        }

    async def initialize(self):
        """Initialize Kafka producers and consumers"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            compression_type='gzip',
            acks='all',
            retries=3
        )
        await self.producer.start()
        logger.info("✅ Kafka producer started")

        # Create consumers for each topic
        for name, topic in self.topics.items():
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=f"{name}-consumer-group",
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            await consumer.start()
            self.consumers[name] = consumer
            logger.info(f"✅ Consumer started for {topic}")

    async def ingest_batch(self, topic: str, data: List[Dict]):
        """Ingest batch data into Kafka"""
        for record in data:
            await self.producer.send(topic, value=record)
        await self.producer.flush()
        logger.info(f"✅ Ingested {len(data)} records to {topic}")

    async def ingest_stream(self, topic: str, data_stream):
        """Ingest streaming data"""
        async for record in data_stream:
            await self.producer.send(topic, value=record)
            logger.debug(f"Streamed record to {topic}")

    async def consume_topic(self, topic_name: str, callback=None):
        """Consume messages from a topic"""
        consumer = self.consumers.get(topic_name)
        if not consumer:
            raise ValueError(f"Consumer for {topic_name} not found")

        async for msg in consumer:
            if callback:
                await callback(msg.value)
            else:
                logger.info(f"Received: {msg.value}")

    async def close(self):
        """Close all connections"""
        if self.producer:
            await self.producer.stop()
        for consumer in self.consumers.values():
            await consumer.stop()
        logger.info("✅ All Kafka connections closed")

class SparkStreamingLayer:
    """Spark Streaming for real-time processing"""

    def __init__(self, app_name: str = "DemandStreaming"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.streaming.schemaInference", "true") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

    def read_from_kafka(self, topics: List[str], bootstrap_servers: str):
        """Read streaming data from Kafka"""

        df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", ",".join(topics)) \
            .option("startingOffsets", "latest") \
            .load()

        # Parse JSON
        from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

        schema = StructType([
            StructField("product_id", StringType(), True),
            StructField("store_id", StringType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("units_sold", IntegerType(), True),
            StructField("price", DoubleType(), True),
            StructField("discount", DoubleType(), True),
            StructField("inventory_level", IntegerType(), True)
        ])

        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")

        return parsed_df

    def process_stream(self, df, watermark="10 minutes"):
        """Process streaming data with aggregations"""

        # Windowed aggregations
        from pyspark.sql.functions import window, sum, avg, count

        result_df = df \
            .withWatermark("timestamp", watermark) \
            .groupBy(
                window(col("timestamp"), "1 hour"),
                col("product_id"),
                col("store_id")
            ) \
            .agg(
                sum("units_sold").alias("total_sales"),
                avg("price").alias("avg_price"),
                count("*").alias("transaction_count")
            )

        return result_df

    def write_to_sink(self, df, output_mode="append", checkpoint_location="/tmp/checkpoints"):
        """Write streaming results to sink"""

        query = df.writeStream \
            .outputMode(output_mode) \
            .format("parquet") \
            .option("path", "s3a://demand-data-lake/processed/") \
            .option("checkpointLocation", checkpoint_location) \
            .partitionBy("product_id", "store_id") \
            .trigger(processingTime="5 minutes") \
            .start()

        return query

    def start_streaming_pipeline(self, bootstrap_servers: str, topics: List[str]):
        """Start complete streaming pipeline"""

        stream_df = self.read_from_kafka(topics, bootstrap_servers)
        processed_df = self.process_stream(stream_df)
        query = self.write_to_sink(processed_df)

        return query