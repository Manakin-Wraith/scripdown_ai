"""
Test script to verify revenue calculation in analytics endpoint
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.analytics_service import AnalyticsService

def test_revenue_calculation():
    """Test the revenue calculation directly"""
    print("Testing Revenue Calculation...")
    print("=" * 60)
    
    analytics = AnalyticsService()
    
    # Get subscription metrics (includes revenue)
    metrics = analytics.get_subscription_metrics()
    
    print("\n📊 Subscription Metrics:")
    print(f"  Total Revenue: R{metrics.get('total_revenue', 0)}")
    print(f"  Successful Payments: {metrics.get('successful_payments', 0)}")
    print(f"  Trial Users: {metrics.get('trial_users', 0)}")
    print(f"  Active Subscribers: {metrics.get('active_subscribers', 0)}")
    
    print("\n" + "=" * 60)
    
    # Expected values from database
    expected_revenue = 98.00
    expected_payments = 2
    
    actual_revenue = metrics.get('total_revenue', 0)
    actual_payments = metrics.get('successful_payments', 0)
    
    print("\n✅ Verification:")
    print(f"  Expected Revenue: R{expected_revenue}")
    print(f"  Actual Revenue: R{actual_revenue}")
    print(f"  Match: {'✓ YES' if actual_revenue == expected_revenue else '✗ NO'}")
    
    print(f"\n  Expected Payments: {expected_payments}")
    print(f"  Actual Payments: {actual_payments}")
    print(f"  Match: {'✓ YES' if actual_payments == expected_payments else '✗ NO'}")
    
    if actual_revenue == expected_revenue and actual_payments == expected_payments:
        print("\n🎉 SUCCESS: Revenue calculation is correct!")
        return True
    else:
        print("\n❌ FAILURE: Revenue calculation mismatch!")
        return False

if __name__ == '__main__':
    success = test_revenue_calculation()
    sys.exit(0 if success else 1)
