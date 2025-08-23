"""
Metrics calculation and performance evaluation for backtesting
Computes standard ML metrics plus real estate specific KPIs
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, precision_recall_curve, roc_curve,
    mean_squared_error, mean_absolute_error, r2_score
)
import warnings
warnings.filterwarnings("ignore")

from .config import config
from .schemas import BacktestResult, MetricsSummary, PredictionSnapshot
from .data_access import BacktestDataAccess

@dataclass
class ClassificationMetrics:
    """Standard classification metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: Dict[str, int]
    
@dataclass
class RegressionMetrics:
    """Standard regression metrics"""
    mse: float
    rmse: float
    mae: float
    r2: float
    mape: float
    
@dataclass
class RealEstateMetrics:
    """Real estate specific metrics"""
    investment_return_accuracy: float
    risk_adjusted_return: float
    portfolio_diversification_score: float
    market_timing_accuracy: float
    deal_recommendation_precision: float
    false_positive_cost: float
    false_negative_cost: float
    
@dataclass
class PerformanceMetrics:
    """Complete metrics package"""
    classification: Optional[ClassificationMetrics]
    regression: Optional[RegressionMetrics]
    real_estate: RealEstateMetrics
    temporal_metrics: Dict[str, float]
    cohort_metrics: Dict[str, Dict[str, float]]
    
