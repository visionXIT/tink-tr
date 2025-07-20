#!/usr/bin/env python3
"""
Финальный тест точного табличного калькулятора прибыли
"""

import datetime
import json
from typing import List, Any


def create_mock_operation(date: datetime.datetime, operation_type: int, payment: float,
                          figi: str = "BBG0013HGFT4", description: str = "") -> Any:
    """Создает мок операцию для тестирования"""
    # Создаем объект операции
    operation = type('MockOperation', (), {
        'date': date,
        'operation_type': operation_type,
        'payment': payment,
        'figi': figi,
        'description': description
    })()

    return operation


def create_exact_april_operations() -> List[Any]:
    """Создает операции точно соответствующие данным из таблицы за апрель"""
    operations = []

    # Данные из таблицы за апрель (31.03-04.04)
    april_week1_data = [
        # 31.03.2025
        {'date': '2025-03-31', 'day_clearing': -937.22, 'evening_clearing': -
            234.10, 'trades': 11, 'commission': 345.83, 'profit': -1517.15},
        # 01.04.2025
        {'date': '2025-04-01', 'day_clearing': -957.54, 'evening_clearing': -
            688.96, 'trades': 22, 'commission': 732.77, 'profit': -2379.27},
        # 02.04.2025
        {'date': '2025-04-02', 'day_clearing': -645.50, 'evening_clearing': -
            885.37, 'trades': 18, 'commission': 552.16, 'profit': -2083.03},
        # 03.04.2025
        {'date': '2025-04-03', 'day_clearing': 659.53, 'evening_clearing': -
            1216.49, 'trades': 12, 'commission': 390.77, 'profit': -947.73},
        # 04.04.2025
        {'date': '2025-04-04', 'day_clearing': 6067.16, 'evening_clearing': 902.59,
            'trades': 2, 'commission': 114.66, 'profit': 6855.09}
    ]

    for day_data in april_week1_data:
        date = datetime.datetime.strptime(day_data['date'], '%Y-%m-%d')

        # Создаем операции точно по логике таблицы
        # 1. Общий заработок за день (как в таблице)
        earnings_op = create_mock_operation(
            date=date.replace(hour=15, minute=0, second=0),
            operation_type=22,  # SELL (положительная сумма)
            # Заработок + комиссии = общая сумма операций
            payment=day_data['profit'] + day_data['commission'],
            description=f"Общий заработок за {day_data['date']}"
        )
        operations.append(earnings_op)

        # 2. Комиссии (отдельно)
        if day_data['commission'] > 0:
            commission_op = create_mock_operation(
                date=date.replace(hour=16, minute=0, second=0),
                operation_type=19,  # COMMISSION
                payment=-day_data['commission'],
                description="Комиссия брокера"
            )
            operations.append(commission_op)

        # 3. Дневная клиринговая (вариационная маржа) - время 10:00-14:00
        if day_data['day_clearing'] != 0:
            margin_op = create_mock_operation(
                # Время дневной клиринговой
                date=date.replace(hour=12, minute=0, second=0),
                # INCOME/EXPENSE
                operation_type=26 if day_data['day_clearing'] > 0 else 27,
                payment=day_data['day_clearing'],
                description="Дневная клиринговая"
            )
            operations.append(margin_op)

        # 4. Вечерняя клиринговая (вариационная маржа) - время 14:05-18:50 и остальное
        if day_data['evening_clearing'] != 0:
            margin_op = create_mock_operation(
                # Время вечерней клиринговой
                date=date.replace(hour=18, minute=0, second=0),
                # INCOME/EXPENSE
                operation_type=26 if day_data['evening_clearing'] > 0 else 27,
                payment=day_data['evening_clearing'],
                description="Вечерняя клиринговая"
            )
            operations.append(margin_op)

    return operations


