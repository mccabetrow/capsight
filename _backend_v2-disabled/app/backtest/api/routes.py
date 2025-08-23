"""
FastAPI routes for backtest endpoints
Provides REST API for backtest operations
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path, Body
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
from pathlib import Path as FilePath
import json
import asyncio
import logging
from io import BytesIO

from ...core.deps import get_current_user
from ..schemas import (
    BacktestRun, BacktestResult, PredictionSnapshot, MetricsSummary,
    BacktestJobConfig, BacktestSchedule, ReplayScenario,
    BacktestCreateRequest, BacktestRunResponse, BacktestListResponse,
    ReplayRequest, ReplayResponse, UpliftRequest, UpliftResponse
)
from ..data_access import BacktestDataAccess
from ..time_slicer import time_slicer
from ..feature_loader import feature_loader
from ..replay import replay_engine
from ..metrics import metrics_calculator
from ..uplift import uplift_analyzer
from ..reports.renderer import report_renderer
from ..jobs.scheduler import job_scheduler

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

# Dependencies
async def get_data_access() -> BacktestDataAccess:
    """Get data access instance"""
    return BacktestDataAccess()

# Pydantic models for API requests/responses
class BacktestMetricsResponse(BaseModel):
    """Response model for metrics"""
    run_id: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    roc_auc: Optional[float] = None
    investment_return_accuracy: float
    risk_adjusted_return: float
    portfolio_diversification_score: float
    created_at: datetime

class BacktestJobResponse(BaseModel):
    """Response model for scheduled jobs"""
    job_id: str
    job_name: str
    status: str
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    run_id: Optional[str] = None

class ReportRequest(BaseModel):
    """Request model for report generation"""
    run_id: str = Field(..., description="Backtest run ID")
    format: str = Field("html", description="Report format: html, pdf, or markdown")
    include_charts: bool = Field(True, description="Include performance charts")
    include_uplift: bool = Field(True, description="Include uplift analysis")
    include_samples: bool = Field(True, description="Include sample predictions")

# BACKTEST RUN ENDPOINTS

@router.post("/runs", response_model=BacktestRunResponse)
async def create_backtest_run(
    request: BacktestCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_access: BacktestDataAccess = Depends(get_data_access)
):
    """Create and execute a new backtest run"""
    
    try:
        # Generate time window
        prediction_date = request.prediction_date or date.today()
        time_window = time_slicer.asof_window(
            asof_date=prediction_date,
            horizon_months=request.horizon_months
        )
        
        # Create backtest run
        run_id = f"api_{request.name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
        backtest_run = BacktestRun(
            run_id=run_id,
            run_name=request.name,
            created_at=datetime.now(),
            prediction_date=datetime.combine(prediction_date, datetime.min.time()),
            horizon_months=request.horizon_months,
            model_version=request.model_version,
            feature_set=request.feature_config or {},
            status="running",
            config={
                "user_id": current_user.get("user_id"),
                "api_request": request.dict(),
                "training_window": {
                    "start": time_window.train_start.isoformat(),
                    "end": time_window.train_end.isoformat()
                }
            }
        )
        
        await data_access.create_backtest_run(backtest_run)
        
        # Schedule background execution
        background_tasks.add_task(
            _execute_backtest_async,
            run_id,
            request,
            time_window
        )
        
        return BacktestRunResponse(
            run_id=run_id,
            name=request.name,
            status="running",
            created_at=backtest_run.created_at,
            prediction_date=prediction_date,
            horizon_months=request.horizon_months,
            model_version=request.model_version,
            prediction_count=0,
            estimated_completion_minutes=15
        )
        
    except Exception as e:
        logger.error(f"Failed to create backtest run: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs", response_model=BacktestListResponse)
async def list_backtest_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_access: BacktestDataAccess = Depends(get_data_access)
):
    """List backtest runs with pagination"""
    
    try:
        # Mock implementation - in production would query database
        runs = await _get_mock_runs(limit, offset, status)
        total_count = 50  # Mock total
        
        return BacktestListResponse(
            runs=runs,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Failed to list backtest runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}", response_model=BacktestRunResponse)
async def get_backtest_run(
    run_id: str = Path(..., description="Backtest run ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_access: BacktestDataAccess = Depends(get_data_access)
):
    """Get specific backtest run details"""
    
    try:
        run = await data_access.get_backtest_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        
        # Get prediction count
        predictions = await data_access.get_prediction_snapshots(run_id)
        prediction_count = len(predictions)
        
        return BacktestRunResponse(
            run_id=run.run_id,
            name=run.run_name,
            status=run.status,
            created_at=run.created_at,
            prediction_date=run.prediction_date.date(),
            horizon_months=run.horizon_months,
            model_version=run.model_version,
            prediction_count=prediction_count,
            completed_at=run.completed_at,
            error_message=run.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/runs/{run_id}")
async def delete_backtest_run(
    run_id: str = Path(..., description="Backtest run ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_access: BacktestDataAccess = Depends(get_data_access)
):
    """Delete a backtest run and associated data"""
    
    try:
        # Check if run exists
        run = await data_access.get_backtest_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        
        # Delete associated data
        await data_access.delete_backtest_run(run_id)
        
        return {"message": f"Backtest run {run_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backtest run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# METRICS ENDPOINTS

@router.get("/runs/{run_id}/metrics", response_model=BacktestMetricsResponse)
async def get_backtest_metrics(
    run_id: str = Path(..., description="Backtest run ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_access: BacktestDataAccess = Depends(get_data_access)
):
    """Get performance metrics for a backtest run"""
    
    try:
        # Check if run exists
        run = await data_access.get_backtest_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        
        # Calculate metrics
        metrics = await metrics_calculator.calculate_backtest_metrics(run_id)
        
        response = BacktestMetricsResponse(
            run_id=run_id,
            investment_return_accuracy=metrics.real_estate.investment_return_accuracy,
            risk_adjusted_return=metrics.real_estate.risk_adjusted_return,
            portfolio_diversification_score=metrics.real_estate.portfolio_diversification_score,
            created_at=datetime.now()
        )
        
        # Add classification metrics if available
        if metrics.classification:
            response.accuracy = metrics.classification.accuracy
            response.precision = metrics.classification.precision
            response.recall = metrics.classification.recall
            response.roc_auc = metrics.classification.roc_auc
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# REPLAY ENDPOINTS

@router.post("/runs/{run_id}/replay", response_model=ReplayResponse)
async def create_replay_analysis(
    run_id: str = Path(..., description="Original backtest run ID"),
    request: ReplayRequest = Body(...),
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_access: BacktestDataAccess = Depends(get_data_access)
):
    """Create replay analysis for existing backtest run"""
    
    try:
        # Check if original run exists
        original_run = await data_access.get_backtest_run(run_id)
        if not original_run:
            raise HTTPException(status_code=404, detail="Original backtest run not found")
        
        # Create replay scenario
        replay_scenario = ReplayScenario(
            scenario_name=request.scenario_name,
            replay_mode=request.replay_mode,
            entity_ids=request.entity_ids,
            model_version=request.model_version,
            scenario_params=request.scenario_params or {},
            feature_overrides=request.feature_overrides,
            threshold_overrides=request.threshold_overrides
        )
        
        # Execute replay in background
        background_tasks.add_task(
            _execute_replay_async,
            run_id,
            replay_scenario,
            current_user.get("user_id")
        )
        
        return ReplayResponse(
            message="Replay analysis started",
            original_run_id=run_id,
            scenario_name=request.scenario_name,
            replay_mode=request.replay_mode,
            estimated_completion_minutes=10
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create replay analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# UPLIFT ENDPOINTS

@router.post("/runs/{run_id}/uplift", response_model=UpliftResponse)
async def create_uplift_analysis(
    run_id: str = Path(..., description="Treatment run ID"),
    request: UpliftRequest = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate uplift analysis for backtest run"""
    
    try:
        # Check if run exists
        data_access = BacktestDataAccess()
        run = await data_access.get_backtest_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        
        # Generate uplift analysis
        uplift_report = await uplift_analyzer.generate_uplift_report(
            treatment_run_id=run_id,
            baseline_strategy=request.baseline_strategy,
            outcome_column=request.outcome_column
        )
        
        return UpliftResponse(
            treatment_run_id=run_id,
            baseline_strategy=request.baseline_strategy,
            relative_uplift_percent=uplift_report['overall_uplift']['relative_uplift_pct'],
            statistical_significance=uplift_report['overall_uplift']['statistical_significance'],
            p_value=uplift_report['overall_uplift']['p_value'],
            incremental_profit=uplift_report['roi_analysis']['incremental_profit'],
            treatment_roi=uplift_report['roi_analysis']['treatment_roi'],
            baseline_roi=uplift_report['roi_analysis']['baseline_roi'],
            cohort_analysis=uplift_report['cohort_analysis'],
            feature_impacts=uplift_report['feature_impacts']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create uplift analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# REPORTING ENDPOINTS

@router.post("/runs/{run_id}/reports")
async def generate_report(
    run_id: str = Path(..., description="Backtest run ID"),
    request: ReportRequest = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate comprehensive report for backtest run"""
    
    try:
        # Check if run exists
        data_access = BacktestDataAccess()
        run = await data_access.get_backtest_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        
        # Generate report
        report_content = await report_renderer.generate_comprehensive_report(
            run_id=run_id,
            output_format=request.format,
            include_charts=request.include_charts,
            include_uplift=request.include_uplift,
            include_sample_predictions=request.include_samples
        )
        
        # Return appropriate response based on format
        if request.format == "pdf":
            # Return PDF as streaming response
            import base64
            pdf_bytes = base64.b64decode(report_content)
            
            return StreamingResponse(
                BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=backtest_report_{run_id}.pdf"}
            )
        else:
            # Return HTML/Markdown content
            return {
                "run_id": run_id,
                "format": request.format,
                "content": report_content,
                "generated_at": datetime.now().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}/executive-summary")
async def get_executive_summary(
    run_id: str = Path(..., description="Backtest run ID"),
    audience: str = Query("executive", description="Target audience: executive or technical"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get executive summary for backtest run"""
    
    try:
        # Check if run exists
        data_access = BacktestDataAccess()
        run = await data_access.get_backtest_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        
        # Generate summary
        summary = await report_renderer.generate_executive_summary(
            run_id=run_id,
            target_audience=audience
        )
        
        return {
            "run_id": run_id,
            "audience": audience,
            "summary": summary,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate executive summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# JOB SCHEDULING ENDPOINTS

@router.post("/jobs", response_model=BacktestJobResponse)
async def create_scheduled_job(
    schedule_config: BacktestSchedule = Body(...),
    job_config: BacktestJobConfig = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Schedule recurring backtest job"""
    
    try:
        # Start scheduler if needed
        await job_scheduler.start_scheduler()
        
        # Schedule job
        job_id = await job_scheduler.schedule_recurring_backtest(
            schedule_config=schedule_config,
            job_config=job_config
        )
        
        return BacktestJobResponse(
            job_id=job_id,
            job_name=job_config.job_name,
            status="scheduled"
        )
        
    except Exception as e:
        logger.error(f"Failed to schedule job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[BacktestJobResponse])
async def list_scheduled_jobs(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all scheduled backtest jobs"""
    
    try:
        jobs = await job_scheduler.list_scheduled_jobs()
        
        return [
            BacktestJobResponse(
                job_id=job["job_id"],
                job_name=job.get("name", "Unnamed Job"),
                status=job.get("status", "scheduled"),
                next_run=job.get("next_run"),
                run_id=job.get("run_id")
            )
            for job in jobs
        ]
        
    except Exception as e:
        logger.error(f"Failed to list scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
async def cancel_scheduled_job(
    job_id: str = Path(..., description="Job ID to cancel"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cancel a scheduled job"""
    
    try:
        success = await job_scheduler.cancel_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or already completed")
        
        return {"message": f"Job {job_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# UTILITY ENDPOINTS

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/config")
async def get_backtest_config(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get backtest configuration and limits"""
    
    from ..config import config
    
    return {
        "max_horizon_months": config.max_horizon_months,
        "min_train_window_months": config.min_train_window_months,
        "default_prediction_thresholds": config.default_prediction_thresholds,
        "sla_thresholds": config.sla_thresholds,
        "supported_model_versions": ["v1.0.0", "v1.1.0", "v1.2.0"],
        "supported_feature_views": [
            "property_features", "market_features", "economic_features", 
            "neighborhood_features"
        ],
        "supported_replay_modes": [
            "model_swap", "parameter_change", "feature_ablation", 
            "threshold_change", "market_scenario"
        ]
    }

# BACKGROUND TASK FUNCTIONS

async def _execute_backtest_async(
    run_id: str,
    request: BacktestCreateRequest,
    time_window
):
    """Execute backtest in background"""
    
    try:
        data_access = BacktestDataAccess()
        
        # Load entity IDs
        entity_ids = request.entity_ids or [f"property_{i}" for i in range(1, 101)]
        
        # Load features
        feature_data = await feature_loader.create_training_dataset(
            entity_ids=entity_ids,
            training_window=time_window,
            feature_views=request.feature_views or ["property_features", "market_features"]
        )
        
        # Generate predictions (mock)
        predictions = await _generate_mock_predictions_api(run_id, entity_ids, request.model_version)
        
        # Save predictions
        for pred in predictions:
            await data_access.create_prediction_snapshot(pred)
        
        # Update run status
        run = await data_access.get_backtest_run(run_id)
        run.status = "completed"
        run.completed_at = datetime.now()
        await data_access.update_backtest_run(run)
        
        logger.info(f"Background backtest completed: {run_id}")
        
    except Exception as e:
        logger.error(f"Background backtest failed: {run_id} - {e}")
        
        # Update run with error
        try:
            run = await data_access.get_backtest_run(run_id)
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.now()
            await data_access.update_backtest_run(run)
        except:
            pass

async def _execute_replay_async(
    original_run_id: str,
    replay_scenario: ReplayScenario,
    user_id: str
):
    """Execute replay analysis in background"""
    
    try:
        replay_run = await replay_engine.replay_historical_predictions(
            original_run_id=original_run_id,
            replay_scenario=replay_scenario
        )
        
        logger.info(f"Background replay completed: {replay_run.run_id}")
        
    except Exception as e:
        logger.error(f"Background replay failed: {original_run_id} - {e}")

async def _generate_mock_predictions_api(run_id: str, entity_ids: List[str], model_version: str):
    """Generate mock predictions for API"""
    
    import numpy as np
    predictions = []
    
    for entity_id in entity_ids:
        pred = PredictionSnapshot(
            snapshot_id=f"pred_{run_id}_{entity_id}",
            backtest_run_id=run_id,
            entity_id=entity_id,
            prediction_value=int(np.random.randint(0, 2)),
            prediction_proba={
                "negative_class_prob": float(np.random.random()),
                "positive_class_prob": float(np.random.random())
            },
            feature_values={
                "sqft": float(np.random.normal(2000, 500)),
                "bedrooms": int(np.random.choice([2, 3, 4, 5])),
                "median_price_zip": float(np.random.normal(400000, 100000))
            },
            model_version=model_version,
            created_at=datetime.now()
        )
        predictions.append(pred)
    
    return predictions

async def _get_mock_runs(limit: int, offset: int, status_filter: Optional[str]) -> List[BacktestRunResponse]:
    """Get mock backtest runs for API"""
    
    runs = []
    for i in range(limit):
        run_id = f"api_run_{offset + i + 1}_{int(datetime.now().timestamp())}"
        status = status_filter or np.random.choice(["completed", "running", "failed"])
        
        runs.append(BacktestRunResponse(
            run_id=run_id,
            name=f"API Test Run {offset + i + 1}",
            status=status,
            created_at=datetime.now() - timedelta(days=i),
            prediction_date=date.today() - timedelta(days=i),
            horizon_months=6,
            model_version="v1.2.0",
            prediction_count=100,
            completed_at=datetime.now() - timedelta(days=i, hours=1) if status == "completed" else None
        ))
    
    return runs
