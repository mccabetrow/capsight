import type { ValuationRequest, ValuationResponse, ApiError } from './types'

export async function fetchValuation(
  request: ValuationRequest
): Promise<ValuationResponse> {
  const url = new URL('/api/value', window.location.origin)
  url.searchParams.set('market_slug', request.market_slug)
  url.searchParams.set('noi_annual', request.noi_annual.toString())

  const response = await fetch(url.toString())
  
  if (!response.ok) {
    const errorData: ApiError = await response.json()
    throw new Error(errorData.message || errorData.error || 'Valuation failed')
  }

  return response.json()
}
