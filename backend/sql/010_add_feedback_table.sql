-- Create feedback table for user feedback collection
-- Run this migration to add feedback functionality

CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL CHECK (type IN ('general', 'bug', 'feature', 'accuracy', 'ui', 'performance')),
    message TEXT NOT NULL CHECK (length(message) > 0 AND length(message) <= 1000),
    email TEXT CHECK (email IS NULL OR email ~* '^[^\s@]+@[^\s@]+\.[^\s@]+$'),
    url TEXT,
    user_agent TEXT,
    ip_address INET,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'resolved', 'closed')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_feedback_created_at ON feedback (created_at DESC);
CREATE INDEX idx_feedback_status ON feedback (status);
CREATE INDEX idx_feedback_type ON feedback (type);

-- Add RLS (Row Level Security) policies
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- Policy: Allow anyone to insert feedback (public submissions)
CREATE POLICY "Allow public feedback submission" ON feedback
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Policy: Only authenticated users with admin role can read feedback
-- Note: This requires setting up user roles or JWT claims
CREATE POLICY "Admin read feedback" ON feedback
    FOR SELECT
    TO authenticated
    USING (
        auth.jwt() ->> 'role' = 'admin' OR 
        auth.jwt() ->> 'user_metadata'::jsonb ->> 'role' = 'admin'
    );

-- Policy: Only authenticated users with admin role can update feedback status
CREATE POLICY "Admin update feedback" ON feedback
    FOR UPDATE
    TO authenticated
    USING (
        auth.jwt() ->> 'role' = 'admin' OR 
        auth.jwt() ->> 'user_metadata'::jsonb ->> 'role' = 'admin'
    )
    WITH CHECK (
        auth.jwt() ->> 'role' = 'admin' OR 
        auth.jwt() ->> 'user_metadata'::jsonb ->> 'role' = 'admin'
    );

-- Create a trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_feedback_updated_at_trigger
    BEFORE UPDATE ON feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_feedback_updated_at();

-- Create a view for feedback stats (accessible to admins)
CREATE VIEW feedback_stats AS
SELECT 
    COUNT(*) as total_feedback,
    COUNT(CASE WHEN status = 'new' THEN 1 END) as new_feedback,
    COUNT(CASE WHEN status = 'reviewed' THEN 1 END) as reviewed_feedback,
    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_feedback,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_feedback,
    COUNT(CASE WHEN type = 'bug' THEN 1 END) as bug_reports,
    COUNT(CASE WHEN type = 'feature' THEN 1 END) as feature_requests,
    COUNT(CASE WHEN type = 'accuracy' THEN 1 END) as accuracy_feedback,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_feedback,
    ROUND(
        COUNT(CASE WHEN email IS NOT NULL THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(*), 0) * 100, 
        2
    ) as contact_rate_percent
FROM feedback;

-- RLS for feedback_stats view
ALTER VIEW feedback_stats OWNER TO postgres;

-- Grant permissions
GRANT SELECT ON feedback_stats TO authenticated;

-- Add comment for documentation
COMMENT ON TABLE feedback IS 'User feedback collection system with RLS for public submissions and admin management';
COMMENT ON COLUMN feedback.type IS 'Categorizes feedback: general, bug, feature, accuracy, ui, performance';
COMMENT ON COLUMN feedback.message IS 'User feedback message (1-1000 characters)';
COMMENT ON COLUMN feedback.email IS 'Optional contact email for follow-up';
COMMENT ON COLUMN feedback.url IS 'Page URL where feedback was submitted';
COMMENT ON COLUMN feedback.user_agent IS 'Browser/client information for debugging';
COMMENT ON COLUMN feedback.ip_address IS 'Client IP for analytics and spam prevention';
COMMENT ON COLUMN feedback.status IS 'Workflow status: new -> reviewed -> resolved/closed';

-- Create a function to get feedback summary (admin only)
CREATE OR REPLACE FUNCTION get_feedback_summary(days_back INTEGER DEFAULT 30)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    -- Check if user is admin (simplified - adjust based on your auth setup)
    IF auth.jwt() ->> 'role' != 'admin' AND 
       auth.jwt() ->> 'user_metadata'::jsonb ->> 'role' != 'admin' THEN
        RAISE EXCEPTION 'Access denied: Admin role required';
    END IF;

    SELECT json_build_object(
        'total', COUNT(*),
        'new', COUNT(CASE WHEN status = 'new' THEN 1 END),
        'by_type', json_object_agg(type, type_count),
        'recent_trend', json_build_object(
            'last_7_days', COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END),
            'previous_7_days', COUNT(CASE WHEN created_at >= NOW() - INTERVAL '14 days' 
                                          AND created_at < NOW() - INTERVAL '7 days' THEN 1 END)
        )
    ) INTO result
    FROM (
        SELECT type, status, created_at, COUNT(*) OVER (PARTITION BY type) as type_count
        FROM feedback
        WHERE created_at >= NOW() - INTERVAL '%s days', days_back
    ) subq;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
