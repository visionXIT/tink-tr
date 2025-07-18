#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced profit calculation solution
Demonstrates how to fix the starting position issue and get accurate profit calculations
"""
from tinkoff.invest.grpc.operations_pb2 import OperationType
from app.utils.quotation import quotation_to_float
from app.utils.profit_calculator import ProfitCalculator
from app.settings import settings
from app.client import client
import os
import sys
import asyncio
import datetime
import pytz
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_enhanced_profit_solution():
    """Test the enhanced profit calculation solution"""
    print("=" * 80)
    print("ENHANCED PROFIT CALCULATION SOLUTION TEST")
    print("=" * 80)

    if client.client is None:
        await client.ainit()

    # Test with last 100 days (where issue typically occurs)
    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.datetime.now(moscow_tz)
    start_date = end_date - datetime.timedelta(days=100)

    print(f"Testing with operations from {start_date} to {end_date}")
    print(f"Account ID: {settings.account_id}")

    # Test 1: Enhanced profit analysis with current positions
    print("\n🔬 TEST 1: ENHANCED PROFIT ANALYSIS WITH CURRENT POSITIONS")
    print("-" * 60)

    try:
        enhanced_result = await client.get_enhanced_profit_analysis(
            settings.account_id, start_date, end_date, use_current_positions=True
        )

        if 'error' in enhanced_result:
            print(f"❌ Error: {enhanced_result['error']}")
        else:
            print(f"✅ Analysis completed successfully")
            print(f"   Method used: {enhanced_result['method_used']}")
            print(f"   Total trades: {len(enhanced_result['trades'])}")
            print(
                f"   Total profit: {enhanced_result['total_profit']:.2f} RUB")
            print(
                f"   Starting positions: {len(enhanced_result['starting_positions'])} instruments")
            print(
                f"   Current positions: {len(enhanced_result['current_positions'])} instruments")

            # Show analysis report summary
            report = enhanced_result['analysis_report']
            print(f"\n   📊 Analysis Report Summary:")
            print(
                f"   - Total operations: {report['summary']['total_operations']}")
            print(
                f"   - Instruments traded: {report['summary']['instruments_traded']}")
            print(
                f"   - Data quality issues: {report['data_quality']['issues_found']}")
            print(
                f"   - Data completeness: {report['data_quality']['data_completeness']}")

            # Show problematic trades
            problematic = enhanced_result['problematic_trades']
            if problematic:
                print(f"\n   ⚠️  Problematic trades found: {len(problematic)}")
                for i, issue in enumerate(problematic[:3], 1):  # Show first 3
                    trade = issue['trade']
                    print(
                        f"   {i}. {trade.direction} {trade.quantity} @ {trade.entry_price:.2f} -> {trade.exit_price:.2f}")
                    print(
                        f"      Net profit: {trade.net_profit:.2f} RUB (Severity: {issue['severity']})")
                    print(f"      Issues: {', '.join(issue['issues'])}")
            else:
                print("   ✅ No problematic trades found")

            # Show validation results
            validation = enhanced_result['validation_result']
            if validation['valid']:
                print("   ✅ Position validation: PASSED")
            else:
                print(
                    f"   ❌ Position validation: FAILED ({len(validation['issues'])} issues)")
                for issue in validation['issues'][:3]:  # Show first 3
                    print(f"      - {issue}")

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")

    # Test 2: Diagnostic analysis
    print("\n🔍 TEST 2: DIAGNOSTIC ANALYSIS")
    print("-" * 60)

    try:
        diagnosis = await client.diagnose_profit_calculation_issues(
            settings.account_id, start_date, end_date
        )

        if 'error' in diagnosis:
            print(f"❌ Error: {diagnosis['error']}")
        else:
            print(f"✅ Diagnosis completed successfully")
            print(f"   Severity: {diagnosis['severity'].upper()}")

            comparison = diagnosis['comparison']
            print(f"\n   📈 Profit Comparison:")
            print(
                f"   - Enhanced method: {comparison['enhanced_profit']:.2f} RUB")
            print(
                f"   - Traditional method: {comparison['traditional_profit']:.2f} RUB")
            print(
                f"   - Difference: {comparison['profit_difference']:.2f} RUB")

            if abs(comparison['profit_difference']) > 1000:
                print(f"   ⚠️  Significant difference detected!")
            else:
                print(f"   ✅ Methods are consistent")

            print(
                f"\n   📋 Issues Detected: {len(diagnosis['issues_detected'])}")
            for issue in diagnosis['issues_detected']:
                print(f"   - {issue}")

            print(f"\n   💡 Recommendations:")
            for rec in diagnosis['recommendations']:
                print(f"   - {rec}")

            if diagnosis['specific_recommendations']:
                print(f"\n   🎯 Specific Recommendations:")
                for rec in diagnosis['specific_recommendations']:
                    print(f"   - {rec}")

    except Exception as e:
        print(f"❌ Test 2 failed: {e}")

    # Test 3: Comparison with traditional method
    print("\n⚖️  TEST 3: COMPARISON WITH TRADITIONAL METHOD")
    print("-" * 60)

    try:
        # Traditional method
        traditional_result = await client.get_profit_analysis_with_auto_detected_positions(
            settings.account_id, start_date, end_date
        )

        # Enhanced method
        enhanced_result = await client.get_enhanced_profit_analysis(
            settings.account_id, start_date, end_date, use_current_positions=True
        )

        if 'error' not in enhanced_result:
            print(f"Traditional method:")
            print(f"   - Trades: {len(traditional_result[0])}")
            print(f"   - Total profit: {traditional_result[1]:.2f} RUB")
            print(f"   - Starting positions: {len(traditional_result[3])}")

            print(f"\nEnhanced method:")
            print(f"   - Trades: {len(enhanced_result['trades'])}")
            print(
                f"   - Total profit: {enhanced_result['total_profit']:.2f} RUB")
            print(
                f"   - Starting positions: {len(enhanced_result['starting_positions'])}")

            profit_diff = enhanced_result['total_profit'] - \
                traditional_result[1]
            print(f"\nDifference: {profit_diff:.2f} RUB")

            if abs(profit_diff) > 10000:
                print("🚨 MAJOR DIFFERENCE DETECTED!")
                print(
                    "   This likely indicates the starting position issue was present.")
                print("   The enhanced method should provide more accurate results.")
            elif abs(profit_diff) > 1000:
                print("⚠️  Moderate difference detected")
            else:
                print("✅ Methods are consistent")
        else:
            print("❌ Cannot compare - enhanced method failed")

    except Exception as e:
        print(f"❌ Test 3 failed: {e}")

    # Test 4: Show detailed position history for problematic instruments
    print("\n📈 TEST 4: DETAILED POSITION HISTORY")
    print("-" * 60)

    try:
        enhanced_result = await client.get_enhanced_profit_analysis(
            settings.account_id, start_date, end_date, use_current_positions=True
        )

        if 'error' not in enhanced_result and enhanced_result['position_history']:
            print("Position history for instruments with significant activity:")

            # Show history for first 2 instruments
            for figi, history in list(enhanced_result['position_history'].items())[:2]:
                print(f"\n   📊 {figi}:")
                print(f"      Total position changes: {len(history)}")

                # Show first few position changes
                for i, change in enumerate(history[:5], 1):
                    date_str = change['date'].strftime(
                        '%Y-%m-%d %H:%M') if change['date'] else 'N/A'
                    op_type = change['operation_type']
                    position = change['position']

                    if op_type == 'INITIAL':
                        print(f"      {i}. {date_str} - INITIAL: {position}")
                    else:
                        change_qty = change.get('quantity', 0)
                        crosses_zero = change.get('crosses_zero', False)
                        cross_indicator = " 🔄" if crosses_zero else ""
                        print(
                            f"      {i}. {date_str} - {op_type} {change_qty}: {position}{cross_indicator}")

                if len(history) > 5:
                    print(f"      ... and {len(history) - 5} more changes")
        else:
            print("No position history available")

    except Exception as e:
        print(f"❌ Test 4 failed: {e}")

    # Summary and recommendations
    print("\n📋 SUMMARY AND RECOMMENDATIONS")
    print("=" * 60)
    print("✅ The enhanced profit calculation system provides:")
    print("   1. Accurate starting position calculation using current positions")
    print("   2. Comprehensive issue detection and analysis")
    print("   3. Detailed position history tracking")
    print("   4. Validation of position consistency")
    print("   5. Comparison with traditional methods")
    print()
    print("💡 To fix the -100,000 profit issue:")
    print("   1. Use client.get_enhanced_profit_analysis() instead of traditional methods")
    print("   2. Set use_current_positions=True for maximum accuracy")
    print("   3. Review the analysis report for data quality issues")
    print("   4. Check problematic trades for manual verification")
    print("   5. Use the diagnostic tool to identify specific issues")
    print()
    print("🔧 For integration in your application:")
    print("   - Replace existing profit calculation calls with enhanced version")
    print("   - Add error handling for API failures")
    print("   - Consider caching starting positions for performance")
    print("   - Monitor data quality metrics over time")


async def main():
    """Main function"""
    await test_enhanced_profit_solution()


if __name__ == "__main__":
    asyncio.run(main())
