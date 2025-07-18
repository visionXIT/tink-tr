#!/usr/bin/env python3
"""
Simple example showing how to fix the profit calculation issue using the enhanced method
This replaces the traditional approach that can show -100,000 profit for the first trade
"""
from app.settings import settings
from app.client import client
import asyncio
import datetime
import pytz


async def fix_profit_calculation_example():
    """Example showing how to fix the profit calculation issue"""
    print("=" * 70)
    print("PROFIT CALCULATION FIX EXAMPLE")
    print("=" * 70)

    if client.client is None:
        await client.ainit()

    # Get operations for last 100 days (where the issue typically occurs)
    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.datetime.now(moscow_tz)
    start_date = end_date - datetime.timedelta(days=100)

    print(
        f"Analyzing operations from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Account: {settings.account_id}")

    # ❌ OLD WAY (can show -100,000 profit issue)
    print("\n❌ OLD WAY (Traditional method - can have issues):")
    print("-" * 50)

    try:
        # This is the old method that can show incorrect -100,000 profit
        old_trades, old_profit, old_operations, old_positions = await client.get_profit_analysis_with_auto_detected_positions(
            settings.account_id, start_date, end_date
        )

        print(f"   Total trades: {len(old_trades)}")
        print(f"   Total profit: {old_profit:.2f} RUB")

        if old_trades:
            first_trade = old_trades[0]
            print(f"   First trade profit: {first_trade.net_profit:.2f} RUB")

            # Check if we have the -100,000 issue
            if first_trade.net_profit < -50000:
                print("   🚨 ISSUE DETECTED: First trade shows unusually large loss!")
                print("   This is likely the starting position issue.")

    except Exception as e:
        print(f"   Error: {e}")

    # ✅ NEW WAY (Enhanced method - fixes the issue)
    print("\n✅ NEW WAY (Enhanced method - fixes the issue):")
    print("-" * 50)

    try:
        # This is the enhanced method that fixes the starting position issue
        enhanced_result = await client.get_enhanced_profit_analysis(
            settings.account_id, start_date, end_date, use_current_positions=True
        )

        if 'error' in enhanced_result:
            print(f"   Error: {enhanced_result['error']}")
        else:
            print(f"   Total trades: {len(enhanced_result['trades'])}")
            print(
                f"   Total profit: {enhanced_result['total_profit']:.2f} RUB")
            print(f"   Method used: {enhanced_result['method_used']}")
            print(
                f"   Starting positions calculated: {len(enhanced_result['starting_positions'])}")

            if enhanced_result['trades']:
                first_trade = enhanced_result['trades'][0]
                print(
                    f"   First trade profit: {first_trade.net_profit:.2f} RUB")

                # Check if the issue is fixed
                if first_trade.net_profit > -50000:
                    print("   ✅ Issue appears to be fixed!")
                else:
                    print("   ⚠️  Large loss still present - may need manual review")

            # Show data quality assessment
            analysis_report = enhanced_result['analysis_report']
            data_quality = analysis_report['data_quality']

            if data_quality['issues_found'] > 0:
                print(
                    f"\n   📋 Data Quality Issues Found: {data_quality['issues_found']}")
                for issue in data_quality['issues']:
                    print(f"   - {issue}")
            else:
                print("   ✅ No data quality issues detected")

            # Show recommendations
            if analysis_report['recommendations']:
                print(f"\n   💡 Recommendations:")
                for rec in analysis_report['recommendations']:
                    print(f"   - {rec}")

    except Exception as e:
        print(f"   Error: {e}")

    # Show comparison
    print("\n📊 COMPARISON:")
    print("-" * 50)

    try:
        if 'old_profit' in locals() and 'enhanced_result' in locals() and 'error' not in enhanced_result:
            profit_difference = enhanced_result['total_profit'] - old_profit
            print(f"   Old method profit: {old_profit:.2f} RUB")
            print(
                f"   Enhanced method profit: {enhanced_result['total_profit']:.2f} RUB")
            print(f"   Difference: {profit_difference:.2f} RUB")

            if abs(profit_difference) > 10000:
                print("   🚨 SIGNIFICANT DIFFERENCE!")
                print("   The enhanced method should be more accurate.")
            elif abs(profit_difference) > 1000:
                print("   ⚠️  Moderate difference detected")
            else:
                print("   ✅ Methods are consistent")
        else:
            print("   Cannot compare - one of the methods failed")

    except Exception as e:
        print(f"   Error in comparison: {e}")

    # Usage recommendations
    print("\n🔧 HOW TO USE IN YOUR CODE:")
    print("-" * 50)
    print("   Replace this:")
    print("   ```python")
    print("   trades, profit, ops, positions = await client.get_profit_analysis_with_auto_detected_positions(")
    print("       account_id, start_date, end_date)")
    print("   ```")
    print()
    print("   With this:")
    print("   ```python")
    print("   result = await client.get_enhanced_profit_analysis(")
    print("       account_id, start_date, end_date, use_current_positions=True)")
    print("   ")
    print("   trades = result['trades']")
    print("   profit = result['total_profit']")
    print("   operations = result['operations']")
    print("   starting_positions = result['starting_positions']")
    print("   ```")
    print()
    print("   💡 Benefits:")
    print("   - Fixes the -100,000 profit issue")
    print("   - Provides data quality analysis")
    print("   - Includes position validation")
    print("   - Offers detailed recommendations")
    print("   - Works with current positions for accuracy")


async def main():
    """Main function"""
    await fix_profit_calculation_example()


if __name__ == "__main__":
    asyncio.run(main())
