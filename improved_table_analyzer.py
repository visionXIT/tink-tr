#!/usr/bin/env python3
"""
Улучшенный анализатор данных из таблиц
"""

from datetime import datetime


def parse_russian_number(text: str) -> float:
    """Parse Russian number format (e.g., '1 234,56 ₽' -> 1234.56)"""
    if not text or text.strip() == '':
        return 0.0

    # Remove currency symbol and spaces
    text = text.replace('₽', '').replace(' ', '')

    # Replace comma with dot for decimal
    text = text.replace(',', '.')

    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_date(date_str: str) -> datetime:
    """Parse date in format 'DD.MM.YYYYг.'"""
    if not date_str or date_str.strip() == '':
        return None

    # Remove 'г.' suffix and parse
    date_str = date_str.replace('г.', '')
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except ValueError:
        return None


def extract_april_data():
    """Extract data from April table"""
    print("=== ДАННЫЕ АПРЕЛЬ ===")

    with open('АПРЕЛЬ-Table 1.csv', 'r', encoding='utf-8') as file:
        content = file.read()

    # Extract periods and their data
    periods = []

    # Split by periods
    period_sections = content.split('САЙТ №1 СМЕНА КОНТРАКТА С 01.04')

    for section in period_sections[1:]:  # Skip first empty section
        lines = section.strip().split('\n')

        # Find period dates
        period_dates = []
        balance_starts = []
        balance_ends = []
        profits = []

        # Find results section
        results_start = -1
        for i, line in enumerate(lines):
            if 'Результаты' in line:
                results_start = i
                break

        if results_start == -1:
            continue

        # Extract daily data
        daily_data = []
        current_day = None

        for i in range(results_start + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            parts = line.split(';')
            if len(parts) < 6:
                continue

            # Check if this is a date row
            if any(part.strip().endswith('г.') for part in parts[:5]):
                # This is a date row
                for j, part in enumerate(parts[:5]):
                    if part.strip() and part.strip().endswith('г.'):
                        date = parse_date(part.strip())
                        if date:
                            current_day = {
                                'date': date,
                                'day_clearing': 0.0,
                                'evening_clearing': 0.0,
                                'trades_count': 0,
                                'commission': 0.0,
                                'earnings': 0.0
                            }
                            daily_data.append(current_day)
                continue

            # Check if this is a data row
            if 'дн.клира' in parts[0]:
                # Day clearing data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['day_clearing'] = parse_russian_number(
                            part)
            elif 'веч.клира' in parts[0]:
                # Evening clearing data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['evening_clearing'] = parse_russian_number(
                            part)
            elif 'кол-во сделок' in parts[0]:
                # Trades count data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['trades_count'] = int(
                            part) if part.strip().isdigit() else 0
            elif 'комиссия' in parts[0]:
                # Commission data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['commission'] = parse_russian_number(
                            part)
            elif 'Заработок' in parts[0]:
                # Earnings data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['earnings'] = parse_russian_number(part)

        if daily_data:
            periods.append({
                'daily_data': daily_data,
                'total_day_clearing': sum(d['day_clearing'] for d in daily_data),
                'total_evening_clearing': sum(d['evening_clearing'] for d in daily_data),
                'total_trades': sum(d['trades_count'] for d in daily_data),
                'total_commission': sum(d['commission'] for d in daily_data),
                'total_earnings': sum(d['earnings'] for d in daily_data)
            })

    # Print results
    for i, period in enumerate(periods):
        print(f"\n--- Период {i+1} ---")

        for day in period['daily_data']:
            print(f"Дата: {day['date'].strftime('%d.%m.%Y')}")
            print(f"  Дневная клиринговая: {day['day_clearing']:.2f}")
            print(f"  Вечерняя клиринговая: {day['evening_clearing']:.2f}")
            print(f"  Количество сделок: {day['trades_count']}")
            print(f"  Комиссия: {day['commission']:.2f}")
            print(f"  Заработок: {day['earnings']:.2f}")
            print()

        print(f"ИТОГО за период:")
        print(f"  Дневная клиринговая: {period['total_day_clearing']:.2f}")
        print(
            f"  Вечерняя клиринговая: {period['total_evening_clearing']:.2f}")
        print(f"  Всего сделок: {period['total_trades']}")
        print(f"  Комиссии: {period['total_commission']:.2f}")
        print(f"  Заработок: {period['total_earnings']:.2f}")
        print(
            f"  Чистая прибыль (заработок - комиссии): {period['total_earnings'] - period['total_commission']:.2f}")

    return periods


