"""
Counterfactual replay engine for "what-if" analysis
Replays historical decisions with different parameters/models
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import json
from enum import Enum

# MLflow imports
try:
    import mlflow
    from mlflow.tracking import MlflowClient
except ImportError:
    # Mock for environments without MLflow
    class mlflow: pass
    class MlflowClient: pass

from .config import config
from .schemas import (
    BacktestRun, BacktestResult, ModelSnapshot, 
    PredictionSnapshot, ReplayScenario
)
from .data_access import BacktestDataAccess
from .feature_loader import FeatureLoader, feature_loader
from .time_slicer import TimeSlicer, time_slicer

class ReplayMode(Enum):
    """Different replay modes for counterfactual analysis"""
    HISTORICAL_ACTUAL = "historical_actual"      # Original historical predictions
    MODEL_SWAP = "model_swap"                    # Different model on same data  
    PARAMETER_CHANGE = "parameter_change"        # Same model, different parameters
    FEATURE_ABLATION = "feature_ablation"        # Remove/add specific features
    THRESHOLD_CHANGE = "threshold_change"        # Different decision thresholds
    MARKET_SCENARIO = "market_scenario"          # Adjust market conditions

@dataclass 
class ReplayContext:
    """Context for a replay scenario"""
    original_run_id: str
    replay_mode: ReplayMode
    scenario_params: Dict[str, Any]
    asof_date: date
    property_ids: List[str]
    model_version: Optional[str] = None
    feature_overrides: Optional[Dict[str, Any]] = None
    threshold_overrides: Optional[Dict[str, float]] = None

class ReplayEngine:
    """Engine for counterfactual replay and what-if analysis"""
    
    def __init__(
        self,
        data_access: Optional[BacktestDataAccess] = None,
        feature_loader: Optional[FeatureLoader] = None,
        mlflow_tracking_uri: Optional[str] = None
    ):
        self.data_access = data_access or BacktestDataAccess()
        self.feature_loader = feature_loader or globals()['feature_loader']
        self.time_slicer = time_slicer
        self.mlflow_uri = mlflow_tracking_uri or config.mlflow_tracking_uri
        self._mlflow_client = None
    
    async def _get_mlflow_client(self) -> MlflowClient:
        """Lazy initialization of MLflow client"""
        if self._mlflow_client is None:
            try:
                mlflow.set_tracking_uri(self.mlflow_uri)
                self._mlflow_client = MlflowClient()
            except:
                print("Warning: MLflow client initialization failed")
                self._mlflow_client = None
        return self._mlflow_client
    
    async def replay_historical_predictions(
        self,
        original_run_id: str,
        replay_scenario: ReplayScenario
    ) -> BacktestRun:
        """
        Replay historical predictions with different parameters
        
        Args:
            original_run_id: ID of original backtest run to replay
            replay_scenario: Scenario configuration for replay
            
        Returns:
            New BacktestRun with replay results
        """
        # Load original run configuration
        original_run = await self.data_access.get_backtest_run(original_run_id)
        if not original_run:
            raise ValueError(f"Original run {original_run_id} not found")
        
        # Create replay context
        replay_context = ReplayContext(
            original_run_id=original_run_id,
            replay_mode=ReplayMode(replay_scenario.replay_mode),
            scenario_params=replay_scenario.scenario_params,
            asof_date=original_run.prediction_date.date(),
            property_ids=replay_scenario.entity_ids or [],
            model_version=replay_scenario.model_version,
            feature_overrides=replay_scenario.feature_overrides,
            threshold_overrides=replay_scenario.threshold_overrides
        )
        
        # Execute replay based on mode
        if replay_context.replay_mode == ReplayMode.HISTORICAL_ACTUAL:
            return await self._replay_historical_actual(original_run, replay_context)
        elif replay_context.replay_mode == ReplayMode.MODEL_SWAP:
            return await self._replay_model_swap(original_run, replay_context)
        elif replay_context.replay_mode == ReplayMode.PARAMETER_CHANGE:
            return await self._replay_parameter_change(original_run, replay_context)
        elif replay_context.replay_mode == ReplayMode.FEATURE_ABLATION:
            return await self._replay_feature_ablation(original_run, replay_context)
        elif replay_context.replay_mode == ReplayMode.THRESHOLD_CHANGE:
            return await self._replay_threshold_change(original_run, replay_context)
        elif replay_context.replay_mode == ReplayMode.MARKET_SCENARIO:
            return await self._replay_market_scenario(original_run, replay_context)
        else:
            raise ValueError(f"Unsupported replay mode: {replay_context.replay_mode}")
    
    async def _replay_historical_actual(
        self,
        original_run: BacktestRun,
        replay_context: ReplayContext
    ) -> BacktestRun:
        """Replay with exact historical conditions (baseline)"""
        
        # Load original predictions
        original_predictions = await self.data_access.get_prediction_snapshots(
            backtest_run_id=original_run.run_id
        )
        
        # Create new run for replay
        replay_run = BacktestRun(
            run_id=f"replay_historical_{original_run.run_id}_{int(datetime.now().timestamp())}",
            run_name=f"Historical Replay of {original_run.run_name}",
            created_at=datetime.now(),
            prediction_date=original_run.prediction_date,
            horizon_months=original_run.horizon_months,
            model_version=original_run.model_version,
            feature_set=original_run.feature_set,
            status="completed",
            config=original_run.config,
            parent_run_id=original_run.run_id,
            replay_scenario=asdict(replay_context)
        )
        
        # Save replay run
        await self.data_access.create_backtest_run(replay_run)
        
        # Copy original predictions as replay predictions
        for pred in original_predictions:
            replay_pred = PredictionSnapshot(
                snapshot_id=f"replay_{pred.snapshot_id}_{replay_run.run_id}",
                backtest_run_id=replay_run.run_id,
                entity_id=pred.entity_id,
                prediction_value=pred.prediction_value,
                prediction_proba=pred.prediction_proba,
                feature_values=pred.feature_values,
                model_version=pred.model_version,
                created_at=datetime.now()
            )
            await self.data_access.create_prediction_snapshot(replay_pred)
        
        return replay_run
    
    async def _replay_model_swap(
        self,
        original_run: BacktestRun,
        replay_context: ReplayContext
    ) -> BacktestRun:
        """Replay with different model on same features"""
        
        # Load original features
        original_features = await self._get_original_features(original_run)
        
        # Load different model
        new_model = await self._load_model(replay_context.model_version)
        
        # Generate predictions with new model
        new_predictions = await self._generate_predictions(
            features_df=original_features,
            model=new_model,
            model_version=replay_context.model_version
        )
        
        # Create replay run
        replay_run = BacktestRun(
            run_id=f"replay_model_{original_run.run_id}_{int(datetime.now().timestamp())}",
            run_name=f"Model Swap Replay of {original_run.run_name}",
            created_at=datetime.now(),
            prediction_date=original_run.prediction_date,
            horizon_months=original_run.horizon_months,
            model_version=replay_context.model_version,
            feature_set=original_run.feature_set,
            status="completed",
            config=original_run.config,
            parent_run_id=original_run.run_id,
            replay_scenario=asdict(replay_context)
        )
        
        await self.data_access.create_backtest_run(replay_run)
        
        # Save new predictions
        await self._save_predictions(replay_run.run_id, new_predictions)
        
        return replay_run
    
    async def _replay_parameter_change(
        self,
        original_run: BacktestRun,
        replay_context: ReplayContext
    ) -> BacktestRun:
        """Replay with same model but different hyperparameters"""
        
        # Load original features
        original_features = await self._get_original_features(original_run)
        
        # Load model with parameter changes
        modified_model = await self._load_model_with_params(
            model_version=original_run.model_version,
            param_overrides=replay_context.scenario_params
        )
        
        # Generate predictions with modified model
        new_predictions = await self._generate_predictions(
            features_df=original_features,
            model=modified_model,
            model_version=f"{original_run.model_version}_modified"
        )
        
        # Create replay run
        replay_run = BacktestRun(
            run_id=f"replay_params_{original_run.run_id}_{int(datetime.now().timestamp())}",
            run_name=f"Parameter Change Replay of {original_run.run_name}",
            created_at=datetime.now(),
            prediction_date=original_run.prediction_date,
            horizon_months=original_run.horizon_months,
            model_version=f"{original_run.model_version}_modified",
            feature_set=original_run.feature_set,
            status="completed",
            config={**original_run.config, "parameter_changes": replay_context.scenario_params},
            parent_run_id=original_run.run_id,
            replay_scenario=asdict(replay_context)
        )
        
        await self.data_access.create_backtest_run(replay_run)
        await self._save_predictions(replay_run.run_id, new_predictions)
        
        return replay_run
    
    async def _replay_feature_ablation(
        self,
        original_run: BacktestRun,
        replay_context: ReplayContext
    ) -> BacktestRun:
        """Replay with different feature set (add/remove features)"""
        
        # Load original features
        original_features = await self._get_original_features(original_run)
        
        # Apply feature modifications
        modified_features = self._modify_features(
            original_features,
            replay_context.feature_overrides or {}
        )
        
        # Load original model
        model = await self._load_model(original_run.model_version)
        
        # Generate predictions with modified features
        new_predictions = await self._generate_predictions(
            features_df=modified_features,
            model=model,
            model_version=original_run.model_version
        )
        
        # Create replay run
        replay_run = BacktestRun(
            run_id=f"replay_features_{original_run.run_id}_{int(datetime.now().timestamp())}",
            run_name=f"Feature Ablation Replay of {original_run.run_name}",
            created_at=datetime.now(),
            prediction_date=original_run.prediction_date,
            horizon_months=original_run.horizon_months,
            model_version=original_run.model_version,
            feature_set={**original_run.feature_set, "feature_changes": replay_context.feature_overrides},
            status="completed",
            config=original_run.config,
            parent_run_id=original_run.run_id,
            replay_scenario=asdict(replay_context)
        )
        
        await self.data_access.create_backtest_run(replay_run)
        await self._save_predictions(replay_run.run_id, new_predictions)
        
        return replay_run
    
    async def _replay_threshold_change(
        self,
        original_run: BacktestRun,
        replay_context: ReplayContext
    ) -> BacktestRun:
        """Replay with different decision thresholds"""
        
        # Load original predictions (probabilities)
        original_predictions = await self.data_access.get_prediction_snapshots(
            backtest_run_id=original_run.run_id
        )
        
        # Apply new thresholds
        new_predictions = []
        new_thresholds = replay_context.threshold_overrides or {}
        
        for pred in original_predictions:
            # Convert probabilities to binary decisions with new thresholds
            new_prediction_value = self._apply_threshold(
                proba=pred.prediction_proba,
                thresholds=new_thresholds
            )
            
            new_pred = PredictionSnapshot(
                snapshot_id=f"replay_thresh_{pred.snapshot_id}_{int(datetime.now().timestamp())}",
                backtest_run_id="",  # Will be set below
                entity_id=pred.entity_id,
                prediction_value=new_prediction_value,
                prediction_proba=pred.prediction_proba,  # Keep original probabilities
                feature_values=pred.feature_values,
                model_version=pred.model_version,
                created_at=datetime.now()
            )
            new_predictions.append(new_pred)
        
        # Create replay run
        replay_run = BacktestRun(
            run_id=f"replay_thresh_{original_run.run_id}_{int(datetime.now().timestamp())}",
            run_name=f"Threshold Change Replay of {original_run.run_name}",
            created_at=datetime.now(),
            prediction_date=original_run.prediction_date,
            horizon_months=original_run.horizon_months,
            model_version=original_run.model_version,
            feature_set=original_run.feature_set,
            status="completed",
            config={**original_run.config, "threshold_changes": new_thresholds},
            parent_run_id=original_run.run_id,
            replay_scenario=asdict(replay_context)
        )
        
        await self.data_access.create_backtest_run(replay_run)
        
        # Update run IDs and save predictions
        for pred in new_predictions:
            pred.backtest_run_id = replay_run.run_id
            await self.data_access.create_prediction_snapshot(pred)
        
        return replay_run
    
    async def _replay_market_scenario(
        self,
        original_run: BacktestRun,
        replay_context: ReplayContext
    ) -> BacktestRun:
        """Replay with simulated market condition changes"""
        
        # Load original features
        original_features = await self._get_original_features(original_run)
        
        # Apply market scenario modifications
        scenario_features = self._apply_market_scenario(
            original_features,
            replay_context.scenario_params
        )
        
        # Load original model
        model = await self._load_model(original_run.model_version)
        
        # Generate predictions with scenario features
        new_predictions = await self._generate_predictions(
            features_df=scenario_features,
            model=model,
            model_version=original_run.model_version
        )
        
        # Create replay run
        replay_run = BacktestRun(
            run_id=f"replay_market_{original_run.run_id}_{int(datetime.now().timestamp())}",
            run_name=f"Market Scenario Replay of {original_run.run_name}",
            created_at=datetime.now(),
            prediction_date=original_run.prediction_date,
            horizon_months=original_run.horizon_months,
            model_version=original_run.model_version,
            feature_set={**original_run.feature_set, "market_scenario": replay_context.scenario_params},
            status="completed",
            config=original_run.config,
            parent_run_id=original_run.run_id,
            replay_scenario=asdict(replay_context)
        )
        
        await self.data_access.create_backtest_run(replay_run)
        await self._save_predictions(replay_run.run_id, new_predictions)
        
        return replay_run
    
    async def _get_original_features(self, original_run: BacktestRun) -> pd.DataFrame:
        """Reconstruct original feature set from run"""
        
        # Load prediction snapshots to get feature values
        predictions = await self.data_access.get_prediction_snapshots(
            backtest_run_id=original_run.run_id
        )
        
        # Reconstruct features DataFrame
        feature_records = []
        for pred in predictions:
            feature_record = {
                "property_id": pred.entity_id,
                **pred.feature_values
            }
            feature_records.append(feature_record)
        
        return pd.DataFrame(feature_records)
    
    def _modify_features(
        self,
        features_df: pd.DataFrame,
        feature_overrides: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply feature modifications for ablation studies"""
        
        result_df = features_df.copy()
        
        for feature_name, modification in feature_overrides.items():
            if modification == "drop":
                # Remove feature
                if feature_name in result_df.columns:
                    result_df = result_df.drop(columns=[feature_name])
            
            elif modification == "zero":
                # Set feature to zero
                if feature_name in result_df.columns:
                    result_df[feature_name] = 0
            
            elif modification == "mean":
                # Set feature to mean value
                if feature_name in result_df.columns:
                    result_df[feature_name] = result_df[feature_name].mean()
            
            elif isinstance(modification, (int, float)):
                # Set feature to specific value
                result_df[feature_name] = modification
            
            elif isinstance(modification, dict) and "multiply" in modification:
                # Scale feature by factor
                if feature_name in result_df.columns:
                    result_df[feature_name] *= modification["multiply"]
        
        return result_df
    
    def _apply_market_scenario(
        self,
        features_df: pd.DataFrame,
        scenario_params: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply market scenario changes to features"""
        
        result_df = features_df.copy()
        
        # Apply interest rate changes
        if "interest_rate_change" in scenario_params:
            rate_change = scenario_params["interest_rate_change"]
            if "mortgage_rate_30y" in result_df.columns:
                result_df["mortgage_rate_30y"] += rate_change
        
        # Apply market price changes
        if "market_price_change" in scenario_params:
            price_change = scenario_params["market_price_change"]
            price_cols = [col for col in result_df.columns if "price" in col.lower()]
            for col in price_cols:
                result_df[col] *= (1 + price_change)
        
        # Apply inventory changes
        if "inventory_change" in scenario_params:
            inventory_change = scenario_params["inventory_change"]
            if "inventory_months" in result_df.columns:
                result_df["inventory_months"] *= (1 + inventory_change)
        
        # Apply economic indicator changes
        if "unemployment_change" in scenario_params:
            unemployment_change = scenario_params["unemployment_change"]
            if "unemployment_rate" in result_df.columns:
                result_df["unemployment_rate"] += unemployment_change
        
        return result_df
    
    def _apply_threshold(
        self,
        proba: Optional[Dict[str, float]],
        thresholds: Dict[str, float]
    ) -> Any:
        """Apply new thresholds to prediction probabilities"""
        
        if not proba:
            return None
        
        # Default threshold
        default_threshold = thresholds.get("default", 0.5)
        
        # Assuming binary classification for now
        if "positive_class_prob" in proba:
            return 1 if proba["positive_class_prob"] >= default_threshold else 0
        
        return None
    
    async def _load_model(self, model_version: str) -> Any:
        """Load model from MLflow"""
        
        # Mock model loading - in production this would use MLflow
        class MockModel:
            def __init__(self, version: str):
                self.version = version
                
            def predict(self, X: pd.DataFrame) -> np.ndarray:
                # Mock predictions
                n_samples = len(X)
                return np.random.rand(n_samples)
            
            def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
                # Mock prediction probabilities
                n_samples = len(X)
                proba_positive = np.random.rand(n_samples)
                return np.column_stack([1 - proba_positive, proba_positive])
        
        return MockModel(model_version)
    
    async def _load_model_with_params(
        self,
        model_version: str,
        param_overrides: Dict[str, Any]
    ) -> Any:
        """Load model and apply parameter modifications"""
        
        # Mock parameter-modified model
        base_model = await self._load_model(model_version)
        
        # In production, this would rebuild the model with new parameters
        class ModifiedModel:
            def __init__(self, base_model, params):
                self.base_model = base_model
                self.params = params
            
            def predict(self, X: pd.DataFrame) -> np.ndarray:
                base_pred = self.base_model.predict(X)
                # Apply parameter modifications
                modifier = self.params.get("prediction_modifier", 1.0)
                return base_pred * modifier
            
            def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
                return self.base_model.predict_proba(X)
        
        return ModifiedModel(base_model, param_overrides)
    
    async def _generate_predictions(
        self,
        features_df: pd.DataFrame,
        model: Any,
        model_version: str
    ) -> List[PredictionSnapshot]:
        """Generate predictions using model on features"""
        
        predictions = []
        
        # Get feature columns (exclude metadata)
        feature_cols = [col for col in features_df.columns 
                       if col not in ["property_id", "train_start", "train_end", 
                                    "prediction_date", "horizon_end"]]
        
        X = features_df[feature_cols].fillna(0)
        
        # Generate predictions
        pred_values = model.predict(X)
        pred_probas = model.predict_proba(X) if hasattr(model, 'predict_proba') else None
        
        for idx, row in features_df.iterrows():
            proba_dict = {}
            if pred_probas is not None:
                proba_dict = {
                    "negative_class_prob": float(pred_probas[idx, 0]),
                    "positive_class_prob": float(pred_probas[idx, 1])
                }
            
            pred = PredictionSnapshot(
                snapshot_id=f"pred_{row['property_id']}_{int(datetime.now().timestamp())}",
                backtest_run_id="",  # Will be set by caller
                entity_id=row["property_id"],
                prediction_value=float(pred_values[idx]),
                prediction_proba=proba_dict if proba_dict else None,
                feature_values=row[feature_cols].to_dict(),
                model_version=model_version,
                created_at=datetime.now()
            )
            predictions.append(pred)
        
        return predictions
    
    async def _save_predictions(
        self,
        run_id: str,
        predictions: List[PredictionSnapshot]
    ) -> None:
        """Save prediction snapshots to database"""
        
        for pred in predictions:
            pred.backtest_run_id = run_id
            await self.data_access.create_prediction_snapshot(pred)
    
    async def compare_replay_results(
        self,
        original_run_id: str,
        replay_run_id: str
    ) -> Dict[str, Any]:
        """Compare results between original and replay runs"""
        
        # Load both runs
        original_run = await self.data_access.get_backtest_run(original_run_id)
        replay_run = await self.data_access.get_backtest_run(replay_run_id)
        
        # Load predictions
        original_preds = await self.data_access.get_prediction_snapshots(original_run_id)
        replay_preds = await self.data_access.get_prediction_snapshots(replay_run_id)
        
        # Convert to DataFrames for analysis
        orig_df = pd.DataFrame([
            {
                "entity_id": p.entity_id,
                "prediction": p.prediction_value,
                "proba": p.prediction_proba.get("positive_class_prob", 0.5) if p.prediction_proba else 0.5
            }
            for p in original_preds
        ])
        
        replay_df = pd.DataFrame([
            {
                "entity_id": p.entity_id,
                "prediction": p.prediction_value,
                "proba": p.prediction_proba.get("positive_class_prob", 0.5) if p.prediction_proba else 0.5
            }
            for p in replay_preds
        ])
        
        # Merge for comparison
        comparison_df = orig_df.merge(
            replay_df,
            on="entity_id",
            suffixes=("_orig", "_replay")
        )
        
        # Calculate comparison metrics
        prediction_agreement = (
            comparison_df["prediction_orig"] == comparison_df["prediction_replay"]
        ).mean()
        
        proba_correlation = comparison_df["proba_orig"].corr(comparison_df["proba_replay"])
        mean_proba_diff = (comparison_df["proba_replay"] - comparison_df["proba_orig"]).mean()
        
        return {
            "original_run": original_run,
            "replay_run": replay_run,
            "comparison_metrics": {
                "prediction_agreement": float(prediction_agreement),
                "probability_correlation": float(proba_correlation) if not pd.isna(proba_correlation) else 0.0,
                "mean_probability_difference": float(mean_proba_diff),
                "total_predictions": len(comparison_df)
            },
            "detailed_comparison": comparison_df.to_dict("records")
        }

# Global instance
replay_engine = ReplayEngine()
