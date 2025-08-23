"""
Uplift analysis and causal inference for backtesting
Measures incremental impact of predictions vs baseline strategies
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from scipy import stats
from sklearn.model_selection import StratifiedKFold

from .config import config
from .schemas import BacktestRun, PredictionSnapshot
from .data_access import BacktestDataAccess

@dataclass
class UpliftResults:
    """Results of uplift analysis"""
    treatment_effect: float
    confidence_interval: Tuple[float, float]
    p_value: float
    statistical_significance: bool
    baseline_performance: float
    treatment_performance: float
    relative_uplift: float
    absolute_uplift: float

@dataclass
class CohortUplift:
    """Uplift analysis for specific cohort"""
    cohort_name: str
    cohort_description: str
    sample_size: int
    uplift_results: UpliftResults

class UpliftAnalyzer:
    """Analyzes uplift and causal impact of predictions"""
    
    def __init__(self, data_access: Optional[BacktestDataAccess] = None):
        self.data_access = data_access or BacktestDataAccess()
        self.significance_level = config.statistical_significance_level
    
    async def calculate_uplift_vs_baseline(
        self,
        treatment_run_id: str,
        baseline_strategy: str = "random",
        outcome_column: str = "actual_success"
    ) -> UpliftResults:
        """
        Calculate uplift of treatment predictions vs baseline strategy
        
        Args:
            treatment_run_id: ID of backtest run to evaluate
            baseline_strategy: "random", "always_invest", "never_invest", or another run_id
            outcome_column: Column name for outcome measurement
            
        Returns:
            UpliftResults with statistical analysis
        """
        # Load treatment predictions and outcomes
        treatment_data = await self._load_run_data(treatment_run_id, outcome_column)
        
        # Generate or load baseline predictions
        baseline_data = await self._generate_baseline_data(
            treatment_data, baseline_strategy, outcome_column
        )
        
        # Calculate uplift
        treatment_performance = self._calculate_performance(
            treatment_data, "treatment_prediction", outcome_column
        )
        baseline_performance = self._calculate_performance(
            baseline_data, "baseline_prediction", outcome_column
        )
        
        # Statistical significance testing
        p_value, confidence_interval = self._calculate_significance(
            treatment_data, baseline_data, outcome_column
        )
        
        # Calculate uplift metrics
        absolute_uplift = treatment_performance - baseline_performance
        relative_uplift = (absolute_uplift / baseline_performance) if baseline_performance > 0 else 0
        
        return UpliftResults(
            treatment_effect=absolute_uplift,
            confidence_interval=confidence_interval,
            p_value=p_value,
            statistical_significance=p_value < self.significance_level,
            baseline_performance=baseline_performance,
            treatment_performance=treatment_performance,
            relative_uplift=relative_uplift,
            absolute_uplift=absolute_uplift
        )
    
    async def _load_run_data(self, run_id: str, outcome_column: str) -> pd.DataFrame:
        """Load predictions and outcomes for a run"""
        
        # Load predictions
        predictions = await self.data_access.get_prediction_snapshots(run_id)
        if not predictions:
            raise ValueError(f"No predictions found for run {run_id}")
        
        # Convert to DataFrame
        pred_records = []
        for pred in predictions:
            record = {
                "entity_id": pred.entity_id,
                "treatment_prediction": pred.prediction_value,
                "prediction_timestamp": pred.created_at
            }
            
            # Add probabilities if available
            if pred.prediction_proba:
                record.update(pred.prediction_proba)
            
            # Add key features for stratification
            if pred.feature_values:
                key_features = ["sqft", "bedrooms", "median_price_zip", "mortgage_rate_30y"]
                for feature in key_features:
                    if feature in pred.feature_values:
                        record[f"feature_{feature}"] = pred.feature_values[feature]
            
            pred_records.append(record)
        
        pred_df = pd.DataFrame(pred_records)
        
        # Load actual outcomes (mock implementation)
        outcomes_df = await self._load_actual_outcomes(run_id, outcome_column)
        
        # Merge predictions with outcomes
        merged_df = pred_df.merge(outcomes_df, on="entity_id", how="inner")
        
        return merged_df
    
    async def _load_actual_outcomes(self, run_id: str, outcome_column: str) -> pd.DataFrame:
        """Load actual outcomes for entities in the run"""
        
        # Mock outcomes - in production this would query actual data
        predictions = await self.data_access.get_prediction_snapshots(run_id)
        entity_ids = [p.entity_id for p in predictions]
        n_entities = len(entity_ids)
        
        np.random.seed(42)  # For reproducible results
        
        if outcome_column == "actual_success":
            # Binary outcome: investment success
            outcomes = np.random.binomial(1, 0.6, n_entities)
        elif outcome_column == "actual_appreciation":
            # Continuous outcome: price appreciation
            outcomes = np.random.normal(0.05, 0.1, n_entities)
        elif outcome_column == "actual_rental_yield":
            # Continuous outcome: rental yield
            outcomes = np.random.normal(0.06, 0.02, n_entities)
        else:
            # Default to success rate
            outcomes = np.random.binomial(1, 0.6, n_entities)
        
        return pd.DataFrame({
            "entity_id": entity_ids,
            outcome_column: outcomes
        })
    
    async def _generate_baseline_data(
        self,
        treatment_data: pd.DataFrame,
        baseline_strategy: str,
        outcome_column: str
    ) -> pd.DataFrame:
        """Generate baseline predictions for comparison"""
        
        baseline_data = treatment_data.copy()
        
        if baseline_strategy == "random":
            # Random predictions
            np.random.seed(123)  # Different seed than treatment
            if outcome_column in ["actual_success"]:
                baseline_data["baseline_prediction"] = np.random.binomial(
                    1, 0.5, len(baseline_data)
                )
            else:
                baseline_data["baseline_prediction"] = np.random.normal(
                    0, 0.05, len(baseline_data)
                )
        
        elif baseline_strategy == "always_invest":
            # Always predict positive
            baseline_data["baseline_prediction"] = 1
        
        elif baseline_strategy == "never_invest":
            # Always predict negative
            baseline_data["baseline_prediction"] = 0
        
        elif baseline_strategy == "market_average":
            # Predict market average performance
            if outcome_column == "actual_success":
                baseline_data["baseline_prediction"] = 1  # Always invest at market rate
            else:
                market_average = baseline_data[outcome_column].mean()
                baseline_data["baseline_prediction"] = market_average
        
        elif baseline_strategy.startswith("run_"):
            # Use another run as baseline
            baseline_run_id = baseline_strategy[4:]  # Remove "run_" prefix
            baseline_preds = await self.data_access.get_prediction_snapshots(baseline_run_id)
            
            baseline_dict = {pred.entity_id: pred.prediction_value for pred in baseline_preds}
            baseline_data["baseline_prediction"] = baseline_data["entity_id"].map(baseline_dict)
            
        else:
            raise ValueError(f"Unknown baseline strategy: {baseline_strategy}")
        
        return baseline_data
    
    def _calculate_performance(
        self,
        data: pd.DataFrame,
        prediction_column: str,
        outcome_column: str
    ) -> float:
        """Calculate performance metric for predictions"""
        
        y_pred = data[prediction_column]
        y_true = data[outcome_column]
        
        if outcome_column in ["actual_success"]:
            # Binary classification: use accuracy
            return (y_pred == y_true).mean()
        else:
            # Regression: use negative MAE (higher is better)
            return -np.mean(np.abs(y_pred - y_true))
    
    def _calculate_significance(
        self,
        treatment_data: pd.DataFrame,
        baseline_data: pd.DataFrame,
        outcome_column: str
    ) -> Tuple[float, Tuple[float, float]]:
        """Calculate statistical significance and confidence interval"""
        
        # Performance for treatment and baseline
        treatment_perf = self._calculate_performance(
            treatment_data, "treatment_prediction", outcome_column
        )
        baseline_perf = self._calculate_performance(
            baseline_data, "baseline_prediction", outcome_column
        )
        
        # Use bootstrap to calculate confidence interval
        n_bootstrap = 1000
        bootstrap_diffs = []
        
        n_samples = len(treatment_data)
        
        for _ in range(n_bootstrap):
            # Bootstrap sample
            boot_indices = np.random.choice(n_samples, n_samples, replace=True)
            boot_treatment = treatment_data.iloc[boot_indices]
            boot_baseline = baseline_data.iloc[boot_indices]
            
            # Calculate performance difference
            boot_treatment_perf = self._calculate_performance(
                boot_treatment, "treatment_prediction", outcome_column
            )
            boot_baseline_perf = self._calculate_performance(
                boot_baseline, "baseline_prediction", outcome_column
            )
            
            bootstrap_diffs.append(boot_treatment_perf - boot_baseline_perf)
        
        bootstrap_diffs = np.array(bootstrap_diffs)
        
        # Calculate p-value (two-tailed test)
        observed_diff = treatment_perf - baseline_perf
        p_value = 2 * min(
            (bootstrap_diffs <= 0).mean(),
            (bootstrap_diffs >= 0).mean()
        )
        
        # Calculate confidence interval
        alpha = self.significance_level
        ci_lower = np.percentile(bootstrap_diffs, 100 * alpha / 2)
        ci_upper = np.percentile(bootstrap_diffs, 100 * (1 - alpha / 2))
        
        return p_value, (ci_lower, ci_upper)
    
    async def analyze_cohort_uplift(
        self,
        treatment_run_id: str,
        cohort_definitions: Dict[str, Dict[str, Any]],
        baseline_strategy: str = "random",
        outcome_column: str = "actual_success"
    ) -> List[CohortUplift]:
        """
        Analyze uplift for different cohorts
        
        Args:
            treatment_run_id: ID of treatment run
            cohort_definitions: Dict defining cohorts (e.g., {"high_price": {"feature_median_price_zip": ">500000"}})
            baseline_strategy: Baseline strategy to compare against
            outcome_column: Outcome column for measurement
            
        Returns:
            List of CohortUplift results
        """
        # Load full dataset
        treatment_data = await self._load_run_data(treatment_run_id, outcome_column)
        
        cohort_results = []
        
        for cohort_name, cohort_def in cohort_definitions.items():
            # Filter data for this cohort
            cohort_data = self._filter_cohort(treatment_data, cohort_def)
            
            if cohort_data.empty:
                continue
            
            # Generate baseline for this cohort
            cohort_baseline = await self._generate_baseline_data(
                cohort_data, baseline_strategy, outcome_column
            )
            
            # Calculate uplift for this cohort
            uplift_results = await self._calculate_cohort_uplift(
                cohort_data, cohort_baseline, outcome_column
            )
            
            cohort_results.append(CohortUplift(
                cohort_name=cohort_name,
                cohort_description=str(cohort_def),
                sample_size=len(cohort_data),
                uplift_results=uplift_results
            ))
        
        return cohort_results
    
    def _filter_cohort(
        self,
        data: pd.DataFrame,
        cohort_definition: Dict[str, Any]
    ) -> pd.DataFrame:
        """Filter data based on cohort definition"""
        
        filtered_data = data.copy()
        
        for feature, condition in cohort_definition.items():
            if feature not in filtered_data.columns:
                continue
            
            if isinstance(condition, str):
                if condition.startswith(">"):
                    threshold = float(condition[1:])
                    filtered_data = filtered_data[filtered_data[feature] > threshold]
                elif condition.startswith("<"):
                    threshold = float(condition[1:])
                    filtered_data = filtered_data[filtered_data[feature] < threshold]
                elif condition.startswith("=="):
                    value = condition[2:]
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                    filtered_data = filtered_data[filtered_data[feature] == value]
            
            elif isinstance(condition, (list, tuple)):
                # Range condition
                if len(condition) == 2:
                    filtered_data = filtered_data[
                        (filtered_data[feature] >= condition[0]) &
                        (filtered_data[feature] <= condition[1])
                    ]
        
        return filtered_data
    
    async def _calculate_cohort_uplift(
        self,
        treatment_data: pd.DataFrame,
        baseline_data: pd.DataFrame,
        outcome_column: str
    ) -> UpliftResults:
        """Calculate uplift for a specific cohort"""
        
        treatment_performance = self._calculate_performance(
            treatment_data, "treatment_prediction", outcome_column
        )
        baseline_performance = self._calculate_performance(
            baseline_data, "baseline_prediction", outcome_column
        )
        
        # Statistical significance (simplified for cohorts)
        p_value, confidence_interval = self._calculate_significance(
            treatment_data, baseline_data, outcome_column
        )
        
        absolute_uplift = treatment_performance - baseline_performance
        relative_uplift = (absolute_uplift / baseline_performance) if baseline_performance > 0 else 0
        
        return UpliftResults(
            treatment_effect=absolute_uplift,
            confidence_interval=confidence_interval,
            p_value=p_value,
            statistical_significance=p_value < self.significance_level,
            baseline_performance=baseline_performance,
            treatment_performance=treatment_performance,
            relative_uplift=relative_uplift,
            absolute_uplift=absolute_uplift
        )
    
    async def calculate_incremental_roi(
        self,
        treatment_run_id: str,
        baseline_strategy: str = "random",
        cost_per_prediction: float = 10.0,
        value_per_success: float = 5000.0,
        cost_per_failure: float = 1000.0
    ) -> Dict[str, float]:
        """
        Calculate incremental ROI of predictions vs baseline
        
        Args:
            treatment_run_id: Treatment run to analyze
            baseline_strategy: Baseline strategy for comparison
            cost_per_prediction: Cost to generate each prediction
            value_per_success: Value generated per successful prediction
            cost_per_failure: Cost incurred per failed prediction
            
        Returns:
            Dictionary with ROI metrics
        """
        # Load data
        treatment_data = await self._load_run_data(treatment_run_id, "actual_success")
        baseline_data = await self._generate_baseline_data(
            treatment_data, baseline_strategy, "actual_success"
        )
        
        n_predictions = len(treatment_data)
        
        # Treatment economics
        treatment_successes = (
            (treatment_data["treatment_prediction"] == 1) & 
            (treatment_data["actual_success"] == 1)
        ).sum()
        treatment_failures = (
            (treatment_data["treatment_prediction"] == 1) & 
            (treatment_data["actual_success"] == 0)
        ).sum()
        
        treatment_revenue = treatment_successes * value_per_success
        treatment_costs = (n_predictions * cost_per_prediction + 
                         treatment_failures * cost_per_failure)
        treatment_profit = treatment_revenue - treatment_costs
        
        # Baseline economics  
        baseline_successes = (
            (baseline_data["baseline_prediction"] == 1) & 
            (baseline_data["actual_success"] == 1)
        ).sum()
        baseline_failures = (
            (baseline_data["baseline_prediction"] == 1) & 
            (baseline_data["actual_success"] == 0)
        ).sum()
        
        baseline_revenue = baseline_successes * value_per_success
        baseline_costs = (n_predictions * cost_per_prediction + 
                        baseline_failures * cost_per_failure)
        baseline_profit = baseline_revenue - baseline_costs
        
        # ROI calculations
        incremental_profit = treatment_profit - baseline_profit
        incremental_investment = treatment_costs - baseline_costs
        
        incremental_roi = (
            incremental_profit / max(abs(incremental_investment), 1)
        ) if incremental_investment != 0 else 0
        
        treatment_roi = treatment_profit / max(treatment_costs, 1)
        baseline_roi = baseline_profit / max(baseline_costs, 1)
        
        return {
            "treatment_profit": float(treatment_profit),
            "baseline_profit": float(baseline_profit),
            "incremental_profit": float(incremental_profit),
            "treatment_roi": float(treatment_roi),
            "baseline_roi": float(baseline_roi),
            "incremental_roi": float(incremental_roi),
            "treatment_successes": int(treatment_successes),
            "baseline_successes": int(baseline_successes),
            "incremental_successes": int(treatment_successes - baseline_successes)
        }
    
    async def analyze_feature_impact(
        self,
        treatment_run_id: str,
        feature_columns: List[str],
        outcome_column: str = "actual_success"
    ) -> Dict[str, float]:
        """
        Analyze impact of individual features on predictions
        
        Returns:
            Dictionary mapping feature names to impact scores
        """
        # Load data
        treatment_data = await self._load_run_data(treatment_run_id, outcome_column)
        
        feature_impacts = {}
        
        for feature in feature_columns:
            if feature not in treatment_data.columns:
                continue
            
            # Calculate correlation between feature and outcome
            feature_values = treatment_data[feature].dropna()
            outcome_values = treatment_data.loc[feature_values.index, outcome_column]
            
            if len(feature_values) > 10:
                correlation = feature_values.corr(outcome_values)
                feature_impacts[feature] = abs(correlation) if not pd.isna(correlation) else 0.0
        
        return feature_impacts
    
    async def generate_uplift_report(
        self,
        treatment_run_id: str,
        baseline_strategy: str = "random",
        outcome_column: str = "actual_success"
    ) -> Dict[str, Any]:
        """Generate comprehensive uplift analysis report"""
        
        # Main uplift analysis
        uplift_results = await self.calculate_uplift_vs_baseline(
            treatment_run_id, baseline_strategy, outcome_column
        )
        
        # Cohort analysis
        cohort_definitions = {
            "high_price": {"feature_median_price_zip": ">500000"},
            "low_price": {"feature_median_price_zip": "<300000"},
            "large_homes": {"feature_sqft": ">2500"},
            "small_homes": {"feature_sqft": "<1500"},
        }
        
        cohort_results = await self.analyze_cohort_uplift(
            treatment_run_id, cohort_definitions, baseline_strategy, outcome_column
        )
        
        # ROI analysis
        roi_results = await self.calculate_incremental_roi(treatment_run_id, baseline_strategy)
        
        # Feature impact analysis
        feature_impacts = await self.analyze_feature_impact(
            treatment_run_id,
            ["feature_sqft", "feature_bedrooms", "feature_median_price_zip", "feature_mortgage_rate_30y"],
            outcome_column
        )
        
        return {
            "treatment_run_id": treatment_run_id,
            "baseline_strategy": baseline_strategy,
            "outcome_column": outcome_column,
            "overall_uplift": {
                "treatment_effect": uplift_results.treatment_effect,
                "relative_uplift_pct": uplift_results.relative_uplift * 100,
                "statistical_significance": uplift_results.statistical_significance,
                "p_value": uplift_results.p_value,
                "confidence_interval": uplift_results.confidence_interval
            },
            "cohort_analysis": [
                {
                    "cohort_name": cohort.cohort_name,
                    "sample_size": cohort.sample_size,
                    "uplift": cohort.uplift_results.treatment_effect,
                    "significant": cohort.uplift_results.statistical_significance
                }
                for cohort in cohort_results
            ],
            "roi_analysis": roi_results,
            "feature_impacts": feature_impacts,
            "generated_at": datetime.now().isoformat()
        }

# Global instance
uplift_analyzer = UpliftAnalyzer()
