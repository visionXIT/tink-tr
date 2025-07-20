#!/usr/bin/env python3
"""
Финальная версия калькулятора с правильной логикой из таблиц
"""

import datetime
import json


def analyze_table_logic():
    """Анализирует логику подсчета из таблиц"""
    print("=== АНАЛИЗ ЛОГИКИ ИЗ ТАБЛИЦ ===")

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

    print("Данные из таблицы за период 31.03-04.04:")
    total_profit = 0.0
    total_commission = 0.0
    total_day_clearing = 0.0
    total_evening_clearing = 0.0

    for day_data in april_week1_data:
        print(f"\n{day_data['date']}:")
        print(f"  Заработок: {day_data['profit']:,.2f} ₽")
        print(f"  Комиссии: {day_data['commission']:,.2f} ₽")
        print(f"  Дневная клиринговая: {day_data['day_clearing']:,.2f} ₽")
        print(f"  Вечерняя клиринговая: {day_data['evening_clearing']:,.2f} ₽")
        print(f"  Сделок: {day_data['trades']}")

        total_profit += day_data['profit']
        total_commission += day_data['commission']
        total_day_clearing += day_data['day_clearing']
        total_evening_clearing += day_data['evening_clearing']

    print(f"\nИТОГО за период:")
    print(f"  Общая прибыль: {total_profit:,.2f} ₽")
    print(f"  Общие комиссии: {total_commission:,.2f} ₽")
    print(f"  Дневная клиринговая: {total_day_clearing:,.2f} ₽")
    print(f"  Вечерняя клиринговая: {total_evening_clearing:,.2f} ₽")

    # Анализируем логику
    print(f"\nАНАЛИЗ ЛОГИКИ:")
    print(f"1. Заработок = сумма всех операций за день (включая вариационную маржу)")
    print(f"2. Комиссии = отдельная статья расходов")
    print(f"3. Итоговая прибыль = заработок - комиссии")
    print(f"4. Вариационная маржа разделяется на дневную и вечернюю по времени")

    # Проверяем расчет
    expected_total = -72.09  # Из таблицы
    calculated_total = total_profit

    print(f"\nПРОВЕРКА:")
    print(f"Ожидаемая прибыль: {expected_total:,.2f} ₽")
    print(f"Рассчитанная прибыль: {calculated_total:,.2f} ₽")
    print(f"Расхождение: {abs(calculated_total - expected_total):,.2f} ₽")

    if abs(calculated_total - expected_total) < 1.0:
        print("✅ Логика правильная!")
    else:
        print("❌ Есть расхождения в логике")

    return april_week1_data


def create_correct_operations_from_table_data(table_data):
    """Создает операции точно по логике из таблицы"""
    operations = []

    for day_data in table_data:
        date = datetime.datetime.strptime(day_data['date'], '%Y-%m-%d')

        # Создаем операции точно по логике таблицы
        # 1. Заработок за день (как в таблице)
        earnings_op = type('MockOperation', (), {
            'date': date.replace(hour=15, minute=0, second=0),
            'operation_type': 22,  # SELL
            'payment': day_data['profit'],  # Заработок из таблицы
            'figi': 'BBG0013HGFT4',
            'description': f"Заработок за {day_data['date']}"
        })()
        operations.append(earnings_op)

        # 2. Комиссии (отдельно)
        if day_data['commission'] > 0:
            commission_op = type('MockOperation', (), {
                'date': date.replace(hour=16, minute=0, second=0),
                'operation_type': 19,  # COMMISSION
                'payment': -day_data['commission'],
                'figi': 'BBG0013HGFT4',
                'description': "Комиссия брокера"
            })()
            operations.append(commission_op)

        # 3. Дневная клиринговая
        if day_data['day_clearing'] != 0:
            margin_op = type('MockOperation', (), {
                'date': date.replace(hour=12, minute=0, second=0),
                'operation_type': 26 if day_data['day_clearing'] > 0 else 27,
                'payment': day_data['day_clearing'],
                'figi': 'BBG0013HGFT4',
                'description': "Дневная клиринговая"
            })()
            operations.append(margin_op)

        # 4. Вечерняя клиринговая
        if day_data['evening_clearing'] != 0:
            margin_op = type('MockOperation', (), {
                'date': date.replace(hour=18, minute=0, second=0),
                'operation_type': 26 if day_data['evening_clearing'] > 0 else 27,
                'payment': day_data['evening_clearing'],
                'figi': 'BBG0013HGFT4',
                'description': "Вечерняя клиринговая"
            })()
            operations.append(margin_op)

    return operations


def test_final_calculator():
    """Тестирует финальный калькулятор"""
    print("\n=== ТЕСТ ФИНАЛЬНОГО КАЛЬКУЛЯТОРА ===")

    # Анализируем логику из таблицы
    table_data = analyze_table_logic()

    # Создаем операции точно по логике таблицы
    operations = create_correct_operations_from_table_data(table_data)
    print(f"\nСоздано {len(operations)} операций")

    # Импортируем калькулятор
    import sys
    sys.path.append('.')

    from app.utils.profit_calculator import TableExactCalculator

    # Создаем экземпляр калькулятора
    calculator = TableExactCalculator()

    # Тестируем анализ
    starting_balance = 44127.39  # Из таблицы
    result = calculator.get_exact_table_analysis(operations, starting_balance)

    print("\n=== РЕЗУЛЬТАТЫ АНАЛИЗА ===")

    # Выводим сводку
    summary = result['summary']
    print(f"СВОДКА:")
    print(f"  Общий заработок: {summary['total_earnings']:,.2f} ₽")
    print(f"  Общие комиссии: {summary['total_commission']:,.2f} ₽")
    print(f"  Итоговая прибыль: {summary['total_profit']:,.2f} ₽")
    print(f"  Общее количество сделок: {summary['total_trades']}")
    print(f"  Дневная клиринговая: {summary['total_day_clearing']:,.2f} ₽")
    print(
        f"  Вечерняя клиринговая: {summary['total_evening_clearing']:,.2f} ₽")

    # Сравниваем с ожидаемыми результатами из таблицы
    print(f"\n=== СРАВНЕНИЕ С ТАБЛИЦЕЙ ===")
    expected_profit = -72.09  # Из таблицы за период 31.03-04.04
    actual_profit = summary['total_profit']

    print(f"Ожидаемая прибыль: {expected_profit:,.2f} ₽")
    print(f"Рассчитанная прибыль: {actual_profit:,.2f} ₽")
    print(f"Расхождение: {abs(actual_profit - expected_profit):,.2f} ₽")

    if abs(actual_profit - expected_profit) < 1.0:
        print("✅ Результат соответствует таблице!")
    else:
        print("❌ Есть расхождения с таблицей")

    # Сохраняем результат в файл
    with open('final_calculator_test_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\nРезультат сохранен в final_calculator_test_result.json")

    return result


def main():
    """Основная функция тестирования"""
    print("ФИНАЛЬНЫЙ ТЕСТ КАЛЬКУЛЯТОРА С ПРАВИЛЬНОЙ ЛОГИКОЙ")
    print("=" * 70)

    # Тест финального калькулятора
    test_final_calculator()

    print("\nТестирование завершено!")


if __name__ == "__main__":
    main()
