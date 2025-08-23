"""
ML Data Access Service
Handles data loading, preprocessing, and persistence for ML pipelines
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...core.database import get_session
from ...models.property import Property
from ...models.forecast import Forecast
from ...models.opportunity import Opportunity
from ..models import PropertyData, MacroData, ForecastResult, ArbitrageScore
from ..config import MLConfig
from ..utils.logging import get_ml_logger
from ..utils.time import to_datetime, date_range

logger = get_ml_logger(__name__)

class MLDataService:
    """Data access service for ML operations"""
    
    def __init__(self, db_session: Session = None):
        self.config = MLConfig()
        self.db = db_session
        logger.info("ML Data Service initialized")
    
    def get_session(self) -> Session:
        """Get database session"""
        if self.db is None:
            self.db = next(get_session())
        return self.db
    
    # Property Data Methods
    
    async def load_property_data(self, property_id: str = None, 
                               start_date: datetime = None,
                               end_date: datetime = None,
                               limit: int = None) -> List[PropertyData]:
        """Load property time series data from database"""
        
        logger.info(f"Loading property data for {property_id} from {start_date} to {end_date}")
        
        try:
            session = self.get_session()
            
            # Build query
            query = session.query(Property)
            
            if property_id:
                query = query.filter(Property.id == property_id)
            
            if start_date:
                query = query.filter(Property.created_at >= start_date)
            
            if end_date:
                query = query.filter(Property.created_at <= end_date)
            
            if limit:
                query = query.limit(limit)
            
            # Execute query
            properties = query.all()
            
            # Convert to PropertyData objects
            property_data = []
            for prop in properties:
                # Extract time series data from property
                data_points = self._extract_property_time_series(prop)
                property_data.extend(data_points)
            
            logger.info(f"Loaded {len(property_data)} property data points")
            
            return property_data
            
        except Exception as e:
            logger.error(f"Error loading property data: {e}")
            raise
    
    async def load_macro_data(self, start_date: datetime = None,
                            end_date: datetime = None) -> List[MacroData]:
        """Load macro-economic time series data"""
        
        logger.info(f"Loading macro data from {start_date} to {end_date}")
        
        try:
            # For now, use synthetic macro data
            # In production, would connect to external data sources (FRED, etc.)
            from ..datasets import DatasetManager
            dataset_manager = DatasetManager()
            
            macro_df = dataset_manager.load_macro_data(start_date, end_date)
            
            # Convert to MacroData objects
            macro_data = []
            for _, row in macro_df.iterrows():
                macro_data.append(MacroData(
                    date=row['date'],
                    interest_rate=row.get('interest_rate'),
                    gdp_growth=row.get('gdp_growth'),
                    inflation=row.get('inflation'),
                    unemployment=row.get('unemployment'),
                    housing_starts=row.get('housing_starts')
                ))
            
            logger.info(f"Loaded {len(macro_data)} macro data points")
            
            return macro_data
            
        except Exception as e:
            logger.error(f"Error loading macro data: {e}")
            raise
    
    async def load_historical_data(self, property_ids: List[str] = None,
                                 start_date: datetime = None,
                                 end_date: datetime = None) -> pd.DataFrame:
        """Load historical data for analysis/backtesting"""
        
        logger.info(f"Loading historical data for {len(property_ids or [])} properties")
        
        try:
            session = self.get_session()
            
            # Custom SQL query for time series data
            sql = """
            SELECT 
                p.id as property_id,
                p.created_at as date,
                p.monthly_noi as noi,
                p.monthly_rent as rent,
                p.occupancy_rate as occupancy,
                p.cap_rate,
                p.market_value
            FROM properties p
            WHERE 1=1
            """
            
            params = {}
            
            if property_ids:
                sql += " AND p.id = ANY(:property_ids)"
                params['property_ids'] = property_ids
            
            if start_date:
                sql += " AND p.created_at >= :start_date"
                params['start_date'] = start_date
            
            if end_date:
                sql += " AND p.created_at <= :end_date"
                params['end_date'] = end_date
            
            sql += " ORDER BY p.id, p.created_at"
            
            # Execute query
            result = session.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convert to DataFrame
            columns = ['property_id', 'date', 'noi', 'rent', 'occupancy', 'cap_rate', 'market_value']
            df = pd.DataFrame(rows, columns=columns)
            
            logger.info(f"Loaded historical data: {df.shape[0]} rows, {df.shape[1]} columns")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            raise
    
    # Forecast Persistence Methods
    
    async def save_forecast(self, forecast_result: ForecastResult) -> str:
        """Save forecast results to database"""
        
        logger.info(f"Saving forecast for {forecast_result.property_id}")
        
        try:
            session = self.get_session()
            
            # Create forecast record
            forecast = Forecast(
                property_id=forecast_result.property_id,
                forecast_type=forecast_result.forecast_type,
                model_type=forecast_result.model_type,
                forecast_data=forecast_result.to_dict(),
                created_at=forecast_result.created_at or datetime.now()
            )
            
            session.add(forecast)
            session.commit()
            
            logger.info(f"Saved forecast with ID: {forecast.id}")
            
            return str(forecast.id)
            
        except Exception as e:
            logger.error(f"Error saving forecast: {e}")
            session.rollback()
            raise
    
    async def load_forecasts(self, property_id: str = None,
                           forecast_type: str = None,
                           start_date: datetime = None,
                           end_date: datetime = None,
                           limit: int = None) -> List[ForecastResult]:
        """Load forecast results from database"""
        
        logger.info(f"Loading forecasts for {property_id}, type: {forecast_type}")
        
        try:
            session = self.get_session()
            
            # Build query
            query = session.query(Forecast)
            
            if property_id:
                query = query.filter(Forecast.property_id == property_id)
            
            if forecast_type:
                query = query.filter(Forecast.forecast_type == forecast_type)
            
            if start_date:
                query = query.filter(Forecast.created_at >= start_date)
            
            if end_date:
                query = query.filter(Forecast.created_at <= end_date)
            
            if limit:
                query = query.limit(limit)
            
            # Execute query
            forecasts = query.all()
            
            # Convert to ForecastResult objects
            results = []
            for forecast in forecasts:
                forecast_data = forecast.forecast_data or {}
                result = ForecastResult(
                    forecast_type=forecast.forecast_type,
                    property_id=forecast.property_id,
                    model_type=forecast.model_type,
                    predictions=forecast_data.get('predictions', []),
                    metrics=forecast_data.get('metrics', {}),
                    metadata=forecast_data.get('metadata', {}),
                    created_at=forecast.created_at
                )
                results.append(result)
            
            logger.info(f"Loaded {len(results)} forecasts")
            
            return results
            
        except Exception as e:
            logger.error(f"Error loading forecasts: {e}")
            raise
    
    # Opportunity Scoring Methods
    
    async def save_arbitrage_score(self, score: ArbitrageScore) -> str:
        """Save arbitrage score to database"""
        
        logger.info(f"Saving arbitrage score for {score.property_id}")
        
        try:
            session = self.get_session()
            
            # Create opportunity record
            opportunity = Opportunity(
                property_id=score.property_id,
                opportunity_type="arbitrage",
                score=score.score,
                confidence=score.confidence,
                expected_return=score.expected_return,
                risk_score=score.risk_score,
                factors=score.factors,
                metadata={
                    'hold_period_months': score.hold_period_months
                },
                created_at=score.created_at or datetime.now()
            )
            
            session.add(opportunity)
            session.commit()
            
            logger.info(f"Saved arbitrage score with ID: {opportunity.id}")
            
            return str(opportunity.id)
            
        except Exception as e:
            logger.error(f"Error saving arbitrage score: {e}")
            session.rollback()
            raise
    
    async def load_arbitrage_scores(self, property_id: str = None,
                                  min_score: float = None,
                                  limit: int = None) -> List[ArbitrageScore]:
        """Load arbitrage scores from database"""
        
        logger.info(f"Loading arbitrage scores for {property_id}")
        
        try:
            session = self.get_session()
            
            # Build query
            query = session.query(Opportunity).filter(
                Opportunity.opportunity_type == "arbitrage"
            )
            
            if property_id:
                query = query.filter(Opportunity.property_id == property_id)
            
            if min_score is not None:
                query = query.filter(Opportunity.score >= min_score)
            
            # Order by score descending
            query = query.order_by(Opportunity.score.desc())
            
            if limit:
                query = query.limit(limit)
            
            # Execute query
            opportunities = query.all()
            
            # Convert to ArbitrageScore objects
            scores = []
            for opp in opportunities:
                score = ArbitrageScore(
                    property_id=opp.property_id,
                    score=opp.score,
                    confidence=opp.confidence,
                    factors=opp.factors or {},
                    expected_return=opp.expected_return,
                    risk_score=opp.risk_score,
                    hold_period_months=opp.metadata.get('hold_period_months') if opp.metadata else None,
                    created_at=opp.created_at
                )
                scores.append(score)
            
            logger.info(f"Loaded {len(scores)} arbitrage scores")
            
            return scores
            
        except Exception as e:
            logger.error(f"Error loading arbitrage scores: {e}")
            raise
    
    # Data Processing Methods
    
    def preprocess_property_data(self, data: List[PropertyData]) -> pd.DataFrame:
        """Convert property data to ML-ready format"""
        
        # Convert to DataFrame
        records = [item.to_dict() for item in data]
        df = pd.DataFrame(records)
        
        if df.empty:
            return df
        
        # Sort by property and date
        df = df.sort_values(['property_id', 'date'])
        
        # Handle missing values
        numeric_columns = ['noi', 'rent', 'occupancy', 'cap_rate', 'market_value']
        for col in numeric_columns:
            if col in df.columns:
                # Forward fill within each property
                df[col] = df.groupby('property_id')[col].fillna(method='ffill')
                
                # Backward fill any remaining NAs
                df[col] = df.groupby('property_id')[col].fillna(method='bfill')
        
        # Create time-based features
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        
        # Create lag features
        for col in numeric_columns:
            if col in df.columns:
                df[f'{col}_lag1'] = df.groupby('property_id')[col].shift(1)
                df[f'{col}_lag3'] = df.groupby('property_id')[col].shift(3)
        
        # Calculate growth rates
        for col in ['noi', 'rent', 'market_value']:
            if col in df.columns:
                df[f'{col}_pct_change'] = df.groupby('property_id')[col].pct_change()
                df[f'{col}_yoy_change'] = df.groupby('property_id')[col].pct_change(periods=12)
        
        logger.info(f"Preprocessed data: {df.shape[0]} rows, {df.shape[1]} features")
        
        return df
    
    def preprocess_macro_data(self, data: List[MacroData]) -> pd.DataFrame:
        """Convert macro data to ML-ready format"""
        
        # Convert to DataFrame
        records = [item.to_dict() for item in data]
        df = pd.DataFrame(records)
        
        if df.empty:
            return df
        
        # Sort by date
        df = df.sort_values('date')
        df['date'] = pd.to_datetime(df['date'])
        
        # Handle missing values with interpolation
        numeric_columns = ['interest_rate', 'gdp_growth', 'inflation', 'unemployment', 'housing_starts']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].interpolate(method='time')
        
        # Create lag features
        for col in numeric_columns:
            if col in df.columns:
                df[f'{col}_lag1'] = df[col].shift(1)
                df[f'{col}_lag3'] = df[col].shift(3)
                df[f'{col}_lag12'] = df[col].shift(12)
        
        # Calculate moving averages
        for col in numeric_columns:
            if col in df.columns:
                df[f'{col}_ma3'] = df[col].rolling(window=3).mean()
                df[f'{col}_ma12'] = df[col].rolling(window=12).mean()
        
        logger.info(f"Preprocessed macro data: {df.shape[0]} rows, {df.shape[1]} features")
        
        return df
    
    def join_property_macro_data(self, property_df: pd.DataFrame, 
                               macro_df: pd.DataFrame) -> pd.DataFrame:
        """Join property and macro data on date"""
        
        if property_df.empty or macro_df.empty:
            return property_df
        
        # Ensure date columns are datetime
        property_df['date'] = pd.to_datetime(property_df['date'])
        macro_df['date'] = pd.to_datetime(macro_df['date'])
        
        # Merge on date (left join to keep all property records)
        merged_df = property_df.merge(
            macro_df, 
            on='date', 
            how='left', 
            suffixes=('', '_macro')
        )
        
        # Forward fill macro data to handle missing dates
        macro_columns = [col for col in merged_df.columns if col.endswith('_macro') or col in macro_df.columns]
        for col in macro_columns:
            if col in merged_df.columns and col != 'date':
                merged_df[col] = merged_df[col].fillna(method='ffill')
        
        logger.info(f"Joined data: {merged_df.shape[0]} rows, {merged_df.shape[1]} columns")
        
        return merged_df
    
    # Utility Methods
    
    def _extract_property_time_series(self, property: Property) -> List[PropertyData]:
        """Extract time series data points from a property record"""
        
        # For now, create a single data point
        # In production, properties might have embedded time series data
        data_point = PropertyData(
            property_id=property.id,
            date=property.created_at or datetime.now(),
            noi=getattr(property, 'monthly_noi', None),
            rent=getattr(property, 'monthly_rent', None),
            occupancy=getattr(property, 'occupancy_rate', None),
            cap_rate=getattr(property, 'cap_rate', None),
            market_value=getattr(property, 'market_value', None),
            operating_expenses=getattr(property, 'operating_expenses', None)
        )
        
        return [data_point]
    
    async def get_data_summary(self) -> Dict[str, Any]:
        """Get summary statistics of available data"""
        
        try:
            session = self.get_session()
            
            # Count properties
            property_count = session.query(Property).count()
            
            # Count forecasts
            forecast_count = session.query(Forecast).count()
            
            # Count opportunities
            opportunity_count = session.query(Opportunity).count()
            
            # Date ranges
            property_dates = session.query(
                session.query(Property.created_at).func.min().label('min_date'),
                session.query(Property.created_at).func.max().label('max_date')
            ).first()
            
            summary = {
                'properties': {
                    'count': property_count,
                    'date_range': {
                        'min': property_dates.min_date.isoformat() if property_dates.min_date else None,
                        'max': property_dates.max_date.isoformat() if property_dates.max_date else None
                    }
                },
                'forecasts': {
                    'count': forecast_count
                },
                'opportunities': {
                    'count': opportunity_count
                },
                'updated_at': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            raise

# Global service instance
_data_service = None

def get_data_service(db_session: Session = None) -> MLDataService:
    """Get global ML data service instance"""
    global _data_service
    
    if _data_service is None:
        _data_service = MLDataService(db_session)
    
    return _data_service

__all__ = ['MLDataService', 'get_data_service']
