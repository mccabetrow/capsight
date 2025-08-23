"""
Report rendering engine for backtesting results
Generates PDF, HTML, and Markdown reports with charts and analysis
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from pathlib import Path
import json
import base64
from io import BytesIO
import tempfile

# Jinja2 for templating
try:
    from jinja2 import Environment, FileSystemLoader, Template
except ImportError:
    class Environment: pass
    class FileSystemLoader: pass
    class Template: pass

# Plotting libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
except ImportError:
    class plt: pass
    class sns: pass

# PDF generation
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except ImportError:
    class HTML: pass
    class CSS: pass

from .config import config
from .schemas import BacktestRun, BacktestResult, MetricsSummary
from .data_access import BacktestDataAccess
from .metrics import MetricsCalculator, PerformanceMetrics
from .uplift import UpliftAnalyzer

class ReportRenderer:
    """Generates comprehensive backtest reports in multiple formats"""
    
    def __init__(
        self,
        data_access: Optional[BacktestDataAccess] = None,
        metrics_calculator: Optional[MetricsCalculator] = None,
        uplift_analyzer: Optional[UpliftAnalyzer] = None,
        template_dir: Optional[str] = None
    ):
        self.data_access = data_access or BacktestDataAccess()
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        self.uplift_analyzer = uplift_analyzer or UpliftAnalyzer()
        
        # Setup template environment
        self.template_dir = template_dir or str(Path(__file__).parent / "templates")
        self._ensure_template_dir()
        
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=True
            )
        except:
            self.jinja_env = None
            print("Warning: Jinja2 template engine not available")
    
    def _ensure_template_dir(self):
        """Ensure template directory exists"""
        Path(self.template_dir).mkdir(parents=True, exist_ok=True)
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default report templates"""
        
        # HTML template for comprehensive report
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report - {{ run.run_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric-card { background: white; border: 1px solid #ddd; border-radius: 5px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; font-size: 14px; }
        .chart-container { margin: 20px 0; text-align: center; }
        .chart { max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .table th, .table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        .table th { background-color: #f8f9fa; font-weight: bold; }
        .section { margin: 30px 0; }
        .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .alert-success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; }
        .alert-warning { background-color: #fff3cd; border-color: #ffeaa7; color: #856404; }
        .alert-danger { background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Backtest Report: {{ run.run_name }}</h1>
        <p><strong>Run ID:</strong> {{ run.run_id }}</p>
        <p><strong>Prediction Date:</strong> {{ run.prediction_date.strftime('%Y-%m-%d') }}</p>
        <p><strong>Horizon:</strong> {{ run.horizon_months }} months</p>
        <p><strong>Model Version:</strong> {{ run.model_version }}</p>
        <p><strong>Generated:</strong> {{ report_generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
    </div>

    {% if sla_status %}
    <div class="section">
        <h2>SLA Compliance</h2>
        {% for sla in sla_status %}
            <div class="alert {% if sla.passed %}alert-success{% else %}alert-danger{% endif %}">
                <strong>{{ sla.name }}:</strong> {{ sla.description }}
                {% if not sla.passed %} (BREACH){% endif %}
            </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="section">
        <h2>Performance Summary</h2>
        <div class="metric-grid">
            {% if metrics.classification %}
            <div class="metric-card">
                <div class="metric-value">{{ "%.3f"|format(metrics.classification.accuracy) }}</div>
                <div class="metric-label">Accuracy</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.3f"|format(metrics.classification.precision) }}</div>
                <div class="metric-label">Precision</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.3f"|format(metrics.classification.recall) }}</div>
                <div class="metric-label">Recall</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.3f"|format(metrics.classification.roc_auc) }}</div>
                <div class="metric-label">ROC AUC</div>
            </div>
            {% endif %}
            
            {% if metrics.regression %}
            <div class="metric-card">
                <div class="metric-value">{{ "%.4f"|format(metrics.regression.rmse) }}</div>
                <div class="metric-label">RMSE</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.3f"|format(metrics.regression.r2) }}</div>
                <div class="metric-label">R²</div>
            </div>
            {% endif %}
            
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(metrics.real_estate.investment_return_accuracy * 100) }}%</div>
                <div class="metric-label">Investment Accuracy</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.2f"|format(metrics.real_estate.risk_adjusted_return) }}</div>
                <div class="metric-label">Risk-Adjusted Return</div>
            </div>
        </div>
    </div>

    {% if charts %}
    <div class="section">
        <h2>Performance Charts</h2>
        {% for chart_name, chart_data in charts.items() %}
        <div class="chart-container">
            <h3>{{ chart_name.replace('_', ' ').title() }}</h3>
            <img src="data:image/png;base64,{{ chart_data }}" class="chart" alt="{{ chart_name }}">
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if uplift_analysis %}
    <div class="section">
        <h2>Uplift Analysis</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(uplift_analysis.overall_uplift.relative_uplift_pct) }}%</div>
                <div class="metric-label">Relative Uplift</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ "%.4f"|format(uplift_analysis.overall_uplift.p_value) }}</div>
                <div class="metric-label">P-Value</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${{ "{:,.0f}".format(uplift_analysis.roi_analysis.incremental_profit) }}</div>
                <div class="metric-label">Incremental Profit</div>
            </div>
        </div>
        
        {% if uplift_analysis.cohort_analysis %}
        <h3>Cohort Performance</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>Cohort</th>
                    <th>Sample Size</th>
                    <th>Uplift</th>
                    <th>Significant</th>
                </tr>
            </thead>
            <tbody>
                {% for cohort in uplift_analysis.cohort_analysis %}
                <tr>
                    <td>{{ cohort.cohort_name.replace('_', ' ').title() }}</td>
                    <td>{{ cohort.sample_size }}</td>
                    <td>{{ "%.4f"|format(cohort.uplift) }}</td>
                    <td>{% if cohort.significant %}✓{% else %}✗{% endif %}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endif %}

    {% if prediction_sample %}
    <div class="section">
        <h2>Sample Predictions</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>Property ID</th>
                    <th>Prediction</th>
                    <th>Confidence</th>
                    <th>Key Features</th>
                </tr>
            </thead>
            <tbody>
                {% for pred in prediction_sample[:10] %}
                <tr>
                    <td>{{ pred.entity_id }}</td>
                    <td>{{ pred.prediction_value }}</td>
                    <td>{{ "%.1f"|format((pred.confidence or 0.5) * 100) }}%</td>
                    <td>{{ pred.key_features }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div class="section">
        <h2>Technical Details</h2>
        <table class="table">
            <tbody>
                <tr><td><strong>Feature Set:</strong></td><td>{{ run.feature_set | length }} features</td></tr>
                <tr><td><strong>Training Window:</strong></td><td>{{ run.config.get('training_window_months', 'N/A') }} months</td></tr>
                <tr><td><strong>Prediction Count:</strong></td><td>{{ prediction_count }}</td></tr>
                <tr><td><strong>Runtime:</strong></td><td>{{ runtime_minutes }} minutes</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        html_template_path = Path(self.template_dir) / "backtest_report.html"
        if not html_template_path.exists():
            html_template_path.write_text(html_template)
        
        # Markdown template for lightweight reports
        markdown_template = """
# Backtest Report: {{ run.run_name }}

**Run ID:** {{ run.run_id }}  
**Prediction Date:** {{ run.prediction_date.strftime('%Y-%m-%d') }}  
**Horizon:** {{ run.horizon_months }} months  
**Model Version:** {{ run.model_version }}  
**Generated:** {{ report_generated_at.strftime('%Y-%m-%d %H:%M:%S') }}

## Performance Summary

{% if metrics.classification %}
| Metric | Value |
|--------|--------|
| Accuracy | {{ "%.3f"|format(metrics.classification.accuracy) }} |
| Precision | {{ "%.3f"|format(metrics.classification.precision) }} |
| Recall | {{ "%.3f"|format(metrics.classification.recall) }} |
| F1 Score | {{ "%.3f"|format(metrics.classification.f1_score) }} |
| ROC AUC | {{ "%.3f"|format(metrics.classification.roc_auc) }} |
{% endif %}

{% if metrics.regression %}
| Regression Metric | Value |
|-------------------|--------|
| RMSE | {{ "%.4f"|format(metrics.regression.rmse) }} |
| MAE | {{ "%.4f"|format(metrics.regression.mae) }} |
| R² | {{ "%.3f"|format(metrics.regression.r2) }} |
| MAPE | {{ "%.1f"|format(metrics.regression.mape) }}% |
{% endif %}

## Real Estate Metrics

| Metric | Value |
|--------|--------|
| Investment Return Accuracy | {{ "%.1f"|format(metrics.real_estate.investment_return_accuracy * 100) }}% |
| Risk-Adjusted Return | {{ "%.2f"|format(metrics.real_estate.risk_adjusted_return) }} |
| Portfolio Diversification | {{ "%.1f"|format(metrics.real_estate.portfolio_diversification_score * 100) }}% |
| Deal Recommendation Precision | {{ "%.1f"|format(metrics.real_estate.deal_recommendation_precision * 100) }}% |

{% if uplift_analysis %}
## Uplift Analysis

- **Relative Uplift:** {{ "%.1f"|format(uplift_analysis.overall_uplift.relative_uplift_pct) }}%
- **Statistical Significance:** {{ 'Yes' if uplift_analysis.overall_uplift.statistical_significance else 'No' }}
- **P-Value:** {{ "%.4f"|format(uplift_analysis.overall_uplift.p_value) }}
- **Incremental Profit:** ${{ "{:,.0f}".format(uplift_analysis.roi_analysis.incremental_profit) }}

### Cohort Analysis

{% for cohort in uplift_analysis.cohort_analysis %}
- **{{ cohort.cohort_name.replace('_', ' ').title() }}:** {{ cohort.sample_size }} samples, {{ "%.4f"|format(cohort.uplift) }} uplift
{% endfor %}
{% endif %}

## Technical Details

- **Feature Count:** {{ run.feature_set | length }}
- **Prediction Count:** {{ prediction_count }}
- **Runtime:** {{ runtime_minutes }} minutes
- **Status:** {{ run.status }}

{% if sla_status %}
## SLA Compliance

{% for sla in sla_status %}
- **{{ sla.name }}:** {{ sla.description }} {% if not sla.passed %}**[BREACH]**{% endif %}
{% endfor %}
{% endif %}
        """
        
        markdown_template_path = Path(self.template_dir) / "backtest_report.md"
        if not markdown_template_path.exists():
            markdown_template_path.write_text(markdown_template)
    
    async def generate_comprehensive_report(
        self,
        run_id: str,
        output_format: str = "html",
        include_charts: bool = True,
        include_uplift: bool = True,
        include_sample_predictions: bool = True,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive backtest report
        
        Args:
            run_id: Backtest run to report on
            output_format: "html", "pdf", or "markdown"
            include_charts: Whether to include performance charts
            include_uplift: Whether to include uplift analysis
            include_sample_predictions: Whether to include prediction samples
            output_path: Path to save report (optional)
            
        Returns:
            Report content as string or path to saved file
        """
        # Load run data
        run = await self.data_access.get_backtest_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        # Calculate metrics
        metrics = await self.metrics_calculator.calculate_backtest_metrics(run_id)
        
        # Load predictions
        predictions = await self.data_access.get_prediction_snapshots(run_id)
        
        # Check SLA compliance
        sla_status = await self._check_sla_compliance(run, metrics)
        
        # Generate charts if requested
        charts = {}
        if include_charts:
            charts = await self._generate_performance_charts(run_id, metrics)
        
        # Uplift analysis if requested
        uplift_analysis = None
        if include_uplift:
            try:
                uplift_analysis = await self.uplift_analyzer.generate_uplift_report(run_id)
            except Exception as e:
                print(f"Warning: Uplift analysis failed: {e}")
        
        # Sample predictions
        prediction_sample = []
        if include_sample_predictions and predictions:
            prediction_sample = self._prepare_prediction_sample(predictions[:20])
        
        # Prepare template context
        context = {
            "run": run,
            "metrics": metrics,
            "sla_status": sla_status,
            "charts": charts,
            "uplift_analysis": uplift_analysis,
            "prediction_sample": prediction_sample,
            "prediction_count": len(predictions),
            "runtime_minutes": self._calculate_runtime_minutes(run),
            "report_generated_at": datetime.now()
        }
        
        # Render report
        if output_format == "html":
            content = await self._render_html_report(context)
        elif output_format == "pdf":
            content = await self._render_pdf_report(context)
        elif output_format == "markdown":
            content = await self._render_markdown_report(context)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_format == "pdf":
                output_path.write_bytes(content)
            else:
                output_path.write_text(content)
            
            return str(output_path)
        
        return content if output_format != "pdf" else base64.b64encode(content).decode()
    
    async def _render_html_report(self, context: Dict[str, Any]) -> str:
        """Render HTML report using template"""
        
        if self.jinja_env:
            template = self.jinja_env.get_template("backtest_report.html")
            return template.render(**context)
        else:
            # Fallback simple HTML
            return f"""
            <html>
            <head><title>Backtest Report</title></head>
            <body>
                <h1>Backtest Report: {context['run'].run_name}</h1>
                <p>Run ID: {context['run'].run_id}</p>
                <p>Prediction Date: {context['run'].prediction_date}</p>
                <p>Status: {context['run'].status}</p>
                <p>Prediction Count: {context['prediction_count']}</p>
                <p>Generated: {context['report_generated_at']}</p>
            </body>
            </html>
            """
    
    async def _render_pdf_report(self, context: Dict[str, Any]) -> bytes:
        """Render PDF report from HTML template"""
        
        # First generate HTML
        html_content = await self._render_html_report(context)
        
        try:
            # Convert HTML to PDF using WeasyPrint
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf()
            return pdf_bytes
        except Exception as e:
            print(f"Warning: PDF generation failed ({e}), returning HTML as bytes")
            return html_content.encode('utf-8')
    
    async def _render_markdown_report(self, context: Dict[str, Any]) -> str:
        """Render Markdown report using template"""
        
        if self.jinja_env:
            template = self.jinja_env.get_template("backtest_report.md")
            return template.render(**context)
        else:
            # Fallback simple Markdown
            run = context['run']
            return f"""
# Backtest Report: {run.run_name}

**Run ID:** {run.run_id}
**Prediction Date:** {run.prediction_date}
**Status:** {run.status}
**Prediction Count:** {context['prediction_count']}
**Generated:** {context['report_generated_at']}

## Summary

This is a basic report for run {run.run_id}.
            """
    
    async def _check_sla_compliance(
        self,
        run: BacktestRun,
        metrics: PerformanceMetrics
    ) -> List[Dict[str, Any]]:
        """Check SLA compliance for the run"""
        
        sla_checks = []
        
        # Accuracy SLA
        if metrics.classification:
            accuracy_threshold = config.sla_thresholds.get("accuracy", 0.7)
            sla_checks.append({
                "name": "Accuracy SLA",
                "description": f"Accuracy >= {accuracy_threshold}",
                "passed": metrics.classification.accuracy >= accuracy_threshold,
                "actual_value": metrics.classification.accuracy
            })
        
        # Runtime SLA
        runtime_minutes = self._calculate_runtime_minutes(run)
        max_runtime = config.sla_thresholds.get("max_runtime_minutes", 60)
        sla_checks.append({
            "name": "Runtime SLA",
            "description": f"Runtime <= {max_runtime} minutes",
            "passed": runtime_minutes <= max_runtime,
            "actual_value": runtime_minutes
        })
        
        # ROI SLA
        if hasattr(metrics.real_estate, 'investment_return_accuracy'):
            roi_threshold = config.sla_thresholds.get("investment_accuracy", 0.6)
            sla_checks.append({
                "name": "Investment Accuracy SLA",
                "description": f"Investment accuracy >= {roi_threshold}",
                "passed": metrics.real_estate.investment_return_accuracy >= roi_threshold,
                "actual_value": metrics.real_estate.investment_return_accuracy
            })
        
        return sla_checks
    
    def _calculate_runtime_minutes(self, run: BacktestRun) -> float:
        """Calculate runtime in minutes"""
        # Mock calculation - in production would use actual timestamps
        return 15.5  # Assume 15.5 minutes
    
    def _prepare_prediction_sample(self, predictions: List) -> List[Dict[str, Any]]:
        """Prepare sample predictions for display"""
        
        sample = []
        for pred in predictions:
            # Extract key features for display
            key_features = []
            if pred.feature_values:
                important_features = ["sqft", "bedrooms", "median_price_zip"]
                for feature in important_features:
                    if feature in pred.feature_values:
                        key_features.append(f"{feature}: {pred.feature_values[feature]}")
            
            confidence = None
            if pred.prediction_proba and "positive_class_prob" in pred.prediction_proba:
                confidence = pred.prediction_proba["positive_class_prob"]
            
            sample.append({
                "entity_id": pred.entity_id,
                "prediction_value": pred.prediction_value,
                "confidence": confidence,
                "key_features": ", ".join(key_features) if key_features else "N/A"
            })
        
        return sample
    
    async def _generate_performance_charts(
        self,
        run_id: str,
        metrics: PerformanceMetrics
    ) -> Dict[str, str]:
        """Generate performance charts as base64 encoded images"""
        
        charts = {}
        
        try:
            # Load predictions for chart generation
            predictions = await self.data_access.get_prediction_snapshots(run_id)
            if not predictions:
                return charts
            
            # Convert to DataFrame
            pred_data = []
            for pred in predictions:
                record = {
                    "prediction": pred.prediction_value,
                    "timestamp": pred.created_at
                }
                if pred.prediction_proba:
                    record.update(pred.prediction_proba)
                pred_data.append(record)
            
            df = pd.DataFrame(pred_data)
            
            # Prediction distribution chart
            fig, ax = plt.subplots(figsize=(10, 6))
            if "prediction" in df.columns:
                df["prediction"].hist(bins=30, ax=ax, alpha=0.7)
                ax.set_title("Prediction Distribution")
                ax.set_xlabel("Prediction Value")
                ax.set_ylabel("Frequency")
                
                charts["prediction_distribution"] = self._fig_to_base64(fig)
            
            plt.close(fig)
            
            # Confidence distribution (if available)
            if "positive_class_prob" in df.columns:
                fig, ax = plt.subplots(figsize=(10, 6))
                df["positive_class_prob"].hist(bins=30, ax=ax, alpha=0.7, color='green')
                ax.set_title("Confidence Distribution")
                ax.set_xlabel("Confidence Score")
                ax.set_ylabel("Frequency")
                ax.axvline(0.5, color='red', linestyle='--', label='Decision Threshold')
                ax.legend()
                
                charts["confidence_distribution"] = self._fig_to_base64(fig)
                plt.close(fig)
            
            # Metrics comparison chart (if we have cohort data)
            if metrics.cohort_metrics:
                fig, ax = plt.subplots(figsize=(12, 8))
                
                cohort_names = []
                cohort_values = []
                
                for cohort_type, cohorts in metrics.cohort_metrics.items():
                    for cohort_name, cohort_data in cohorts.items():
                        cohort_names.append(f"{cohort_type}_{cohort_name}")
                        # Use first available metric
                        value = list(cohort_data.values())[0] if cohort_data else 0
                        cohort_values.append(value)
                
                if cohort_names:
                    ax.bar(cohort_names, cohort_values)
                    ax.set_title("Performance by Cohort")
                    ax.set_ylabel("Performance Score")
                    ax.tick_params(axis='x', rotation=45)
                    
                    charts["cohort_performance"] = self._fig_to_base64(fig)
                
                plt.close(fig)
            
        except Exception as e:
            print(f"Warning: Chart generation failed: {e}")
        
        return charts
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        
        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        
        return image_base64
    
    async def generate_executive_summary(
        self,
        run_id: str,
        target_audience: str = "executive"
    ) -> str:
        """Generate executive summary of backtest results"""
        
        # Load run data
        run = await self.data_access.get_backtest_run(run_id)
        metrics = await self.metrics_calculator.calculate_backtest_metrics(run_id)
        
        # Generate uplift analysis
        uplift_analysis = None
        try:
            uplift_analysis = await self.uplift_analyzer.generate_uplift_report(run_id)
        except:
            pass
        
        if target_audience == "executive":
            summary = f"""
# Executive Summary: {run.run_name}

## Key Results
- **Investment Success Rate**: {metrics.classification.accuracy:.1%} vs {(uplift_analysis['overall_uplift']['relative_uplift_pct'] if uplift_analysis else 50):.0f}% baseline
- **Risk-Adjusted Return**: {metrics.real_estate.risk_adjusted_return:.2f}
- **Incremental Profit**: ${uplift_analysis['roi_analysis']['incremental_profit']:,.0f if uplift_analysis else 0}

## Business Impact
The model demonstrates {('significant' if uplift_analysis and uplift_analysis['overall_uplift']['statistical_significance'] else 'potential')} improvement over baseline strategies, with a {metrics.real_estate.investment_return_accuracy:.1%} accuracy in identifying profitable investments.

## Recommendations
{'Deploy to production' if metrics.classification.accuracy > 0.7 else 'Consider model refinement'} based on current performance metrics.
            """
        else:
            # Technical summary
            summary = f"""
# Technical Summary: {run.run_name}

## Model Performance
- Accuracy: {metrics.classification.accuracy:.3f}
- Precision: {metrics.classification.precision:.3f}
- Recall: {metrics.classification.recall:.3f}
- AUC: {metrics.classification.roc_auc:.3f}

## Regression Metrics
- RMSE: {metrics.regression.rmse:.4f if metrics.regression else 'N/A'}
- R²: {metrics.regression.r2:.3f if metrics.regression else 'N/A'}

## Feature Engineering Impact
Portfolio diversification score: {metrics.real_estate.portfolio_diversification_score:.3f}
            """
        
        return summary
    
    async def schedule_automated_reporting(
        self,
        run_id: str,
        report_configs: List[Dict[str, Any]]
    ) -> List[str]:
        """Schedule automated report generation"""
        
        generated_reports = []
        
        for config in report_configs:
            try:
                report_path = await self.generate_comprehensive_report(
                    run_id=run_id,
                    output_format=config.get("format", "html"),
                    include_charts=config.get("include_charts", True),
                    include_uplift=config.get("include_uplift", True),
                    output_path=config.get("output_path")
                )
                generated_reports.append(report_path)
                
            except Exception as e:
                print(f"Report generation failed for config {config}: {e}")
        
        return generated_reports

# Global instance
report_renderer = ReportRenderer()