def test_exact_table_calculator():
    """Test the exact table calculator with table data"""
    print("=== ТЕСТ ТОЧНОГО ТАБЛИЧНОГО КАЛЬКУЛЯТОРА ===")

    # Create mock operations that exactly match table data
    operations = []

    # April data - manually extracted from CSV with exact values
    april_data = [
        # Period 1: 31.03-04.04 (profit: -72.09)
        {
            'date': datetime.datetime(2025, 3, 31), 'day_clearing': -937.22, 'evening_clearing': -234.10, 'trades': 11, 'commission': 345.83, 'earnings': -1517.15
        },
        {
            'date': datetime.datetime(2025, 4, 1), 'day_clearing': -957.54, 'evening_clearing': -688.96, 'trades': 22, 'commission': 732.77, 'earnings': -2379.27
        },
        {
            'date': datetime.datetime(2025, 4, 2), 'day_clearing': -645.50, 'evening_clearing': -885.37, 'trades': 18, 'commission': 552.16, 'earnings': -2083.03
        },
        {
            'date': datetime.datetime(2025, 4, 3), 'day_clearing': 659.53, 'evening_clearing': -1216.49, 'trades': 12, 'commission': 390.77, 'earnings': -947.73
        },
        {
            'date': datetime.datetime(2025, 4, 4), 'day_clearing': 6067.16, 'evening_clearing': 902.59, 'trades': 2, 'commission': 114.66, 'earnings': 6855.09
        },

        # Period 2: 07.04-11.04 (profit: -12417.69)
        {
            'date': datetime.datetime(2025, 4, 7), 'day_clearing': 168.55, 'evening_clearing': -2780.15, 'trades': 14, 'commission': 423.50, 'earnings': -3035.10
        },
        {
            'date': datetime.datetime(2025, 4, 8), 'day_clearing': -2887.33, 'evening_clearing': -206.48, 'trades': 17, 'commission': 443.33, 'earnings': -3537.14
        },
        {
            'date': datetime.datetime(2025, 4, 9), 'day_clearing': 1512.76, 'evening_clearing': -2821.37, 'trades': 7, 'commission': 181.37, 'earnings': -1489.98
        },
        {
            'date': datetime.datetime(2025, 4, 10), 'day_clearing': 4915.88, 'evening_clearing': -2654.44, 'trades': 11, 'commission': 315.97, 'earnings': 1945.47
        },
        {
            'date': datetime.datetime(2025, 4, 11), 'day_clearing': -4939.49, 'evening_clearing': -940.81, 'trades': 9, 'commission': 420.64, 'earnings': -6300.94
        },

        # Period 3: 14.04-18.04 (profit: -6928.85)
        {
            'date': datetime.datetime(2025, 4, 14), 'day_clearing': -1621.23, 'evening_clearing': -1002.51, 'trades': 6, 'commission': 261.67, 'earnings': -2885.41
        },
        {
            'date': datetime.datetime(2025, 4, 15), 'day_clearing': 571.10, 'evening_clearing': -266.57, 'trades': 7, 'commission': 187.16, 'earnings': 117.37
        },
        {
            'date': datetime.datetime(2025, 4, 16), 'day_clearing': -1629.55, 'evening_clearing': 209.09, 'trades': 11, 'commission': 336.16, 'earnings': -1756.62
        },
        {
            'date': datetime.datetime(2025, 4, 17), 'day_clearing': -2015.18, 'evening_clearing': 317.16, 'trades': 10, 'commission': 276.17, 'earnings': -1974.19
        },
        {
            'date': datetime.datetime(2025, 4, 18), 'day_clearing': -319.87, 'evening_clearing': 84.60, 'trades': 7, 'commission': 194.73, 'earnings': -430.00
        },

        # Period 4: 21.04-25.04 (profit: 4841.46)
        {
            'date': datetime.datetime(2025, 4, 21), 'day_clearing': -97.36, 'evening_clearing': 993.80, 'trades': 23, 'commission': 647.75, 'earnings': 248.69
        },
        {
            'date': datetime.datetime(2025, 4, 22), 'day_clearing': 40.39, 'evening_clearing': -415.19, 'trades': 18, 'commission': 489.18, 'earnings': -863.98
        },
        {
            'date': datetime.datetime(2025, 4, 23), 'day_clearing': 1140.48, 'evening_clearing': 3636.62, 'trades': 2, 'commission': 55.56, 'earnings': 4721.54
        },
        {
            'date': datetime.datetime(2025, 4, 24), 'day_clearing': -345.94, 'evening_clearing': 171.95, 'trades': 14, 'commission': 0, 'earnings': -173.99
        },
        {
            'date': datetime.datetime(2025, 4, 25), 'day_clearing': 1085.39, 'evening_clearing': -176.19, 'trades': 8, 'commission': 0, 'earnings': 909.20
        },

        # Period 5: 28.04-30.04 (profit: 1228.83)
        {
            'date': datetime.datetime(2025, 4, 28), 'day_clearing': -24.82, 'evening_clearing': 1609.73, 'trades': 11, 'commission': 329.29, 'earnings': 1255.62
        },
        {
            'date': datetime.datetime(2025, 4, 29), 'day_clearing': 1262.92, 'evening_clearing': 555.92, 'trades': 4, 'commission': 118.98, 'earnings': 1699.86
        },
        {
            'date': datetime.datetime(2025, 4, 30), 'day_clearing': 701.46, 'evening_clearing': -1410.45, 'trades': 41, 'commission': 1017.66, 'earnings': -1726.65
        }
    ]

    # Create operations that exactly match the table data
    for day_data in april_data:
        # Create operations that sum up to the exact table values
        # For each day, create operations that when summed give the exact table values

        # Day clearing operation
        if day_data['day_clearing'] != 0:
            day_op = type('MockOperation', (), {
                'date': day_data['date'].replace(hour=14, minute=0, second=0),
                'operation_type': 26 if day_data['day_clearing'] > 0 else 27,
                'payment': day_data['day_clearing'],
                'description': 'Дневная клиринговая'
            })()
            operations.append(day_op)

        # Evening clearing operation
        if day_data['evening_clearing'] != 0:
            evening_op = type('MockOperation', (), {
                'date': day_data['date'].replace(hour=18, minute=0, second=0),
                'operation_type': 26 if day_data['evening_clearing'] > 0 else 27,
                'payment': day_data['evening_clearing'],
                'description': 'Вечерняя клиринговая'
            })()
            operations.append(evening_op)

        # Commission operation
        if day_data['commission'] > 0:
            commission_op = type('MockOperation', (), {
                'date': day_data['date'].replace(hour=16, minute=0, second=0),
                'operation_type': 19,
                'payment': -day_data['commission'],
                'description': 'Комиссия брокера'
            })()
            operations.append(commission_op)

        # Create buy/sell operations that sum to the earnings
        # The earnings in the table represent the net result of all trades
        if day_data['trades'] > 0:
            # Create operations that sum to the exact earnings value
            # We'll create pairs of buy/sell operations
            for i in range(day_data['trades']):
                # Buy operation
                buy_op = type('MockOperation', (), {
                    'date': day_data['date'].replace(hour=10, minute=i, second=0),
                    'operation_type': 15,
                    'payment': -1000.0,
                    'description': f'Покупка {i+1}'
                })()
                operations.append(buy_op)

                # Sell operation that balances to the earnings
                sell_amount = 1000.0 + \
                    (day_data['earnings'] / day_data['trades'])
                sell_op = type('MockOperation', (), {
                    'date': day_data['date'].replace(hour=15, minute=i, second=0),
                    'operation_type': 22,
                    'payment': sell_amount,
                    'description': f'Продажа {i+1}'
                })()
                operations.append(sell_op)

    print(f"Создано {len(operations)} операций")

    # Initialize calculator
    calculator = TableExactCalculator()

    # Calculate profit using exact table method
    result = calculator.get_exact_table_analysis(
        operations, starting_balance=44127.39)

    print("\n=== РЕЗУЛЬТАТЫ РАСЧЕТА ===")
    print(f"Общая прибыль: {result['summary']['total_profit']:.2f}")
    print(f"Общие комиссии: {result['summary']['total_commission']:.2f}")
    print(f"Всего сделок: {result['summary']['total_trades']}")
    print(
        f"Дневная клиринговая: {result['summary']['total_day_clearing']:.2f}")
    print(
        f"Вечерняя клиринговая: {result['summary']['total_evening_clearing']:.2f}")
    print(f"Общий заработок: {result['summary']['total_earnings']:.2f}")

    # Expected results from table
    expected_april_total = -13348.34  # From table
    calculated_total = result['summary']['total_profit']

    print(f"\n=== СРАВНЕНИЕ ===")
    print(f"Ожидаемая прибыль (из таблицы): {expected_april_total:.2f}")
    print(f"Рассчитанная прибыль: {calculated_total:.2f}")
    print(f"Расхождение: {abs(calculated_total - expected_april_total):.2f}")

    # Print daily breakdown
    print(f"\n=== ДЕТАЛИ ПО ДНЯМ ===")
    for date, data in result['daily_data'].items():
        print(f"Дата: {date}")
        print(f"  Дневная клиринговая: {data['day_clearing']:.2f}")
        print(f"  Вечерняя клиринговая: {data['evening_clearing']:.2f}")
        print(f"  Комиссии: {data['commission']:.2f}")
        print(f"  Сделки: {data['trades_count']}")
        print(f"  Заработок: {data['total_profit']:.2f}")
        print()


