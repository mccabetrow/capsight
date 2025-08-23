"""
CapSight Alert Testing Script
Generates synthetic events to test monitoring and alerting systems
"""
import requests
import time
import json
from datetime import datetime
import random
import sys

class AlertTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_sentry_integration(self):
        """Test Sentry error capture"""
        print("🚨 Testing Sentry Integration...")
        
        try:
            # Generate intentional error
            response = self.session.get(f"{self.base_url}/api/v1/test/error")
            if response.status_code == 500:
                print("✓ Error endpoint triggered (should appear in Sentry)")
            else:
                print("⚠ Error endpoint didn't return expected 500")
                
        except Exception as e:
            print(f"✗ Sentry test failed: {e}")
    
    def test_accuracy_alert(self):
        """Test accuracy drop alert"""
        print("📉 Testing Accuracy Drop Alert...")
        
        try:
            # Simulate accuracy drop
            payload = {
                "model_id": "property_valuator_v2",
                "accuracy": 0.85,  # Below 90% threshold
                "timestamp": datetime.now().isoformat()
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/test/accuracy_alert",
                json=payload
            )
            
            if response.status_code == 200:
                print("✓ Accuracy alert triggered")
            else:
                print("⚠ Accuracy alert test inconclusive")
                
        except Exception as e:
            print(f"✗ Accuracy alert test failed: {e}")
    
    def test_freshness_alert(self):
        """Test data freshness alert"""
        print("⏰ Testing Data Freshness Alert...")
        
        try:
            # Simulate stale data
            payload = {
                "data_source": "mls_listings",
                "last_update": "2024-12-19T08:00:00Z",  # 2+ hours old
                "freshness_threshold": 3600  # 1 hour
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/test/freshness_alert",
                json=payload
            )
            
            if response.status_code == 200:
                print("✓ Freshness alert triggered")
            else:
                print("⚠ Freshness alert test inconclusive")
                
        except Exception as e:
            print(f"✗ Freshness alert test failed: {e}")
    
    def test_high_latency_alert(self):
        """Test high latency alert"""
        print("🐌 Testing High Latency Alert...")
        
        try:
            # Simulate slow request
            response = self.session.get(f"{self.base_url}/api/v1/test/slow")
            
            if response.status_code == 200:
                print("✓ Slow endpoint accessed (should trigger latency alert)")
            else:
                print("⚠ Slow endpoint test inconclusive")
                
        except Exception as e:
            print(f"✗ Latency alert test failed: {e}")
    
    def generate_load_spike(self):
        """Generate load spike to test scaling alerts"""
        print("📈 Generating Load Spike...")
        
        # Generate 50 requests quickly
        for i in range(50):
            try:
                self.session.get(f"{self.base_url}/health", timeout=1)
                if i % 10 == 0:
                    print(f"  Sent {i}/50 requests...")
            except:
                pass  # Ignore timeouts during load test
        
        print("✓ Load spike generated (check Grafana for metrics)")
    
    def test_grafana_dashboards(self):
        """Verify Grafana dashboards are accessible"""
        print("📊 Testing Grafana Dashboard Access...")
        
        grafana_url = "http://localhost:3000"
        
        try:
            response = self.session.get(grafana_url, timeout=10)
            if response.status_code == 200:
                print("✓ Grafana dashboard accessible")
            else:
                print(f"⚠ Grafana returned status: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Grafana dashboard test failed: {e}")
    
    def test_prometheus_metrics(self):
        """Verify Prometheus is collecting metrics"""
        print("🎯 Testing Prometheus Metrics...")
        
        prometheus_url = "http://localhost:9090"
        
        try:
            response = self.session.get(prometheus_url, timeout=10)
            if response.status_code == 200:
                print("✓ Prometheus accessible")
                
                # Check if API metrics are being collected
                metrics_response = self.session.get(f"{self.base_url}/metrics")
                if metrics_response.status_code == 200:
                    print("✓ API metrics endpoint accessible")
                else:
                    print("⚠ API metrics endpoint not accessible")
            else:
                print(f"⚠ Prometheus returned status: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Prometheus test failed: {e}")
    
    def run_full_alert_test(self):
        """Run comprehensive alert testing"""
        print("🔔 CAPSIGHT ALERT SYSTEM TEST")
        print("=" * 50)
        print(f"Testing against: {self.base_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test monitoring infrastructure
        self.test_grafana_dashboards()
        self.test_prometheus_metrics()
        
        print()
        
        # Test alert mechanisms
        self.test_sentry_integration()
        self.test_accuracy_alert()
        self.test_freshness_alert() 
        self.test_high_latency_alert()
        
        print()
        
        # Generate synthetic load
        self.generate_load_spike()
        
        print()
        print("🎉 Alert testing complete!")
        print()
        print("📋 Next Steps:")
        print("1. Check Grafana dashboards: http://localhost:3000")
        print("2. Verify Prometheus targets: http://localhost:9090/targets")
        print("3. Check Sentry for captured errors (if configured)")
        print("4. Review PagerDuty alerts (if configured)")
        print("5. Monitor for 5-10 minutes to see alert recovery")

if __name__ == "__main__":
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    tester = AlertTester(base_url)
    tester.run_full_alert_test()
