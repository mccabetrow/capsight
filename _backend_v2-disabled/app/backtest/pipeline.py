"""
Main backtest pipeline orchestration.

This module provides the high-level orchestration for running complete
backtests, including time slicing, feature loading, model execution,
metrics calculation, and report generation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback

from .config import BacktestConfig, get_backtest_settings
from .schemas import BacktestRun, BacktestResult, BacktestMetrics, TimeSlice
from .data_access import BacktestDataAccess
from .time_slicer import BacktestTimeSlicer
from .feature_loader import FeatureLoader
from .replay import CounterfactualReplay
from .metrics import BacktestMetrics as MetricsCalculator
from .uplift import UpliftAnalysis
from .reports.renderer import ReportRenderer

logger = logging.getLogger(__name__)


class BacktestPipeline:
    """Main backtest pipeline orchestrator."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.settings = get_backtest_settings()
        self.data_access = BacktestDataAccess()
        self.time_slicer = BacktestTimeSlicer(config)
        self.feature_loader = FeatureLoader(config)
        self.metrics_calculator = MetricsCalculator()
        self.report_renderer = ReportRenderer()
        
    async def run_full_backtest(self) -> Dict[str, Any]:
        """
        Execute a complete backtest pipeline.
        
        Returns:
            Dict containing run results, metrics, and metadata
        """
        logger.info(f"Starting backtest: {self.config.name}")
        start_time = datetime.utcnow()
        
        try:
            # Create backtest run record
            run_id = await self.data_access.create_backtest_run(self.config)
            logger.info(f"Created backtest run: {run_id}")
            
            # Generate time slices
            time_slices = self.time_slicer.create_time_slices()
            logger.info(f"Generated {len(time_slices)} time slices")
            
            # Process each time slice
            all_results = []
            slice_metrics = []
            
            for i, time_slice in enumerate(time_slices):
                logger.info(f"Processing time slice {i+1}/{len(time_slices)}: "
                           f"{time_slice.test_start} to {time_slice.test_end}")
                
                # Process single time slice
                slice_results = await self._process_time_slice(
                    run_id, time_slice, i
                )
                
                if slice_results:
                    all_results.extend(slice_results['results'])
                    slice_metrics.append(slice_results['metrics'])
            
            # Store results
            if all_results:
                await self.data_access.store_backtest_results(all_results)
                logger.info(f"Stored {len(all_results)} backtest results")
            
            # Calculate aggregate metrics
            aggregate_metrics = await self._calculate_aggregate_metrics(
                all_results, slice_metrics
            )
            
            # Store metrics summary
            await self.data_access.store_metrics_summary(
                run_id, aggregate_metrics
            )
            
            # Update run status
            await self.data_access.update_run_status(
                run_id, "completed", end_time=datetime.utcnow()
            )
            
            # Generate report
            report_path = await self._generate_report(
                run_id, aggregate_metrics, all_results
            )
            
            end_time = datetime.utcnow()
            runtime_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"Backtest completed successfully in {runtime_seconds:.2f}s")
            
            return {
                'run_id': run_id,
                'status': 'completed',
                'runtime_seconds': runtime_seconds,
                'metrics': aggregate_metrics,
                'results_count': len(all_results),
                'report_path': report_path,
                'time_slices_processed': len(time_slices)
            }
            
        except Exception as e:
            # Handle errors gracefully
            logger.error(f"Backtest failed: {str(e)}")
            logger.error(traceback.format_exc())
            
            if 'run_id' in locals():
                await self.data_access.update_run_status(
                    run_id, "failed", error_message=str(e)
                )
            
            return {
                'status': 'failed',
                'error': str(e),
                'runtime_seconds': (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _process_time_slice(
        self, 
        run_id: str, 
        time_slice: TimeSlice, 
        slice_index: int
    ) -> Optional[Dict[str, Any]]:
        """Process a single time slice."""
        try:
            # Load features for the time slice
            features_df = await self.feature_loader.load_features(
                feature_sets=self.config.feature_sets,
                entities=self._get_entities_for_slice(time_slice),
                as_of_time=time_slice.test_start
            )
            
            if features_df.empty:
                logger.warning(f"No features loaded for slice {slice_index}")
                return None
            
            # Load historical predictions if available
            historical_predictions = await self.data_access.get_historical_predictions(
                start_time=time_slice.test_start,
                end_time=time_slice.test_end,
                model_version=self.config.model_version
            )
            
            # Generate predictions for this slice
            predictions = await self._generate_predictions(
                features_df, time_slice
            )
            
            # Load actual outcomes (for backtesting)
            actuals = await self._load_actual_outcomes(time_slice)
            
            # Create backtest results
            results = []
            for _, row in predictions.iterrows():
                actual_value = actuals.get(row['entity_id'], None)
                
                result = BacktestResult(
                    run_id=run_id,
                    time_slice=time_slice.test_start,
                    property_id=row['entity_id'],
                    prediction_value=row['prediction'],
                    actual_value=actual_value,
                    confidence_score=row.get('confidence', 0.0),
                    feature_values=row.get('features', {}),
                    model_version=self.config.model_version
                )
                results.append(result)
            
            # Calculate metrics for this slice
            slice_metrics = await self._calculate_slice_metrics(
                predictions, actuals, time_slice
            )
            
            return {
                'results': results,
                'metrics': slice_metrics,
                'predictions_count': len(predictions),
                'features_count': len(features_df.columns)
            }
            
        except Exception as e:
            logger.error(f"Error processing time slice {slice_index}: {str(e)}")
            return None
    
    async def _generate_predictions(
        self, 
        features_df, 
        time_slice: TimeSlice
    ) -> Any:
        """Generate predictions using the ML model."""
        # This would integrate with MLflow to load and run the model
        # For now, we'll return mock predictions
        
        import pandas as pd
        import numpy as np
        
        np.random.seed(42)
        
        predictions = pd.DataFrame({
            'entity_id': features_df.index,
            'prediction': np.random.random(len(features_df)),
            'confidence': np.random.uniform(0.7, 0.95, len(features_df))
        })
        
        return predictions
    
    async def _load_actual_outcomes(self, time_slice: TimeSlice) -> Dict[str, float]:
        """Load actual outcomes for comparison."""
        # This would load real historical data
        # For now, return mock data
        
        import numpy as np
        
        np.random.seed(42)
        entities = self._get_entities_for_slice(time_slice)
        
        return {
            entity: np.random.random()
            for entity in entities[:100]  # Limit for demo
        }
    
    def _get_entities_for_slice(self, time_slice: TimeSlice) -> List[str]:
        """Get relevant entities for a time slice."""
        # This would query the database for relevant properties
        # For now, return mock entity IDs
        
        return [f'property_{i}' for i in range(1, 101)]
    
    async def _calculate_slice_metrics(
        self, 
        predictions, 
        actuals: Dict[str, float], 
        time_slice: TimeSlice
    ) -> Dict[str, float]:
        """Calculate metrics for a single time slice."""
        try:
            # Align predictions with actuals
            aligned_data = []
            for _, pred_row in predictions.iterrows():
                entity_id = pred_row['entity_id']
                if entity_id in actuals:
                    aligned_data.append({
                        'prediction': pred_row['prediction'],
                        'actual': actuals[entity_id],
                        'confidence': pred_row.get('confidence', 0.0)
                    })
            
            if not aligned_data:
                return {}
            
            import pandas as pd
            aligned_df = pd.DataFrame(aligned_data)
            
            # Calculate ML metrics
            y_true = aligned_df['actual'].values
            y_pred = aligned_df['prediction'].values
            
            ml_metrics = self.metrics_calculator.calculate_ml_metrics(y_true, y_pred)
            
            # Calculate investment metrics
            investment_metrics = self.metrics_calculator.calculate_investment_metrics(
                y_pred, y_true
            )
            
            # Combine metrics
            return {
                **ml_metrics,
                **investment_metrics,
                'slice_start': time_slice.test_start.isoformat(),
                'slice_end': time_slice.test_end.isoformat(),
                'predictions_count': len(aligned_data)
            }
            
        except Exception as e:
            logger.error(f"Error calculating slice metrics: {str(e)}")
            return {}
    
    async def _calculate_aggregate_metrics(
        self,
        all_results: List[BacktestResult],
        slice_metrics: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calculate aggregate metrics across all time slices."""
        try:
            if not slice_metrics:
                return {}
            
            # Aggregate numeric metrics
            numeric_metrics = {}
            for key in slice_metrics[0].keys():
                if key not in ['slice_start', 'slice_end'] and isinstance(slice_metrics[0].get(key), (int, float)):
                    values = [sm.get(key, 0) for sm in slice_metrics if isinstance(sm.get(key), (int, float))]
                    if values:
                        numeric_metrics[f'avg_{key}'] = sum(values) / len(values)
                        numeric_metrics[f'min_{key}'] = min(values)
                        numeric_metrics[f'max_{key}'] = max(values)
            
            # Overall performance metrics
            overall_predictions = [r.prediction_value for r in all_results if r.actual_value is not None]
            overall_actuals = [r.actual_value for r in all_results if r.actual_value is not None]
            
            if overall_predictions and overall_actuals:
                overall_ml_metrics = self.metrics_calculator.calculate_ml_metrics(
                    overall_actuals, overall_predictions
                )
                overall_investment_metrics = self.metrics_calculator.calculate_investment_metrics(
                    overall_predictions, overall_actuals
                )
                
                numeric_metrics.update({
                    f'overall_{k}': v 
                    for k, v in {**overall_ml_metrics, **overall_investment_metrics}.items()
                })
            
            # Summary statistics
            summary = {
                'total_predictions': len(all_results),
                'successful_predictions': len([r for r in all_results if r.actual_value is not None]),
                'time_slices_count': len(slice_metrics),
                'model_version': self.config.model_version,
                'feature_sets': self.config.feature_sets,
                'backtest_period_days': (self.config.end_date - self.config.start_date).days,
                'created_at': datetime.utcnow().isoformat()
            }
            
            return {
                **numeric_metrics,
                **summary
            }
            
        except Exception as e:
            logger.error(f"Error calculating aggregate metrics: {str(e)}")
            return {'error': str(e)}
    
    async def _generate_report(
        self,
        run_id: str,
        metrics: Dict[str, Any],
        results: List[BacktestResult]
    ) -> Optional[str]:
        """Generate backtest report."""
        try:
            # Prepare report data
            report_data = {
                'title': f'Backtest Report - {self.config.name}',
                'run_id': run_id,
                'model_version': self.config.model_version,
                'config': self.config.dict(),
                'metrics': metrics,
                'summary': {
                    'total_predictions': len(results),
                    'avg_accuracy': metrics.get('overall_accuracy', 0),
                    'avg_roc_auc': metrics.get('overall_roc_auc', 0),
                    'sharpe_ratio': metrics.get('overall_sharpe_ratio', 0)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Generate HTML report
            report_filename = f"backtest_report_{run_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
            report_path = f"reports/{report_filename}"
            
            success = self.report_renderer.render_html_report(
                report_data, report_path
            )
            
            if success:
                logger.info(f"Generated report: {report_path}")
                return report_path
            else:
                logger.error("Failed to generate report")
                return None
                
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None


# Main entry point functions
async def run_full_backtest(config: BacktestConfig) -> Dict[str, Any]:
    """
    Run a complete backtest with the given configuration.
    
    Args:
        config: Backtest configuration
        
    Returns:
        Dict containing backtest results and metadata
    """
    pipeline = BacktestPipeline(config)
    return await pipeline.run_full_backtest()


async def run_counterfactual_replay(
    config: BacktestConfig,
    scenario_name: str,
    replay_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run counterfactual replay analysis.
    
    Args:
        config: Base backtest configuration
        scenario_name: Name for the replay scenario
        replay_params: Optional parameters for replay adjustment
        
    Returns:
        Dict containing replay results
    """
    data_access = BacktestDataAccess()
    replay = CounterfactualReplay(config, data_access)
    
    if replay_params:
        # What-if replay with parameter adjustments
        return await replay.run_what_if_replay(scenario_name, replay_params)
    else:
        # Standard replay
        return await replay.run_replay(scenario_name)


async def run_uplift_analysis(
    treatment_model: str,
    control_model: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    Run uplift analysis comparing two model versions.
    
    Args:
        treatment_model: Treatment model version
        control_model: Control model version  
        start_date: Analysis start date
        end_date: Analysis end date
        
    Returns:
        Dict containing uplift analysis results
    """
    data_access = BacktestDataAccess()
    uplift = UpliftAnalysis(data_access)
    
    return await uplift.compare_model_versions(
        treatment_version=treatment_model,
        control_version=control_model,
        start_date=start_date,
        end_date=end_date
    )


# Example usage
if __name__ == "__main__":
    import asyncio
    from datetime import datetime, timedelta
    
    # Example configuration
    config = BacktestConfig(
        name="example_backtest",
        model_version="v1.0.0",
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now() - timedelta(days=1),
        time_slice_hours=24,
        feature_sets=["property_features", "market_features"],
        prediction_targets=["price_change", "investment_score"],
        metrics=["accuracy", "roc_auc", "sharpe_ratio"]
    )
    
    # Run backtest
    async def main():
        results = await run_full_backtest(config)
        print(f"Backtest completed: {results}")
    
    asyncio.run(main())