class MetricsCalculator:
    """Calculates comprehensive performance metrics for backtesting"""
    
    def __init__(self, data_access: Optional[BacktestDataAccess] = None):
        self.data_access = data_access or BacktestDataAccess()
        self.default_thresholds = config.default_prediction_thresholds
        
    async def calculate_backtest_metrics(
        self,
        run_id: str,
        actual_outcomes: Optional[pd.DataFrame] = None
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive metrics for a backtest run
        
        Args:
            run_id: Backtest run identifier
            actual_outcomes: DataFrame with actual outcomes (if available)
            
        Returns:
            Complete performance metrics
        """
        # Load predictions
        predictions = await self.data_access.get_prediction_snapshots(run_id)
        if not predictions:
            raise ValueError(f"No predictions found for run {run_id}")
        
        # Convert to DataFrame
        pred_df = self._predictions_to_dataframe(predictions)
        
        # Load or generate actual outcomes
        if actual_outcomes is None:
            actual_outcomes = await self._load_actual_outcomes(run_id)
        
        # Merge predictions with actuals
        merged_df = pred_df.merge(
            actual_outcomes,
            on="entity_id",
            how="inner"
        )
        
        if merged_df.empty:
            raise ValueError("No matching predictions and actuals found")
        
        # Calculate different types of metrics
        classification_metrics = self._calculate_classification_metrics(merged_df)
        regression_metrics = self._calculate_regression_metrics(merged_df)
        real_estate_metrics = self._calculate_real_estate_metrics(merged_df)
        temporal_metrics = self._calculate_temporal_metrics(merged_df)
        cohort_metrics = self._calculate_cohort_metrics(merged_df)
        
        return PerformanceMetrics(
            classification=classification_metrics,
            regression=regression_metrics,
            real_estate=real_estate_metrics,
            temporal_metrics=temporal_metrics,
            cohort_metrics=cohort_metrics
        )
    
    def _predictions_to_dataframe(self, predictions: List[PredictionSnapshot]) -> pd.DataFrame:
        """Convert prediction snapshots to DataFrame"""
        
        records = []
        for pred in predictions:
            record = {
                "entity_id": pred.entity_id,
                "prediction_value": pred.prediction_value,
                "prediction_timestamp": pred.created_at
            }
            
            # Extract probabilities if available
            if pred.prediction_proba:
                record.update(pred.prediction_proba)
            
            # Extract key features
            if pred.feature_values:
                # Include most important features for analysis
                key_features = [
                    "sqft", "bedrooms", "bathrooms", "age_years",
                    "median_price_zip", "days_on_market_avg", "mortgage_rate_30y"
                ]
                for feature in key_features:
                    if feature in pred.feature_values:
                        record[f"feature_{feature}"] = pred.feature_values[feature]
            
            records.append(record)
        
        return pd.DataFrame(records)
    
    async def _load_actual_outcomes(self, run_id: str) -> pd.DataFrame:
        """Load actual outcomes for comparison (mock implementation)"""
        
        # In production, this would query actual sales/rental data
        # For now, generate realistic mock outcomes
        
        # Get run details to understand prediction horizon
        run_details = await self.data_access.get_backtest_run(run_id)
        if not run_details:
            raise ValueError(f"Run {run_id} not found")
        
        # Load predictions to get entity IDs
        predictions = await self.data_access.get_prediction_snapshots(run_id)
        entity_ids = [p.entity_id for p in predictions]
        
        # Generate mock actual outcomes
        n_entities = len(entity_ids)
        
        # Simulate realistic real estate outcomes
        np.random.seed(42)  # For reproducible results
        
        # Investment success (binary classification)
        success_rate = 0.65  # 65% of investments are successful
        actual_success = np.random.binomial(1, success_rate, n_entities)
        
        # Price appreciation (regression)
        annual_appreciation = 0.05  # 5% annual appreciation
        horizon_years = run_details.horizon_months / 12.0
        expected_appreciation = annual_appreciation * horizon_years
        
        actual_appreciation = np.random.normal(
            expected_appreciation,
            expected_appreciation * 0.4,  # 40% volatility
            n_entities
        )
        
        # Rental yield (additional regression target)
        actual_rental_yield = np.random.normal(0.06, 0.02, n_entities)  # 6% ± 2%
        
        # Days to sale/rent
        actual_days_to_transaction = np.random.lognormal(3.5, 0.8, n_entities)
        
        return pd.DataFrame({
            "entity_id": entity_ids,
            "actual_success": actual_success,
            "actual_appreciation": actual_appreciation,
            "actual_rental_yield": actual_rental_yield,
            "actual_days_to_transaction": actual_days_to_transaction,
            "outcome_date": datetime.now()
        })
    
    def _calculate_classification_metrics(self, df: pd.DataFrame) -> Optional[ClassificationMetrics]:
        """Calculate classification metrics if applicable"""
        
        if "actual_success" not in df.columns:
            return None
        
        y_true = df["actual_success"]
        
        # Use prediction_value as binary prediction if available
        if "prediction_value" in df.columns:
            y_pred = df["prediction_value"]
        else:
            # Convert probabilities to binary predictions
            threshold = self.default_thresholds.get("investment_success", 0.5)
            y_pred = (df.get("positive_class_prob", df.get("proba", 0.5)) >= threshold).astype(int)
        
        # Calculate basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        # ROC AUC (requires probabilities)
        roc_auc = 0.5
        if "positive_class_prob" in df.columns or "proba" in df.columns:
            y_proba = df.get("positive_class_prob", df.get("proba", 0.5))
            try:
                roc_auc = roc_auc_score(y_true, y_proba)
            except ValueError:
                roc_auc = 0.5  # No discrimination
        
        # Confusion matrix
        tn = ((y_true == 0) & (y_pred == 0)).sum()
        fp = ((y_true == 0) & (y_pred == 1)).sum()
        fn = ((y_true == 1) & (y_pred == 0)).sum()
        tp = ((y_true == 1) & (y_pred == 1)).sum()
        
        confusion_matrix = {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp)
        }
        
        return ClassificationMetrics(
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            roc_auc=float(roc_auc),
            confusion_matrix=confusion_matrix
        )
    
    def _calculate_regression_metrics(self, df: pd.DataFrame) -> Optional[RegressionMetrics]:
        """Calculate regression metrics if applicable"""
        
        # Check for regression targets
        target_cols = ["actual_appreciation", "actual_rental_yield", "actual_days_to_transaction"]
        available_targets = [col for col in target_cols if col in df.columns]
        
        if not available_targets:
            return None
        
        # Use first available target (usually appreciation)
        target_col = available_targets[0]
        y_true = df[target_col]
        
        # Use prediction_value as regression prediction
        if "prediction_value" in df.columns:
            y_pred = df["prediction_value"]
        else:
            # If no direct prediction, use a derived value
            y_pred = np.full(len(y_true), y_true.mean())
        
        # Calculate metrics
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # Mean Absolute Percentage Error
        mape = np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-8))) * 100
        
        return RegressionMetrics(
            mse=float(mse),
            rmse=float(rmse),
            mae=float(mae),
            r2=float(r2),
            mape=float(mape)
        )
    
    def _calculate_real_estate_metrics(self, df: pd.DataFrame) -> RealEstateMetrics:
        """Calculate real estate specific metrics"""
        
        # Investment return accuracy
        if "actual_appreciation" in df.columns and "prediction_value" in df.columns:
            appreciation_error = np.abs(df["actual_appreciation"] - df["prediction_value"])
            investment_accuracy = 1.0 - np.mean(appreciation_error / np.abs(df["actual_appreciation"]).clip(0.01))
            investment_accuracy = max(0.0, investment_accuracy)
        else:
            investment_accuracy = 0.5
        
        # Risk-adjusted return (Sharpe-like ratio)
        if "actual_appreciation" in df.columns:
            returns = df["actual_appreciation"]
            risk_free_rate = 0.02  # Assume 2% risk-free rate
            excess_returns = returns - risk_free_rate
            sharpe_ratio = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
            risk_adjusted_return = max(-2.0, min(2.0, sharpe_ratio))  # Bound to reasonable range
        else:
            risk_adjusted_return = 0.0
        
        # Portfolio diversification score (based on feature diversity)
        feature_cols = [col for col in df.columns if col.startswith("feature_")]
        if feature_cols:
            # Calculate correlation matrix and use average correlation as diversification measure
            feature_df = df[feature_cols].select_dtypes(include=[np.number])
            if not feature_df.empty and len(feature_df.columns) > 1:
                corr_matrix = feature_df.corr().abs()
                avg_correlation = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
                diversification_score = 1.0 - avg_correlation
            else:
                diversification_score = 0.5
        else:
            diversification_score = 0.5
        
        # Market timing accuracy (simplified)
        market_timing_accuracy = investment_accuracy * 0.8  # Correlated with investment accuracy
        
        # Deal recommendation precision
        if "actual_success" in df.columns:
            true_positives = ((df.get("prediction_value", 0) == 1) & (df["actual_success"] == 1)).sum()
            predicted_positives = (df.get("prediction_value", 0) == 1).sum()
            deal_precision = true_positives / max(1, predicted_positives)
        else:
            deal_precision = 0.5
        
        # Cost calculations (simplified business impact)
        if "actual_success" in df.columns:
            # Assume each false positive costs $10K in opportunity cost
            false_positives = ((df.get("prediction_value", 0) == 1) & (df["actual_success"] == 0)).sum()
            false_positive_cost = false_positives * 10000
            
            # Assume each false negative costs $25K in missed opportunity
            false_negatives = ((df.get("prediction_value", 0) == 0) & (df["actual_success"] == 1)).sum()
            false_negative_cost = false_negatives * 25000
        else:
            false_positive_cost = 0.0
            false_negative_cost = 0.0
        
        return RealEstateMetrics(
            investment_return_accuracy=float(investment_accuracy),
            risk_adjusted_return=float(risk_adjusted_return),
            portfolio_diversification_score=float(diversification_score),
            market_timing_accuracy=float(market_timing_accuracy),
            deal_recommendation_precision=float(deal_precision),
            false_positive_cost=float(false_positive_cost),
            false_negative_cost=float(false_negative_cost)
        )
    
    def _calculate_temporal_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate time-based performance metrics"""
        
        metrics = {}
        
        # If we have prediction timestamps, analyze temporal patterns
        if "prediction_timestamp" in df.columns:
            df["prediction_hour"] = pd.to_datetime(df["prediction_timestamp"]).dt.hour
            df["prediction_weekday"] = pd.to_datetime(df["prediction_timestamp"]).dt.weekday
            
            # Performance by hour of day
            if "actual_success" in df.columns:
                hourly_performance = df.groupby("prediction_hour")["actual_success"].mean()
                metrics["best_hour_performance"] = float(hourly_performance.max())
                metrics["worst_hour_performance"] = float(hourly_performance.min())
                metrics["hour_performance_variance"] = float(hourly_performance.var())
        
        # Prediction consistency over time
        if "actual_appreciation" in df.columns and "prediction_value" in df.columns:
            rolling_error = (df["actual_appreciation"] - df["prediction_value"]).abs()
            metrics["prediction_consistency"] = float(1.0 / (1.0 + rolling_error.std()))
        
        # Default values if calculations not possible
        for key in ["best_hour_performance", "worst_hour_performance", 
                   "hour_performance_variance", "prediction_consistency"]:
            if key not in metrics:
                metrics[key] = 0.5
        
        return metrics
    
    def _calculate_cohort_metrics(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate performance metrics by different cohorts"""
        
        cohort_metrics = {}
        
        # Property size cohorts
        if "feature_sqft" in df.columns:
            df["size_cohort"] = pd.cut(
                df["feature_sqft"],
                bins=[0, 1500, 2500, float("inf")],
                labels=["small", "medium", "large"]
            )
            
            size_metrics = {}
            for cohort in ["small", "medium", "large"]:
                cohort_df = df[df["size_cohort"] == cohort]
                if not cohort_df.empty and "actual_success" in cohort_df.columns:
                    accuracy = (
                        cohort_df.get("prediction_value", 0.5) == cohort_df["actual_success"]
                    ).mean()
                    size_metrics[cohort] = {"accuracy": float(accuracy)}
                else:
                    size_metrics[cohort] = {"accuracy": 0.5}
            
            cohort_metrics["property_size"] = size_metrics
        
        # Market condition cohorts
        if "feature_mortgage_rate_30y" in df.columns:
            df["rate_cohort"] = pd.cut(
                df["feature_mortgage_rate_30y"],
                bins=[0, 3.0, 4.0, float("inf")],
                labels=["low_rate", "medium_rate", "high_rate"]
            )
            
            rate_metrics = {}
            for cohort in ["low_rate", "medium_rate", "high_rate"]:
                cohort_df = df[df["rate_cohort"] == cohort]
                if not cohort_df.empty and "actual_appreciation" in cohort_df.columns:
                    mean_return = cohort_df["actual_appreciation"].mean()
                    rate_metrics[cohort] = {"mean_return": float(mean_return)}
                else:
                    rate_metrics[cohort] = {"mean_return": 0.0}
            
            cohort_metrics["interest_rate"] = rate_metrics
        
        # Price range cohorts
        if "feature_median_price_zip" in df.columns:
            df["price_cohort"] = pd.cut(
                df["feature_median_price_zip"],
                bins=[0, 300000, 600000, float("inf")],
                labels=["affordable", "mid_market", "luxury"]
            )
            
            price_metrics = {}
            for cohort in ["affordable", "mid_market", "luxury"]:
                cohort_df = df[df["price_cohort"] == cohort]
                if not cohort_df.empty:
                    if "actual_success" in cohort_df.columns:
                        success_rate = cohort_df["actual_success"].mean()
                        price_metrics[cohort] = {"success_rate": float(success_rate)}
                    else:
                        price_metrics[cohort] = {"success_rate": 0.5}
                else:
                    price_metrics[cohort] = {"success_rate": 0.5}
            
            cohort_metrics["price_range"] = price_metrics
        
        return cohort_metrics
    
    async def calculate_model_drift(
        self,
        baseline_run_id: str,
        comparison_run_id: str
    ) -> Dict[str, float]:
        """Calculate model drift metrics between two runs"""
        
        # Load predictions from both runs
        baseline_preds = await self.data_access.get_prediction_snapshots(baseline_run_id)
        comparison_preds = await self.data_access.get_prediction_snapshots(comparison_run_id)
        
        # Convert to DataFrames
        baseline_df = self._predictions_to_dataframe(baseline_preds)
        comparison_df = self._predictions_to_dataframe(comparison_preds)
        
        # Calculate drift metrics
        drift_metrics = {}
        
        # Prediction distribution shift
        if "prediction_value" in baseline_df.columns and "prediction_value" in comparison_df.columns:
            baseline_mean = baseline_df["prediction_value"].mean()
            comparison_mean = comparison_df["prediction_value"].mean()
            mean_shift = abs(comparison_mean - baseline_mean)
            
            baseline_std = baseline_df["prediction_value"].std()
            comparison_std = comparison_df["prediction_value"].std()
            std_shift = abs(comparison_std - baseline_std)
            
            drift_metrics["mean_prediction_shift"] = float(mean_shift)
            drift_metrics["std_prediction_shift"] = float(std_shift)
        
        # Feature distribution shift (if available)
        feature_cols = [col for col in baseline_df.columns if col.startswith("feature_")]
        if feature_cols:
            feature_drift_scores = []
            for col in feature_cols:
                if col in comparison_df.columns:
                    # Simple Kolmogorov-Smirnov-like test
                    baseline_vals = baseline_df[col].dropna()
                    comparison_vals = comparison_df[col].dropna()
                    
                    if len(baseline_vals) > 0 and len(comparison_vals) > 0:
                        # Calculate difference in distributions
                        baseline_quantiles = np.quantile(baseline_vals, np.linspace(0, 1, 11))
                        comparison_quantiles = np.quantile(comparison_vals, np.linspace(0, 1, 11))
                        drift_score = np.mean(np.abs(comparison_quantiles - baseline_quantiles))
                        feature_drift_scores.append(drift_score)
            
            if feature_drift_scores:
                drift_metrics["average_feature_drift"] = float(np.mean(feature_drift_scores))
                drift_metrics["max_feature_drift"] = float(np.max(feature_drift_scores))
        
        return drift_metrics
    
    async def save_metrics_summary(
        self,
        run_id: str,
        metrics: PerformanceMetrics
    ) -> MetricsSummary:
        """Save metrics summary to database"""
        
        # Convert metrics to dictionary format for storage
        metrics_dict = {}
        
        if metrics.classification:
            metrics_dict["classification"] = {
                "accuracy": metrics.classification.accuracy,
                "precision": metrics.classification.precision,
                "recall": metrics.classification.recall,
                "f1_score": metrics.classification.f1_score,
                "roc_auc": metrics.classification.roc_auc,
                "confusion_matrix": metrics.classification.confusion_matrix
            }
        
        if metrics.regression:
            metrics_dict["regression"] = {
                "mse": metrics.regression.mse,
                "rmse": metrics.regression.rmse,
                "mae": metrics.regression.mae,
                "r2": metrics.regression.r2,
                "mape": metrics.regression.mape
            }
        
        metrics_dict["real_estate"] = {
            "investment_return_accuracy": metrics.real_estate.investment_return_accuracy,
            "risk_adjusted_return": metrics.real_estate.risk_adjusted_return,
            "portfolio_diversification_score": metrics.real_estate.portfolio_diversification_score,
            "market_timing_accuracy": metrics.real_estate.market_timing_accuracy,
            "deal_recommendation_precision": metrics.real_estate.deal_recommendation_precision,
            "false_positive_cost": metrics.real_estate.false_positive_cost,
            "false_negative_cost": metrics.real_estate.false_negative_cost
        }
        
        metrics_dict["temporal"] = metrics.temporal_metrics
        metrics_dict["cohort"] = metrics.cohort_metrics
        
        # Create summary object
        summary = MetricsSummary(
            summary_id=f"metrics_{run_id}_{int(datetime.now().timestamp())}",
            backtest_run_id=run_id,
            metrics_data=metrics_dict,
            sla_breaches=[],  # Will be calculated separately
            created_at=datetime.now()
        )
        
        # Save to database
        await self.data_access.create_metrics_summary(summary)
        
        return summary

# Global instance
metrics_calculator = MetricsCalculator()