def test_with_real_table_data():
    """Тестирует с реальными данными из таблицы"""
    print("\n=== ТЕСТ С РЕАЛЬНЫМИ ДАННЫМИ ИЗ ТАБЛИЦЫ ===")

    # Загружаем мок операции из файла
    try:
        with open('mock_operations_from_table.json', 'r', encoding='utf-8') as f:
            mock_operations = json.load(f)

        print(f"Загружено {len(mock_operations)} операций из файла")

        # Конвертируем в формат для калькулятора
        operations = []
        for op_data in mock_operations:
            # Конвертируем строку даты в datetime
            date_str = op_data['date']
            if isinstance(date_str, str):
                date = datetime.datetime.fromisoformat(
                    date_str.replace('Z', '+00:00'))
            else:
                date = datetime.datetime.now()

            # Создаем объект операции
            operation = type('MockOperation', (), {
                'date': date,
                'operation_type': op_data['operation_type'],
                'payment': op_data['payment'],
                'figi': op_data.get('figi', 'BBG0013HGFT4'),
                'description': op_data.get('description', '')
            })()

            operations.append(operation)

        # Тестируем калькулятор
        from app.utils.profit_calculator import TableExactCalculator
        calculator = TableExactCalculator()

        starting_balance = 44127.39  # Из таблицы
        result = calculator.get_exact_table_analysis(
            operations, starting_balance)

        print(f"\nРезультат с реальными данными:")
        print(
            f"  Общий заработок: {result['summary']['total_earnings']:,.2f} ₽")
        print(
            f"  Общие комиссии: {result['summary']['total_commission']:,.2f} ₽")
        print(
            f"  Итоговая прибыль: {result['summary']['total_profit']:,.2f} ₽")
        print(
            f"  Общее количество сделок: {result['summary']['total_trades']}")

        # Сохраняем результат
        with open('real_data_exact_test_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, default=str)

        print("Результат сохранен в real_data_exact_test_result.json")

    except FileNotFoundError:
        print("Файл mock_operations_from_table.json не найден. Запустите сначала improved_table_analyzer.py")


def main():
    """Основная функция тестирования"""
    print("ТЕСТИРОВАНИЕ ТОЧНОГО ТАБЛИЧНОГО КАЛЬКУЛЯТОРА")
    print("=" * 60)

    # Тест с точными мок данными
    test_exact_table_calculator()

    # Тест с реальными данными из таблицы
    test_with_real_table_data()

    print("\nТестирование завершено!")


if __name__ == "__main__":
    main()
