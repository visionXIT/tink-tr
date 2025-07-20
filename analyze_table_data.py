#!/usr/bin/env python3
"""
Script to analyze the CSV table data and understand the exact profit calculation logic
"""

import re


def parse_russian_number(text: str) -> float:
    """Parse Russian number format (e.g., '1 234,56 ₽' -> 1234.56)"""
    if not text or text.strip() == '':
        return 0.0

    # Remove currency symbol, spaces, and non-breaking spaces
    text = text.replace('₽', '').replace(' ', '').replace('\xa0', '')

    # Replace comma with dot for decimal
    text = text.replace(',', '.')

    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_april_data():
    """Parse April CSV data"""
    data = {}

    with open('АПРЕЛЬ-Table 1.csv', 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract weekly sections
    sections = content.split('САЙТ №1 СМЕНА КОНТРАКТА С 01.04')

    for i, section in enumerate(sections[1:], 1):  # Skip first empty section
        lines = section.strip().split('\n')

        # Extract balance info
        balance_start = None
        balance_end = None

        for line in lines:
            if 'Сумма перед тестированием' in line:
                match = re.search(r'(\d+[\s\xa0,]*\d*,\d+)', line)
                if match:
                    balance_start = parse_russian_number(match.group(1))
            elif 'Сумма после тестирования' in line:
                match = re.search(r'(\d+[\s\xa0,]*\d*,\d+)', line)
                if match:
                    balance_end = parse_russian_number(match.group(1))

        # Extract daily data
        daily_data = {}
        in_results = False

        for line in lines:
            if 'Результаты' in line:
                in_results = True
                continue
            elif in_results and line.strip() == '':
                break
            elif in_results:
                parts = line.split(';')
                if len(parts) >= 6 and parts[0].strip():
                    day_name = parts[0].strip()
                    if 'дн.клира' in day_name:
                        daily_data['day_clearing'] = [
                            parse_russian_number(x) for x in parts[1:6]]
                    elif 'веч.клира' in day_name:
                        daily_data['evening_clearing'] = [
                            parse_russian_number(x) for x in parts[1:6]]
                    elif 'кол-во сделок' in day_name:
                        daily_data['trades_count'] = [
                            int(x) if x.strip() else 0 for x in parts[1:6]]
                    elif 'комиссия' in day_name:
                        daily_data['commission'] = [
                            parse_russian_number(x) for x in parts[1:6]]
                    elif 'Заработок' in day_name:
                        daily_data['earnings'] = [
                            parse_russian_number(x) for x in parts[1:6]]

        data[f'week_{i}'] = {
            'balance_start': balance_start,
            'balance_end': balance_end,
            'daily_data': daily_data
        }

    return data


def parse_may_data():
    """Parse May CSV data"""
    data = {}

    with open('МАЙ-Table 1.csv', 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract weekly sections
    sections = content.split('САЙТ №1 СМЕНА КОНТРАКТА С 02.05')

    for i, section in enumerate(sections[1:], 1):  # Skip first empty section
        lines = section.strip().split('\n')

        # Extract balance info
        balance_start = None
        balance_end = None

        for line in lines:
            if 'Сумма перед тестированием' in line:
                match = re.search(r'(\d+[\s\xa0,]*\d*,\d+)', line)
                if match:
                    balance_start = parse_russian_number(match.group(1))
            elif 'Сумма после тестирования' in line:
                match = re.search(r'(\d+[\s\xa0,]*\d*,\d+)', line)
                if match:
                    balance_end = parse_russian_number(match.group(1))

        # Extract daily data
        daily_data = {}
        in_results = False

        for line in lines:
            if 'Результаты' in line:
                in_results = True
                continue
            elif in_results and line.strip() == '':
                break
            elif in_results:
                parts = line.split(';')
                if len(parts) >= 6 and parts[0].strip():
                    day_name = parts[0].strip()
                    if 'дн.клира' in day_name:
                        daily_data['day_clearing'] = [
                            parse_russian_number(x) for x in parts[1:6]]
                    elif 'веч.клира' in day_name:
                        daily_data['evening_clearing'] = [
                            parse_russian_number(x) for x in parts[1:6]]
                    elif 'кол-во сделок' in day_name:
                        daily_data['trades_count'] = [
                            int(x) if x.strip() else 0 for x in parts[1:6]]
                    elif 'комиссия' in day_name:
                        daily_data['commission'] = [
                            parse_russian_number(x) for x in parts[1:6]]
                    elif 'Заработок' in day_name:
                        daily_data['earnings'] = [
                            parse_russian_number(x) for x in parts[1:6]]

        data[f'week_{i}'] = {
            'balance_start': balance_start,
            'balance_end': balance_end,
            'daily_data': daily_data
        }

    return data


def analyze_profit_logic():
    """Analyze the profit calculation logic from the tables"""

    print("=== APRIL DATA ANALYSIS ===")
    april_data = parse_april_data()

    for week_key, week_data in april_data.items():
        print(f"\n{week_key}:")
        print(f"  Balance start: {week_data['balance_start']}")
        print(f"  Balance end: {week_data['balance_end']}")

        daily_data = week_data['daily_data']

        if 'day_clearing' in daily_data:
            print("  Day clearing:", daily_data['day_clearing'])
        if 'evening_clearing' in daily_data:
            print("  Evening clearing:", daily_data['evening_clearing'])
        if 'commission' in daily_data:
            print("  Commission:", daily_data['commission'])
        if 'earnings' in daily_data:
            print("  Earnings:", daily_data['earnings'])

        # Calculate total earnings and commissions
        if 'earnings' in daily_data and 'commission' in daily_data:
            total_earnings = sum(daily_data['earnings'])
            total_commission = sum(daily_data['commission'])
            net_profit = total_earnings - total_commission
            print(f"  Total earnings: {total_earnings}")
            print(f"  Total commission: {total_commission}")
            print(f"  Net profit: {net_profit}")
            print(
                f"  Expected balance change: {week_data['balance_end'] - week_data['balance_start']}")

    print("\n=== MAY DATA ANALYSIS ===")
    may_data = parse_may_data()

    for week_key, week_data in may_data.items():
        print(f"\n{week_key}:")
        print(f"  Balance start: {week_data['balance_start']}")
        print(f"  Balance end: {week_data['balance_end']}")

        daily_data = week_data['daily_data']

        if 'day_clearing' in daily_data:
            print("  Day clearing:", daily_data['day_clearing'])
        if 'evening_clearing' in daily_data:
            print("  Evening clearing:", daily_data['evening_clearing'])
        if 'commission' in daily_data:
            print("  Commission:", daily_data['commission'])
        if 'earnings' in daily_data:
            print("  Earnings:", daily_data['earnings'])

        # Calculate total earnings and commissions
        if 'earnings' in daily_data and 'commission' in daily_data:
            total_earnings = sum(daily_data['earnings'])
            total_commission = sum(daily_data['commission'])
            net_profit = total_earnings - total_commission
            print(f"  Total earnings: {total_earnings}")
            print(f"  Total commission: {total_commission}")
            print(f"  Net profit: {net_profit}")
            if week_data['balance_start'] and week_data['balance_end']:
                print(
                    f"  Expected balance change: {week_data['balance_end'] - week_data['balance_start']}")


if __name__ == "__main__":
    analyze_profit_logic()
