"""Add backtest tables

Revision ID: 001_add_backtest_tables
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_backtest_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add backtest tables to database"""
    
    # Create backtest_runs table
    op.create_table(
        'backtest_runs',
        sa.Column('run_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('run_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('prediction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('horizon_months', sa.Integer, nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('feature_set', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='created'),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('parent_run_id', sa.String(255), nullable=True),
        sa.Column('replay_scenario', postgresql.JSONB, nullable=True),
        
        # Indexes
        sa.Index('ix_backtest_runs_created_at', 'created_at'),
        sa.Index('ix_backtest_runs_status', 'status'),
        sa.Index('ix_backtest_runs_model_version', 'model_version'),
        sa.Index('ix_backtest_runs_parent_run_id', 'parent_run_id'),
        
        # Constraints
        sa.CheckConstraint('horizon_months > 0 AND horizon_months <= 60', name='check_horizon_months'),
        sa.CheckConstraint("status IN ('created', 'running', 'completed', 'failed', 'cancelled')", name='check_status'),
        
        # Foreign key to parent run
        sa.ForeignKeyConstraint(['parent_run_id'], ['backtest_runs.run_id'], name='fk_parent_run_id', ondelete='SET NULL'),
        
        comment='Backtest run configurations and metadata'
    )
    
    # Create backtest_results table
    op.create_table(
        'backtest_results',
        sa.Column('result_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('backtest_run_id', sa.String(255), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_backtest_results_run_id', 'backtest_run_id'),
        sa.Index('ix_backtest_results_metric_name', 'metric_name'),
        sa.Index('ix_backtest_results_created_at', 'created_at'),
        
        # Foreign key
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.run_id'], name='fk_results_run_id', ondelete='CASCADE'),
        
        # Unique constraint
        sa.UniqueConstraint('backtest_run_id', 'metric_name', name='unique_run_metric'),
        
        comment='Individual metric results for backtest runs'
    )
    
    # Create prediction_snapshots table
    op.create_table(
        'prediction_snapshots',
        sa.Column('snapshot_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('backtest_run_id', sa.String(255), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('prediction_value', sa.Float, nullable=False),
        sa.Column('prediction_proba', postgresql.JSONB, nullable=True),
        sa.Column('feature_values', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_prediction_snapshots_run_id', 'backtest_run_id'),
        sa.Index('ix_prediction_snapshots_entity_id', 'entity_id'),
        sa.Index('ix_prediction_snapshots_model_version', 'model_version'),
        sa.Index('ix_prediction_snapshots_created_at', 'created_at'),
        sa.Index('ix_prediction_snapshots_prediction_value', 'prediction_value'),
        
        # Composite indexes for common queries
        sa.Index('ix_prediction_snapshots_run_entity', 'backtest_run_id', 'entity_id'),
        sa.Index('ix_prediction_snapshots_run_model', 'backtest_run_id', 'model_version'),
        
        # Foreign key
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.run_id'], name='fk_snapshots_run_id', ondelete='CASCADE'),
        
        # Unique constraint
        sa.UniqueConstraint('backtest_run_id', 'entity_id', name='unique_run_entity_prediction'),
        
        comment='Individual prediction snapshots for backtest runs'
    )
    
    # Create metrics_summary table
    op.create_table(
        'metrics_summary',
        sa.Column('summary_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('backtest_run_id', sa.String(255), nullable=False),
        sa.Column('metrics_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('sla_breaches', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_metrics_summary_run_id', 'backtest_run_id'),
        sa.Index('ix_metrics_summary_created_at', 'created_at'),
        
        # Foreign key
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.run_id'], name='fk_metrics_run_id', ondelete='CASCADE'),
        
        # Unique constraint (one summary per run)
        sa.UniqueConstraint('backtest_run_id', name='unique_run_metrics_summary'),
        
        comment='Aggregated metrics summary for backtest runs'
    )
    
    # Create model_snapshots table for tracking model versions
    op.create_table(
        'model_snapshots',
        sa.Column('snapshot_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('model_type', sa.String(100), nullable=False),
        sa.Column('model_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('feature_schema', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('performance_metrics', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('mlflow_run_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        
        # Indexes
        sa.Index('ix_model_snapshots_version', 'model_version'),
        sa.Index('ix_model_snapshots_type', 'model_type'),
        sa.Index('ix_model_snapshots_created_at', 'created_at'),
        sa.Index('ix_model_snapshots_is_active', 'is_active'),
        sa.Index('ix_model_snapshots_mlflow_run_id', 'mlflow_run_id'),
        
        # Unique constraint
        sa.UniqueConstraint('model_version', name='unique_model_version'),
        
        comment='Snapshots of model versions used in backtesting'
    )
    
    # Create backtest_jobs table for scheduled jobs
    op.create_table(
        'backtest_jobs',
        sa.Column('job_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('job_name', sa.String(255), nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('job_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('schedule_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='scheduled'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_id', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        
        # Indexes
        sa.Index('ix_backtest_jobs_job_type', 'job_type'),
        sa.Index('ix_backtest_jobs_status', 'status'),
        sa.Index('ix_backtest_jobs_next_run_at', 'next_run_at'),
        sa.Index('ix_backtest_jobs_created_at', 'created_at'),
        sa.Index('ix_backtest_jobs_is_active', 'is_active'),
        
        # Foreign key to last run
        sa.ForeignKeyConstraint(['last_run_id'], ['backtest_runs.run_id'], name='fk_jobs_last_run_id', ondelete='SET NULL'),
        
        # Constraints
        sa.CheckConstraint("job_type IN ('standard_backtest', 'replay_analysis', 'uplift_analysis', 'model_comparison')", 
                          name='check_job_type'),
        sa.CheckConstraint("status IN ('scheduled', 'running', 'paused', 'cancelled')", name='check_job_status'),
        
        comment='Scheduled backtest jobs configuration'
    )
    
    # Create feature_sets table for tracking feature configurations
    op.create_table(
        'feature_sets',
        sa.Column('feature_set_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('feature_set_name', sa.String(255), nullable=False),
        sa.Column('feature_views', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('transformations', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('feature_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        
        # Indexes
        sa.Index('ix_feature_sets_name', 'feature_set_name'),
        sa.Index('ix_feature_sets_created_at', 'created_at'),
        sa.Index('ix_feature_sets_is_active', 'is_active'),
        
        # Unique constraint
        sa.UniqueConstraint('feature_set_name', name='unique_feature_set_name'),
        
        comment='Feature set configurations for backtesting'
    )
    
    # Create audit_logs table for tracking changes
    op.create_table(
        'backtest_audit_logs',
        sa.Column('log_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id', sa.String(255), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('old_values', postgresql.JSONB, nullable=True),
        sa.Column('new_values', postgresql.JSONB, nullable=True),
        sa.Column('changed_by', sa.String(255), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('change_reason', sa.String(500), nullable=True),
        
        # Indexes
        sa.Index('ix_audit_logs_table_name', 'table_name'),
        sa.Index('ix_audit_logs_record_id', 'record_id'),
        sa.Index('ix_audit_logs_action', 'action'),
        sa.Index('ix_audit_logs_changed_at', 'changed_at'),
        sa.Index('ix_audit_logs_changed_by', 'changed_by'),
        
        # Composite index for common queries
        sa.Index('ix_audit_logs_table_record', 'table_name', 'record_id'),
        
        # Constraints
        sa.CheckConstraint("action IN ('INSERT', 'UPDATE', 'DELETE')", name='check_audit_action'),
        
        comment='Audit log for tracking changes to backtest data'
    )
    
    # Add some useful views
    op.execute("""
        CREATE VIEW backtest_run_summary AS
        SELECT 
            br.run_id,
            br.run_name,
            br.created_at,
            br.status,
            br.model_version,
            br.horizon_months,
            COUNT(ps.snapshot_id) as prediction_count,
            AVG(ps.prediction_value) as avg_prediction,
            ms.metrics_data,
            CASE 
                WHEN br.completed_at IS NOT NULL THEN 
                    EXTRACT(EPOCH FROM (br.completed_at - br.created_at))/60.0
                ELSE NULL 
            END as runtime_minutes
        FROM backtest_runs br
        LEFT JOIN prediction_snapshots ps ON br.run_id = ps.backtest_run_id
        LEFT JOIN metrics_summary ms ON br.run_id = ms.backtest_run_id
        GROUP BY br.run_id, br.run_name, br.created_at, br.status, 
                 br.model_version, br.horizon_months, br.completed_at, ms.metrics_data;
    """)
    
    op.execute("""
        CREATE VIEW model_performance_summary AS
        SELECT 
            ms.model_version,
            COUNT(DISTINCT br.run_id) as backtest_count,
            AVG(CASE WHEN br.status = 'completed' THEN 1.0 ELSE 0.0 END) as success_rate,
            AVG(
                CASE 
                    WHEN ms.metrics_data->'real_estate'->>'investment_return_accuracy' IS NOT NULL 
                    THEN (ms.metrics_data->'real_estate'->>'investment_return_accuracy')::float
                    ELSE NULL 
                END
            ) as avg_investment_accuracy,
            MIN(br.created_at) as first_used,
            MAX(br.created_at) as last_used
        FROM model_snapshots ms
        LEFT JOIN backtest_runs br ON ms.model_version = br.model_version
        LEFT JOIN metrics_summary met ON br.run_id = met.backtest_run_id
        GROUP BY ms.model_version;
    """)
    
    # Create some useful functions
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_old_predictions(days_to_keep INTEGER DEFAULT 90)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM prediction_snapshots 
            WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL
            AND backtest_run_id IN (
                SELECT run_id FROM backtest_runs 
                WHERE status = 'completed' 
                AND created_at < NOW() - (days_to_keep || ' days')::INTERVAL
            );
            
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION get_model_drift_metrics(
            baseline_model_version VARCHAR,
            comparison_model_version VARCHAR,
            date_range_days INTEGER DEFAULT 30
        )
        RETURNS TABLE(
            metric_name TEXT,
            baseline_value FLOAT,
            comparison_value FLOAT,
            drift_score FLOAT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH baseline AS (
                SELECT 
                    AVG(ps.prediction_value) as avg_prediction,
                    STDDEV(ps.prediction_value) as std_prediction
                FROM prediction_snapshots ps
                JOIN backtest_runs br ON ps.backtest_run_id = br.run_id
                WHERE br.model_version = baseline_model_version
                AND ps.created_at >= NOW() - (date_range_days || ' days')::INTERVAL
            ),
            comparison AS (
                SELECT 
                    AVG(ps.prediction_value) as avg_prediction,
                    STDDEV(ps.prediction_value) as std_prediction
                FROM prediction_snapshots ps
                JOIN backtest_runs br ON ps.backtest_run_id = br.run_id
                WHERE br.model_version = comparison_model_version
                AND ps.created_at >= NOW() - (date_range_days || ' days')::INTERVAL
            )
            SELECT 
                'mean_prediction_drift'::TEXT,
                b.avg_prediction,
                c.avg_prediction,
                ABS(c.avg_prediction - b.avg_prediction)::FLOAT
            FROM baseline b, comparison c
            UNION ALL
            SELECT 
                'std_prediction_drift'::TEXT,
                b.std_prediction,
                c.std_prediction,
                ABS(c.std_prediction - b.std_prediction)::FLOAT
            FROM baseline b, comparison c;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Remove backtest tables from database"""
    
    # Drop views first
    op.execute("DROP VIEW IF EXISTS model_performance_summary")
    op.execute("DROP VIEW IF EXISTS backtest_run_summary")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_predictions(INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS get_model_drift_metrics(VARCHAR, VARCHAR, INTEGER)")
    
    # Drop tables in reverse dependency order
    op.drop_table('backtest_audit_logs')
    op.drop_table('feature_sets')
    op.drop_table('backtest_jobs')
    op.drop_table('model_snapshots')
    op.drop_table('metrics_summary')
    op.drop_table('prediction_snapshots')
    op.drop_table('backtest_results')
    op.drop_table('backtest_runs')
