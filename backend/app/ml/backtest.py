"""
Backtest Module for ML Model Validation
Walk-forward backtesting with performance metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .config import MLConfig, ARTIFACTS_PATH, PLOTS_PATH, METRICS_PATH
from .datasets import DatasetLoader
from .pipelines import (
    RatesForecastPipeline, 
    CapRateForecastPipeline,
    NoiRentForecastPipeline,
    EnsembleScoringPipeline
)
from .scoring import ArbitrageScorer
from .utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class BacktestEngine:
    """Walk-forward backtesting for ML models"""
    
    def __init__(self):
        self.dataset_loader = DatasetLoader()
        self.results = {}
        self.metrics = {}
        
    def run_walk_forward_backtest(self, 
                                 data_months: int = 36,
                                 train_months: int = 18,
                                 test_months: int = 3,
                                 step_months: int = 1) -> Dict[str, Any]:
        """Run walk-forward backtest"""
        
        logger.info(f"Starting walk-forward backtest: {data_months}M data, "
                   f"{train_months}M train, {test_months}M test, {step_months}M step")
        
        # Load data
        property_df, macro_df = self.dataset_loader.synthetic_generator.generate_full_dataset(
            n_properties=15, months_back=data_months
        )
        
        # Get date range for backtesting
        dates = sorted(property_df['date'].unique())
        min_date = dates[0]
        max_date = dates[-1]
        
        # Calculate backtest windows
        backtest_results = []
        current_end_date = min_date + timedelta(days=train_months * 30)
        
        fold = 0
        while current_end_date + timedelta(days=test_months * 30) <= max_date:
            fold += 1
            train_start = current_end_date - timedelta(days=train_months * 30)
            train_end = current_end_date
            test_start = current_end_date + timedelta(days=1)
            test_end = test_start + timedelta(days=test_months * 30)
            
            logger.info(f"Fold {fold}: Train {train_start.strftime('%Y-%m')} to {train_end.strftime('%Y-%m')}, "
                       f"Test {test_start.strftime('%Y-%m')} to {test_end.strftime('%Y-%m')}")
            
            try:
                fold_result = self._run_single_fold(
                    property_df, macro_df, train_start, train_end, test_start, test_end, fold
                )
                backtest_results.append(fold_result)
                
            except Exception as e:
                logger.error(f"Fold {fold} failed: {e}")
                continue
            
            # Move to next window
            current_end_date += timedelta(days=step_months * 30)
        
        # Aggregate results
        aggregated_metrics = self._aggregate_backtest_results(backtest_results)
        
        # Save results
        self._save_backtest_results(backtest_results, aggregated_metrics)
        
        return {
            'fold_results': backtest_results,
            'aggregated_metrics': aggregated_metrics,
            'n_folds': len(backtest_results)
        }
    
    def _run_single_fold(self, property_df: pd.DataFrame, macro_df: pd.DataFrame,
                        train_start: datetime, train_end: datetime,
                        test_start: datetime, test_end: datetime,
                        fold: int) -> Dict[str, Any]:
        """Run a single backtest fold"""
        
        # Split data
        train_prop = property_df[
            (property_df['date'] >= train_start) & (property_df['date'] <= train_end)
        ].copy()
        test_prop = property_df[
            (property_df['date'] >= test_start) & (property_df['date'] <= test_end)
        ].copy()
        
        train_macro = macro_df[
            (macro_df['date'] >= train_start) & (macro_df['date'] <= train_end)
        ].copy()
        test_macro = macro_df[
            (macro_df['date'] >= test_start) & (macro_df['date'] <= test_end)
        ].copy()
        
        logger.info(f"Fold {fold}: {len(train_prop)} train samples, {len(test_prop)} test samples")
        
        # Train models
        rates_pipeline = RatesForecastPipeline()
        caprate_pipeline = CapRateForecastPipeline()
        noi_rent_pipeline = NoiRentForecastPipeline()
        
        try:
            rates_pipeline.fit(train_macro)
            caprate_pipeline.fit(train_prop)
            noi_rent_pipeline.fit(train_prop)
        except Exception as e:
            logger.error(f"Model training failed in fold {fold}: {e}")
            raise
        
        # Generate forecasts
        horizon_months = 3  # Match test period
        
        rates_forecasts = rates_pipeline.predict(horizon_months)
        caprate_forecasts = caprate_pipeline.predict(
            markets=train_prop['market'].unique().tolist(),
            asset_types=train_prop['asset_type'].unique().tolist(),
            horizon_months=horizon_months
        )
        noi_rent_forecasts = noi_rent_pipeline.predict(
            property_ids=train_prop['property_id'].unique().tolist(),
            horizon_months=horizon_months
        )
        
        # Calculate metrics for individual forecasts
        rates_metrics = self._evaluate_rates_forecast(rates_forecasts, test_macro)
        caprate_metrics = self._evaluate_caprate_forecast(caprate_forecasts, test_prop)
        noi_rent_metrics = self._evaluate_noi_rent_forecast(noi_rent_forecasts, test_prop)
        
        # Score opportunities
        scorer = ArbitrageScorer()
        scores = scorer.batch_score(
            test_prop, rates_forecasts, caprate_forecasts, noi_rent_forecasts
        )
        
        # Evaluate scoring performance
        scoring_metrics = self._evaluate_scoring_performance(scores, test_prop)
        
        return {
            'fold': fold,
            'train_period': f"{train_start.strftime('%Y-%m')} to {train_end.strftime('%Y-%m')}",
            'test_period': f"{test_start.strftime('%Y-%m')} to {test_end.strftime('%Y-%m')}",
            'rates_metrics': rates_metrics,
            'caprate_metrics': caprate_metrics,
            'noi_rent_metrics': noi_rent_metrics,
            'scoring_metrics': scoring_metrics,
            'n_train_samples': len(train_prop),
            'n_test_samples': len(test_prop),
            'n_scores': len(scores)
        }
    
    def _evaluate_rates_forecast(self, forecasts: Dict, test_macro: pd.DataFrame) -> Dict[str, float]:
        """Evaluate rates forecasting accuracy"""
        metrics = {}
        
        if test_macro.empty:
            return metrics
        
        # Get actual values for comparison
        test_macro_sorted = test_macro.sort_values('date')
        
        for rate_type in ['base_rate', 'mortgage_30y', 'corp_bbb_spread']:
            if rate_type in forecasts and rate_type in test_macro.columns:
                forecast_data = forecasts[rate_type]
                
                if 'forecasts' in forecast_data and forecast_data['forecasts']:
                    predicted = np.array(forecast_data['forecasts'][:len(test_macro_sorted)])
                    actual = test_macro_sorted[rate_type].values[:len(predicted)]
                    
                    if len(predicted) > 0 and len(actual) > 0:
                        # Mean Absolute Error
                        mae = np.mean(np.abs(predicted - actual))
                        # Mean Absolute Percentage Error
                        mape = np.mean(np.abs((predicted - actual) / (actual + 1e-8))) * 100
                        # Root Mean Square Error
                        rmse = np.sqrt(np.mean((predicted - actual) ** 2))
                        
                        metrics[f'{rate_type}_mae'] = float(mae)
                        metrics[f'{rate_type}_mape'] = float(mape)
                        metrics[f'{rate_type}_rmse'] = float(rmse)
        
        return metrics
    
    def _evaluate_caprate_forecast(self, forecasts: Dict, test_prop: pd.DataFrame) -> Dict[str, float]:
        """Evaluate cap rate forecasting accuracy"""
        metrics = {}
        
        if test_prop.empty or 'cap_rate_observed' not in test_prop.columns:
            return metrics
        
        # Aggregate actual cap rates by segment
        actual_by_segment = test_prop.groupby(['market', 'asset_type'])['cap_rate_observed'].mean()
        
        mae_values = []
        mape_values = []
        
        for segment_name, forecast_data in forecasts.items():
            if 'forecasts' not in forecast_data or not forecast_data['forecasts']:
                continue
            
            market = forecast_data.get('market', 'unknown')
            asset_type = forecast_data.get('asset_type', 'unknown')
            
            if (market, asset_type) in actual_by_segment.index:
                predicted = forecast_data['forecasts'][0]  # First forecast period
                actual = actual_by_segment[(market, asset_type)]
                
                mae = abs(predicted - actual)
                mape = abs(predicted - actual) / (actual + 1e-8) * 100
                
                mae_values.append(mae)
                mape_values.append(mape)
        
        if mae_values:
            metrics['caprate_mae'] = float(np.mean(mae_values))
            metrics['caprate_mape'] = float(np.mean(mape_values))
            metrics['caprate_rmse'] = float(np.sqrt(np.mean([x**2 for x in mae_values])))
        
        return metrics
    
    def _evaluate_noi_rent_forecast(self, forecasts: Dict, test_prop: pd.DataFrame) -> Dict[str, float]:
        """Evaluate NOI/rent forecasting accuracy"""
        metrics = {}
        
        if test_prop.empty:
            return metrics
        
        # Get actual values by property
        actual_by_property = test_prop.groupby('property_id').agg({
            'noi': 'mean',
            'rent': 'mean'
        }).fillna(0)
        
        for target_col in ['noi', 'rent']:
            mae_values = []
            mape_values = []
            
            for prop_id, forecast_data in forecasts.items():
                if prop_id not in actual_by_property.index:
                    continue
                
                if ('forecasts' in forecast_data and 
                    target_col in forecast_data['forecasts'] and
                    'forecasts' in forecast_data['forecasts'][target_col]):
                    
                    predicted_values = forecast_data['forecasts'][target_col]['forecasts']
                    if predicted_values:
                        predicted = predicted_values[0]  # First forecast period
                        actual = actual_by_property.loc[prop_id, target_col]
                        
                        if actual > 0:  # Avoid division by zero
                            mae = abs(predicted - actual)
                            mape = abs(predicted - actual) / actual * 100
                            
                            mae_values.append(mae)
                            mape_values.append(mape)
            
            if mae_values:
                metrics[f'{target_col}_mae'] = float(np.mean(mae_values))
                metrics[f'{target_col}_mape'] = float(np.mean(mape_values))
                metrics[f'{target_col}_rmse'] = float(np.sqrt(np.mean([x**2 for x in mae_values])))
        
        return metrics
    
    def _evaluate_scoring_performance(self, scores: List[Dict], test_prop: pd.DataFrame) -> Dict[str, float]:
        """Evaluate arbitrage scoring performance"""
        metrics = {}
        
        if not scores or test_prop.empty:
            return metrics
        
        # Extract scores and create realized returns (synthetic)
        score_values = [s['score'] for s in scores if not s.get('error')]
        confidence_values = [s['confidence'] for s in scores if not s.get('error')]
        
        if not score_values:
            return metrics
        
        # Create synthetic "realized returns" based on property fundamentals
        # In real backtest, this would be actual forward returns
        realized_returns = []
        for score_data in scores:
            if score_data.get('error'):
                continue
            
            prop_id = score_data.get('property_id')
            prop_data = test_prop[test_prop['property_id'] == prop_id]
            
            if not prop_data.empty:
                # Synthetic return based on fundamentals
                cap_rate = prop_data['cap_rate_observed'].iloc[0] if not prop_data['cap_rate_observed'].isna().iloc[0] else 0.065
                noi_growth = np.random.normal(0.03, 0.02)  # 3% +/- 2%
                
                # Higher cap rates and NOI growth = higher returns
                synthetic_return = (cap_rate - 0.05) + noi_growth + np.random.normal(0, 0.01)
                realized_returns.append(synthetic_return)
            else:
                realized_returns.append(0)
        
        if len(realized_returns) == len(score_values):
            # Calculate rank correlation (Spearman)
            from scipy.stats import spearmanr
            try:
                correlation, p_value = spearmanr(score_values, realized_returns)
                metrics['rank_ic'] = float(correlation) if not np.isnan(correlation) else 0.0
                metrics['rank_ic_pvalue'] = float(p_value) if not np.isnan(p_value) else 1.0
            except:
                metrics['rank_ic'] = 0.0
                metrics['rank_ic_pvalue'] = 1.0
            
            # Top quartile performance
            score_threshold = np.percentile(score_values, 75)
            top_quartile_mask = np.array(score_values) >= score_threshold
            
            if top_quartile_mask.sum() > 0:
                top_quartile_return = np.mean([realized_returns[i] for i in range(len(realized_returns)) if top_quartile_mask[i]])
                rest_return = np.mean([realized_returns[i] for i in range(len(realized_returns)) if not top_quartile_mask[i]])
                
                metrics['top_quartile_return'] = float(top_quartile_return)
                metrics['rest_return'] = float(rest_return)
                metrics['excess_return'] = float(top_quartile_return - rest_return)
        
        # Score distribution metrics
        metrics['mean_score'] = float(np.mean(score_values))
        metrics['score_std'] = float(np.std(score_values))
        metrics['mean_confidence'] = float(np.mean(confidence_values)) if confidence_values else 0.0
        
        return metrics
    
    def _aggregate_backtest_results(self, fold_results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results across all folds"""
        
        if not fold_results:
            return {}
        
        # Collect all metrics
        all_metrics = {}
        
        for fold_result in fold_results:
            for category in ['rates_metrics', 'caprate_metrics', 'noi_rent_metrics', 'scoring_metrics']:
                if category in fold_result:
                    for metric_name, value in fold_result[category].items():
                        if metric_name not in all_metrics:
                            all_metrics[metric_name] = []
                        all_metrics[metric_name].append(value)
        
        # Calculate aggregate statistics
        aggregated = {}
        for metric_name, values in all_metrics.items():
            if values:
                aggregated[f'{metric_name}_mean'] = float(np.mean(values))
                aggregated[f'{metric_name}_std'] = float(np.std(values))
                aggregated[f'{metric_name}_median'] = float(np.median(values))
                aggregated[f'{metric_name}_min'] = float(np.min(values))
                aggregated[f'{metric_name}_max'] = float(np.max(values))
        
        # Overall summary
        aggregated['n_folds'] = len(fold_results)
        aggregated['avg_train_samples'] = np.mean([r['n_train_samples'] for r in fold_results])
        aggregated['avg_test_samples'] = np.mean([r['n_test_samples'] for r in fold_results])
        
        return aggregated
    
    def _save_backtest_results(self, fold_results: List[Dict], aggregated_metrics: Dict):
        """Save backtest results and create plots"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = METRICS_PATH / f"backtest_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'fold_results': fold_results,
                'aggregated_metrics': aggregated_metrics,
                'timestamp': timestamp
            }, f, indent=2)
        
        # Save summary metrics
        summary_file = METRICS_PATH / "backtest_summary_latest.json"
        with open(summary_file, 'w') as f:
            json.dump(aggregated_metrics, f, indent=2)
        
        # Create plots
        self._create_backtest_plots(fold_results, timestamp)
        
        logger.info(f"Backtest results saved to {results_file}")
    
    def _create_backtest_plots(self, fold_results: List[Dict], timestamp: str):
        """Create visualization plots for backtest results"""
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('CapSight ML Backtest Results', fontsize=16)
            
            # Plot 1: Forecasting accuracy over time
            folds = [r['fold'] for r in fold_results]
            
            # Rates MAE
            rates_mae = [r['rates_metrics'].get('base_rate_mae', 0) for r in fold_results]
            axes[0, 0].plot(folds, rates_mae, marker='o', label='Base Rate MAE')
            axes[0, 0].set_title('Rates Forecasting Accuracy')
            axes[0, 0].set_xlabel('Fold')
            axes[0, 0].set_ylabel('MAE')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # Cap Rate MAE
            caprate_mae = [r['caprate_metrics'].get('caprate_mae', 0) for r in fold_results]
            axes[0, 1].plot(folds, caprate_mae, marker='s', color='orange', label='Cap Rate MAE')
            axes[0, 1].set_title('Cap Rate Forecasting Accuracy')
            axes[0, 1].set_xlabel('Fold')
            axes[0, 1].set_ylabel('MAE')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # NOI forecasting
            noi_mae = [r['noi_rent_metrics'].get('noi_mae', 0) for r in fold_results]
            axes[1, 0].plot(folds, noi_mae, marker='^', color='green', label='NOI MAE')
            axes[1, 0].set_title('NOI Forecasting Accuracy')
            axes[1, 0].set_xlabel('Fold')
            axes[1, 0].set_ylabel('MAE')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # Scoring performance
            rank_ic = [r['scoring_metrics'].get('rank_ic', 0) for r in fold_results]
            axes[1, 1].plot(folds, rank_ic, marker='d', color='red', label='Rank IC')
            axes[1, 1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
            axes[1, 1].set_title('Scoring Performance (Rank IC)')
            axes[1, 1].set_xlabel('Fold')
            axes[1, 1].set_ylabel('Correlation')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save plot
            plot_file = PLOTS_PATH / f"backtest_results_{timestamp}.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Backtest plots saved to {plot_file}")
            
        except Exception as e:
            logger.error(f"Failed to create backtest plots: {e}")
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get latest backtest metrics"""
        
        summary_file = METRICS_PATH / "backtest_summary_latest.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                return json.load(f)
        else:
            return {"error": "No backtest results found"}

def run_quick_backtest() -> Dict[str, Any]:
    """Run a quick backtest for testing"""
    engine = BacktestEngine()
    
    return engine.run_walk_forward_backtest(
        data_months=24,
        train_months=12, 
        test_months=3,
        step_months=3
    )

__all__ = [
    'BacktestEngine',
    'run_quick_backtest'
]
