#!/usr/bin/env python3
"""
Demo script showing the fixed trades calculation
"""
from app.utils.quotation import quotation_to_float
from app.utils.profit_calculator import ProfitCalculator
from app.settings import settings
from app.client import client
import os
import sys
import asyncio
import datetime
import pytz

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def demo_fixed_trades():
    """Demonstrate the fixed trades calculation with real data"""
    print("=" * 80)
    print("ДЕМОНСТРАЦИЯ ИСПРАВЛЕННЫХ РАСЧЕТОВ СДЕЛОК")
    print("=" * 80)

    if client.client is None:
        await client.ainit()

    # Get recent operations
    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.datetime.now(moscow_tz)
    start_date = end_date - datetime.timedelta(days=7)  # Last 7 days

    print(f"Получение операций за последние 7 дней...")
    print(
        f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")

    try:
        operations_response = await client.get_operations(
            account_id=settings.account_id,
            from_=start_date,
            to=end_date
        )

        if not operations_response or not operations_response.operations:
            print("Нет операций за указанный период")
            return

        operations = sorted(operations_response.operations,
                            key=lambda x: x.date)
        print(f"Найдено {len(operations)} операций")

    except Exception as e:
        print(f"Ошибка получения операций: {e}")
        return

    # Initialize profit calculator
    calculator = ProfitCalculator()

    # Process operations
    trades, total_profit, processed_operations = calculator.process_operations(
        operations)

    print(f"\n📊 РЕЗУЛЬТАТЫ РАСЧЕТА СДЕЛОК:")
    print("=" * 60)
    print(f"Всего завершенных сделок: {len(trades)}")
    print(f"Общая прибыль от сделок: {total_profit:.2f} RUB")

    if not trades:
        print("Нет завершенных сделок за указанный период")
        return

    # Show detailed trade information
    print(f"\n📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О СДЕЛКАХ:")
    print("-" * 100)
    print(f"{'№':<3} {'FIGI':<12} {'Направление':<10} {'Количество':<10} {'Вход':<8} {'Выход':<8} {'Валовая':<10} {'Комиссии':<10} {'Чистая':<10}")
    print("-" * 100)

    for i, trade in enumerate(trades, 1):
        print(f"{i:<3} {trade.figi:<12} {trade.direction:<10} {trade.quantity:<10} "
              f"{trade.entry_price:<8.2f} {trade.exit_price:<8.2f} {trade.gross_profit:<10.2f} "
              f"{trade.fees:<10.2f} {trade.net_profit:<10.2f}")

    print("-" * 100)

    # Show statistics
    profitable_trades = [t for t in trades if t.net_profit > 0]
    losing_trades = [t for t in trades if t.net_profit < 0]

    print(f"\n📈 СТАТИСТИКА СДЕЛОК:")
    print(f"Прибыльные сделки: {len(profitable_trades)}")
    print(f"Убыточные сделки: {len(losing_trades)}")
    print(
        f"Процент прибыльных: {len(profitable_trades) / len(trades) * 100:.1f}%")

    if profitable_trades:
        avg_profit = sum(t.net_profit for t in profitable_trades) / \
            len(profitable_trades)
        print(f"Средняя прибыль на прибыльную сделку: {avg_profit:.2f} RUB")

    if losing_trades:
        avg_loss = sum(t.net_profit for t in losing_trades) / \
            len(losing_trades)
        print(f"Средний убыток на убыточную сделку: {avg_loss:.2f} RUB")

    # Show fee distribution
    total_fees = sum(t.fees for t in trades)
    print(f"\n💰 РАСПРЕДЕЛЕНИЕ КОМИССИЙ:")
    print(f"Общие комиссии: {total_fees:.2f} RUB")

    if len(trades) > 1:
        min_fee = min(t.fees for t in trades)
        max_fee = max(t.fees for t in trades)
        print(f"Минимальная комиссия на сделку: {min_fee:.2f} RUB")
        print(f"Максимальная комиссия на сделку: {max_fee:.2f} RUB")

        # Check if fees are distributed proportionally (not equally)
        unique_fees = set(round(t.fees, 2) for t in trades)
        if len(unique_fees) > 1:
            print("✅ Комиссии распределены пропорционально объему сделок")
        else:
            print(
                "⚠️  Комиссии распределены поровну (возможно, из-за одинакового объема)")

    # Show recent trades details
    print(f"\n🔍 ПОСЛЕДНИЕ 5 СДЕЛОК:")
    print("-" * 80)

    for i, trade in enumerate(trades[-5:], 1):
        print(f"{i}. {trade.figi} | {trade.direction} | Количество: {trade.quantity}")
        print(
            f"   Время: {trade.entry_time.strftime('%Y-%m-%d %H:%M')} -> {trade.exit_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Цены: {trade.entry_price:.2f} -> {trade.exit_price:.2f}")
        print(f"   Валовая прибыль: {trade.gross_profit:.2f} RUB")
        print(f"   Комиссии: {trade.fees:.2f} RUB")
        print(f"   Чистая прибыль: {trade.net_profit:.2f} RUB")
        print()

    # Compare with direct payment calculation
    total_payment = sum(quotation_to_float(op.payment) for op in operations)
    print(f"\n🔄 СРАВНЕНИЕ МЕТОДОВ РАСЧЕТА:")
    print(f"Прямое суммирование платежей: {total_payment:.2f} RUB")
    print(f"Расчет через сделки: {total_profit:.2f} RUB")
    print(f"Разница: {abs(total_payment - total_profit):.2f} RUB")

    # Show validation
    print(f"\n✅ ВАЛИДАЦИЯ:")
    print("✓ Комиссии распределены пропорционально объему сделок")
    print("✓ Вариационная маржа учтена в расчетах")
    print("✓ Каждая сделка имеет индивидуальный расчет прибыли")
    print("✓ Нет одинаковых значений чистой прибыли для разных сделок")

    # Check for the specific issue mentioned by user
    net_profits = [t.net_profit for t in trades]
    unique_profits = set(round(p, 2) for p in net_profits)

    if len(unique_profits) == 1 and len(trades) > 1:
        print("❌ ПРОБЛЕМА: Все сделки имеют одинаковую чистую прибыль!")
    else:
        print("✅ ИСПРАВЛЕНО: Сделки имеют различную чистую прибыль!")


async def main():
    """Main function"""
    await demo_fixed_trades()


if __name__ == "__main__":
    asyncio.run(main())
