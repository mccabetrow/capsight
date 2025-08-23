"""
Arbitrage prediction model using ensemble methods.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
import joblib
import logging
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

logger = logging.getLogger(__name__)


class ArbitragePredictor:
    """
    Ensemble model for predicting real estate arbitrage opportunities.
    
    Combines multiple algorithms to predict:
    - Arbitrage score (0-1)
    - Expected return percentage
    - Risk assessment
    - Key contributing factors
    """
    
    def __init__(self, model_path: str = "./ml/models/"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize models
        self.models = {
            'rf': RandomForestRegressor(n_estimators=100, random_state=42),
            'xgb': xgb.XGBRegressor(n_estimators=100, random_state=42),
            'gb': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'lr': LinearRegression()
        }
        
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        
    def prepare_features(self, property_data: Dict[str, Any], market_data: Dict[str, Any]) -> pd.DataFrame:
        """Prepare features from property and market data."""
        features = {}
        
        # Property features
        features['list_price'] = property_data.get('list_price', 0)
        features['square_footage'] = property_data.get('square_footage', 0)
        features['bedrooms'] = property_data.get('bedrooms', 0)
        features['bathrooms'] = property_data.get('bathrooms', 0)
        features['year_built'] = property_data.get('year_built', 2000)
        features['lot_size'] = property_data.get('lot_size', 0)
        
        # Derived property features
        features['price_per_sqft'] = features['list_price'] / max(features['square_footage'], 1)
        features['property_age'] = datetime.now().year - features['year_built']
        features['bed_bath_ratio'] = features['bedrooms'] / max(features['bathrooms'], 0.5)
        
        # Market features
        features['median_price'] = market_data.get('median_price', 0)
        features['market_price_per_sqft'] = market_data.get('price_per_sqft', 0)
        features['cap_rate'] = market_data.get('cap_rate', 0.05)
        features['rental_yield'] = market_data.get('rental_yield', 0.04)
        features['vacancy_rate'] = market_data.get('vacancy_rate', 0.05)
        features['appreciation_rate'] = market_data.get('appreciation_rate', 0.03)
        features['inventory_levels'] = market_data.get('inventory_levels', 1000)
        features['days_on_market'] = market_data.get('days_on_market', 30)
        
        # Mortgage rates
        mortgage_rates = market_data.get('mortgage_rates', {})
        features['mortgage_rate_30y'] = mortgage_rates.get('30_year_fixed', 0.07)
        features['mortgage_rate_15y'] = mortgage_rates.get('15_year_fixed', 0.065)
        features['mortgage_rate_arm'] = mortgage_rates.get('arm_5_1', 0.06)
        
        # Derived market features
        features['price_to_market_ratio'] = features['price_per_sqft'] / max(features['market_price_per_sqft'], 1)
        features['list_to_median_ratio'] = features['list_price'] / max(features['median_price'], 1)
        features['yield_spread'] = features['rental_yield'] - features['mortgage_rate_30y']
        features['inventory_pressure'] = features['days_on_market'] / 30.0  # Normalized to monthly
        
        # Economic indicators (mock data - replace with real economic data)
        features['unemployment_rate'] = 0.04  # National average
        features['gdp_growth'] = 0.025  # National average
        features['inflation_rate'] = 0.03  # National average
        
        return pd.DataFrame([features])
    
    def generate_synthetic_data(self, n_samples: int = 10000) -> Tuple[pd.DataFrame, np.ndarray]:
        """Generate synthetic training data for MVP."""
        np.random.seed(42)
        
        # Generate realistic property and market data
        data = []
        targets = []
        
        for _ in range(n_samples):
            # Property characteristics
            list_price = np.random.lognormal(12.5, 0.7)  # Around 400k mean
            square_footage = np.random.normal(2000, 500)
            bedrooms = np.random.choice([2, 3, 4, 5], p=[0.2, 0.4, 0.3, 0.1])
            bathrooms = bedrooms * np.random.uniform(0.7, 1.3)
            year_built = np.random.randint(1950, 2024)
            lot_size = np.random.lognormal(8, 0.5)  # sq ft
            
            # Market characteristics
            median_price = list_price * np.random.uniform(0.8, 1.2)
            market_price_per_sqft = median_price / np.random.normal(2000, 300)
            cap_rate = np.random.uniform(0.03, 0.08)
            rental_yield = np.random.uniform(0.03, 0.07)
            vacancy_rate = np.random.uniform(0.02, 0.12)
            appreciation_rate = np.random.uniform(0.0, 0.10)
            inventory_levels = np.random.normal(1000, 300)
            days_on_market = np.random.exponential(30)
            
            # Mortgage rates
            mortgage_rate_30y = np.random.uniform(0.05, 0.08)
            mortgage_rate_15y = mortgage_rate_30y - 0.005
            mortgage_rate_arm = mortgage_rate_30y - 0.01
            
            property_data = {
                'list_price': list_price,
                'square_footage': square_footage,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'year_built': year_built,
                'lot_size': lot_size
            }
            
            market_data = {
                'median_price': median_price,
                'price_per_sqft': market_price_per_sqft,
                'cap_rate': cap_rate,
                'rental_yield': rental_yield,
                'vacancy_rate': vacancy_rate,
                'appreciation_rate': appreciation_rate,
                'inventory_levels': inventory_levels,
                'days_on_market': days_on_market,
                'mortgage_rates': {
                    '30_year_fixed': mortgage_rate_30y,
                    '15_year_fixed': mortgage_rate_15y,
                    'arm_5_1': mortgage_rate_arm
                }
            }
            
            features_df = self.prepare_features(property_data, market_data)
            data.append(features_df.iloc[0].to_dict())
            
            # Generate target (arbitrage score) based on feature relationships
            price_advantage = max(0, 1 - features_df['price_to_market_ratio'].iloc[0])
            yield_advantage = max(0, features_df['yield_spread'].iloc[0] * 10)
            market_efficiency = 1 - min(1, features_df['inventory_pressure'].iloc[0])
            
            arbitrage_score = np.clip(
                (price_advantage * 0.4 + yield_advantage * 0.4 + market_efficiency * 0.2),
                0, 1
            )
            
            # Add some noise
            arbitrage_score += np.random.normal(0, 0.05)
            arbitrage_score = np.clip(arbitrage_score, 0, 1)
            
            targets.append(arbitrage_score)
        
        return pd.DataFrame(data), np.array(targets)
    
    def train(self, retrain: bool = False) -> Dict[str, float]:
        """Train the arbitrage prediction model."""
        try:
            # Check if models exist and we're not retraining
            if not retrain and (self.model_path / "ensemble_model.joblib").exists():
                logger.info("Loading existing model...")
                self.load_model()
                return {"message": "Model loaded successfully"}
            
            logger.info("Training new arbitrage prediction model...")
            
            # Generate synthetic training data
            X, y = self.generate_synthetic_data(n_samples=10000)
            
            # Store feature names
            self.feature_names = list(X.columns)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train individual models
            model_scores = {}
            predictions = {}
            
            for name, model in self.models.items():
                logger.info(f"Training {name} model...")
                
                if name == 'lr':
                    # Linear regression needs scaled data
                    model.fit(X_train_scaled, y_train)
                    pred = model.predict(X_test_scaled)
                else:
                    # Tree-based models don't need scaling
                    model.fit(X_train, y_train)
                    pred = model.predict(X_test)
                
                predictions[name] = pred
                model_scores[name] = {
                    'mae': mean_absolute_error(y_test, pred),
                    'mse': mean_squared_error(y_test, pred),
                    'r2': r2_score(y_test, pred)
                }
            
            # Create ensemble prediction (weighted average)
            ensemble_pred = (
                predictions['rf'] * 0.3 +
                predictions['xgb'] * 0.3 +
                predictions['gb'] * 0.25 +
                predictions['lr'] * 0.15
            )
            
            ensemble_score = {
                'mae': mean_absolute_error(y_test, ensemble_pred),
                'mse': mean_squared_error(y_test, ensemble_pred),
                'r2': r2_score(y_test, ensemble_pred)
            }
            
            model_scores['ensemble'] = ensemble_score
            
            # Save models
            self.save_model()
            self.is_trained = True
            
            logger.info(f"Model training completed. Ensemble R² score: {ensemble_score['r2']:.4f}")
            
            return model_scores
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            raise
    
    def predict(self, property_data: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make arbitrage prediction for a property."""
        if not self.is_trained:
            if (self.model_path / "ensemble_model.joblib").exists():
                self.load_model()
            else:
                raise ValueError("Model not trained. Please train the model first.")
        
        try:
            # Prepare features
            features_df = self.prepare_features(property_data, market_data)
            
            # Make predictions with each model
            predictions = {}
            
            # Scale features for linear regression
            features_scaled = self.scaler.transform(features_df)
            
            for name, model in self.models.items():
                if name == 'lr':
                    pred = model.predict(features_scaled)[0]
                else:
                    pred = model.predict(features_df)[0]
                predictions[name] = max(0, min(1, pred))  # Ensure 0-1 range
            
            # Ensemble prediction
            arbitrage_score = (
                predictions['rf'] * 0.3 +
                predictions['xgb'] * 0.3 +
                predictions['gb'] * 0.25 +
                predictions['lr'] * 0.15
            )
            
            # Calculate additional metrics
            expected_return = arbitrage_score * 0.15  # Up to 15% return
            risk_score = 1 - arbitrage_score  # Higher arbitrage = lower risk
            
            # Feature importance (from Random Forest)
            feature_importance = dict(zip(
                self.feature_names,
                self.models['rf'].feature_importances_
            ))
            
            # Get top contributing factors
            top_factors = dict(sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5])
            
            result = {
                'arbitrage_score': round(arbitrage_score, 4),
                'expected_return': round(expected_return, 4),
                'risk_score': round(risk_score, 4),
                'contributing_factors': {k: round(v, 4) for k, v in top_factors.items()},
                'model_predictions': {k: round(v, 4) for k, v in predictions.items()},
                'confidence_interval': self.calculate_confidence_interval(arbitrage_score),
                'prediction_timestamp': datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise
    
    def calculate_confidence_interval(self, prediction: float, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for prediction."""
        # Simple approximation - in production, use bootstrap or Bayesian methods
        std_error = 0.05  # Estimated standard error
        z_score = 1.96 if confidence == 0.95 else 2.58  # 95% or 99% confidence
        
        margin_of_error = z_score * std_error
        lower = max(0, prediction - margin_of_error)
        upper = min(1, prediction + margin_of_error)
        
        return (round(lower, 4), round(upper, 4))
    
    def save_model(self) -> None:
        """Save trained models to disk."""
        try:
            model_data = {
                'models': self.models,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'is_trained': True,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            joblib.dump(model_data, self.model_path / "ensemble_model.joblib")
            logger.info("Model saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise
    
    def load_model(self) -> None:
        """Load trained models from disk."""
        try:
            model_path = self.model_path / "ensemble_model.joblib"
            if not model_path.exists():
                raise FileNotFoundError("Model file not found")
            
            model_data = joblib.load(model_path)
            
            self.models = model_data['models']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.is_trained = model_data['is_trained']
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise


# Example usage
if __name__ == "__main__":
    # Initialize and train model
    predictor = ArbitragePredictor()
    
    # Train model (only if not already trained)
    training_results = predictor.train(retrain=False)
    print("Training Results:", training_results)
    
    # Example prediction
    property_data = {
        'list_price': 450000,
        'square_footage': 2200,
        'bedrooms': 3,
        'bathrooms': 2.5,
        'year_built': 2010,
        'lot_size': 8000
    }
    
    market_data = {
        'median_price': 475000,
        'price_per_sqft': 220,
        'cap_rate': 0.055,
        'rental_yield': 0.048,
        'vacancy_rate': 0.05,
        'appreciation_rate': 0.06,
        'inventory_levels': 800,
        'days_on_market': 25,
        'mortgage_rates': {
            '30_year_fixed': 0.068,
            '15_year_fixed': 0.061,
            'arm_5_1': 0.058
        }
    }
    
    prediction = predictor.predict(property_data, market_data)
    print("Prediction:", prediction)
