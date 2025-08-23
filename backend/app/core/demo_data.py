"""
Demo Mode Configuration and Data Generation for CapSight
Provides realistic sample data when DEMO_MODE=true
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal
import uuid

# Demo mode flag
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

class DemoDataGenerator:
    """Generates realistic demo data for CapSight"""
    
    def __init__(self):
        self.cities = [
            {"name": "Austin", "state": "TX", "growth_rate": 0.08, "market_temp": "hot"},
            {"name": "Dallas", "state": "TX", "growth_rate": 0.06, "market_temp": "warm"},
            {"name": "Houston", "state": "TX", "growth_rate": 0.05, "market_temp": "warm"},
            {"name": "San Antonio", "state": "TX", "growth_rate": 0.04, "market_temp": "stable"},
            {"name": "Denver", "state": "CO", "growth_rate": 0.07, "market_temp": "hot"},
            {"name": "Phoenix", "state": "AZ", "growth_rate": 0.06, "market_temp": "warm"},
            {"name": "Atlanta", "state": "GA", "growth_rate": 0.05, "market_temp": "warm"},
            {"name": "Nashville", "state": "TN", "growth_rate": 0.09, "market_temp": "hot"},
            {"name": "Tampa", "state": "FL", "growth_rate": 0.07, "market_temp": "hot"},
            {"name": "Charlotte", "state": "NC", "growth_rate": 0.06, "market_temp": "warm"}
        ]
        
        self.property_types = ["single_family", "condo", "townhouse", "duplex"]
        self.street_names = [
            "Investment Ave", "Profit Lane", "ROI Street", "Cash Flow Blvd", 
            "Equity Drive", "Revenue Road", "Capital Circle", "Yield Way",
            "Portfolio Place", "Market Square", "Growth Street", "Value Vista"
        ]
        
    def generate_demo_properties(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generate demo property data"""
        properties = []
        
        for i in range(count):
            city_data = random.choice(self.cities)
            property_type = random.choice(self.property_types)
            
            # Base property characteristics
            if property_type == "single_family":
                bedrooms = random.randint(2, 5)
                bathrooms = random.randint(2, 4)
                sqft = random.randint(1200, 3500)
                lot_size = random.uniform(0.15, 0.5)
            elif property_type == "condo":
                bedrooms = random.randint(1, 3)
                bathrooms = random.randint(1, 3)
                sqft = random.randint(800, 1800)
                lot_size = None
            elif property_type == "townhouse":
                bedrooms = random.randint(2, 4)
                bathrooms = random.randint(2, 3)
                sqft = random.randint(1100, 2200)
                lot_size = random.uniform(0.05, 0.2)
            else:  # duplex
                bedrooms = random.randint(4, 6)
                bathrooms = random.randint(3, 5)
                sqft = random.randint(1800, 3000)
                lot_size = random.uniform(0.2, 0.4)
            
            # Price based on location and size
            base_price_per_sqft = {
                "Austin": random.randint(300, 450),
                "Dallas": random.randint(200, 350),
                "Houston": random.randint(180, 320),
                "San Antonio": random.randint(150, 280),
                "Denver": random.randint(350, 500),
                "Phoenix": random.randint(250, 400),
                "Atlanta": random.randint(200, 350),
                "Nashville": random.randint(280, 420),
                "Tampa": random.randint(220, 380),
                "Charlotte": random.randint(190, 340)
            }[city_data["name"]]
            
            list_price = base_price_per_sqft * sqft
            market_value = list_price * random.uniform(0.95, 1.05)
            
            # Rental estimates
            rent_multiplier = 0.006 if property_type == "single_family" else 0.007
            estimated_rent = list_price * rent_multiplier
            
            # Calculate investment metrics
            annual_rent = estimated_rent * 12
            cap_rate = (annual_rent / list_price) * 100
            monthly_expenses = estimated_rent * 0.3  # 30% for expenses
            cash_flow = estimated_rent - monthly_expenses - (list_price * 0.003)  # mortgage payment estimate
            
            property_data = {
                "id": str(uuid.uuid4()),
                "address": f"{random.randint(100, 9999)} {random.choice(self.street_names)}",
                "city": city_data["name"],
                "state": city_data["state"],
                "zip_code": f"{random.randint(70000, 99999)}",
                "property_type": property_type,
                "list_price": round(list_price, 2),
                "market_value": round(market_value, 2),
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "square_feet": sqft,
                "lot_size_acres": lot_size,
                "year_built": random.randint(1990, 2024),
                "estimated_rental_income": round(estimated_rent, 2),
                "cap_rate": round(cap_rate, 2),
                "cash_flow": round(cash_flow, 2),
                "days_on_market": random.randint(1, 120),
                "status": random.choice(["active", "pending", "under_contract"] + ["active"] * 5),
                "coordinates": {
                    "lat": round(random.uniform(25.0, 47.0), 6),
                    "lng": round(random.uniform(-125.0, -80.0), 6)
                },
                "photos": self._generate_photo_urls(3),
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat(),
                "updated_at": (datetime.utcnow() - timedelta(days=random.randint(0, 7))).isoformat()
            }
            
            properties.append(property_data)
        
        return properties
    
    def generate_demo_opportunities(self, properties: List[Dict[str, Any]], count: int = 25) -> List[Dict[str, Any]]:
        """Generate demo arbitrage opportunities"""
        opportunities = []
        
        # Select properties with good investment potential
        good_properties = [p for p in properties if p["cap_rate"] > 6.0 and p["cash_flow"] > 200]
        selected_properties = random.sample(good_properties, min(count, len(good_properties)))
        
        for prop in selected_properties:
            opportunity_type = random.choice(["flip", "rental", "brrrr"])
            
            if opportunity_type == "flip":
                # Flip opportunity
                arv = prop["list_price"] * random.uniform(1.15, 1.35)  # After Repair Value
                rehab_cost = prop["list_price"] * random.uniform(0.10, 0.25)
                profit = arv - prop["list_price"] - rehab_cost - (arv * 0.1)  # 10% for costs
                timeline = random.randint(3, 8)
                
                opportunity = {
                    "id": str(uuid.uuid4()),
                    "property_id": prop["id"],
                    "property": {
                        "address": prop["address"],
                        "city": prop["city"],
                        "state": prop["state"],
                        "price": prop["list_price"],
                        "property_type": prop["property_type"]
                    },
                    "opportunity_type": "flip",
                    "confidence_score": round(random.uniform(7.5, 9.5), 1),
                    "potential_profit": round(profit, 2),
                    "profit_margin": round((profit / prop["list_price"]) * 100, 1),
                    "investment_required": round(prop["list_price"] + rehab_cost, 2),
                    "timeline_months": timeline,
                    "risk_level": random.choice(["low", "medium", "high"]),
                    "arv": round(arv, 2),
                    "rehab_estimate": round(rehab_cost, 2)
                }
            
            elif opportunity_type == "rental":
                # Rental opportunity
                annual_cash_flow = prop["cash_flow"] * 12
                
                opportunity = {
                    "id": str(uuid.uuid4()),
                    "property_id": prop["id"],
                    "property": {
                        "address": prop["address"],
                        "city": prop["city"],
                        "state": prop["state"],
                        "price": prop["list_price"],
                        "property_type": prop["property_type"]
                    },
                    "opportunity_type": "rental",
                    "confidence_score": round(random.uniform(8.0, 9.8), 1),
                    "potential_profit": round(annual_cash_flow, 2),
                    "profit_margin": None,
                    "investment_required": round(prop["list_price"] * 1.05, 2),  # Include closing costs
                    "timeline_months": None,
                    "risk_level": "low" if prop["cap_rate"] > 8 else "medium",
                    "cap_rate": prop["cap_rate"],
                    "cash_on_cash_return": round((annual_cash_flow / (prop["list_price"] * 0.25)) * 100, 1)
                }
            
            else:  # BRRRR
                # Buy, Rehab, Rent, Refinance, Repeat
                rehab_cost = prop["list_price"] * random.uniform(0.15, 0.30)
                arv = prop["list_price"] * random.uniform(1.20, 1.40)
                refinance_amount = arv * 0.75  # 75% LTV
                cash_left_in_deal = prop["list_price"] + rehab_cost - refinance_amount
                annual_cash_flow = (prop["estimated_rental_income"] * 12) - (refinance_amount * 0.05)  # 5% debt service
                
                opportunity = {
                    "id": str(uuid.uuid4()),
                    "property_id": prop["id"],
                    "property": {
                        "address": prop["address"],
                        "city": prop["city"],
                        "state": prop["state"],
                        "price": prop["list_price"],
                        "property_type": prop["property_type"]
                    },
                    "opportunity_type": "brrrr",
                    "confidence_score": round(random.uniform(7.0, 9.0), 1),
                    "potential_profit": round(annual_cash_flow, 2),
                    "profit_margin": None,
                    "investment_required": round(cash_left_in_deal, 2),
                    "timeline_months": random.randint(6, 12),
                    "risk_level": "medium",
                    "arv": round(arv, 2),
                    "rehab_estimate": round(rehab_cost, 2),
                    "refinance_amount": round(refinance_amount, 2)
                }
            
            # Add common fields
            opportunity.update({
                "market_trends": {
                    "price_growth_6m": round(random.uniform(2.0, 12.0), 1),
                    "demand_score": round(random.uniform(6.0, 9.5), 1),
                    "inventory_days": random.randint(20, 80)
                },
                "ai_insights": self._generate_ai_insights(opportunity_type),
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(0, 14))).isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=random.randint(3, 14))).isoformat()
            })
            
            opportunities.append(opportunity)
        
        return opportunities
    
    def generate_demo_forecasts(self, properties: List[Dict[str, Any]], count: int = 30) -> List[Dict[str, Any]]:
        """Generate demo forecast data"""
        forecasts = []
        selected_properties = random.sample(properties, min(count, len(properties)))
        
        for prop in selected_properties:
            forecast_type = random.choice(["price_prediction", "rental_prediction"])
            
            if forecast_type == "price_prediction":
                current_value = prop["list_price"]
                growth_rates = [0.04, 0.045, 0.05, 0.055, 0.06]  # Annual growth rates
            else:
                current_value = prop["estimated_rental_income"]
                growth_rates = [0.03, 0.035, 0.04, 0.045, 0.05]  # Rental growth rates
            
            predictions = {}
            confidence_intervals = {}
            
            periods = [3, 6, 12, 24, 36]
            for i, period in enumerate(periods):
                base_rate = growth_rates[i] if i < len(growth_rates) else growth_rates[-1]
                rate_variation = random.uniform(-0.01, 0.01)
                actual_rate = base_rate + rate_variation
                
                predicted_value = current_value * ((1 + actual_rate) ** (period / 12))
                
                predictions[f"{period}_months"] = round(predicted_value, 2)
                confidence_intervals[f"{period}_months"] = {
                    "low": round(predicted_value * 0.92, 2),
                    "high": round(predicted_value * 1.08, 2)
                }
            
            forecast = {
                "id": str(uuid.uuid4()),
                "property_id": prop["id"],
                "property_address": prop["address"],
                "forecast_type": forecast_type,
                "current_value": current_value,
                "predicted_values": predictions,
                "confidence_intervals": confidence_intervals,
                "factors": [
                    {"name": "Market Conditions", "impact": "positive", "weight": 0.35},
                    {"name": "Economic Indicators", "impact": "neutral", "weight": 0.25},
                    {"name": "Local Development", "impact": "positive", "weight": 0.20},
                    {"name": "Interest Rates", "impact": "negative", "weight": 0.20}
                ],
                "model_accuracy": round(random.uniform(0.82, 0.94), 2),
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(0, 10))).isoformat(),
                "updated_at": (datetime.utcnow() - timedelta(days=random.randint(0, 3))).isoformat()
            }
            
            forecasts.append(forecast)
        
        return forecasts
    
    def generate_demo_analytics(self) -> Dict[str, Any]:
        """Generate demo analytics data"""
        return {
            "overview": {
                "total_properties": random.randint(150, 200),
                "active_opportunities": random.randint(20, 35),
                "total_forecasts": random.randint(60, 80),
                "potential_profit": random.randint(2000000, 3500000)
            },
            "recent_activity": [
                {
                    "type": "opportunity_found",
                    "property_address": f"{random.randint(100, 999)} {random.choice(self.street_names)}, {random.choice(self.cities)['name']}, TX",
                    "profit_potential": random.randint(50000, 120000),
                    "timestamp": (datetime.utcnow() - timedelta(hours=random.randint(1, 48))).isoformat()
                }
                for _ in range(5)
            ],
            "market_trends": {
                "price_growth_ytd": round(random.uniform(6.0, 12.0), 1),
                "rental_growth_ytd": round(random.uniform(4.0, 8.0), 1),
                "inventory_change": round(random.uniform(-20.0, -5.0), 1),
                "demand_index": round(random.uniform(7.0, 9.5), 1)
            },
            "performance_metrics": {
                "accuracy_score": round(random.uniform(0.85, 0.95), 2),
                "successful_predictions": random.randint(40, 60),
                "total_predictions": random.randint(50, 70),
                "avg_profit_realized": random.randint(60000, 80000)
            }
        }
    
    def _generate_photo_urls(self, count: int) -> List[str]:
        """Generate realistic photo URLs"""
        photos = [
            "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800",
            "https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800",
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=800",
            "https://images.unsplash.com/photo-1605276374104-dee2a0ed3cd6?w=800",
            "https://images.unsplash.com/photo-1582407947304-fd86f028f716?w=800",
            "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800",
            "https://images.unsplash.com/photo-1493663284031-b7e3aaa4c4a0?w=800",
            "https://images.unsplash.com/photo-1449844908441-8829872d2607?w=800"
        ]
        return random.sample(photos, min(count, len(photos)))
    
    def _generate_ai_insights(self, opportunity_type: str) -> List[str]:
        """Generate AI insights based on opportunity type"""
        common_insights = [
            "Strong neighborhood appreciation trend",
            "High-demand school district",
            "Growing job market in area",
            "Low crime rate neighborhood"
        ]
        
        flip_insights = [
            "Below-market purchase price",
            "Minimal structural issues",
            "High-end finishes potential",
            "Fast-selling neighborhood"
        ]
        
        rental_insights = [
            "Excellent rental market fundamentals",
            "Low vacancy rates historically", 
            "Strong tenant demand",
            "Rent growth outpacing inflation"
        ]
        
        brrrr_insights = [
            "High refinance potential",
            "Value-add opportunities",
            "Strong rental comps",
            "Emerging market area"
        ]
        
        if opportunity_type == "flip":
            pool = common_insights + flip_insights
        elif opportunity_type == "rental":
            pool = common_insights + rental_insights
        else:  # BRRRR
            pool = common_insights + brrrr_insights
        
        return random.sample(pool, random.randint(3, 5))

# Global demo data generator instance
demo_generator = DemoDataGenerator()

def get_demo_data() -> Dict[str, Any]:
    """Get all demo data for the application"""
    if not DEMO_MODE:
        return None
    
    properties = demo_generator.generate_demo_properties(50)
    opportunities = demo_generator.generate_demo_opportunities(properties, 25)
    forecasts = demo_generator.generate_demo_forecasts(properties, 30)
    analytics = demo_generator.generate_demo_analytics()
    
    return {
        "properties": properties,
        "opportunities": opportunities,
        "forecasts": forecasts,
        "analytics": analytics,
        "generated_at": datetime.utcnow().isoformat(),
        "demo_mode": True
    }

def is_demo_mode() -> bool:
    """Check if demo mode is enabled"""
    return DEMO_MODE