def extract_may_data():
    """Extract data from May table"""
    print("\n=== ДАННЫЕ МАЙ ===")

    with open('МАЙ-Table 1.csv', 'r', encoding='utf-8') as file:
        content = file.read()

    # Extract periods and their data
    periods = []

    # Split by periods
    period_sections = content.split('САЙТ №1 СМЕНА КОНТРАКТА С 02.05')

    for section in period_sections[1:]:  # Skip first empty section
        lines = section.strip().split('\n')

        # Find results section
        results_start = -1
        for i, line in enumerate(lines):
            if 'Результаты' in line:
                results_start = i
                break

        if results_start == -1:
            continue

        # Extract daily data
        daily_data = []
        current_day = None

        for i in range(results_start + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            parts = line.split(';')
            if len(parts) < 6:
                continue

            # Check if this is a date row
            if any(part.strip().endswith('г.') for part in parts[:5]):
                # This is a date row
                for j, part in enumerate(parts[:5]):
                    if part.strip() and part.strip().endswith('г.'):
                        date = parse_date(part.strip())
                        if date:
                            current_day = {
                                'date': date,
                                'day_clearing': 0.0,
                                'evening_clearing': 0.0,
                                'trades_count': 0,
                                'commission': 0.0,
                                'earnings': 0.0
                            }
                            daily_data.append(current_day)
                continue

            # Check if this is a data row
            if 'дн.клира' in parts[0]:
                # Day clearing data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['day_clearing'] = parse_russian_number(
                            part)
            elif 'веч.клира' in parts[0]:
                # Evening clearing data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['evening_clearing'] = parse_russian_number(
                            part)
            elif 'кол-во сделок' in parts[0]:
                # Trades count data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['trades_count'] = int(
                            part) if part.strip().isdigit() else 0
            elif 'комиссия' in parts[0]:
                # Commission data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['commission'] = parse_russian_number(
                            part)
            elif 'Заработок' in parts[0]:
                # Earnings data
                for j, part in enumerate(parts[1:6]):
                    if j < len(daily_data):
                        daily_data[j]['earnings'] = parse_russian_number(part)

        if daily_data:
            periods.append({
                'daily_data': daily_data,
                'total_day_clearing': sum(d['day_clearing'] for d in daily_data),
                'total_evening_clearing': sum(d['evening_clearing'] for d in daily_data),
                'total_trades': sum(d['trades_count'] for d in daily_data),
                'total_commission': sum(d['commission'] for d in daily_data),
                'total_earnings': sum(d['earnings'] for d in daily_data)
            })

    # Print results
    for i, period in enumerate(periods):
        print(f"\n--- Период {i+1} ---")

        for day in period['daily_data']:
            print(f"Дата: {day['date'].strftime('%d.%m.%Y')}")
            print(f"  Дневная клиринговая: {day['day_clearing']:.2f}")
            print(f"  Вечерняя клиринговая: {day['evening_clearing']:.2f}")
            print(f"  Количество сделок: {day['trades_count']}")
            print(f"  Комиссия: {day['commission']:.2f}")
            print(f"  Заработок: {day['earnings']:.2f}")
            print()

        print(f"ИТОГО за период:")
        print(f"  Дневная клиринговая: {period['total_day_clearing']:.2f}")
        print(
            f"  Вечерняя клиринговая: {period['total_evening_clearing']:.2f}")
        print(f"  Всего сделок: {period['total_trades']}")
        print(f"  Комиссии: {period['total_commission']:.2f}")
        print(f"  Заработок: {period['total_earnings']:.2f}")
        print(
            f"  Чистая прибыль (заработок - комиссии): {period['total_earnings'] - period['total_commission']:.2f}")

    return periods


def extract_balance_progression():
    """Extract balance progression from tables"""
    print("\n=== ПРОГРЕССИЯ БАЛАНСА ===")

    # April balances from table
    april_balances = {
        '31.03-04.04': {'start': 44127.39, 'end': 44055.30, 'profit': -72.09},
        '07.04-11.04': {'start': 44055.30, 'end': 31637.61, 'profit': -12417.69},
        '14.04-18.04': {'start': 31637.61, 'end': 24708.76, 'profit': -6928.85},
        '21.04-25.04': {'start': 24708.76, 'end': 29550.22, 'profit': 4841.46},
        '28.04-30.04': {'start': 29550.22, 'end': 30779.05, 'profit': 1228.83}
    }

    print("АПРЕЛЬ:")
    for period, data in april_balances.items():
        print(
            f"  {period}: {data['start']:.2f} -> {data['end']:.2f} (прибыль: {data['profit']:.2f})")

    # May balances
    may_balances = {
        '01.05-02.05': {'start': 30779.05, 'end': None, 'profit': None},
        '05.05-09.05': {'start': None, 'end': None, 'profit': None},
        '12.05-16.05': {'start': None, 'end': None, 'profit': 4175.82}
    }

    print("\nМАЙ:")
    for period, data in may_balances.items():
        if data['start'] and data['end']:
            print(
                f"  {period}: {data['start']:.2f} -> {data['end']:.2f} (прибыль: {data['profit']:.2f})")
        elif data['profit']:
            print(f"  {period}: прибыль: {data['profit']:.2f}")


