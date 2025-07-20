#!/usr/bin/env python3
"""
Test script to check current balance calculation
"""

from app.utils.quotation import quotation_to_float
from app.settings import settings
from app.client import client
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))


async def test_current_balance():
    """Test current balance calculation"""

    print("🔍 TESTING CURRENT BALANCE CALCULATION")
    print("=" * 50)

    try:
        # Initialize client
        if client.client is None:
            await client.ainit()

        # Get current portfolio
        portfolio = await client.get_portfolio(account_id=settings.account_id)

        # Calculate current balance
        current_balance = quotation_to_float(portfolio.total_amount_shares) + \
            quotation_to_float(portfolio.total_amount_currencies)

        print(f"📊 CURRENT PORTFOLIO BALANCE:")
        print(
            f"   Total amount shares: {quotation_to_float(portfolio.total_amount_shares):,.2f} ₽")
        print(
            f"   Total amount currencies: {quotation_to_float(portfolio.total_amount_currencies):,.2f} ₽")
        print(
            f"   Total amount futures: {quotation_to_float(portfolio.total_amount_futures):,.2f} ₽")
        print(f"   🔥 TOTAL BALANCE: {current_balance:,.2f} ₽")

        # Check if this matches the expected value
        expected_balance = 24935
        if abs(current_balance - expected_balance) < 1:
            print(
                f"✅ SUCCESS: Current balance ({current_balance:,.2f} ₽) matches expected ({expected_balance:,.2f} ₽)")
        else:
            print(
                f"⚠️  WARNING: Current balance ({current_balance:,.2f} ₽) differs from expected ({expected_balance:,.2f} ₽)")

        # Test API endpoint
        print(f"\n🌐 TESTING API ENDPOINT:")
        import requests
        try:
            response = requests.get(
                "http://127.0.0.1:8000/api/performance-data?period=week&weeks_back=1", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    latest_period = data['data'][0]  # Most recent period
                    api_balance = latest_period.get('balance_end', 0)
                    print(f"   API latest balance: {api_balance:,.2f} ₽")

                    if abs(api_balance - current_balance) < 1:
                        print(f"✅ SUCCESS: API balance matches current balance")
                    else:
                        print(
                            f"⚠️  WARNING: API balance ({api_balance:,.2f} ₽) differs from current balance ({current_balance:,.2f} ₽)")
                else:
                    print("❌ API returned no data")
            else:
                print(f"❌ API returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing API: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_current_balance())
