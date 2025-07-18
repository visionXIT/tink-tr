#!/usr/bin/env python3
"""
Script to retrieve real operations from Tinkoff Invest for the last 100 days
and check the first trade to demonstrate the starting position issue and fix
"""
from app.settings import settings
from app.client import client
from app.utils.quotation import quotation_to_float
from tinkoff.invest.grpc.operations_pb2 import OperationType
import asyncio
import datetime
import pytz


async def check_first_trade_real_data():
    """Check the first trade with real data from last 100 days"""
    print("=" * 80)
    print("CHECKING FIRST TRADE WITH REAL DATA (LAST 100 DAYS)")
    print("=" * 80)

    if client.client is None:
        await client.ainit()

    # Get operations for last 100 days
    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.datetime.now(moscow_tz)
    start_date = end_date - datetime.timedelta(days=100)

    print(
        f"Retrieving operations from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Account: {settings.account_id}")

    try:
        operations_response = await client.get_operations(
            account_id=settings.account_id,
            from_=start_date,
            to=end_date
        )

        if not operations_response or not operations_response.operations:
            print("❌ No operations found for the specified period")
            return

        operations = sorted(operations_response.operations,
                            key=lambda x: x.date)
        print(f"✅ Found {len(operations)} operations")

        # Filter trading operations
        trading_operations = [op for op in operations if op.operation_type in [
            OperationType.OPERATION_TYPE_BUY,
            OperationType.OPERATION_TYPE_SELL
        ]]

        print(f"📊 Trading operations: {len(trading_operations)}")

        if not trading_operations:
            print("❌ No trading operations found")
            return

        # Show first few trading operations
        print(f"\n📋 FIRST 5 TRADING OPERATIONS:")
        print("-" * 90)
        print(
            f"{'Date':<20} {'Type':<6} {'FIGI':<15} {'Qty':<8} {'Price':<12} {'Payment':<15}")
        print("-" * 90)

        for i, op in enumerate(trading_operations[:5]):
            op_type = "BUY" if op.operation_type == OperationType.OPERATION_TYPE_BUY else "SELL"
            price = quotation_to_float(op.price)
            payment = quotation_to_float(op.payment)
            date_str = op.date.strftime('%Y-%m-%d %H:%M:%S')

            print(
                f"{date_str:<20} {op_type:<6} {op.figi:<15} {op.quantity:<8} {price:<12.2f} {payment:<15.2f}")

        print("-" * 90)

        # Method 1: Traditional approach
        print(f"\n🔍 METHOD 1: TRADITIONAL APPROACH (POTENTIAL ISSUE)")
        print("-" * 60)

        try:
            traditional_trades, traditional_profit, _, traditional_positions = await client.get_profit_analysis_with_auto_detected_positions(
                settings.account_id, start_date, end_date
            )

            print(f"Total trades: {len(traditional_trades)}")
            print(f"Total profit: {traditional_profit:.2f} RUB")
            print(f"Starting positions detected: {len(traditional_positions)}")

            if traditional_trades:
                first_trade = traditional_trades[0]
                print(f"\n📈 FIRST TRADE ANALYSIS:")
                print(
                    f"   Entry time: {first_trade.entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(
                    f"   Exit time: {first_trade.exit_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Direction: {first_trade.direction}")
                print(f"   FIGI: {first_trade.figi}")
                print(f"   Quantity: {first_trade.quantity}")
                print(f"   Entry price: {first_trade.entry_price:.2f}")
                print(f"   Exit price: {first_trade.exit_price:.2f}")
                print(f"   Gross profit: {first_trade.gross_profit:.2f} RUB")
                print(f"   Fees: {first_trade.fees:.2f} RUB")
                print(f"   Net profit: {first_trade.net_profit:.2f} RUB")

                # Check for the issue
                if first_trade.net_profit < -10000:
                    print(f"   🚨 ISSUE DETECTED: Large loss in first trade!")
                    print(f"   This is likely the starting position issue.")
                elif first_trade.net_profit < -1000:
                    print(f"   ⚠️  Warning: Significant loss in first trade")
                else:
                    print(f"   ✅ First trade looks reasonable")

        except Exception as e:
            print(f"❌ Error with traditional method: {e}")

        # Method 2: Enhanced approach
        print(f"\n✅ METHOD 2: ENHANCED APPROACH (WITH FIX)")
        print("-" * 60)

        try:
            enhanced_result = await client.get_enhanced_profit_analysis(
                settings.account_id, start_date, end_date, use_current_positions=True
            )

            if 'error' in enhanced_result:
                print(f"❌ Error: {enhanced_result['error']}")
            else:
                print(f"Total trades: {len(enhanced_result['trades'])}")
                print(
                    f"Total profit: {enhanced_result['total_profit']:.2f} RUB")
                print(
                    f"Starting positions calculated: {len(enhanced_result['starting_positions'])}")
                print(
                    f"Current positions: {len(enhanced_result['current_positions'])}")

                if enhanced_result['trades']:
                    first_trade = enhanced_result['trades'][0]
                    print(f"\n📈 FIRST TRADE ANALYSIS (ENHANCED):")
                    print(
                        f"   Entry time: {first_trade.entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(
                        f"   Exit time: {first_trade.exit_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Direction: {first_trade.direction}")
                    print(f"   FIGI: {first_trade.figi}")
                    print(f"   Quantity: {first_trade.quantity}")
                    print(f"   Entry price: {first_trade.entry_price:.2f}")
                    print(f"   Exit price: {first_trade.exit_price:.2f}")
                    print(
                        f"   Gross profit: {first_trade.gross_profit:.2f} RUB")
                    print(f"   Fees: {first_trade.fees:.2f} RUB")
                    print(f"   Net profit: {first_trade.net_profit:.2f} RUB")

                    # Check the result
                    if first_trade.net_profit < -10000:
                        print(
                            f"   🚨 Still showing large loss - may need manual review")
                    elif first_trade.net_profit < -1000:
                        print(f"   ⚠️  Moderate loss detected")
                    else:
                        print(f"   ✅ First trade looks much better!")

                # Show starting positions
                print(f"\n📊 STARTING POSITIONS CALCULATED:")
                for figi, position in enhanced_result['starting_positions'].items():
                    print(f"   {figi}: {position}")

                # Show current positions
                print(f"\n📊 CURRENT POSITIONS:")
                for figi, position in enhanced_result['current_positions'].items():
                    print(f"   {figi}: {position}")

                # Show data quality issues
                analysis_report = enhanced_result['analysis_report']
                if analysis_report['data_quality']['issues_found'] > 0:
                    print(f"\n⚠️  DATA QUALITY ISSUES:")
                    for issue in analysis_report['data_quality']['issues']:
                        print(f"   - {issue}")

                # Show recommendations
                if analysis_report['recommendations']:
                    print(f"\n💡 RECOMMENDATIONS:")
                    for rec in analysis_report['recommendations']:
                        print(f"   - {rec}")

        except Exception as e:
            print(f"❌ Error with enhanced method: {e}")
            import traceback
            traceback.print_exc()

        # Comparison
        print(f"\n📊 COMPARISON:")
        print("-" * 60)

        try:
            if 'traditional_profit' in locals() and 'enhanced_result' in locals() and 'error' not in enhanced_result:
                traditional_first_profit = traditional_trades[0].net_profit if traditional_trades else 0
                enhanced_first_profit = enhanced_result['trades'][
                    0].net_profit if enhanced_result['trades'] else 0

                print(f"Traditional method:")
                print(f"   - Total profit: {traditional_profit:.2f} RUB")
                print(
                    f"   - First trade profit: {traditional_first_profit:.2f} RUB")
                print(f"   - Total trades: {len(traditional_trades)}")

                print(f"\nEnhanced method:")
                print(
                    f"   - Total profit: {enhanced_result['total_profit']:.2f} RUB")
                print(
                    f"   - First trade profit: {enhanced_first_profit:.2f} RUB")
                print(f"   - Total trades: {len(enhanced_result['trades'])}")

                profit_diff = enhanced_result['total_profit'] - \
                    traditional_profit
                first_trade_diff = enhanced_first_profit - traditional_first_profit

                print(f"\nDifferences:")
                print(f"   - Total profit difference: {profit_diff:.2f} RUB")
                print(
                    f"   - First trade difference: {first_trade_diff:.2f} RUB")

                if abs(profit_diff) > 10000:
                    print(f"   🚨 MAJOR DIFFERENCE in total profit!")

                if abs(first_trade_diff) > 1000:
                    print(f"   🚨 SIGNIFICANT DIFFERENCE in first trade!")
                    print(f"   This confirms the starting position issue was present.")
                else:
                    print(f"   ✅ First trade difference is reasonable")

        except Exception as e:
            print(f"❌ Error in comparison: {e}")

        print(f"\n✅ ANALYSIS COMPLETE!")
        print(f"If you see significant differences, it confirms the starting position issue was present.")
        print(f"The enhanced method should provide more accurate results.")

    except Exception as e:
        print(f"❌ Error retrieving operations: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_first_trade_real_data())
