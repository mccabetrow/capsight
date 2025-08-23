import { NextApiRequest, NextApiResponse } from 'next'
import { createServiceRoleClient } from '../../lib/supabase'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const supabase = createServiceRoleClient()
    
    // Get latest accuracy metrics
    const { data: metrics, error } = await supabase
      .from('eval_metrics')
      .select('*')
      .order('metric_date', { ascending: false })
      .limit(1)
      .single()

    if (error) {
      console.error('Supabase error:', error)
      return res.status(500).json({ error: 'Failed to fetch metrics' })
    }

    if (!metrics) {
      return res.status(404).json({ error: 'No metrics available' })
    }

    // Determine status based on SLA targets
    const status = getAccuracyStatus(metrics)

    res.status(200).json({
      status,
      metrics: {
        mape: metrics.mape,
        caprate_rmse_bps: metrics.caprate_rmse_bps,
        interval_coverage: metrics.interval_coverage,
        sample_size: metrics.n,
        last_updated: metrics.metric_date
      },
      sla_targets: {
        mape_target: 10.0,
        rmse_target_bps: 50.0,
        coverage_target_min: 78.0,
        coverage_target_max: 82.0
      }
    })
  } catch (error) {
    console.error('API error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}

function getAccuracyStatus(metrics: any): 'green' | 'amber' | 'red' {
  const mapeOk = !metrics.mape || metrics.mape <= 10.0
  const rmseOk = !metrics.caprate_rmse_bps || metrics.caprate_rmse_bps <= 50.0
  const coverageOk = !metrics.interval_coverage || 
    (metrics.interval_coverage >= 78.0 && metrics.interval_coverage <= 82.0)

  if (mapeOk && rmseOk && coverageOk) {
    return 'green'
  }

  // Check if any metric is severely off target
  const mapeBad = metrics.mape && metrics.mape > 15.0
  const rmseBad = metrics.caprate_rmse_bps && metrics.caprate_rmse_bps > 75.0
  const coverageBad = metrics.interval_coverage && 
    (metrics.interval_coverage < 70.0 || metrics.interval_coverage > 90.0)

  if (mapeBad || rmseBad || coverageBad) {
    return 'red'
  }

  return 'amber'
}
