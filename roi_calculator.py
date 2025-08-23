#!/usr/bin/env python3
"""
CapSight ROI Calculator for Sales Calls

Quick ROI estimation tool to demonstrate value proposition during prospect calls.
Shows potential annual value creation from improved timing and accuracy.

Usage:
    python roi_calculator.py --deals 20 --avg-value 12000000 --improvement-bps 40
    python roi_calculator.py --interactive
"""

import argparse
import json
from typing import Dict, Any


class CapSightROICalculator:
    """Calculate ROI for CapSight implementation."""
    
    def __init__(self):
        self.baseline_accuracy_bps = 40  # Industry standard cap rate error
        self.typical_deals_per_year = 20
        self.typical_deal_value = 12_000_000
        self.typical_improvement_bps = 15  # Conservative estimate
    
    def calculate_roi(
        self, 
        deals_per_year: int,
        avg_deal_value: float,
        accuracy_improvement_bps: float,
        current_accuracy_bps: float = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive ROI metrics."""
        
        if current_accuracy_bps is None:
            current_accuracy_bps = self.baseline_accuracy_bps
        
        # Value creation from improved timing
        timing_value_per_deal = (accuracy_improvement_bps / 10_000) * avg_deal_value
        annual_timing_value = timing_value_per_deal * deals_per_year
        
        # Additional value streams
        due_diligence_savings = deals_per_year * 25_000  # $25k per deal saved
        deal_flow_improvement = deals_per_year * 0.15 * avg_deal_value * 0.02  # 15% more deals, 2% better returns
        market_timing_premium = annual_timing_value * 0.3  # 30% additional from timing
        
        total_annual_value = annual_timing_value + due_diligence_savings + deal_flow_improvement + market_timing_premium
        
        # CapSight cost (estimated)
        annual_cost = 250_000  # Platform + data fees
        
        # ROI calculation
        net_annual_value = total_annual_value - annual_cost
        roi_multiple = total_annual_value / annual_cost if annual_cost > 0 else 0
        payback_months = (annual_cost / (total_annual_value / 12)) if total_annual_value > 0 else 999
        
        return {
            'inputs': {
                'deals_per_year': deals_per_year,
                'avg_deal_value': avg_deal_value,
                'accuracy_improvement_bps': accuracy_improvement_bps,
                'current_accuracy_bps': current_accuracy_bps
            },
            'value_streams': {
                'timing_value_annual': annual_timing_value,
                'due_diligence_savings': due_diligence_savings,
                'deal_flow_improvement': deal_flow_improvement,
                'market_timing_premium': market_timing_premium,
                'total_annual_value': total_annual_value
            },
            'financials': {
                'annual_cost': annual_cost,
                'net_annual_value': net_annual_value,
                'roi_multiple': roi_multiple,
                'payback_months': payback_months
            },
            'per_deal_metrics': {
                'value_per_deal': timing_value_per_deal,
                'cost_per_deal': annual_cost / deals_per_year,
                'net_value_per_deal': timing_value_per_deal - (annual_cost / deals_per_year)
            }
        }
    
    def format_currency(self, amount: float) -> str:
        """Format currency for display."""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}k"
        else:
            return f"${amount:,.0f}"
    
    def print_roi_analysis(self, roi_data: Dict[str, Any], prospect_name: str = None):
        """Print formatted ROI analysis."""
        
        if prospect_name:
            print(f"\n🏦 CapSight ROI Analysis - {prospect_name}")
        else:
            print(f"\n🏦 CapSight ROI Analysis")
        print("=" * 60)
        
        inputs = roi_data['inputs']
        values = roi_data['value_streams'] 
        financials = roi_data['financials']
        per_deal = roi_data['per_deal_metrics']
        
        # Input summary
        print(f"\n📊 INPUT ASSUMPTIONS:")
        print(f"   • Annual Deal Volume: {inputs['deals_per_year']} deals")
        print(f"   • Average Deal Value: {self.format_currency(inputs['avg_deal_value'])}")
        print(f"   • Accuracy Improvement: {inputs['accuracy_improvement_bps']} basis points")
        print(f"   • Current Accuracy: {inputs['current_accuracy_bps']} bps (industry baseline)")
        
        # Value creation breakdown
        print(f"\n💰 ANNUAL VALUE CREATION:")
        print(f"   • Timing Advantage: {self.format_currency(values['timing_value_annual'])}")
        print(f"   • Due Diligence Savings: {self.format_currency(values['due_diligence_savings'])}")
        print(f"   • Enhanced Deal Flow: {self.format_currency(values['deal_flow_improvement'])}")
        print(f"   • Market Timing Premium: {self.format_currency(values['market_timing_premium'])}")
        print(f"   ────────────────────────")
        print(f"   • TOTAL ANNUAL VALUE: {self.format_currency(values['total_annual_value'])}")
        
        # Financial summary
        print(f"\n📈 FINANCIAL METRICS:")
        print(f"   • CapSight Annual Cost: {self.format_currency(financials['annual_cost'])}")
        print(f"   • Net Annual Value: {self.format_currency(financials['net_annual_value'])}")
        print(f"   • ROI Multiple: {financials['roi_multiple']:.1f}x")
        print(f"   • Payback Period: {financials['payback_months']:.1f} months")
        
        # Per-deal metrics
        print(f"\n🎯 PER-DEAL IMPACT:")
        print(f"   • Value per Deal: {self.format_currency(per_deal['value_per_deal'])}")
        print(f"   • Cost per Deal: {self.format_currency(per_deal['cost_per_deal'])}")
        print(f"   • Net Value per Deal: {self.format_currency(per_deal['net_value_per_deal'])}")
        
        # Key insights
        self._print_key_insights(roi_data)
        
        # Sales talking points
        self._print_sales_points(roi_data)
    
    def _print_key_insights(self, roi_data: Dict[str, Any]):
        """Print key insights and recommendations."""
        financials = roi_data['financials']
        inputs = roi_data['inputs']
        
        print(f"\n🔍 KEY INSIGHTS:")
        
        if financials['roi_multiple'] > 3:
            print(f"   ✅ STRONG ROI: {financials['roi_multiple']:.1f}x return justifies investment")
        elif financials['roi_multiple'] > 2:
            print(f"   ✅ GOOD ROI: {financials['roi_multiple']:.1f}x return with solid business case")
        elif financials['roi_multiple'] > 1.5:
            print(f"   ⚠️  MARGINAL ROI: {financials['roi_multiple']:.1f}x return - consider deal volume increase")
        else:
            print(f"   ❌ LOW ROI: {financials['roi_multiple']:.1f}x - may need different value proposition")
        
        if financials['payback_months'] < 12:
            print(f"   ⚡ FAST PAYBACK: {financials['payback_months']:.1f} month payback period")
        elif financials['payback_months'] < 24:
            print(f"   ⏳ REASONABLE PAYBACK: {financials['payback_months']:.1f} month payback period")
        else:
            print(f"   🐌 SLOW PAYBACK: {financials['payback_months']:.1f} months - consider higher deal volume")
        
        # Break-even analysis
        break_even_deals = 250_000 / (roi_data['per_deal_metrics']['net_value_per_deal'])
        if break_even_deals < inputs['deals_per_year']:
            print(f"   📊 BREAK-EVEN: {break_even_deals:.0f} deals needed (you do {inputs['deals_per_year']})")
        else:
            print(f"   📊 BREAK-EVEN: Need {break_even_deals:.0f} deals/year for break-even")
    
    def _print_sales_points(self, roi_data: Dict[str, Any]):
        """Print key sales talking points."""
        values = roi_data['value_streams']
        financials = roi_data['financials']
        
        print(f"\n🎯 SALES TALKING POINTS:")
        print(f"   • \"One good deal pays for CapSight all year\"")
        print(f"   • \"{self.format_currency(values['total_annual_value'])} annual value vs {self.format_currency(financials['annual_cost'])} cost\"")
        print(f"   • \"Break-even in {financials['payback_months']:.0f} months\"")
        print(f"   • \"Every deal generates {self.format_currency(roi_data['per_deal_metrics']['net_value_per_deal'])} net value\"")
        print(f"   • \"Save 2-3 weeks per deal on due diligence\"")
        print(f"   • \"Spot opportunities 2-4 days before competition\"")
        
        print(f"\n📞 CLOSING QUESTIONS:")
        print(f"   • \"What's the cost of missing one good deal per year?\"")
        print(f"   • \"How much do you spend on due diligence that doesn't close?\"")
        print(f"   • \"What's your competitive advantage in deal sourcing today?\"")
        print(f"   • \"Ready for a 2-week pilot to prove the {financials['roi_multiple']:.1f}x ROI?\"")
    
    def interactive_calculator(self):
        """Run interactive ROI calculator."""
        print("🏦 CapSight Interactive ROI Calculator")
        print("=" * 40)
        
        try:
            # Get inputs
            print("\nPlease provide the following information:")
            
            prospect_name = input("Prospect name (optional): ").strip()
            if not prospect_name:
                prospect_name = None
            
            deals = int(input(f"Annual deal volume [{self.typical_deals_per_year}]: ") or self.typical_deals_per_year)
            
            avg_value_input = input(f"Average deal value [{self.typical_deal_value:,}]: ").strip()
            if avg_value_input:
                # Handle inputs like "12M", "5.5M", "500K"
                if avg_value_input.upper().endswith('M'):
                    avg_value = float(avg_value_input[:-1]) * 1_000_000
                elif avg_value_input.upper().endswith('K'):
                    avg_value = float(avg_value_input[:-1]) * 1_000
                else:
                    avg_value = float(avg_value_input.replace(',', ''))
            else:
                avg_value = self.typical_deal_value
            
            improvement = float(input(f"Expected accuracy improvement (bps) [{self.typical_improvement_bps}]: ") or self.typical_improvement_bps)
            
            # Calculate and display
            roi_data = self.calculate_roi(deals, avg_value, improvement)
            self.print_roi_analysis(roi_data, prospect_name)
            
            # Save results
            save = input("\nSave results to file? (y/n): ").lower() == 'y'
            if save:
                filename = f"roi_analysis_{prospect_name or 'prospect'}_{deals}deals.json"
                filename = filename.replace(' ', '_').replace('/', '_')
                
                with open(filename, 'w') as f:
                    json.dump(roi_data, f, indent=2)
                
                print(f"📁 Results saved to: {filename}")
            
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Invalid input or cancelled.")
            return


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="CapSight ROI Calculator")
    parser.add_argument("--deals", type=int, help="Annual deal volume")
    parser.add_argument("--avg-value", type=float, help="Average deal value")
    parser.add_argument("--improvement-bps", type=float, help="Accuracy improvement in basis points")
    parser.add_argument("--current-bps", type=float, help="Current accuracy (basis points)")
    parser.add_argument("--prospect", help="Prospect name")
    parser.add_argument("--interactive", action="store_true", help="Run interactive mode")
    parser.add_argument("--save", help="Save results to specified JSON file")
    
    args = parser.parse_args()
    
    calculator = CapSightROICalculator()
    
    if args.interactive:
        calculator.interactive_calculator()
        return
    
    # Use provided values or defaults
    deals = args.deals or calculator.typical_deals_per_year
    avg_value = args.avg_value or calculator.typical_deal_value
    improvement = args.improvement_bps or calculator.typical_improvement_bps
    current_bps = args.current_bps or calculator.baseline_accuracy_bps
    
    # Calculate ROI
    roi_data = calculator.calculate_roi(deals, avg_value, improvement, current_bps)
    
    # Display results
    calculator.print_roi_analysis(roi_data, args.prospect)
    
    # Save if requested
    if args.save:
        with open(args.save, 'w') as f:
            json.dump(roi_data, f, indent=2)
        print(f"\n💾 Results saved to: {args.save}")


if __name__ == "__main__":
    main()
