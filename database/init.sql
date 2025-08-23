-- CapSight Database Schema
-- PostgreSQL initialization script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user' NOT NULL,
    subscription_tier VARCHAR(50) DEFAULT 'free' NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Properties table
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(500) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20),
    property_type VARCHAR(50) NOT NULL,
    list_price DECIMAL(15,2),
    square_footage INTEGER,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    year_built INTEGER,
    lot_size DECIMAL(10,2),
    
    -- Financial metrics
    estimated_value DECIMAL(15,2),
    current_cap_rate DECIMAL(5,4),
    projected_cap_rate DECIMAL(5,4),
    rental_yield DECIMAL(5,4),
    
    -- Metadata
    data_source VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market data table
CREATE TABLE market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location VARCHAR(200) NOT NULL,
    property_type VARCHAR(50),
    
    -- Market metrics
    median_price DECIMAL(15,2),
    price_per_sqft DECIMAL(10,2),
    cap_rate DECIMAL(5,4),
    rental_yield DECIMAL(5,4),
    vacancy_rate DECIMAL(5,4),
    appreciation_rate DECIMAL(5,4),
    inventory_levels INTEGER,
    days_on_market DECIMAL(5,1),
    
    -- Interest rates
    mortgage_rate_30y DECIMAL(5,4),
    mortgage_rate_15y DECIMAL(5,4),
    mortgage_rate_arm DECIMAL(5,4),
    
    -- Data quality
    data_source VARCHAR(50),
    confidence_score DECIMAL(3,2),
    
    -- Timestamps
    data_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one record per location/date/type combination
    UNIQUE(location, property_type, data_date)
);

-- Opportunities table
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id),
    
    -- Opportunity metrics
    arbitrage_score DECIMAL(5,4) NOT NULL,
    expected_return DECIMAL(5,4),
    risk_score DECIMAL(5,4),
    opportunity_type VARCHAR(50) NOT NULL,
    
    -- Analysis
    key_factors JSONB,
    investment_thesis TEXT,
    time_sensitivity VARCHAR(20),
    
    -- Market context
    market_trends JSONB,
    comparable_sales JSONB,
    
    -- Confidence and expiration
    confidence_lower DECIMAL(5,4),
    confidence_upper DECIMAL(5,4),
    
    -- Subscription requirements
    subscription_tier_required VARCHAR(50) DEFAULT 'basic',
    
    -- Timestamps
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Predictions table (audit trail)
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    prediction_type VARCHAR(50) NOT NULL,
    
    -- Input data
    property_data JSONB,
    market_data JSONB,
    
    -- Results
    arbitrage_score DECIMAL(5,4),
    expected_return DECIMAL(5,4),
    risk_score DECIMAL(5,4),
    contributing_factors JSONB,
    model_used VARCHAR(50),
    confidence_interval JSONB,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Post-facto accuracy (filled in later)
    actual_outcome DECIMAL(5,4),
    accuracy_score DECIMAL(5,4)
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) UNIQUE,
    
    -- Stripe data
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    
    -- Plan details
    plan_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    
    -- Billing periods
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMP,
    
    -- Trial
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage tracking table
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    
    -- Usage metrics
    opportunities_viewed INTEGER DEFAULT 0,
    predictions_requested INTEGER DEFAULT 0,
    api_calls_made INTEGER DEFAULT 0,
    alerts_triggered INTEGER DEFAULT 0,
    
    -- Time period
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one record per user per billing period
    UNIQUE(user_id, period_start, period_end)
);

-- Alerts table
CREATE TABLE opportunity_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    
    -- Filter criteria
    min_score DECIMAL(5,4) DEFAULT 0.0,
    max_score DECIMAL(5,4) DEFAULT 1.0,
    location VARCHAR(200),
    property_type VARCHAR(50),
    opportunity_type VARCHAR(50),
    min_expected_return DECIMAL(5,4),
    max_risk_score DECIMAL(5,4),
    price_range_min DECIMAL(15,2),
    price_range_max DECIMAL(15,2),
    
    -- Notification settings
    notification_methods JSONB, -- ['email', 'sms', 'webhook']
    webhook_url VARCHAR(500),
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered TIMESTAMP
);

-- Data ingestion tasks table
CREATE TABLE ingestion_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    
    -- Task details
    source VARCHAR(50) NOT NULL,
    parameters JSONB,
    status VARCHAR(20) NOT NULL, -- 'started', 'running', 'completed', 'failed'
    progress DECIMAL(5,2) DEFAULT 0.0,
    
    -- Results
    records_processed INTEGER,
    errors_count INTEGER,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Audit trail table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_properties_location ON properties(city, state);
CREATE INDEX idx_properties_type_price ON properties(property_type, list_price);
CREATE INDEX idx_market_data_location_date ON market_data(location, data_date DESC);
CREATE INDEX idx_opportunities_score ON opportunities(arbitrage_score DESC);
CREATE INDEX idx_opportunities_expires ON opportunities(expires_at);
CREATE INDEX idx_predictions_user_date ON predictions(user_id, created_at DESC);
CREATE INDEX idx_usage_tracking_user_period ON usage_tracking(user_id, period_start, period_end);
CREATE INDEX idx_audit_log_user_date ON audit_log(user_id, created_at DESC);

-- Create GIN indexes for JSONB columns
CREATE INDEX idx_opportunities_factors ON opportunities USING gin(key_factors);
CREATE INDEX idx_predictions_data ON predictions USING gin(property_data, market_data);
CREATE INDEX idx_alerts_notifications ON opportunity_alerts USING gin(notification_methods);

-- Update triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_opportunities_updated_at BEFORE UPDATE ON opportunities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_usage_tracking_updated_at BEFORE UPDATE ON usage_tracking FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON opportunity_alerts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development
INSERT INTO users (email, full_name, company, hashed_password, role, subscription_tier) VALUES
('admin@capsight.ai', 'Admin User', 'CapSight', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiChQD3XbL6u', 'admin', 'enterprise'),
('demo@capsight.ai', 'Demo User', 'Demo Company', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiChQD3XbL6u', 'user', 'pro');

-- Sample market data
INSERT INTO market_data (location, property_type, median_price, price_per_sqft, cap_rate, rental_yield, vacancy_rate, appreciation_rate, inventory_levels, days_on_market, mortgage_rate_30y, mortgage_rate_15y, mortgage_rate_arm, data_source, confidence_score, data_date) VALUES
('Austin, TX', 'single_family', 650000, 280, 0.048, 0.042, 0.04, 0.08, 1200, 28, 0.068, 0.061, 0.058, 'synthetic', 0.85, CURRENT_DATE),
('Denver, CO', 'single_family', 580000, 295, 0.045, 0.038, 0.03, 0.09, 800, 25, 0.068, 0.061, 0.058, 'synthetic', 0.82, CURRENT_DATE),
('Miami, FL', 'multi_family', 420000, 340, 0.055, 0.048, 0.06, 0.07, 1500, 35, 0.068, 0.061, 0.058, 'synthetic', 0.88, CURRENT_DATE);

COMMIT;
