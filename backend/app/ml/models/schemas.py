"""
Data schemas for CapSight ML Pipeline
Pydantic models and dataclasses for ML inputs/outputs
"""

from datetime import datetime, date
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback for environments without pydantic
    PYDANTIC_AVAILABLE = False
    BaseModel = object

class ForecastType(str, Enum):
    """Types of forecasts supported"""
    CAP_RATE = "cap_rate"
    INTEREST_RATE = "interest_rate" 
    NOI = "noi"
    RENT = "rent"
    OCCUPANCY = "occupancy"

class ModelType(str, Enum):
    """Types of models supported"""
    PROPHET = "prophet"
    ARIMA = "arima"
    LINEAR = "linear"
    XGBOOST = "xgboost"
    ENSEMBLE = "ensemble"

@dataclass
class PropertyData:
    """Property time series data"""
    property_id: str
    date: datetime
    noi: Optional[float] = None
    rent: Optional[float] = None
    occupancy: Optional[float] = None
    cap_rate: Optional[float] = None
    market_value: Optional[float] = None
    operating_expenses: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PropertyData':
        """Create from dictionary"""
        if isinstance(data.get('date'), str):
            data['date'] = datetime.fromisoformat(data['date'])
        return cls(**data)

@dataclass
class MacroData:
    """Macro-economic time series data"""
    date: datetime
    interest_rate: Optional[float] = None
    gdp_growth: Optional[float] = None
    inflation: Optional[float] = None
    unemployment: Optional[float] = None
    housing_starts: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MacroData':
        """Create from dictionary"""
        if isinstance(data.get('date'), str):
            data['date'] = datetime.fromisoformat(data['date'])
        return cls(**data)

