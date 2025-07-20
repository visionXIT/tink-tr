#!/usr/bin/env python3
"""
Test script to verify the new API endpoint works correctly
"""

import requests


def test_api_endpoint():
    """Test the new API endpoint"""

    # Test the exact table profit endpoint
    url = "http://localhost:8000/api/exact-table-profit"
    params = {
        "days": 30,
        "starting_balance": 44127.39
    }

    try:
        print("Testing API endpoint...")
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            print("✅ API endpoint working!")
            print(f"Method: {data.get('method', 'unknown')}")
            print(f"Period: {data.get('period', {})}")

            summary = data.get('summary', {})
            print(f"Total profit: {summary.get('total_profit', 0):.2f}")
            print(
                f"Total commission: {summary.get('total_commission', 0):.2f}")
            print(f"Total trades: {summary.get('total_trades', 0)}")
            print(
                f"Total day clearing: {summary.get('total_day_clearing', 0):.2f}")
            print(
                f"Total evening clearing: {summary.get('total_evening_clearing', 0):.2f}")

            # Check if we have daily data
            daily_data = data.get('daily_data', {})
            if daily_data:
                print(f"\nDaily data available for {len(daily_data)} days")
                # Show first few days
                for i, (date, day_data) in enumerate(sorted(daily_data.items())):
                    if i >= 3:  # Only show first 3 days
                        break
                    print(
                        f"  {date}: net={day_data.get('total_profit', 0):.2f}, commission={day_data.get('commission', 0):.2f}")

            # Check balance progression
            balance_progression = data.get('balance_progression', {})
            if balance_progression:
                print(
                    f"\nBalance progression available for {len(balance_progression)} days")
                # Show first and last balance
                sorted_balances = sorted(balance_progression.items())
                if sorted_balances:
                    first_date, first_balance = sorted_balances[0]
                    last_date, last_balance = sorted_balances[-1]
                    print(f"  {first_date}: {first_balance:.2f}")
                    print(f"  {last_date}: {last_balance:.2f}")

        else:
            print(f"❌ API endpoint failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Could not connect to API. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")


def test_default_profit_analysis():
    """Test the default profit analysis endpoint"""

    url = "http://localhost:8000/api/profit-analysis"
    params = {
        "days": 30
    }

    try:
        print("\nTesting default profit analysis endpoint...")
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            print("✅ Default profit analysis endpoint working!")
            print(f"Method: {data.get('method', 'unknown')}")

            summary = data.get('summary', {})
            print(f"Total profit: {summary.get('total_profit', 0):.2f}")
            print(
                f"Total commission: {summary.get('total_commission', 0):.2f}")
            print(f"Total trades: {summary.get('total_trades', 0)}")

        else:
            print(
                f"❌ Default profit analysis endpoint failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Could not connect to API. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error testing default profit analysis: {e}")


if __name__ == "__main__":
    print("Testing API endpoints...")
    test_api_endpoint()
    test_default_profit_analysis()
    print("\nTesting completed!")
