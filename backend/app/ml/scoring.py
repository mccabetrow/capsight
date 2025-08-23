"""
Arbitrage Scoring Logic
Transparent scoring system with fallback calculations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import logging

from .config import MLConfig

logger = logging.getLogger(__name__)

class ArbitrageScorer:
    """Transparent arbitrage opportunity scoring"""
    
    def __init__(self, scoring_weights: Optional[Dict[str, float]] = None):
        self.weights = scoring_weights or MLConfig.SCORING_WEIGHTS
        self.min_score = 0
        self.max_score = 100
    
    def calculate_score(self, 
                       property_data: Dict[str, Any],
                       rate_forecasts: Optional[Dict] = None,
                       caprate_forecasts: Optional[Dict] = None,
                       noi_rent_forecasts: Optional[Dict] = None) -> Dict[str, Any]:
        """Calculate arbitrage score with rationale"""
        
        scores = {}
        rationale_parts = []
        confidence_factors = []
        
        # 1. Cap Rate Compression Component
        cap_score, cap_rationale, cap_confidence = self._calculate_cap_rate_component(
            property_data, caprate_forecasts
        )
        scores['cap_rate_compression'] = cap_score
        if cap_rationale:
            rationale_parts.append(cap_rationale)
        confidence_factors.append(cap_confidence)
        
        # 2. NOI Growth Component
        noi_score, noi_rationale, noi_confidence = self._calculate_noi_component(
            property_data, noi_rent_forecasts
        )
        scores['noi_growth'] = noi_score
        if noi_rationale:
            rationale_parts.append(noi_rationale)
        confidence_factors.append(noi_confidence)
        
        # 3. Rate Environment Component
        rate_score, rate_rationale, rate_confidence = self._calculate_rate_component(
            property_data, rate_forecasts
        )
        scores['rate_environment'] = rate_score
        if rate_rationale:
            rationale_parts.append(rate_rationale)
        confidence_factors.append(rate_confidence)
        
        # 4. Momentum Component
        momentum_score, momentum_rationale, momentum_confidence = self._calculate_momentum_component(
            property_data
        )
        scores['momentum'] = momentum_score
        if momentum_rationale:
            rationale_parts.append(momentum_rationale)
        confidence_factors.append(momentum_confidence)
        
        # Combine scores
        total_score = sum(scores[component] * self.weights[component] 
                         for component in scores.keys())
        
        # Scale to 0-100
        final_score = np.clip(total_score * 100, self.min_score, self.max_score)
        
        # Overall confidence
        overall_confidence = np.mean(confidence_factors)
        
        # Create rationale string
        rationale = self._create_rationale(rationale_parts, final_score)
        
        # Determine investment window
        window_start, window_end = self._calculate_investment_window(property_data, rate_forecasts)
        
        return {
            'score': float(final_score),
            'confidence': float(overall_confidence),
            'rationale': rationale,
            'components': scores,
            'window_start': window_start,
            'window_end': window_end,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_cap_rate_component(self, property_data: Dict, 
                                     caprate_forecasts: Optional[Dict] = None) -> Tuple[float, str, float]:
        """Calculate cap rate compression opportunity"""
        
        current_cap_rate = property_data.get('cap_rate_observed')
        market = property_data.get('market', 'unknown')
        asset_type = property_data.get('asset_type', 'unknown')
        
        if not current_cap_rate:
            return 0.0, "", 0.3
        
        # Try to get forecast
        predicted_cap_rate = None
        confidence = 0.5
        
        if caprate_forecasts:
            # Find matching forecast
            segment_key = f"{market}_{asset_type}"
            segment_forecast = caprate_forecasts.get(segment_key)
            
            if segment_forecast and segment_forecast.get('forecasts'):
                predicted_cap_rate = segment_forecast['forecasts'][0]
                confidence = 0.8 if segment_forecast.get('model_used') == 'prophet' else 0.6
        
        # Fallback: assume slight compression
        if predicted_cap_rate is None:
            predicted_cap_rate = current_cap_rate * 0.98  # 2% compression
            confidence = 0.4
        
        # Calculate compression (negative change is good)
        compression = current_cap_rate - predicted_cap_rate
        
        # Score based on compression magnitude
        # 0.5% compression = ~0.5 score, 2% compression = ~1.0 score
        score = np.clip(compression / 0.02, -0.5, 1.0)  # -50bps to +200bps range
        
        # Create rationale
        if compression > 0.001:  # >10bps compression
            rationale = f"Cap rate compression of {compression:.0%} expected"
        elif compression < -0.001:  # >10bps expansion
            rationale = f"Cap rate expansion risk of {abs(compression):.0%}"
        else:
            rationale = "Stable cap rate environment"
        
        return score, rationale, confidence
    
    def _calculate_noi_component(self, property_data: Dict,
                                noi_rent_forecasts: Optional[Dict] = None) -> Tuple[float, str, float]:
        """Calculate NOI growth opportunity"""
        
        property_id = property_data.get('property_id') or property_data.get('id')
        current_noi = property_data.get('noi')
        
        if not current_noi or not property_id:
            return 0.0, "", 0.3
        
        # Try to get NOI forecast
        predicted_noi = None
        confidence = 0.5
        
        if noi_rent_forecasts and property_id in noi_rent_forecasts:
            prop_forecast = noi_rent_forecasts[property_id]
            if (prop_forecast.get('forecasts', {}).get('noi', {}).get('forecasts')):
                predicted_noi = prop_forecast['forecasts']['noi']['forecasts'][0]
                model_used = prop_forecast['forecasts']['noi'].get('model_used', 'none')
                confidence = 0.8 if model_used == 'prophet' else 0.6
        
        # Fallback: assume modest growth
        if predicted_noi is None:
            predicted_noi = current_noi * 1.03  # 3% annual growth
            confidence = 0.4
        
        # Calculate growth rate
        growth_rate = (predicted_noi - current_noi) / current_noi
        
        # Score based on growth rate
        # 5% growth = 0.5 score, 10% growth = 1.0 score
        score = np.clip(growth_rate / 0.10, -0.5, 1.0)
        
        # Create rationale
        if growth_rate > 0.02:  # >2% growth
            rationale = f"NOI growth of {growth_rate:.1%} projected"
        elif growth_rate < -0.02:  # >2% decline
            rationale = f"NOI decline risk of {abs(growth_rate):.1%}"
        else:
            rationale = "Stable NOI expectations"
        
        return score, rationale, confidence
    
    def _calculate_rate_component(self, property_data: Dict,
                                 rate_forecasts: Optional[Dict] = None) -> Tuple[float, str, float]:
        """Calculate rate environment opportunity"""
        
        current_rate = property_data.get('base_rate', 0.035)  # 3.5% default
        
        # Try to get rate forecast
        predicted_rate = None
        confidence = 0.5
        
        if rate_forecasts and 'base_rate' in rate_forecasts:
            rate_data = rate_forecasts['base_rate']
            if rate_data.get('forecasts'):
                predicted_rate = rate_data['forecasts'][0]
                model_used = rate_data.get('model_used', 'none')
                confidence = 0.8 if model_used == 'prophet' else 0.6
        
        # Fallback: assume slight increase
        if predicted_rate is None:
            predicted_rate = current_rate + 0.002  # 20bps increase
            confidence = 0.4
        
        # Calculate rate change (negative change is good for valuations)
        rate_change = predicted_rate - current_rate
        
        # Score based on rate change
        # -100bps = 1.0 score, +100bps = -0.5 score
        score = np.clip(-rate_change / 0.01, -0.5, 1.0)
        
        # Create rationale
        if rate_change < -0.0025:  # >25bps decrease
            rationale = f"Favorable rate decline of {abs(rate_change):.0%}"
        elif rate_change > 0.0025:  # >25bps increase
            rationale = f"Rate headwinds of +{rate_change:.0%}"
        else:
            rationale = "Neutral rate environment"
        
        return score, rationale, confidence
    
    def _calculate_momentum_component(self, property_data: Dict) -> Tuple[float, str, float]:
        """Calculate momentum/trend component"""
        
        # Look for momentum indicators in property data
        momentum_indicators = []
        
        # NOI momentum
        if 'noi_growth_3m' in property_data:
            noi_momentum = property_data['noi_growth_3m'] or 0
            momentum_indicators.append(noi_momentum)
        
        # Rent momentum  
        if 'rent_growth_3m' in property_data:
            rent_momentum = property_data['rent_growth_3m'] or 0
            momentum_indicators.append(rent_momentum)
        
        # Occupancy momentum
        if 'occupancy' in property_data:
            occupancy = property_data['occupancy'] or 0.9
            # High occupancy is positive momentum
            occupancy_momentum = (occupancy - 0.85) / 0.10  # 85-95% range
            momentum_indicators.append(occupancy_momentum)
        
        if not momentum_indicators:
            return 0.0, "", 0.3
        
        # Average momentum
        avg_momentum = np.mean(momentum_indicators)
        
        # Score momentum (scale to 0-1 range)
        score = np.clip(avg_momentum, -0.5, 1.0)
        confidence = 0.7  # Historical data is relatively reliable
        
        # Create rationale
        if avg_momentum > 0.02:  # >2% positive momentum
            rationale = f"Positive momentum of {avg_momentum:.1%}"
        elif avg_momentum < -0.02:  # >2% negative momentum
            rationale = f"Negative momentum of {abs(avg_momentum):.1%}"
        else:
            rationale = "Neutral momentum trends"
        
        return score, rationale, confidence
    
    def _create_rationale(self, rationale_parts: List[str], final_score: float) -> str:
        """Create final rationale string"""
        
        # Filter out empty rationales
        valid_parts = [part for part in rationale_parts if part.strip()]
        
        # Add overall assessment
        if final_score >= 75:
            assessment = "Excellent arbitrage opportunity"
        elif final_score >= 60:
            assessment = "Good investment potential"
        elif final_score >= 40:
            assessment = "Moderate opportunity"
        elif final_score >= 25:
            assessment = "Limited upside potential"
        else:
            assessment = "High-risk opportunity"
        
        # Combine
        if valid_parts:
            top_factors = "; ".join(valid_parts[:3])  # Top 3 factors
            return f"{assessment}. {top_factors}."
        else:
            return f"{assessment}. Mixed market signals."
    
    def _calculate_investment_window(self, property_data: Dict,
                                   rate_forecasts: Optional[Dict] = None) -> Tuple[str, str]:
        """Calculate optimal investment window"""
        
        # Default to next 6 months
        start_date = datetime.now() + timedelta(days=30)  # Next month
        end_date = start_date + timedelta(days=180)  # 6 months
        
        # Adjust based on rate environment
        if rate_forecasts and 'base_rate' in rate_forecasts:
            rate_data = rate_forecasts['base_rate']
            if rate_data.get('forecasts'):
                # If rates are expected to decline, extend window
                rate_trend = np.mean(rate_data['forecasts'][:3])  # Next 3 months
                current_rate = property_data.get('base_rate', 0.035)
                
                if rate_trend < current_rate - 0.005:  # >50bps decline expected
                    end_date = start_date + timedelta(days=270)  # Extend to 9 months
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def batch_score(self, properties_df: pd.DataFrame,
                   rate_forecasts: Optional[Dict] = None,
                   caprate_forecasts: Optional[Dict] = None,
                   noi_rent_forecasts: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Score multiple properties"""
        
        logger.info(f"Batch scoring {len(properties_df)} properties")
        
        results = []
        
        for _, property_row in properties_df.iterrows():
            property_data = property_row.to_dict()
            
            try:
                score_result = self.calculate_score(
                    property_data, rate_forecasts, caprate_forecasts, noi_rent_forecasts
                )
                
                # Add property identification
                score_result['property_id'] = property_data.get('property_id') or property_data.get('id')
                score_result['market'] = property_data.get('market')
                score_result['asset_type'] = property_data.get('asset_type')
                
                results.append(score_result)
                
            except Exception as e:
                logger.error(f"Failed to score property {property_data.get('property_id', 'unknown')}: {e}")
                
                # Add failed result
                results.append({
                    'property_id': property_data.get('property_id'),
                    'score': 0.0,
                    'confidence': 0.0,
                    'rationale': f"Scoring failed: {str(e)}",
                    'error': True
                })
        
        logger.info(f"Batch scoring completed. {len([r for r in results if not r.get('error')])} successful scores")
        
        return results
    
    def get_score_distribution(self, scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze score distribution"""
        
        valid_scores = [s['score'] for s in scores if not s.get('error')]
        
        if not valid_scores:
            return {'error': 'No valid scores'}
        
        scores_array = np.array(valid_scores)
        
        return {
            'count': len(valid_scores),
            'mean': float(np.mean(scores_array)),
            'median': float(np.median(scores_array)),
            'std': float(np.std(scores_array)),
            'min': float(np.min(scores_array)),
            'max': float(np.max(scores_array)),
            'percentiles': {
                '25th': float(np.percentile(scores_array, 25)),
                '75th': float(np.percentile(scores_array, 75)),
                '90th': float(np.percentile(scores_array, 90)),
                '95th': float(np.percentile(scores_array, 95))
            },
            'high_quality_count': len([s for s in valid_scores if s >= 70]),
            'good_count': len([s for s in valid_scores if s >= 50 and s < 70]),
            'poor_count': len([s for s in valid_scores if s < 30])
        }

def create_default_scorer() -> ArbitrageScorer:
    """Create scorer with default configuration"""
    return ArbitrageScorer()

__all__ = [
    'ArbitrageScorer',
    'create_default_scorer'
]
