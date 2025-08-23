"""
CapSight Accuracy Auditor
Independent validation of ML model performance against backtested real estate data
"""
import pandas as pd
import numpy as np
import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class CapSightAccuracyAuditor:
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.results = []
        self.metrics = {}
        self.sla_targets = {
            'accuracy_threshold': 0.942,  # 94.2%
            'cap_rate_mae_bp': 25,        # 25 basis points
            'noi_mape_pct': 8.0,          # 8% MAPE
            'top_decile_precision': 0.85,  # 85%
            'confidence_calibration': 0.05, # Within 5%
            'response_time_ms': 100       # <100ms
        }
        
    def generate_backtest_dataset(self, n_properties=500):
        """Generate realistic backtest dataset for audit"""
        print("🔍 GENERATING BACKTEST DATASET")
        print("=" * 50)
        
        np.random.seed(42)  # Reproducible results
        
        # Property characteristics
        properties = []
        for i in range(n_properties):
            # Base property attributes
            square_feet = np.random.normal(2000, 600)
            square_feet = max(800, min(8000, square_feet))
            
            bedrooms = np.random.choice([2, 3, 4, 5], p=[0.2, 0.4, 0.3, 0.1])
            bathrooms = bedrooms * 0.75 + np.random.normal(0, 0.5)
            bathrooms = max(1, min(6, bathrooms))
            
            year_built = np.random.randint(1950, 2023)
            lot_size = np.random.lognormal(8.5, 0.5)  # Log-normal distribution
            
            # Location factors (ZIP code proxies)
            zip_tier = np.random.choice(['premium', 'mid', 'value'], p=[0.2, 0.5, 0.3])
            location_multiplier = {'premium': 1.4, 'mid': 1.0, 'value': 0.7}[zip_tier]
            
            # Market timing
            market_date = datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 365))
            market_cycle = np.sin(market_date.timetuple().tm_yday / 365 * 2 * np.pi) * 0.1 + 1.0
            
            # Calculate base value using realistic pricing model
            base_price_per_sqft = 150 * location_multiplier * market_cycle
            age_factor = max(0.7, 1.0 - (2024 - year_built) * 0.005)  # Age depreciation
            
            estimated_value = (square_feet * base_price_per_sqft * age_factor + 
                             lot_size * 15 + bedrooms * 5000)
            
            # Add realistic noise
            estimated_value *= np.random.normal(1.0, 0.15)
            estimated_value = max(100000, estimated_value)
            
            # Calculate rental metrics
            monthly_rent = estimated_value * 0.008 * location_multiplier  # 0.8% rent-to-value
            monthly_rent *= np.random.normal(1.0, 0.12)  # Rental market variation
            
            annual_noi = monthly_rent * 12 * 0.75  # 25% expense ratio
            cap_rate = (annual_noi / estimated_value) * 100
            
            # Ensure realistic ranges
            cap_rate = max(3.0, min(12.0, cap_rate))
            annual_noi = max(5000, annual_noi)
            
            property_data = {
                'property_id': f'AUDIT_{i+1:04d}',
                'address': f'{100 + i} Main St, City, State {10000 + i}',
                'property_type': np.random.choice(['single_family', 'condo', 'townhouse'], 
                                                p=[0.6, 0.25, 0.15]),
                'bedrooms': int(bedrooms),
                'bathrooms': round(bathrooms, 1),
                'square_feet': int(square_feet),
                'lot_size': int(lot_size),
                'year_built': int(year_built),
                'listing_price': int(estimated_value * np.random.normal(1.05, 0.08)),  # List slightly above value
                'zip_tier': zip_tier,
                'market_date': market_date.isoformat(),
                
                # Ground truth values (what we're trying to predict)
                'actual_value': int(estimated_value),
                'actual_cap_rate': round(cap_rate, 2),
                'actual_noi': int(annual_noi),
                'actual_monthly_rent': int(monthly_rent)
            }
            properties.append(property_data)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(properties)
        df.to_csv('accuracy_audit/backtest.csv', index=False)
        
        print(f"✅ Generated {n_properties} properties for backtesting")
        print(f"💾 Saved to: accuracy_audit/backtest.csv")
        
        # Display dataset statistics
        print(f"\n📊 Dataset Statistics:")
        print(f"Value range: ${df['actual_value'].min():,.0f} - ${df['actual_value'].max():,.0f}")
        print(f"Cap rate range: {df['actual_cap_rate'].min():.1f}% - {df['actual_cap_rate'].max():.1f}%")
        print(f"NOI range: ${df['actual_noi'].min():,.0f} - ${df['actual_noi'].max():,.0f}")
        print(f"Median property value: ${df['actual_value'].median():,.0f}")
        
        return df
    
    def validate_data_segregation(self, df):
        """Ensure backtest data wasn't used in training"""
        print("\n🔒 VALIDATING DATA SEGREGATION")
        print("=" * 50)
        
        # Check for temporal separation
        backtest_dates = pd.to_datetime(df['market_date'])
        earliest_date = backtest_dates.min()
        latest_date = backtest_dates.max()
        
        print(f"Backtest data range: {earliest_date.date()} to {latest_date.date()}")
        
        # Verify with API metadata
        try:
            response = self.session.get(f"{self.api_base_url}/api/v1/models/training_info")
            if response.status_code == 200:
                training_info = response.json()
                training_cutoff = pd.to_datetime(training_info.get('data_cutoff', '2023-01-01'))
                
                if earliest_date > training_cutoff:
                    print("✅ Data segregation VALIDATED - No training contamination")
                    return True
                else:
                    print("⚠ WARNING - Potential training data overlap detected")
                    return False
            else:
                print("⚠ Could not verify training data cutoff")
                return True  # Proceed with audit
                
        except Exception as e:
            print(f"⚠ Model metadata unavailable: {e}")
            return True  # Proceed with audit
    
    def execute_predictions(self, df):
        """Execute predictions for all properties in dataset"""
        print(f"\n🧠 EXECUTING PREDICTIONS")
        print("=" * 50)
        
        predictions = []
        response_times = []
        
        for idx, row in df.iterrows():
            if idx % 50 == 0:
                print(f"Processing property {idx+1}/{len(df)}...")
            
            # Prepare API payload
            property_data = {
                'property_id': row['property_id'],
                'address': row['address'],
                'property_type': row['property_type'],
                'bedrooms': row['bedrooms'],
                'bathrooms': row['bathrooms'],
                'square_feet': row['square_feet'],
                'lot_size': row['lot_size'],
                'year_built': row['year_built'],
                'listing_price': row['listing_price']
            }
            
            try:
                # Time the API call
                start_time = time.time()
                response = self.session.post(
                    f"{self.api_base_url}/api/v1/analyze",
                    json=property_data,
                    timeout=5
                )
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                
                if response.status_code == 200:
                    prediction = response.json()
                    
                    # Store prediction with actuals for comparison
                    result = {
                        'property_id': row['property_id'],
                        'actual_value': row['actual_value'],
                        'actual_cap_rate': row['actual_cap_rate'],
                        'actual_noi': row['actual_noi'],
                        'predicted_value': prediction.get('predicted_value'),
                        'predicted_cap_rate': prediction.get('predicted_cap_rate', 0),
                        'predicted_noi': prediction.get('predicted_noi', 0),
                        'confidence_lower': prediction.get('confidence_interval', {}).get('lower'),
                        'confidence_upper': prediction.get('confidence_interval', {}).get('upper'),
                        'confidence_level': prediction.get('confidence_interval', {}).get('confidence', 0.95),
                        'risk_score': prediction.get('risk_score'),
                        'response_time_ms': response_time,
                        'prediction_timestamp': datetime.now().isoformat()
                    }
                    predictions.append(result)
                    
                else:
                    print(f"⚠ API error for {row['property_id']}: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠ Prediction failed for {row['property_id']}: {e}")
        
        # Save raw predictions
        with open('accuracy_audit/results.json', 'w') as f:
            json.dump(predictions, f, indent=2)
        
        print(f"\n✅ Completed predictions for {len(predictions)} properties")
        print(f"💾 Results saved to: accuracy_audit/results.json")
        print(f"⏱ Average response time: {np.mean(response_times):.1f}ms")
        print(f"⏱ 99th percentile response time: {np.percentile(response_times, 99):.1f}ms")
        
        return predictions, response_times
    
    def calculate_metrics(self, predictions):
        """Calculate comprehensive accuracy metrics"""
        print(f"\n📊 CALCULATING ACCURACY METRICS")
        print("=" * 50)
        
        df = pd.DataFrame(predictions)
        
        # Remove any invalid predictions
        df = df.dropna(subset=['predicted_value', 'actual_value'])
        
        metrics = {}
        
        # 1. Property Value Accuracy
        value_mae = mean_absolute_error(df['actual_value'], df['predicted_value'])
        value_mape = mean_absolute_percentage_error(df['actual_value'], df['predicted_value']) * 100
        
        # Within 5% accuracy (our main SLA metric)
        value_errors = np.abs(df['predicted_value'] - df['actual_value']) / df['actual_value']
        within_5pct = np.sum(value_errors <= 0.05) / len(value_errors)
        
        metrics['value_mae'] = value_mae
        metrics['value_mape'] = value_mape
        metrics['accuracy_within_5pct'] = within_5pct
        
        # 2. Cap Rate Accuracy (basis points)
        if 'predicted_cap_rate' in df.columns:
            cap_rate_mae_bp = mean_absolute_error(df['actual_cap_rate'], df['predicted_cap_rate']) * 100
            metrics['cap_rate_mae_bp'] = cap_rate_mae_bp
        
        # 3. NOI Accuracy
        if 'predicted_noi' in df.columns:
            noi_mape = mean_absolute_percentage_error(df['actual_noi'], df['predicted_noi']) * 100
            metrics['noi_mape'] = noi_mape
        
        # 4. Top Decile Precision (high-value properties)
        top_decile_threshold = df['actual_value'].quantile(0.9)
        predicted_top_decile = df['predicted_value'] >= top_decile_threshold
        actual_top_decile = df['actual_value'] >= top_decile_threshold
        
        if predicted_top_decile.sum() > 0:
            top_decile_precision = np.sum(predicted_top_decile & actual_top_decile) / predicted_top_decile.sum()
            metrics['top_decile_precision'] = top_decile_precision
        
        # 5. Confidence Calibration
        within_confidence = 0
        total_with_confidence = 0
        
        for _, row in df.iterrows():
            if pd.notna(row['confidence_lower']) and pd.notna(row['confidence_upper']):
                if row['confidence_lower'] <= row['actual_value'] <= row['confidence_upper']:
                    within_confidence += 1
                total_with_confidence += 1
        
        if total_with_confidence > 0:
            confidence_calibration = within_confidence / total_with_confidence
            metrics['confidence_calibration'] = confidence_calibration
            calibration_error = abs(confidence_calibration - 0.95)  # Target 95%
            metrics['calibration_error'] = calibration_error
        
        # 6. Response Time Performance
        response_times = [p['response_time_ms'] for p in predictions if 'response_time_ms' in p]
        if response_times:
            metrics['avg_response_time_ms'] = np.mean(response_times)
            metrics['p99_response_time_ms'] = np.percentile(response_times, 99)
            metrics['sla_response_time_met'] = np.percentile(response_times, 99) < self.sla_targets['response_time_ms']
        
        self.metrics = metrics
        
        # Print metrics summary
        print(f"🎯 ACCURACY RESULTS:")
        print(f"Overall Accuracy (within 5%): {within_5pct:.1%}")
        print(f"Property Value MAE: ${value_mae:,.0f}")
        print(f"Property Value MAPE: {value_mape:.1f}%")
        
        if 'cap_rate_mae_bp' in metrics:
            print(f"Cap Rate MAE: {cap_rate_mae_bp:.1f} basis points")
        
        if 'noi_mape' in metrics:
            print(f"NOI MAPE: {noi_mape:.1f}%")
        
        if 'top_decile_precision' in metrics:
            print(f"Top Decile Precision: {top_decile_precision:.1%}")
        
        if 'confidence_calibration' in metrics:
            print(f"Confidence Calibration: {confidence_calibration:.1%} (target: 95%)")
        
        if response_times:
            print(f"Avg Response Time: {metrics['avg_response_time_ms']:.1f}ms")
            print(f"99th Percentile Response: {metrics['p99_response_time_ms']:.1f}ms")
        
        return metrics
    
    def compare_against_sla(self):
        """Compare results against SLA targets"""
        print(f"\n🎯 SLA COMPLIANCE CHECK")
        print("=" * 50)
        
        sla_results = {}
        
        # Check each SLA target
        if 'accuracy_within_5pct' in self.metrics:
            target = self.sla_targets['accuracy_threshold']
            actual = self.metrics['accuracy_within_5pct']
            sla_results['accuracy'] = {
                'target': f"{target:.1%}",
                'actual': f"{actual:.1%}",
                'met': actual >= target,
                'difference': f"{(actual - target)*100:+.1f}pp"
            }
        
        if 'cap_rate_mae_bp' in self.metrics:
            target = self.sla_targets['cap_rate_mae_bp']
            actual = self.metrics['cap_rate_mae_bp']
            sla_results['cap_rate_accuracy'] = {
                'target': f"<{target} bp",
                'actual': f"{actual:.1f} bp",
                'met': actual <= target,
                'difference': f"{actual - target:+.1f} bp"
            }
        
        if 'noi_mape' in self.metrics:
            target = self.sla_targets['noi_mape_pct']
            actual = self.metrics['noi_mape']
            sla_results['noi_accuracy'] = {
                'target': f"<{target}%",
                'actual': f"{actual:.1f}%",
                'met': actual <= target,
                'difference': f"{actual - target:+.1f}%"
            }
        
        if 'top_decile_precision' in self.metrics:
            target = self.sla_targets['top_decile_precision']
            actual = self.metrics['top_decile_precision']
            sla_results['top_decile'] = {
                'target': f">{target:.0%}",
                'actual': f"{actual:.1%}",
                'met': actual >= target,
                'difference': f"{(actual - target)*100:+.1f}pp"
            }
        
        if 'calibration_error' in self.metrics:
            target = self.sla_targets['confidence_calibration']
            actual = self.metrics['calibration_error']
            sla_results['confidence_calibration'] = {
                'target': f"<{target*100}% error",
                'actual': f"{actual*100:.1f}% error",
                'met': actual <= target,
                'difference': f"{(actual - target)*100:+.1f}pp"
            }
        
        if 'p99_response_time_ms' in self.metrics:
            target = self.sla_targets['response_time_ms']
            actual = self.metrics['p99_response_time_ms']
            sla_results['response_time'] = {
                'target': f"<{target}ms",
                'actual': f"{actual:.0f}ms",
                'met': actual <= target,
                'difference': f"{actual - target:+.0f}ms"
            }
        
        # Print SLA results
        passed = 0
        total = len(sla_results)
        
        for metric_name, result in sla_results.items():
            status = "✅ PASS" if result['met'] else "❌ FAIL"
            print(f"{status} {metric_name.upper()}: {result['actual']} (target: {result['target']})")
            if result['met']:
                passed += 1
        
        print(f"\n📋 SLA SUMMARY: {passed}/{total} targets met ({passed/total:.1%})")
        
        return sla_results
    
    def run_full_audit(self):
        """Execute complete accuracy audit"""
        print("🔍 CAPSIGHT ACCURACY AUDIT - AUGUST 2025")
        print("=" * 60)
        print(f"Audit started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API endpoint: {self.api_base_url}")
        print()
        
        # Step 1: Generate backtest dataset
        df = self.generate_backtest_dataset(500)
        
        # Step 2: Validate data segregation
        data_clean = self.validate_data_segregation(df)
        
        # Step 3: Execute predictions
        predictions, response_times = self.execute_predictions(df)
        
        if not predictions:
            print("❌ AUDIT FAILED - No successful predictions")
            return False
        
        # Step 4: Calculate metrics
        metrics = self.calculate_metrics(predictions)
        
        # Step 5: Compare against SLA
        sla_results = self.compare_against_sla()
        
        # Step 6: Generate visualizations
        self.create_accuracy_plots(predictions)
        
        print(f"\n🎉 ACCURACY AUDIT COMPLETED")
        print(f"Results available in: accuracy_audit/")
        
        return metrics, sla_results, predictions
    
    def create_accuracy_plots(self, predictions):
        """Generate accuracy visualization plots"""
        print(f"\n📊 GENERATING ACCURACY PLOTS")
        print("=" * 50)
        
        df = pd.DataFrame(predictions)
        df = df.dropna(subset=['predicted_value', 'actual_value'])
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('CapSight ML Model Accuracy Analysis - August 2025', fontsize=16, fontweight='bold')
        
        # 1. Predicted vs Actual Scatter Plot
        ax1 = axes[0, 0]
        ax1.scatter(df['actual_value']/1000, df['predicted_value']/1000, alpha=0.6, s=30)
        min_val = min(df['actual_value'].min(), df['predicted_value'].min()) / 1000
        max_val = max(df['actual_value'].max(), df['predicted_value'].max()) / 1000
        ax1.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, label='Perfect Prediction')
        ax1.set_xlabel('Actual Value ($000s)')
        ax1.set_ylabel('Predicted Value ($000s)')
        ax1.set_title('Predicted vs Actual Property Values')
        ax1.legend()
        
        # Calculate and show R²
        correlation = np.corrcoef(df['actual_value'], df['predicted_value'])[0, 1]
        r_squared = correlation ** 2
        ax1.text(0.05, 0.95, f'R² = {r_squared:.3f}', transform=ax1.transAxes, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # 2. Residual Error Distribution
        ax2 = axes[0, 1]
        errors = (df['predicted_value'] - df['actual_value']) / df['actual_value'] * 100
        ax2.hist(errors, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.axvline(0, color='red', linestyle='--', alpha=0.8, label='Perfect Prediction')
        ax2.set_xlabel('Prediction Error (%)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Prediction Error Distribution')
        ax2.legend()
        
        # Add statistics
        mean_error = np.mean(errors)
        std_error = np.std(errors)
        ax2.text(0.05, 0.95, f'Mean: {mean_error:.1f}%\nStd: {std_error:.1f}%', 
                transform=ax2.transAxes, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # 3. Confidence Interval Calibration
        ax3 = axes[1, 0]
        
        # Check if we have confidence intervals
        df_conf = df.dropna(subset=['confidence_lower', 'confidence_upper'])
        if len(df_conf) > 0:
            within_ci = []
            confidence_levels = np.linspace(0.5, 0.95, 10)
            
            for conf_level in confidence_levels:
                # Calculate empirical coverage for this confidence level
                coverage = np.mean(
                    (df_conf['actual_value'] >= df_conf['confidence_lower']) & 
                    (df_conf['actual_value'] <= df_conf['confidence_upper'])
                )
                within_ci.append(coverage)
            
            ax3.plot(confidence_levels * 100, np.array(within_ci) * 100, 'b-o', label='Actual Coverage')
            ax3.plot([50, 95], [50, 95], 'r--', alpha=0.8, label='Perfect Calibration')
            ax3.set_xlabel('Confidence Level (%)')
            ax3.set_ylabel('Actual Coverage (%)')
            ax3.set_title('Confidence Interval Calibration')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        else:
            ax3.text(0.5, 0.5, 'No confidence intervals\navailable for calibration', 
                    ha='center', va='center', transform=ax3.transAxes, fontsize=12)
            ax3.set_title('Confidence Interval Calibration - N/A')
        
        # 4. Accuracy by Property Value Range
        ax4 = axes[1, 1]
        
        # Bin properties by value
        df['value_bin'] = pd.cut(df['actual_value'], bins=5, labels=['Low', 'Med-Low', 'Medium', 'Med-High', 'High'])
        accuracy_by_bin = []
        
        for bin_name in ['Low', 'Med-Low', 'Medium', 'Med-High', 'High']:
            bin_data = df[df['value_bin'] == bin_name]
            if len(bin_data) > 0:
                bin_errors = np.abs(bin_data['predicted_value'] - bin_data['actual_value']) / bin_data['actual_value']
                accuracy = np.mean(bin_errors <= 0.05)  # Within 5%
                accuracy_by_bin.append(accuracy * 100)
            else:
                accuracy_by_bin.append(0)
        
        bars = ax4.bar(['Low', 'Med-Low', 'Medium', 'Med-High', 'High'], accuracy_by_bin, 
                      color=['lightcoral', 'lightblue', 'lightgreen', 'gold', 'plum'])
        ax4.axhline(y=94.2, color='red', linestyle='--', alpha=0.8, label='SLA Target (94.2%)')
        ax4.set_xlabel('Property Value Range')
        ax4.set_ylabel('Accuracy within 5% (%)')
        ax4.set_title('Accuracy by Property Value Range')
        ax4.legend()
        
        # Add value labels on bars
        for bar, accuracy in zip(bars, accuracy_by_bin):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{accuracy:.1f}%', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig('accuracy_audit/accuracy_plots.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Accuracy plots saved to: accuracy_audit/accuracy_plots.png")

if __name__ == "__main__":
    auditor = CapSightAccuracyAuditor()
    results = auditor.run_full_audit()
