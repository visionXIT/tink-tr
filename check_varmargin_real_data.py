#!/usr/bin/env python3
"""
Check if variation margin is properly accounted for in real data
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

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def check_varmargin_in_real_data():
    """Check if variation margin is properly accounted for in real data"""
    print("=" * 80)
    print("ПРОВЕРКА УЧЕТА ВАРИАЦИОННОЙ МАРЖИ В РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 80)

    if client.client is None:
        await client.ainit()

    # Get operations for specific date when we know there was variation margin
    moscow_tz = pytz.timezone('Europe/Moscow')
    # Focus on 2025-07-16 when we know there was 3391.15 rub variation margin
    start_date = moscow_tz.localize(datetime.datetime(2025, 7, 16, 0, 0, 0))
    end_date = moscow_tz.localize(datetime.datetime(2025, 7, 16, 23, 59, 59))

    print(f"Анализ операций за {start_date.strftime('%Y-%m-%d')}...")

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

    # Analyze variation margin operations
    print(f"\n📊 АНАЛИЗ ВАРИАЦИОННОЙ МАРЖИ:")
    print("-" * 60)

    varmargin_operations = []
    total_varmargin = 0.0

    for op in operations:
        if op.operation_type in [OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                                 OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN]:
            amount = quotation_to_float(op.payment)
            total_varmargin += amount
            varmargin_operations.append((op.date, amount))

            op_type = "НАЧИСЛЕНИЕ" if op.operation_type == OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN else "СПИСАНИЕ"
            print(
                f"{op.date.strftime('%Y-%m-%d %H:%M')} | {op_type} | {amount:>10.2f} RUB")

    print("-" * 60)
    print(f"ИТОГО вариационная маржа: {total_varmargin:.2f} RUB")

    # Calculate profits using different methods
    print(f"\n🔍 СРАВНЕНИЕ МЕТОДОВ РАСЧЕТА:")
    print("-" * 60)

    # Method 1: Direct payment sum (should include variation margin)
    total_payment = sum(quotation_to_float(op.payment) for op in operations)
    print(f"Прямое суммирование платежей: {total_payment:.2f} RUB")

    # Method 2: Trade-based calculation (should include variation margin distributed across trades)
    calculator = ProfitCalculator()
    trades, total_profit, processed_operations = calculator.process_operations(
        operations)
    print(f"Расчет через сделки: {total_profit:.2f} RUB")

    # Method 3: Calculate without variation margin to see the difference
    operations_without_varmargin = [
        op for op in operations
        if op.operation_type not in [OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                                     OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN]
    ]

    calculator_no_varmargin = ProfitCalculator()
    trades_no_varmargin, profit_no_varmargin, _ = calculator_no_varmargin.process_operations(
        operations_without_varmargin)
    print(f"Расчет БЕЗ вариационной маржи: {profit_no_varmargin:.2f} RUB")

    # Check the difference
    varmargin_impact = total_profit - profit_no_varmargin
    print(f"Влияние вариационной маржи: {varmargin_impact:.2f} RUB")

    print(f"\n✅ ПРОВЕРКА КОРРЕКТНОСТИ:")
    print("-" * 60)

    # Check if variation margin impact matches actual variation margin
    if abs(varmargin_impact - total_varmargin) < 0.01:
        print("✅ Вариационная маржа УЧИТЫВАЕТСЯ КОРРЕКТНО!")
        print(f"   Расчетное влияние: {varmargin_impact:.2f} RUB")
        print(f"   Фактическая вариационная маржа: {total_varmargin:.2f} RUB")
    else:
        print("❌ Вариационная маржа НЕ УЧИТЫВАЕТСЯ КОРРЕКТНО!")
        print(f"   Расчетное влияние: {varmargin_impact:.2f} RUB")
        print(f"   Фактическая вариационная маржа: {total_varmargin:.2f} RUB")
        print(f"   Разница: {abs(varmargin_impact - total_varmargin):.2f} RUB")

    # Show detailed trade analysis
    if trades:
        print(f"\n📋 ДЕТАЛЬНЫЙ АНАЛИЗ СДЕЛОК:")
        print("-" * 80)

        for i, trade in enumerate(trades[:5], 1):  # Show first 5 trades
            # Calculate margin impact for this trade
            base_net_profit = trade.gross_profit - trade.fees
            margin_impact = trade.net_profit - base_net_profit

            print(f"Сделка {i}:")
            print(f"  Валовая прибыль: {trade.gross_profit:.2f} RUB")
            print(f"  Комиссии: {trade.fees:.2f} RUB")
            print(f"  Базовая чистая прибыль: {base_net_profit:.2f} RUB")
            print(f"  Влияние вариационной маржи: {margin_impact:.2f} RUB")
            print(f"  Итоговая чистая прибыль: {trade.net_profit:.2f} RUB")
            print()

    # Show specific check for 3391.15 rub mentioned by user
    if any(abs(amount - 3391.15) < 0.01 for _, amount in varmargin_operations):
        print(f"🎯 СПЕЦИАЛЬНАЯ ПРОВЕРКА: Операция на 3391.15 RUB найдена!")
        print(
            f"   Эта вариационная маржа {'УЧТЕНА' if abs(varmargin_impact - total_varmargin) < 0.01 else 'НЕ УЧТЕНА'} в расчете сделок.")

    print(f"\n📈 ИТОГОВЫЙ ВЫВОД:")
    print("=" * 60)
    if abs(varmargin_impact - total_varmargin) < 0.01:
        print("✅ Вариационная маржа ПРАВИЛЬНО учитывается в расчете прибыли!")
        print("✅ Система корректно обрабатывает все операции вариационной маржи!")
    else:
        print("❌ Найдена проблема с учетом вариационной маржи!")
        print("❌ Требуется дополнительная настройка системы!")


async def main():
    """Main function"""
    await check_varmargin_in_real_data()


if __name__ == "__main__":
    asyncio.run(main())
