import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

// Use service role key for write access to feedback table
const supabase = createClient(supabaseUrl, supabaseServiceKey);

interface FeedbackData {
  type: 'general' | 'bug' | 'feature' | 'accuracy' | 'ui' | 'performance';
  message: string;
  email?: string;
  url?: string;
  user_agent?: string;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { type, message, email, url, user_agent }: FeedbackData = req.body;

    // Validate required fields
    if (!type || !message || message.trim().length === 0) {
      return res.status(400).json({ error: 'Type and message are required' });
    }

    // Validate message length
    if (message.length > 1000) {
      return res.status(400).json({ error: 'Message too long (max 1000 characters)' });
    }

    // Validate email format if provided
    if (email && email.length > 0) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        return res.status(400).json({ error: 'Invalid email format' });
      }
    }

    // Get client IP for basic analytics
    const clientIp = req.headers['x-forwarded-for'] || req.connection.remoteAddress || 'unknown';

    // Insert feedback into database
    const { data, error } = await supabase
      .from('feedback')
      .insert({
        type,
        message: message.trim(),
        email: email || null,
        url: url || null,
        user_agent: user_agent || null,
        ip_address: Array.isArray(clientIp) ? clientIp[0] : clientIp,
        created_at: new Date().toISOString(),
        status: 'new'
      })
      .select('id')
      .single();

    if (error) {
      console.error('Database error:', error);
      return res.status(500).json({ error: 'Failed to save feedback' });
    }

    console.log(`Feedback submitted: ID ${data.id}, Type: ${type}, IP: ${clientIp}`);

    return res.status(201).json({ 
      success: true, 
      id: data.id,
      message: 'Feedback submitted successfully'
    });

  } catch (error) {
    console.error('Feedback API error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