def create_mock_operations_from_table_data(april_periods, may_periods):
    """Create mock operations based on table data for testing"""
    operations = []

    # Process April data
    for period in april_periods:
        for day in period['daily_data']:
            # Create operations for this day

            # Trades (buy/sell operations)
            if day['trades_count'] > 0:
                for trade_idx in range(day['trades_count']):
                    # Create buy operation
                    buy_op = {
                        'date': day['date'].replace(hour=10, minute=0, second=0),
                        'operation_type': 15,  # BUY
                        'payment': -1000.0,  # Negative for buy
                        'quantity': 1,
                        'figi': 'BBG0013HGFT4',  # Brent futures
                        'description': 'Покупка Brent'
                    }
                    operations.append(buy_op)

                    # Create sell operation
                    sell_op = {
                        'date': day['date'].replace(hour=15, minute=0, second=0),
                        'operation_type': 22,  # SELL
                        'payment': 1000.0 + (day['earnings'] / day['trades_count'] if day['trades_count'] > 0 else 0),
                        'quantity': 1,
                        'figi': 'BBG0013HGFT4',
                        'description': 'Продажа Brent'
                    }
                    operations.append(sell_op)

            # Commission
            if day['commission'] > 0:
                commission_op = {
                    'date': day['date'].replace(hour=16, minute=0, second=0),
                    'operation_type': 19,  # COMMISSION
                    'payment': -day['commission'],
                    'description': 'Комиссия брокера'
                }
                operations.append(commission_op)

            # Day clearing (variation margin)
            if day['day_clearing'] != 0:
                margin_op = {
                    'date': day['date'].replace(hour=14, minute=0, second=0),
                    # INCOME/EXPENSE
                    'operation_type': 26 if day['day_clearing'] > 0 else 27,
                    'payment': day['day_clearing'],
                    'description': 'Дневная клиринговая'
                }
                operations.append(margin_op)

            # Evening clearing (variation margin)
            if day['evening_clearing'] != 0:
                margin_op = {
                    'date': day['date'].replace(hour=18, minute=0, second=0),
                    # INCOME/EXPENSE
                    'operation_type': 26 if day['evening_clearing'] > 0 else 27,
                    'payment': day['evening_clearing'],
                    'description': 'Вечерняя клиринговая'
                }
                operations.append(margin_op)

    # Process May data
    for period in may_periods:
        for day in period['daily_data']:
            # Similar logic for May
            if day['trades_count'] > 0:
                for trade_idx in range(day['trades_count']):
                    buy_op = {
                        'date': day['date'].replace(hour=10, minute=0, second=0),
                        'operation_type': 15,
                        'payment': -1000.0,
                        'quantity': 1,
                        'figi': 'BBG0013HGFT4',
                        'description': 'Покупка Brent'
                    }
                    operations.append(buy_op)

                    sell_op = {
                        'date': day['date'].replace(hour=15, minute=0, second=0),
                        'operation_type': 22,
                        'payment': 1000.0 + (day['earnings'] / day['trades_count'] if day['trades_count'] > 0 else 0),
                        'quantity': 1,
                        'figi': 'BBG0013HGFT4',
                        'description': 'Продажа Brent'
                    }
                    operations.append(sell_op)

            if day['commission'] > 0:
                commission_op = {
                    'date': day['date'].replace(hour=16, minute=0, second=0),
                    'operation_type': 19,
                    'payment': -day['commission'],
                    'description': 'Комиссия брокера'
                }
                operations.append(commission_op)

            if day['day_clearing'] != 0:
                margin_op = {
                    'date': day['date'].replace(hour=14, minute=0, second=0),
                    'operation_type': 26 if day['day_clearing'] > 0 else 27,
                    'payment': day['day_clearing'],
                    'description': 'Дневная клиринговая'
                }
                operations.append(margin_op)

            if day['evening_clearing'] != 0:
                margin_op = {
                    'date': day['date'].replace(hour=18, minute=0, second=0),
                    'operation_type': 26 if day['evening_clearing'] > 0 else 27,
                    'payment': day['evening_clearing'],
                    'description': 'Вечерняя клиринговая'
                }
                operations.append(margin_op)

    return operations


if __name__ == "__main__":
    april_periods = extract_april_data()
    may_periods = extract_may_data()
    extract_balance_progression()

    # Create mock operations
    mock_operations = create_mock_operations_from_table_data(
        april_periods, may_periods)
    print(f"\nСоздано {len(mock_operations)} мок операций для тестирования")

    # Save mock operations
    import json
    with open('mock_operations_from_table.json', 'w', encoding='utf-8') as f:
        json.dump(mock_operations, f, indent=2, default=str)
    print("Мок операции сохранены в mock_operations_from_table.json")