@dataclass 
class ForecastPoint:
    """Single forecast prediction point"""
    date: datetime
    value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class ForecastResult:
    """Complete forecast results"""
    forecast_type: str
    property_id: Optional[str] = None
    model_type: str = "prophet"
    predictions: List[ForecastPoint] = None
    metrics: Dict[str, float] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.predictions is None:
            self.predictions = []
        if self.metrics is None:
            self.metrics = {}
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['predictions'] = [p if isinstance(p, dict) else p.to_dict() for p in self.predictions]
        return data
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert predictions to DataFrame"""
        if not self.predictions:
            return pd.DataFrame()
        
        data = []
        for pred in self.predictions:
            if isinstance(pred, ForecastPoint):
                data.append(pred.to_dict())
            else:
                data.append(pred)
        
        return pd.DataFrame(data)

@dataclass
class ArbitrageScore:
    """Arbitrage opportunity score"""
    property_id: str
    score: float
    confidence: float
    factors: Dict[str, float]
    expected_return: Optional[float] = None
    risk_score: Optional[float] = None
    hold_period_months: Optional[int] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArbitrageScore':
        """Create from dictionary"""
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

@dataclass
class BacktestResult:
    """Backtest performance results"""
    model_name: str
    test_period_start: datetime
    test_period_end: datetime
    metrics: Dict[str, float]
    predictions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

# Pydantic models (if available)
if PYDANTIC_AVAILABLE:
    
    class PropertyDataModel(BaseModel):
        """Pydantic model for property data"""
        property_id: str
        date: datetime
        noi: Optional[float] = None
        rent: Optional[float] = None
        occupancy: Optional[float] = None
        cap_rate: Optional[float] = None
        market_value: Optional[float] = None
        operating_expenses: Optional[float] = None
        
        @validator('occupancy')
        def validate_occupancy(cls, v):
            if v is not None and (v < 0 or v > 1):
                raise ValueError('Occupancy must be between 0 and 1')
            return v
        
        @validator('cap_rate')
        def validate_cap_rate(cls, v):
            if v is not None and (v < 0 or v > 1):
                raise ValueError('Cap rate must be between 0 and 1')
            return v
    
    class MacroDataModel(BaseModel):
        """Pydantic model for macro data"""
        date: datetime
        interest_rate: Optional[float] = None
        gdp_growth: Optional[float] = None
        inflation: Optional[float] = None
        unemployment: Optional[float] = None
        housing_starts: Optional[float] = None
        
        @validator('interest_rate')
        def validate_interest_rate(cls, v):
            if v is not None and v < 0:
                raise ValueError('Interest rate cannot be negative')
            return v
    
    class ForecastPointModel(BaseModel):
        """Pydantic model for forecast point"""
        date: datetime
        value: float
        lower_bound: Optional[float] = None
        upper_bound: Optional[float] = None
        confidence: Optional[float] = None
        
        @validator('confidence')
        def validate_confidence(cls, v):
            if v is not None and (v < 0 or v > 1):
                raise ValueError('Confidence must be between 0 and 1')
            return v
    
    class ForecastResultModel(BaseModel):
        """Pydantic model for forecast result"""
        forecast_type: ForecastType
        property_id: Optional[str] = None
        model_type: ModelType = ModelType.PROPHET
        predictions: List[ForecastPointModel] = Field(default_factory=list)
        metrics: Dict[str, float] = Field(default_factory=dict)
        metadata: Dict[str, Any] = Field(default_factory=dict)
        created_at: datetime = Field(default_factory=datetime.now)
    
    class ArbitrageScoreModel(BaseModel):
        """Pydantic model for arbitrage score"""
        property_id: str
        score: float = Field(..., ge=0, le=100, description="Arbitrage score 0-100")
        confidence: float = Field(..., ge=0, le=1, description="Confidence 0-1")
        factors: Dict[str, float]
        expected_return: Optional[float] = None
        risk_score: Optional[float] = Field(None, ge=0, le=100)
        hold_period_months: Optional[int] = Field(None, gt=0)
        created_at: datetime = Field(default_factory=datetime.now)
    
    class BacktestResultModel(BaseModel):
        """Pydantic model for backtest result"""
        model_name: str
        test_period_start: datetime
        test_period_end: datetime
        metrics: Dict[str, float]
        predictions: List[Dict[str, Any]]
        metadata: Dict[str, Any] = Field(default_factory=dict)

# Input/Output request/response models
class ForecastRequest:
    """Request for forecast generation"""
    
    def __init__(self, property_id: str = None, forecast_type: str = "cap_rate",
                 start_date: datetime = None, end_date: datetime = None,
                 horizon_months: int = 12, model_type: str = "prophet",
                 include_confidence: bool = True, **kwargs):
        self.property_id = property_id
        self.forecast_type = forecast_type
        self.start_date = start_date or datetime.now()
        self.end_date = end_date
        self.horizon_months = horizon_months
        self.model_type = model_type
        self.include_confidence = include_confidence
        self.kwargs = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'property_id': self.property_id,
            'forecast_type': self.forecast_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'horizon_months': self.horizon_months,
            'model_type': self.model_type,
            'include_confidence': self.include_confidence,
            **self.kwargs
        }

class ArbitrageRequest:
    """Request for arbitrage scoring"""
    
    def __init__(self, property_ids: List[str] = None, 
                 hold_period_months: int = 60,
                 min_expected_return: float = 0.1,
                 risk_tolerance: str = "moderate",
                 **kwargs):
        self.property_ids = property_ids or []
        self.hold_period_months = hold_period_months
        self.min_expected_return = min_expected_return
        self.risk_tolerance = risk_tolerance
        self.kwargs = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'property_ids': self.property_ids,
            'hold_period_months': self.hold_period_months,
            'min_expected_return': self.min_expected_return,
            'risk_tolerance': self.risk_tolerance,
            **self.kwargs
        }

class BatchPredictRequest:
    """Request for batch predictions"""
    
    def __init__(self, properties: List[Dict[str, Any]], 
                 forecast_types: List[str] = None,
                 horizon_months: int = 12,
                 include_scoring: bool = True,
                 **kwargs):
        self.properties = properties
        self.forecast_types = forecast_types or ["cap_rate", "noi", "rent"]
        self.horizon_months = horizon_months
        self.include_scoring = include_scoring
        self.kwargs = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'properties': self.properties,
            'forecast_types': self.forecast_types,
            'horizon_months': self.horizon_months,
            'include_scoring': self.include_scoring,
            **self.kwargs
        }

# Utility functions
def validate_property_data(data: Dict[str, Any]) -> bool:
    """Validate property data structure"""
    required_fields = ['property_id', 'date']
    
    for field in required_fields:
        if field not in data:
            return False
    
    # Check data types
    if not isinstance(data['property_id'], str):
        return False
    
    # Check date format
    if isinstance(data['date'], str):
        try:
            datetime.fromisoformat(data['date'])
        except ValueError:
            return False
    elif not isinstance(data['date'], datetime):
        return False
    
    # Check numeric fields
    numeric_fields = ['noi', 'rent', 'occupancy', 'cap_rate', 'market_value']
    for field in numeric_fields:
        if field in data and data[field] is not None:
            if not isinstance(data[field], (int, float)):
                return False
    
    return True

def convert_to_property_data(data: Union[Dict, PropertyData]) -> PropertyData:
    """Convert various formats to PropertyData"""
    if isinstance(data, PropertyData):
        return data
    elif isinstance(data, dict):
        return PropertyData.from_dict(data)
    else:
        raise ValueError(f"Cannot convert {type(data)} to PropertyData")

def convert_to_dataframe(data: List[Union[PropertyData, Dict]]) -> pd.DataFrame:
    """Convert list of property data to DataFrame"""
    records = []
    
    for item in data:
        if isinstance(item, PropertyData):
            records.append(item.to_dict())
        elif isinstance(item, dict):
            records.append(item)
        else:
            raise ValueError(f"Cannot convert {type(item)} to dict")
    
    return pd.DataFrame(records)

__all__ = [
    'ForecastType',
    'ModelType', 
    'PropertyData',
    'MacroData',
    'ForecastPoint',
    'ForecastResult',
    'ArbitrageScore',
    'BacktestResult',
    'ForecastRequest',
    'ArbitrageRequest',
    'BatchPredictRequest',
    'validate_property_data',
    'convert_to_property_data',
    'convert_to_dataframe'
]

# Add pydantic models to __all__ if available
if PYDANTIC_AVAILABLE:
    __all__.extend([
        'PropertyDataModel',
        'MacroDataModel',
        'ForecastPointModel',
        'ForecastResultModel',
        'ArbitrageScoreModel',
        'BacktestResultModel'
    ])
