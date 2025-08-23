"""
Database access layer for backtesting
Handles all database operations for backtest runs, results, and metrics
"""
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
import asyncio
import json
from contextlib import asynccontextmanager

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update, delete, and_, or_, desc, asc, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .config import config
from .schemas import (
    BacktestStatus, BacktestRunDB, BacktestResultDB, BacktestMetrics,
    BacktestResult, PredictionSnapshot
)

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

class BacktestDataAccess:
    """Data access layer for backtesting operations"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or config.database_url
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session with proper cleanup"""
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # Backtest Run Operations
    async def create_backtest_run(
        self,
        horizon_months: int,
        sample_size: int,
        markets_filter: Optional[List[str]] = None,
        asset_types_filter: Optional[List[str]] = None,
        scenario_label: Optional[str] = None,
        scenario_params: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> uuid.UUID:
        """Create a new backtest run"""
        run_id = uuid.uuid4()
        
        async with self.get_session() as session:
            query = """
                INSERT INTO backtest_runs (
                    id, status, horizon_months, sample_size, 
                    markets_filter, asset_types_filter, scenario_label, 
                    scenario_params, notes, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            await session.execute(query, (
                run_id,
                BacktestStatus.PENDING.value,
                horizon_months,
                sample_size,
                json.dumps(markets_filter) if markets_filter else None,
                json.dumps(asset_types_filter) if asset_types_filter else None,
                scenario_label,
                json.dumps(scenario_params) if scenario_params else None,
                notes,
                datetime.utcnow()
            ))
            
        return run_id
    
    async def update_backtest_run_status(
        self,
        run_id: uuid.UUID,
        status: BacktestStatus,
        total_properties: Optional[int] = None,
        processed_properties: Optional[int] = None,
        failed_properties: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update backtest run status and progress"""
        async with self.get_session() as session:
            updates = {"status": status.value}
            
            if status == BacktestStatus.RUNNING and total_properties is not None:
                updates["started_at"] = datetime.utcnow()
                updates["total_properties"] = total_properties
            elif status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED, BacktestStatus.CANCELLED]:
                updates["ended_at"] = datetime.utcnow()
            
            if processed_properties is not None:
                updates["processed_properties"] = processed_properties
            if failed_properties is not None:
                updates["failed_properties"] = failed_properties
            if error_message:
                updates["error_message"] = error_message
            
            set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
            query = f"UPDATE backtest_runs SET {set_clause} WHERE id = $1"
            
            result = await session.execute(query, (run_id, *updates.values()))
            return result.rowcount > 0
    
    async def get_backtest_run(self, run_id: uuid.UUID) -> Optional[BacktestRunDB]:
        """Get backtest run by ID"""
        async with self.get_session() as session:
            query = """
                SELECT id, started_at, ended_at, status, horizon_months, sample_size,
                       markets_filter, asset_types_filter, scenario_label, scenario_params,
                       notes, total_properties, processed_properties, failed_properties,
                       created_at
                FROM backtest_runs WHERE id = $1
            """
            
            result = await session.fetchrow(query, run_id)
            if not result:
                return None
            
            return BacktestRunDB(
                id=result['id'],
                started_at=result['started_at'],
                ended_at=result['ended_at'],
                status=BacktestStatus(result['status']),
                horizon_months=result['horizon_months'],
                sample_size=result['sample_size'],
                markets_filter=json.loads(result['markets_filter']) if result['markets_filter'] else None,
                asset_types_filter=json.loads(result['asset_types_filter']) if result['asset_types_filter'] else None,
                scenario_label=result['scenario_label'],
                scenario_params=json.loads(result['scenario_params']) if result['scenario_params'] else None,
                notes=result['notes'],
                total_properties=result['total_properties'],
                processed_properties=result['processed_properties'],
                failed_properties=result['failed_properties'],
                created_at=result['created_at']
            )
    
    async def list_backtest_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[BacktestStatus] = None
    ) -> List[BacktestRunDB]:
        """List backtest runs with pagination"""
        async with self.get_session() as session:
            where_clause = f"WHERE status = ${len([limit, offset])+1}" if status_filter else ""
            params = [limit, offset]
            if status_filter:
                params.append(status_filter.value)
            
            query = f"""
                SELECT id, started_at, ended_at, status, horizon_months, sample_size,
                       markets_filter, asset_types_filter, scenario_label, scenario_params,
                       notes, total_properties, processed_properties, failed_properties,
                       created_at
                FROM backtest_runs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            
            results = await session.fetch(query, *params)
            return [
                BacktestRunDB(
                    id=row['id'],
                    started_at=row['started_at'],
                    ended_at=row['ended_at'],
                    status=BacktestStatus(row['status']),
                    horizon_months=row['horizon_months'],
                    sample_size=row['sample_size'],
                    markets_filter=json.loads(row['markets_filter']) if row['markets_filter'] else None,
                    asset_types_filter=json.loads(row['asset_types_filter']) if row['asset_types_filter'] else None,
                    scenario_label=row['scenario_label'],
                    scenario_params=json.loads(row['scenario_params']) if row['scenario_params'] else None,
                    notes=row['notes'],
                    total_properties=row['total_properties'],
                    processed_properties=row['processed_properties'],
                    failed_properties=row['failed_properties'],
                    created_at=row['created_at']
                )
                for row in results
            ]
    
    # Backtest Results Operations
    async def bulk_insert_backtest_results(
        self, 
        results: List[BacktestResult]
    ) -> int:
        """Bulk insert backtest results for performance"""
        if not results:
            return 0
        
        async with self.get_session() as session:
            query = """
                INSERT INTO backtest_results (
                    id, run_id, asof_date, property_id, market, asset_type,
                    y_true_noi, y_pred_noi, noi_mape, y_true_caprate_bps,
                    y_pred_caprate_bps, caprate_mae_bps, arbitrage_score,
                    decile_rank, confidence, interval_lower, interval_upper,
                    model_name, model_version, training_data_cutoff,
                    data_sources, feature_fingerprint, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 
                         $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
            """
            
            # Prepare batch data
            batch_data = []
            for result in results:
                batch_data.append((
                    result.id or uuid.uuid4(),
                    result.run_id,
                    result.asof_date,
                    result.property_id,
                    result.market,
                    result.asset_type,
                    result.y_true_noi,
                    result.y_pred_noi,
                    result.noi_mape,
                    result.y_true_caprate_bps,
                    result.y_pred_caprate_bps,
                    result.caprate_mae_bps,
                    result.arbitrage_score,
                    result.decile_rank,
                    result.confidence,
                    result.interval_lower,
                    result.interval_upper,
                    result.model_name,
                    result.model_version,
                    result.training_data_cutoff,
                    json.dumps(result.data_sources),
                    result.feature_fingerprint,
                    result.created_at or datetime.utcnow()
                ))
            
            await session.executemany(query, batch_data)
            return len(batch_data)
    
    async def get_backtest_results(
        self,
        run_id: uuid.UUID,
        limit: int = 1000,
        offset: int = 0,
        market_filter: Optional[str] = None,
        asset_type_filter: Optional[str] = None
    ) -> List[BacktestResultDB]:
        """Get paginated backtest results"""
        async with self.get_session() as session:
            conditions = ["run_id = $1"]
            params = [run_id, limit, offset]
            param_idx = 4
            
            if market_filter:
                conditions.append(f"market = ${param_idx}")
                params.append(market_filter)
                param_idx += 1
            
            if asset_type_filter:
                conditions.append(f"asset_type = ${param_idx}")
                params.append(asset_type_filter)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT * FROM backtest_results
                WHERE {where_clause}
                ORDER BY asof_date, property_id
                LIMIT $2 OFFSET $3
            """
            
            results = await session.fetch(query, *params)
            return [
                BacktestResultDB(
                    id=row['id'],
                    run_id=row['run_id'],
                    asof_date=row['asof_date'],
                    property_id=row['property_id'],
                    market=row['market'],
                    asset_type=row['asset_type'],
                    y_true_noi=row['y_true_noi'],
                    y_pred_noi=row['y_pred_noi'],
                    noi_mape=row['noi_mape'],
                    y_true_caprate_bps=row['y_true_caprate_bps'],
                    y_pred_caprate_bps=row['y_pred_caprate_bps'],
                    caprate_mae_bps=row['caprate_mae_bps'],
                    arbitrage_score=row['arbitrage_score'],
                    decile_rank=row['decile_rank'],
                    confidence=row['confidence'],
                    interval_lower=row['interval_lower'],
                    interval_upper=row['interval_upper'],
                    model_name=row['model_name'],
                    model_version=row['model_version'],
                    training_data_cutoff=row['training_data_cutoff'],
                    data_sources=json.loads(row['data_sources']),
                    feature_fingerprint=row['feature_fingerprint'],
                    created_at=row['created_at']
                )
                for row in results
            ]
    
    # Metrics Operations
    async def store_metrics_summary(
        self,
        run_id: uuid.UUID,
        metrics: BacktestMetrics
    ) -> bool:
        """Store computed metrics summary"""
        async with self.get_session() as session:
            query = """
                INSERT INTO metrics_summary (id, run_id, json_blob, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (run_id) DO UPDATE SET
                    json_blob = EXCLUDED.json_blob,
                    created_at = EXCLUDED.created_at
            """
            
            await session.execute(query, (
                uuid.uuid4(),
                run_id,
                json.dumps(metrics.dict()),
                datetime.utcnow()
            ))
            
            return True
    
    async def get_metrics_summary(self, run_id: uuid.UUID) -> Optional[BacktestMetrics]:
        """Get stored metrics summary"""
        async with self.get_session() as session:
            query = "SELECT json_blob FROM metrics_summary WHERE run_id = $1"
            result = await session.fetchrow(query, run_id)
            
            if not result:
                return None
            
            return BacktestMetrics(**json.loads(result['json_blob']))
    
    # Prediction Snapshots (Audit Trail)
    async def store_prediction_snapshot(
        self,
        asof_date: date,
        property_id: str,
        feature_fingerprint: str,
        payload: Dict[str, Any]
    ) -> uuid.UUID:
        """Store prediction snapshot for audit trail"""
        snapshot_id = uuid.uuid4()
        
        async with self.get_session() as session:
            query = """
                INSERT INTO prediction_snapshots 
                (id, asof_date, property_id, feature_fingerprint, payload_jsonb, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """
            
            await session.execute(query, (
                snapshot_id,
                asof_date,
                property_id,
                feature_fingerprint,
                json.dumps(payload),
                datetime.utcnow()
            ))
        
        return snapshot_id
    
    # Utility methods
    async def cleanup_old_runs(self, days_old: int = 90) -> int:
        """Clean up old backtest runs and results"""
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days_old)
        
        async with self.get_session() as session:
            # Get runs to delete
            query = "SELECT id FROM backtest_runs WHERE created_at < $1"
            old_runs = await session.fetch(query, cutoff_date)
            run_ids = [row['id'] for row in old_runs]
            
            if not run_ids:
                return 0
            
            # Delete in order due to foreign keys
            await session.execute(
                f"DELETE FROM backtest_results WHERE run_id = ANY($1::uuid[])",
                run_ids
            )
            await session.execute(
                f"DELETE FROM metrics_summary WHERE run_id = ANY($1::uuid[])",
                run_ids
            )
            await session.execute(
                f"DELETE FROM backtest_runs WHERE id = ANY($1::uuid[])",
                run_ids
            )
            
            return len(run_ids)
    
    async def get_run_statistics(self) -> Dict[str, Any]:
        """Get overall backtest system statistics"""
        async with self.get_session() as session:
            query = """
                SELECT 
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_runs,
                    COUNT(*) FILTER (WHERE status = 'running') as running_runs,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
                    AVG(processed_properties) FILTER (WHERE status = 'completed') as avg_properties,
                    MAX(created_at) as last_run_date
                FROM backtest_runs
            """
            
            result = await session.fetchrow(query)
            
            # Get total results count
            results_query = "SELECT COUNT(*) as total_results FROM backtest_results"
            results_result = await session.fetchrow(results_query)
            
            return {
                "total_runs": result['total_runs'] or 0,
                "completed_runs": result['completed_runs'] or 0,
                "running_runs": result['running_runs'] or 0,
                "failed_runs": result['failed_runs'] or 0,
                "avg_properties_per_run": float(result['avg_properties']) if result['avg_properties'] else 0,
                "last_run_date": result['last_run_date'],
                "total_predictions": results_result['total_results'] or 0
            }

# Global instance
data_access = BacktestDataAccess()
