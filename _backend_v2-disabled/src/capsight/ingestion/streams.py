"""
Data ingestion layer for CapSight - streams financial markets, CRE data, and alternative signals
Handles real-time streaming (Kafka) and batch ETL processes
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..core.config import settings, KAFKA_TOPICS
from ..core.utils import logger, METRICS, TimestampedData, Circuit, retry_with_backoff

# Mock imports (will resolve when requirements are installed)
try:
    from kafka import KafkaProducer, KafkaConsumer
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    import aiohttp
    import pandas as pd
except ImportError:
    pass


@dataclass
class MarketDataPoint:
    """Standardized market data point"""
    symbol: str
    value: float
    timestamp: datetime
    source: str
    data_type: str  # 'treasury', 'credit', 'equity', 'commodity'
    metadata: Dict[str, Any]


class DataSource(ABC):
    """Abstract base class for all data sources"""
    
    def __init__(self, source_name: str, update_frequency_seconds: int = 60):
        self.source_name = source_name
        self.update_frequency = update_frequency_seconds
        self.last_update = None
        self.circuit = Circuit(failure_threshold=3, recovery_timeout=300)
    
    @abstractmethod
    async def fetch_data(self) -> List[MarketDataPoint]:
        """Fetch data from the source"""
        pass
    
    async def is_stale(self) -> bool:
        """Check if data source is stale based on SLA"""
        if not self.last_update:
            return True
        age = (datetime.now(timezone.utc) - self.last_update).total_seconds()
        return age > self.update_frequency * 2


class TreasuryRateSource(DataSource):
    """FRED Treasury rates ingestion"""
    
    def __init__(self):
        super().__init__("fred_treasury", update_frequency_seconds=300)  # 5 min
        self.fred_series = {
            "DGS10": "treasury_10y_rate",
            "DGS2": "treasury_2y_rate", 
            "DGS30": "treasury_30y_rate",
            "DGS5": "treasury_5y_rate",
            "DFF": "fed_funds_rate"
        }
    
    @retry_with_backoff(max_retries=3)
    async def fetch_data(self) -> List[MarketDataPoint]:
        """Fetch Treasury rates from FRED API"""
        data_points = []
        
        try:
            # Mock FRED API call (replace with actual fredapi client)
            async with aiohttp.ClientSession() as session:
                for fred_code, capsight_name in self.fred_series.items():
                    url = f"https://api.stlouisfed.org/fred/series/observations"
                    params = {
                        "series_id": fred_code,
                        "api_key": settings.fred_api_key,
                        "file_type": "json",
                        "limit": 1,
                        "sort_order": "desc"
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            json_data = await response.json()
                            observations = json_data.get("observations", [])
                            
                            if observations:
                                latest = observations[0]
                                value = float(latest["value"]) if latest["value"] != "." else None
                                
                                if value is not None:
                                    data_points.append(MarketDataPoint(
                                        symbol=capsight_name,
                                        value=value,
                                        timestamp=datetime.fromisoformat(latest["date"]).replace(tzinfo=timezone.utc),
                                        source="fred",
                                        data_type="treasury",
                                        metadata={"fred_series_id": fred_code}
                                    ))
        
        except Exception as e:
            logger.error("Failed to fetch Treasury data", error=str(e), source=self.source_name)
            METRICS["data_ingestion_rate"].labels(source="fred", status="error").inc()
            raise
        
        self.last_update = datetime.now(timezone.utc)
        METRICS["data_ingestion_rate"].labels(source="fred", status="success").inc(len(data_points))
        return data_points


class CreditSpreadSource(DataSource):
    """Corporate and mortgage credit spreads"""
    
    def __init__(self):
        super().__init__("credit_spreads", update_frequency_seconds=900)  # 15 min
        self.spread_symbols = [
            "BAMLH0A0HYM2",  # High Yield Master II OAS
            "BAMLC0A4CBBB",  # BBB Corp OAS  
            "BAMLH0A1HYBB",  # High Yield BB OAS
            "MORTGAGE30US"   # 30Y Fixed Mortgage
        ]
    
    async def fetch_data(self) -> List[MarketDataPoint]:
        """Fetch credit spreads from FRED"""
        # Similar implementation to Treasury rates
        data_points = []
        
        # Mock implementation - replace with actual API calls
        mock_spreads = {
            "investment_grade_spread": 1.25,
            "high_yield_spread": 4.85,
            "mbs_spread": 0.75,
            "cmbs_aaa_spread": 1.15
        }
        
        now = datetime.now(timezone.utc)
        for symbol, spread in mock_spreads.items():
            data_points.append(MarketDataPoint(
                symbol=symbol,
                value=spread,
                timestamp=now,
                source="fred",
                data_type="credit",
                metadata={}
            ))
        
        self.last_update = now
        return data_points


class REITDataSource(DataSource):
    """Public REIT data for implied cap rates"""
    
    def __init__(self):
        super().__init__("reit_data", update_frequency_seconds=3600)  # 1 hour
        self.reit_symbols = [
            "PLD",   # Industrial 
            "AMT",   # Towers
            "CCI",   # Towers
            "EQIX",  # Data Centers
            "SPG",   # Retail
            "AVB",   # Residential
            "EXR",   # Self Storage
            "O"      # Net Lease
        ]
    
    async def fetch_data(self) -> List[MarketDataPoint]:
        """Fetch REIT pricing and fundamentals"""
        data_points = []
        
        # Mock REIT data - replace with yfinance or Bloomberg
        mock_reit_data = {
            "PLD": {"price": 145.32, "dividend_yield": 0.028, "nav_premium": 0.15},
            "AMT": {"price": 189.47, "dividend_yield": 0.032, "nav_premium": 0.08},
            "EQIX": {"price": 785.23, "dividend_yield": 0.019, "nav_premium": 0.22}
        }
        
        now = datetime.now(timezone.utc)
        for symbol, data in mock_reit_data.items():
            # Calculate implied cap rate (dividend yield adjusted for NAV premium)
            implied_caprate = data["dividend_yield"] / (1 + data["nav_premium"])
            
            data_points.append(MarketDataPoint(
                symbol=f"{symbol}_implied_caprate",
                value=implied_caprate,
                timestamp=now,
                source="reit_analysis",
                data_type="equity", 
                metadata={
                    "reit_symbol": symbol,
                    "price": data["price"],
                    "dividend_yield": data["dividend_yield"],
                    "nav_premium": data["nav_premium"]
                }
            ))
        
        self.last_update = now
        return data_points


class MobilityDataSource(DataSource):
    """Foot traffic and mobility signals"""
    
    def __init__(self):
        super().__init__("mobility", update_frequency_seconds=21600)  # 6 hours
    
    async def fetch_data(self) -> List[MarketDataPoint]:
        """Fetch mobility data from SafeGraph or similar"""
        data_points = []
        
        # Mock mobility data
        mock_mobility = {
            "retail_foot_traffic_index": 95.2,
            "office_occupancy_rate": 0.67,
            "transit_usage_index": 88.1
        }
        
        now = datetime.now(timezone.utc)
        for metric, value in mock_mobility.items():
            data_points.append(MarketDataPoint(
                symbol=metric,
                value=value,
                timestamp=now,
                source="safegraph",
                data_type="mobility",
                metadata={}
            ))
        
        self.last_update = now
        return data_points


class StreamingIngestionService:
    """Main streaming ingestion orchestrator"""
    
    def __init__(self):
        self.sources = [
            TreasuryRateSource(),
            CreditSpreadSource(),
            REITDataSource(),
            MobilityDataSource()
        ]
        self.producer = None
        self.running = False
    
    async def start(self):
        """Start all data ingestion streams"""
        logger.info("Starting streaming ingestion service")
        
        # Initialize Kafka producer
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode()
            )
            await self.producer.start()
        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            # Fallback to file-based queue
            self.producer = None
        
        self.running = True
        
        # Start ingestion tasks for each source
        tasks = []
        for source in self.sources:
            task = asyncio.create_task(self._run_source_ingestion(source))
            tasks.append(task)
        
        # Start health monitoring task
        health_task = asyncio.create_task(self._monitor_data_freshness())
        tasks.append(health_task)
        
        logger.info("All ingestion streams started", source_count=len(self.sources))
        
        # Wait for all tasks
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """Stop ingestion service"""
        self.running = False
        if self.producer:
            await self.producer.stop()
        logger.info("Streaming ingestion service stopped")
    
    async def _run_source_ingestion(self, source: DataSource):
        """Run continuous ingestion for a single source"""
        while self.running:
            try:
                # Fetch data from source
                data_points = await source.fetch_data()
                
                # Stream to Kafka
                for point in data_points:
                    await self._stream_data_point(point)
                
                logger.debug("Ingested data", 
                           source=source.source_name, 
                           point_count=len(data_points))
                
            except Exception as e:
                logger.error("Source ingestion failed", 
                           source=source.source_name, 
                           error=str(e))
                METRICS["data_ingestion_rate"].labels(
                    source=source.source_name, 
                    status="error"
                ).inc()
            
            # Wait for next update
            await asyncio.sleep(source.update_frequency)
    
    async def _stream_data_point(self, point: MarketDataPoint):
        """Stream individual data point to appropriate Kafka topic"""
        
        # Determine topic based on data type
        topic_mapping = {
            "treasury": KAFKA_TOPICS["treasury_rates"],
            "credit": KAFKA_TOPICS["mbs_spreads"],  
            "equity": KAFKA_TOPICS["reit_data"],
            "mobility": KAFKA_TOPICS["mobility_data"]
        }
        
        topic = topic_mapping.get(point.data_type)
        if not topic:
            logger.warn("Unknown data type", data_type=point.data_type)
            return
        
        # Prepare message
        message = {
            "symbol": point.symbol,
            "value": point.value,
            "timestamp": point.timestamp.isoformat(),
            "source": point.source,
            "data_type": point.data_type,
            "metadata": point.metadata
        }
        
        try:
            if self.producer:
                await self.producer.send(topic, message)
            else:
                # Fallback: write to local queue file
                await self._write_to_local_queue(topic, message)
                
            METRICS["data_ingestion_rate"].labels(
                source=point.source, 
                status="success"
            ).inc()
            
        except Exception as e:
            logger.error("Failed to stream data point", 
                        symbol=point.symbol, 
                        error=str(e))
            raise
    
    async def _write_to_local_queue(self, topic: str, message: Dict[str, Any]):
        """Fallback: write to local file queue when Kafka unavailable"""
        import os
        queue_dir = "data_queue"
        os.makedirs(queue_dir, exist_ok=True)
        
        filename = f"{queue_dir}/{topic}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(filename, "a") as f:
            f.write(json.dumps(message) + "\n")
    
    async def _monitor_data_freshness(self):
        """Monitor data freshness and alert on SLA violations"""
        while self.running:
            for source in self.sources:
                if await source.is_stale():
                    logger.warning("Data source is stale", 
                                 source=source.source_name,
                                 last_update=source.last_update)
                    
                    # Update freshness metric  
                    if source.last_update:
                        age = (datetime.now(timezone.utc) - source.last_update).total_seconds()
                        METRICS["data_freshness_seconds"].labels(source=source.source_name).set(age)
            
            await asyncio.sleep(60)  # Check every minute


class BatchETLService:
    """Batch ETL for historical data backfill and daily aggregations"""
    
    def __init__(self):
        self.batch_size = 1000
    
    async def backfill_treasury_data(self, start_date: datetime, end_date: datetime):
        """Backfill historical Treasury rates"""
        logger.info("Starting Treasury data backfill", 
                   start=start_date.isoformat(), 
                   end=end_date.isoformat())
        
        # Mock backfill implementation
        current = start_date
        batch = []
        
        while current <= end_date:
            # Mock historical data point
            data_point = MarketDataPoint(
                symbol="treasury_10y_rate",
                value=4.5 + (current.timestamp() % 100) / 1000,  # Mock variation
                timestamp=current,
                source="fred_historical",
                data_type="treasury",
                metadata={"backfill": True}
            )
            
            batch.append(data_point)
            
            if len(batch) >= self.batch_size:
                await self._process_batch(batch)
                batch = []
            
            current += timedelta(days=1)
        
        # Process remaining batch
        if batch:
            await self._process_batch(batch)
        
        logger.info("Treasury data backfill completed")
    
    async def _process_batch(self, batch: List[MarketDataPoint]):
        """Process batch of data points"""
        # Stream to appropriate topics
        ingestion_service = StreamingIngestionService()
        for point in batch:
            await ingestion_service._stream_data_point(point)


# Export main services
__all__ = [
    "StreamingIngestionService",
    "BatchETLService", 
    "MarketDataPoint",
    "DataSource"
]
