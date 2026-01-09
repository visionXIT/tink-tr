import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from t_tech.invest.grpc.operations_pb2 import OperationType

from app.utils.quotation import quotation_to_float

logger = logging.getLogger(__name__)


class TableExactCalculator:
    """
    Калькулятор прибыли, точно воспроизводящий логику подсчета из таблиц

    Этот калькулятор использует точную логику из таблиц:
    - Заработок = сумма всех операций за день (включая вариационную маржу)
    - Дневная клиринговая = вариационная маржа с 10:00 до 14:00
    - Вечерняя клиринговая = вариационная маржа с 14:05 до 18:50 и остальное время
    - Комиссии = операции типа BROKER_FEE
    - Итоговая прибыль = заработок - комиссии
    """

    def __init__(self):
        self.operation_types = {
            15: "BUY",  # Покупка (отрицательные суммы)
            22: "SELL",  # Продажа (положительные суммы)
            19: "COMMISSION",  # Комиссии (небольшие отрицательные)
            26: "INCOME",  # Доходы (положительные)
            27: "EXPENSE",  # Расходы (отрицательные)
        }

    def convert_money_value(self, money_value) -> float:
        """Конвертирует MoneyValue в число с правильным масштабированием"""
        if hasattr(money_value, "units") and hasattr(money_value, "nano"):
            return money_value.units + money_value.nano / 1e9
        elif hasattr(money_value, "currency"):
            return money_value.units + money_value.nano / 1e9
        else:
            return float(money_value) if money_value else 0.0

    def classify_operation(self, operation) -> Dict[str, Any]:
        """Классифицирует операцию по типу с правильной обработкой данных"""
        op_type = getattr(
            operation, "type", getattr(operation, "operation_type", "unknown")
        )
        payment = getattr(operation, "payment", None)

        # Правильная конвертация суммы
        amount_value = self.convert_money_value(payment) if payment else 0.0

        # Определяем категорию операции
        if op_type == 15:  # Покупка
            category = "BUY"
        elif op_type == 22:  # Продажа
            category = "SELL"
        elif op_type == 19:  # Комиссии
            category = "COMMISSION"
        elif op_type == 26:  # Доходы
            category = "INCOME"
        elif op_type == 27:  # Расходы
            category = "EXPENSE"
        else:
            category = "OTHER"

        return {
            "type": op_type,
            "type_name": self.operation_types.get(op_type, f"UNKNOWN_{op_type}"),
            "amount": amount_value,
            "category": category,
            "date": operation.date,
            "description": getattr(operation, "description", ""),
            "figi": getattr(operation, "figi", ""),
            "instrument_name": getattr(operation, "name", ""),
        }

    def calculate_daily_profit_exact_table_logic(
        self, operations: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Рассчитывает прибыль по дням точно по логике таблиц

        Логика из таблиц:
        - Заработок = сумма всех операций за день (включая вариационную маржу)
        - Дневная клиринговая = вариационная маржа с 10:00 до 14:00
        - Вечерняя клиринговая = вариационная маржа с 14:05 до 18:50 и остальное время
        - Комиссии = операции типа BROKER_FEE
        - Итоговая прибыль = заработок - комиссии
        """
        daily_data = {}

        for op in operations:
            classified_op = self.classify_operation(op)
            date_str = classified_op["date"].strftime("%Y-%m-%d")

            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "day_clearing": 0.0,  # Дневная клиринговая
                    "evening_clearing": 0.0,  # Вечерняя клиринговая
                    "commission": 0.0,  # Комиссии
                    "trades_count": 0,  # Количество сделок
                    # Общий заработок (как в таблице)
                    "total_profit": 0.0,
                    "operations": [],
                }

            daily_data[date_str]["operations"].append(classified_op)

            # Определяем тип операции и время
            operation_hour = classified_op["date"].hour
            operation_type = classified_op["type"]

            if operation_type == 19:  # Комиссии
                daily_data[date_str]["commission"] += abs(classified_op["amount"])
            elif operation_type in [15, 22]:  # Покупка/продажа
                daily_data[date_str]["trades_count"] += 1
                # Включаем в общий заработок (как в таблице)
                daily_data[date_str]["total_profit"] += classified_op["amount"]
            elif operation_type in [26, 27]:  # Вариационная маржа
                # Определяем дневная или вечерняя клиринговая по времени
                # Дневная клиринговая (10:00-14:00)
                if 10 <= operation_hour <= 13:
                    daily_data[date_str]["day_clearing"] += classified_op["amount"]
                else:  # Вечерняя клиринговая (14:05-18:50 и остальное время)
                    daily_data[date_str]["evening_clearing"] += classified_op["amount"]

                # Вариационная маржа тоже включается в общий заработок (как в таблице)
                daily_data[date_str]["total_profit"] += classified_op["amount"]
            else:
                # Прочие операции тоже включаем в общий заработок (как в таблице)
                daily_data[date_str]["total_profit"] += classified_op["amount"]

        return daily_data

    def calculate_period_summary_exact_table_logic(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Рассчитывает сводку за период точно по логике таблиц
        """
        summary = {
            "total_days": len(daily_data),
            "total_profit": 0.0,  # Итоговая прибыль (заработок - комиссии)
            "total_commission": 0.0,
            "total_trades": 0,
            "total_day_clearing": 0.0,
            "total_evening_clearing": 0.0,
            "total_earnings": 0.0,  # Общий заработок (сумма всех операций)
            "daily_breakdown": daily_data,
        }

        for date, data in daily_data.items():
            # Общий заработок
            summary["total_earnings"] += data["total_profit"]
            summary["total_commission"] += data["commission"]
            summary["total_trades"] += data["trades_count"]
            summary["total_day_clearing"] += data["day_clearing"]
            summary["total_evening_clearing"] += data["evening_clearing"]

        # Итоговая прибыль = заработок - комиссии (как в таблице)
        summary["total_profit"] = (
            summary["total_earnings"] - summary["total_commission"]
        )

        return summary

    def calculate_balance_progression_exact(
        self, operations: List[Any], starting_balance: float
    ) -> Dict[str, float]:
        """
        Рассчитывает прогрессию баланса точно по логике таблиц
        """
        if not operations:
            return {}

        # Сортируем операции по дате
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Группируем операции по дням
        daily_operations = defaultdict(list)
        for op in sorted_operations:
            date_str = op.date.strftime("%Y-%m-%d")
            daily_operations[date_str].append(op)

        # Рассчитываем баланс для каждого дня
        balance_progression = {}
        current_balance = starting_balance

        # Находим самую раннюю дату
        earliest_date = min(daily_operations.keys())

        # Устанавливаем начальный баланс для самой ранней даты
        balance_progression[earliest_date] = starting_balance

        # Рассчитываем баланс для каждого дня
        for date_str in sorted(daily_operations.keys()):
            if date_str != earliest_date:
                # Баланс на начало дня = баланс предыдущего дня
                current_balance = balance_progression.get(prev_date, starting_balance)

            # Суммируем все операции за день (как в таблице)
            daily_profit = 0.0
            daily_commission = 0.0

            for op in daily_operations[date_str]:
                payment = self.convert_money_value(op.payment)
                op_type = getattr(op, "operation_type", getattr(op, "type", None))

                if op_type == 19:  # Комиссии
                    daily_commission += abs(payment)
                else:
                    # Все остальные операции включаем в прибыль
                    daily_profit += payment

            # Итоговая прибыль за день = общая прибыль - комиссии (как в таблице)
            net_daily_profit = daily_profit - daily_commission

            # Баланс на конец дня = баланс начала дня + чистая прибыль за день
            current_balance += net_daily_profit
            balance_progression[date_str] = current_balance

            prev_date = date_str

        return balance_progression

    def get_exact_table_analysis(
        self, operations: List[Any], starting_balance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Возвращает анализ точно по логике таблиц

        Args:
            operations: Список операций
            starting_balance: Начальный баланс

        Returns:
            Словарь с анализом точно по логике таблиц
        """
        if not operations:
            return {
                "daily_data": {},
                "summary": {
                    "total_profit": 0.0,
                    "total_commission": 0.0,
                    "total_trades": 0,
                    "total_day_clearing": 0.0,
                    "total_evening_clearing": 0.0,
                    "total_earnings": 0.0,
                },
                "balance_progression": {},
                "table_format": {
                    "total_profit": 0.0,
                    "total_commission": 0.0,
                    "total_trades": 0,
                    "daily_breakdown": {},
                },
            }

        # Рассчитываем данные по дням
        daily_data = self.calculate_daily_profit_exact_table_logic(operations)

        # Рассчитываем сводку за период
        summary = self.calculate_period_summary_exact_table_logic(daily_data)

        # Рассчитываем прогрессию баланса
        balance_progression = self.calculate_balance_progression_exact(
            operations, starting_balance
        )

        # Формируем формат таблицы
        table_format = {
            "total_profit": summary["total_profit"],
            "total_commission": summary["total_commission"],
            "total_trades": summary["total_trades"],
            "daily_breakdown": daily_data,
        }

        return {
            "daily_data": daily_data,
            "summary": summary,
            "balance_progression": balance_progression,
            "table_format": table_format,
        }


class TableCompatibleProfitCalculator:
    """
    Калькулятор прибыли, совместимый с логикой подсчета из таблиц

    Этот калькулятор точно воспроизводит логику подсчета из таблиц:
    - Правильная обработка вариационной маржи (дневная и вечерняя клиринговая)
    - Корректный подсчет комиссий
    - Точный расчет балансов на начало и конец периода
    - Правильная группировка операций по дням
    """

    def __init__(self):
        self.operation_types = {
            15: "BUY",  # Покупка (отрицательные суммы)
            22: "SELL",  # Продажа (положительные суммы)
            19: "COMMISSION",  # Комиссии (небольшие отрицательные)
            26: "INCOME",  # Доходы (положительные)
            27: "EXPENSE",  # Расходы (отрицательные)
        }

    def convert_money_value(self, money_value) -> float:
        """Конвертирует MoneyValue в число с правильным масштабированием"""
        if hasattr(money_value, "units") and hasattr(money_value, "nano"):
            return money_value.units + money_value.nano / 1e9
        elif hasattr(money_value, "currency"):
            return money_value.units + money_value.nano / 1e9
        else:
            return float(money_value) if money_value else 0.0

    def classify_operation(self, operation) -> Dict[str, Any]:
        """Классифицирует операцию по типу с правильной обработкой данных"""
        op_type = getattr(
            operation, "type", getattr(operation, "operation_type", "unknown")
        )
        payment = getattr(operation, "payment", None)

        # Правильная конвертация суммы
        amount_value = self.convert_money_value(payment) if payment else 0.0

        # Определяем категорию операции
        if op_type == 15:  # Покупка
            category = "BUY"
        elif op_type == 22:  # Продажа
            category = "SELL"
        elif op_type == 19:  # Комиссии
            category = "COMMISSION"
        elif op_type == 26:  # Доходы
            category = "INCOME"
        elif op_type == 27:  # Расходы
            category = "EXPENSE"
        else:
            category = "OTHER"

        return {
            "type": op_type,
            "type_name": self.operation_types.get(op_type, f"UNKNOWN_{op_type}"),
            "amount": amount_value,
            "category": category,
            "date": operation.date,
            "description": getattr(operation, "description", ""),
            "figi": getattr(operation, "figi", ""),
            "instrument_name": getattr(operation, "name", ""),
        }

    def calculate_daily_profit_table_compatible(
        self, operations: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Рассчитывает прибыль по дням в формате, совместимом с таблицами

        Логика соответствует таблицам:
        - Дневная клиринговая: вариационная маржа с 10:00 до 14:00
        - Вечерняя клиринговая: вариационная маржа с 14:05 до 18:50 и остальное время
        - Комиссии: операции типа BROKER_FEE
        - Заработок: сумма всех операций за день
        """
        daily_data = {}

        for op in operations:
            classified_op = self.classify_operation(op)
            date_str = classified_op["date"].strftime("%Y-%m-%d")

            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "day_clearing": 0.0,  # Дневная клиринговая
                    "evening_clearing": 0.0,  # Вечерняя клиринговая
                    "commission": 0.0,  # Комиссии
                    "trades_count": 0,  # Количество сделок
                    "total_profit": 0.0,  # Общий заработок
                    "operations": [],
                }

            daily_data[date_str]["operations"].append(classified_op)

            # Определяем тип операции и время
            operation_hour = classified_op["date"].hour
            operation_type = classified_op["type"]

            if operation_type == 19:  # Комиссии
                daily_data[date_str]["commission"] += abs(classified_op["amount"])
            elif operation_type in [15, 22]:  # Покупка/продажа
                daily_data[date_str]["trades_count"] += 1
                daily_data[date_str]["total_profit"] += classified_op["amount"]
            elif operation_type in [26, 27]:  # Вариационная маржа
                # Определяем дневная или вечерняя клиринговая по времени
                # Дневная клиринговая (10:00-14:00)
                if 10 <= operation_hour <= 13:
                    daily_data[date_str]["day_clearing"] += classified_op["amount"]
                else:  # Вечерняя клиринговая (14:05-18:50 и остальное время)
                    daily_data[date_str]["evening_clearing"] += classified_op["amount"]

                # Вариационная маржа тоже включается в общий заработок
                daily_data[date_str]["total_profit"] += classified_op["amount"]
            else:
                # Прочие операции тоже включаем в общий заработок
                daily_data[date_str]["total_profit"] += classified_op["amount"]

        return daily_data

    def calculate_period_summary_table_compatible(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Рассчитывает сводку за период в формате, совместимом с таблицами
        """
        summary = {
            "total_days": len(daily_data),
            "total_profit": 0.0,
            "total_commission": 0.0,
            "total_trades": 0,
            "total_day_clearing": 0.0,
            "total_evening_clearing": 0.0,
            "daily_breakdown": daily_data,
        }

        for date, data in daily_data.items():
            summary["total_profit"] += data["total_profit"]
            summary["total_commission"] += data["commission"]
            summary["total_trades"] += data["trades_count"]
            summary["total_day_clearing"] += data["day_clearing"]
            summary["total_evening_clearing"] += data["evening_clearing"]

        return summary

    def calculate_balance_progression(
        self, operations: List[Any], starting_balance: float
    ) -> Dict[str, float]:
        """
        Рассчитывает прогрессию баланса по дням

        Args:
            operations: Список операций
            starting_balance: Начальный баланс

        Returns:
            Словарь {дата: баланс}
        """
        if not operations:
            return {}

        # Сортируем операции по дате
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Группируем операции по дням
        daily_operations = defaultdict(list)
        for op in sorted_operations:
            date_str = op.date.strftime("%Y-%m-%d")
            daily_operations[date_str].append(op)

        # Рассчитываем баланс для каждого дня
        balance_progression = {}
        current_balance = starting_balance

        # Находим самую раннюю дату
        earliest_date = min(daily_operations.keys())

        # Устанавливаем начальный баланс для самой ранней даты
        balance_progression[earliest_date] = starting_balance

        # Рассчитываем баланс для каждого дня
        for date_str in sorted(daily_operations.keys()):
            if date_str != earliest_date:
                # Баланс на начало дня = баланс предыдущего дня
                current_balance = balance_progression.get(prev_date, starting_balance)

            # Суммируем все операции за день
            daily_profit = 0.0
            for op in daily_operations[date_str]:
                payment = self.convert_money_value(op.payment)
                daily_profit += payment

            # Баланс на конец дня = баланс начала дня + прибыль за день
            current_balance += daily_profit
            balance_progression[date_str] = current_balance

            prev_date = date_str

        return balance_progression

    def get_table_compatible_analysis(
        self, operations: List[Any], starting_balance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Возвращает анализ в формате, совместимом с таблицами

        Args:
            operations: Список операций
            starting_balance: Начальный баланс

        Returns:
            Словарь с анализом в формате таблиц
        """
        if not operations:
            return {
                "daily_data": {},
                "summary": {
                    "total_profit": 0.0,
                    "total_commission": 0.0,
                    "total_trades": 0,
                    "total_day_clearing": 0.0,
                    "total_evening_clearing": 0.0,
                },
                "balance_progression": {},
                "table_format": {
                    "total_profit": 0.0,
                    "total_commission": 0.0,
                    "total_trades": 0,
                    "daily_breakdown": {},
                },
            }

        # Рассчитываем данные по дням
        daily_data = self.calculate_daily_profit_table_compatible(operations)

        # Рассчитываем сводку
        summary = self.calculate_period_summary_table_compatible(daily_data)

        # Рассчитываем прогрессию баланса
        balance_progression = self.calculate_balance_progression(
            operations, starting_balance
        )

        return {
            "daily_data": daily_data,
            "summary": summary,
            "balance_progression": balance_progression,
            "table_format": {
                "total_profit": summary["total_profit"],
                "total_commission": summary["total_commission"],
                "total_trades": summary["total_trades"],
                "total_day_clearing": summary["total_day_clearing"],
                "total_evening_clearing": summary["total_evening_clearing"],
                "daily_breakdown": daily_data,
            },
        }


class FixedProfitCalculator:
    """Исправленный калькулятор прибыли на основе реальных типов операций API"""

    def __init__(self):
        # Реальные типы операций из API t_tech
        self.operation_types = {
            15: "BUY",  # Покупка (отрицательные суммы)
            22: "SELL",  # Продажа (положительные суммы)
            19: "COMMISSION",  # Комиссии (небольшие отрицательные)
            26: "INCOME",  # Доходы (положительные)
            27: "EXPENSE",  # Расходы (отрицательные)
        }

    def convert_money_value(self, money_value) -> float:
        """Конвертирует MoneyValue в число с правильным масштабированием"""
        if hasattr(money_value, "units") and hasattr(money_value, "nano"):
            # Правильная конвертация: units + nano/1e9
            return money_value.units + money_value.nano / 1e9
        elif hasattr(money_value, "currency"):
            # Если это MoneyValue объект
            return money_value.units + money_value.nano / 1e9
        else:
            return float(money_value) if money_value else 0.0

    def classify_operation(self, operation) -> Dict[str, Any]:
        """Классифицирует операцию по типу с правильной обработкой данных"""
        op_type = getattr(
            operation, "type", getattr(operation, "operation_type", "unknown")
        )
        payment = getattr(operation, "payment", None)

        # Правильная конвертация суммы
        amount_value = self.convert_money_value(payment) if payment else 0.0

        # Определяем категорию операции
        if op_type == 15:  # Покупка
            category = "BUY"
        elif op_type == 22:  # Продажа
            category = "SELL"
        elif op_type == 19:  # Комиссии
            category = "COMMISSION"
        elif op_type == 26:  # Доходы
            category = "INCOME"
        elif op_type == 27:  # Расходы
            category = "EXPENSE"
        else:
            category = "OTHER"

        return {
            "type": op_type,
            "type_name": self.operation_types.get(op_type, f"UNKNOWN_{op_type}"),
            "amount": amount_value,
            "category": category,
            "date": operation.date,
            "description": getattr(operation, "description", ""),
            "figi": getattr(operation, "figi", ""),
            "instrument_name": getattr(operation, "name", ""),
        }

    def calculate_daily_profit(
        self, operations: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Рассчитывает прибыль по дням с правильной обработкой данных"""
        daily_data = {}

        for op in operations:
            classified_op = self.classify_operation(op)
            date_str = classified_op["date"].strftime("%Y-%m-%d")

            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "total_amount": 0,
                    "buy_amount": 0,
                    "sell_amount": 0,
                    "commission": 0,
                    "income": 0,
                    "expense": 0,
                    "other": 0,
                    "trades_count": 0,
                    "operations_count": 0,
                    "operations": [],
                }

            daily_data[date_str]["operations"].append(classified_op)
            daily_data[date_str]["total_amount"] += classified_op["amount"]
            daily_data[date_str]["operations_count"] += 1

            # Распределяем по категориям
            if classified_op["category"] == "BUY":
                # Берем модуль
                daily_data[date_str]["buy_amount"] += abs(classified_op["amount"])
                daily_data[date_str]["trades_count"] += 1
            elif classified_op["category"] == "SELL":
                daily_data[date_str]["sell_amount"] += classified_op["amount"]
                daily_data[date_str]["trades_count"] += 1
            elif classified_op["category"] == "COMMISSION":
                # Берем модуль
                daily_data[date_str]["commission"] += abs(classified_op["amount"])
            elif classified_op["category"] == "INCOME":
                daily_data[date_str]["income"] += classified_op["amount"]
            elif classified_op["category"] == "EXPENSE":
                # Берем модуль
                daily_data[date_str]["expense"] += abs(classified_op["amount"])
            else:
                daily_data[date_str]["other"] += classified_op["amount"]

        return daily_data

    def calculate_period_summary(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Рассчитывает сводку за период с правильными формулами"""
        summary = {
            "total_days": len(daily_data),
            "total_amount": 0,
            "total_buy": 0,
            "total_sell": 0,
            "total_commission": 0,
            "total_income": 0,
            "total_expense": 0,
            "total_other": 0,
            "total_trades": 0,
            "total_operations": 0,
            "net_profit": 0,  # Чистая прибыль (продажи - покупки - комиссии)
            "gross_profit": 0,  # Валовая прибыль (все доходы)
            "profit_margin": 0,  # Маржа прибыли
            "trade_volume": 0,  # Объем торговли
        }

        for date, data in daily_data.items():
            summary["total_amount"] += data["total_amount"]
            summary["total_buy"] += data["buy_amount"]
            summary["total_sell"] += data["sell_amount"]
            summary["total_commission"] += data["commission"]
            summary["total_income"] += data["income"]
            summary["total_expense"] += data["expense"]
            summary["total_other"] += data["other"]
            summary["total_trades"] += data["trades_count"]
            summary["total_operations"] += data["operations_count"]

        # Рассчитываем чистую прибыль (как в таблице)
        summary["net_profit"] = (
            summary["total_sell"] - summary["total_buy"] - summary["total_commission"]
        )
        summary["gross_profit"] = summary["total_sell"] + summary["total_income"]
        summary["trade_volume"] = summary["total_buy"] + summary["total_sell"]

        # Рассчитываем маржу прибыли
        if summary["trade_volume"] != 0:
            summary["profit_margin"] = (
                summary["net_profit"] / summary["trade_volume"]
            ) * 100

        return summary

    def get_table_compatible_profit(self, operations: List[Any]) -> Dict[str, Any]:
        """Возвращает прибыль в формате, совместимом с таблицей"""
        daily_data = self.calculate_daily_profit(operations)
        summary = self.calculate_period_summary(daily_data)

        return {
            "daily_data": daily_data,
            "summary": summary,
            "table_format": {
                "total_profit": summary["net_profit"],
                "total_commission": summary["total_commission"],
                "total_trades": summary["total_trades"],
                "profit_percentage": summary["profit_margin"],
                "daily_breakdown": daily_data,
            },
        }


@dataclass
class TradingSession:
    """Represents a trading session with multiple operations"""

    session_id: str
    figi: str
    instrument_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    operations: List[Dict[str, Any]]  # All operations in this session
    total_quantity_sold: int
    total_quantity_bought: int
    total_sell_amount: float  # Total received from sells
    total_buy_amount: float  # Total paid for buys
    gross_profit: float
    fees: float
    variation_margin: float
    net_profit: float
    direction: str  # 'SHORT' for sell-first sessions


@dataclass
class Trade:
    """Represents a completed trade (buy-sell pair) - kept for backward compatibility"""

    trade_id: str
    figi: str
    instrument_name: str
    entry_time: datetime.datetime
    exit_time: datetime.datetime
    entry_price: float
    exit_price: float
    quantity: int
    direction: str  # 'LONG' or 'SHORT'
    gross_profit: float
    fees: float
    net_profit: float
    entry_operation_id: str
    exit_operation_id: str
    # New fields for session-based calculation
    session_data: Optional[TradingSession] = None
    variation_margin: float = 0.0


@dataclass
class PeriodProfit:
    """Represents profit for a specific time period"""

    start_date: datetime.datetime
    end_date: datetime.datetime
    starting_balance: float
    ending_balance: float
    total_profit: float
    total_fees: float
    net_profit: float
    profit_percentage: float
    trades_count: int
    winning_trades: int
    losing_trades: int


class ProfitCalculator:
    """Advanced profit calculation system for trading operations"""

    def __init__(self, timezone_offset: int = 3):
        self.timezone_offset = timezone_offset
        self.reset()
        # Добавляем исправленный калькулятор
        self.fixed_calculator = FixedProfitCalculator()

    def reset(self):
        """Reset the calculator state"""
        self.positions = defaultdict(list)  # figi -> list of operations
        self.completed_trades = []
        self.fees_buffer = []
        self.margin_operations = []
        self.trading_sessions = []  # New: completed trading sessions

    def correct_timezone(self, date: datetime.datetime) -> datetime.datetime:
        """Apply timezone correction"""
        return date + datetime.timedelta(hours=self.timezone_offset)

    def get_fixed_profit_analysis(self, operations: List[Any]) -> Dict[str, Any]:
        """Получает анализ прибыли с исправленными расчетами"""
        return self.fixed_calculator.get_table_compatible_profit(operations)

    def process_operations(
        self, operations: List[Any]
    ) -> Tuple[List[Trade], float, List[Any]]:
        """
        Process a list of operations and calculate trades and profit using session-based logic

        Args:
            operations: List of trading operations from t_tech API

        Returns:
            Tuple of (completed_trades, total_profit, all_processed_operations)
        """
        return self.process_operations_with_starting_positions(operations, {})

    def process_operations_with_starting_positions(
        self, operations: List[Any], starting_positions: Dict[str, int] = None
    ) -> Tuple[List[Trade], float, List[Any]]:
        """
        Process a list of operations and calculate trades and profit using session-based logic
        with support for known starting positions

        Args:
            operations: List of trading operations from t_tech API
            starting_positions: Dict mapping FIGI to starting position (positive = long, negative = short)

        Returns:
            Tuple of (completed_trades, total_profit, all_processed_operations)
        """
        if starting_positions is None:
            starting_positions = {}

        self.reset()

        # Sort operations by date (oldest first)
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Separate trading operations from fees and margin operations
        trading_operations = []
        for operation in sorted_operations:
            if operation.operation_type == OperationType.OPERATION_TYPE_BROKER_FEE:
                self._process_fee_operation(operation)
            elif operation.operation_type in [
                OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
            ]:
                self._process_margin_operation(operation)
            elif operation.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                trading_operations.append(operation)

        # Group trading operations into sessions with starting positions
        self._group_operations_into_sessions(trading_operations, starting_positions)

        # Convert sessions to trades (for backward compatibility)
        self._convert_sessions_to_trades()

        # Calculate total profit
        total_profit = sum(trade.net_profit for trade in self.completed_trades)

        return self.completed_trades, total_profit, sorted_operations

    def analyze_starting_positions(
        self, operations: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze operations to provide insights about possible starting positions.

        This method helps determine what the starting position might have been
        for each FIGI by analyzing the first operation and potential position changes.

        Args:
            operations: List of trading operations from t_tech API

        Returns:
            Dict mapping FIGI to analysis results containing:
            - first_operation: Details about the first operation
            - possible_scenarios: List of possible starting positions and their implications
        """
        if not operations:
            return {}

        # Sort operations by date (oldest first)
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Group by FIGI
        figi_operations = defaultdict(list)
        for op in sorted_operations:
            if op.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                figi_operations[op.figi].append(op)

        analysis = {}

        for figi, ops in figi_operations.items():
            first_op = ops[0]

            # Calculate what happens with different starting positions
            scenarios = []

            # Scenario 1: Starting from 0 (traditional assumption)
            scenarios.append(
                {
                    "starting_position": 0,
                    "description": "Начинаем с нулевой позиции (традиционное предположение)",
                    "first_operation_result": first_op.quantity
                    if first_op.operation_type == OperationType.OPERATION_TYPE_BUY
                    else -first_op.quantity,
                    "crosses_zero": False,
                }
            )

            # Scenario 2: Starting position that would make first operation cross zero
            if first_op.operation_type == OperationType.OPERATION_TYPE_BUY:
                # If first operation is BUY, maybe we had a short position
                scenarios.append(
                    {
                        "starting_position": -first_op.quantity,
                        "description": f"Начинаем с короткой позиции -{first_op.quantity} лотов (первая операция закрывает позицию)",
                        "first_operation_result": 0,
                        "crosses_zero": True,
                    }
                )

                # Or maybe we had an even larger short position
                scenarios.append(
                    {
                        "starting_position": -(first_op.quantity * 2),
                        "description": f"Начинаем с короткой позиции -{first_op.quantity * 2} лотов (первая операция частично закрывает)",
                        "first_operation_result": -first_op.quantity,
                        "crosses_zero": False,
                    }
                )
            else:
                # If first operation is SELL, maybe we had a long position
                scenarios.append(
                    {
                        "starting_position": first_op.quantity,
                        "description": f"Начинаем с длинной позиции +{first_op.quantity} лотов (первая операция закрывает позицию)",
                        "first_operation_result": 0,
                        "crosses_zero": True,
                    }
                )

                # Or maybe we had an even larger long position
                scenarios.append(
                    {
                        "starting_position": first_op.quantity * 2,
                        "description": f"Начинаем с длинной позиции +{first_op.quantity * 2} лотов (первая операция частично закрывает)",
                        "first_operation_result": first_op.quantity,
                        "crosses_zero": False,
                    }
                )

            analysis[figi] = {
                "first_operation": {
                    "type": "Покупка"
                    if first_op.operation_type == OperationType.OPERATION_TYPE_BUY
                    else "Продажа",
                    "quantity": first_op.quantity,
                    "price": quotation_to_float(first_op.price),
                    "date": first_op.date,
                    "amount": quotation_to_float(first_op.payment),
                },
                "possible_scenarios": scenarios,
                "total_operations": len(ops),
            }

        return analysis

    def calculate_starting_positions_from_current(
        self, operations: List[Any], current_positions: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Calculate starting positions by working backwards from current positions

        Args:
            operations: List of operations from start_date to end_date
            current_positions: Current positions {FIGI: quantity}

        Returns:
            Dict mapping FIGI to starting position
        """
        if not operations:
            return current_positions.copy()

        # Sort operations by date (newest first for reverse calculation)
        operations = sorted(operations, key=lambda x: x.date, reverse=True)

        # Start with current positions
        starting_positions = current_positions.copy()

        # Process operations in reverse chronological order
        for operation in operations:
            if operation.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                figi = operation.figi
                quantity = operation.quantity

                # Initialize position if not exists
                if figi not in starting_positions:
                    starting_positions[figi] = 0

                # Reverse the operation:
                # If it was a BUY, we had fewer shares before → subtract
                # If it was a SELL, we had more shares before → add
                if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                    starting_positions[figi] -= quantity
                else:  # SELL
                    starting_positions[figi] += quantity

        return starting_positions

    def auto_detect_starting_positions(self, operations: List[Any]) -> Dict[str, int]:
        """
        Автоматически определяет наиболее вероятные начальные позиции
        на основе анализа первых операций для каждого FIGI

        Args:
            operations: Список операций

        Returns:
            Dict с предполагаемыми начальными позициями
        """
        if not operations:
            return {}

        # Группируем операции по FIGI
        figi_operations = defaultdict(list)
        for op in operations:
            if op.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                figi_operations[op.figi].append(op)

        detected_positions = {}

        for figi, ops in figi_operations.items():
            if not ops:
                continue

            # Сортируем операции по времени
            ops = sorted(ops, key=lambda x: x.date)
            first_op = ops[0]

            # Определяем наиболее вероятную начальную позицию
            if first_op.operation_type == OperationType.OPERATION_TYPE_BUY:
                # Первая операция - покупка
                # Наиболее вероятно, что это закрытие короткой позиции
                detected_positions[figi] = -first_op.quantity
            else:
                # Первая операция - продажа
                # Наиболее вероятно, что это закрытие длинной позиции
                detected_positions[figi] = first_op.quantity

        return detected_positions

    def process_operations_with_auto_positions(
        self, operations: List[Any]
    ) -> Tuple[List[Trade], float, List[Any], Dict[str, int]]:
        """
        Обрабатывает операции с автоматическим определением начальных позиций

        Args:
            operations: Список операций

        Returns:
            Tuple (trades, total_profit, operations, detected_starting_positions)
        """
        # Автоматически определяем начальные позиции
        starting_positions = self.auto_detect_starting_positions(operations)

        # Обрабатываем операции с новой непрерывной логикой
        trades, total_profit, processed_operations = self.process_operations_continuous(
            operations, starting_positions
        )

        return trades, total_profit, processed_operations, starting_positions

    def _assign_fees_to_trades(self):
        """Assign fees and variation margin to trades after all operations are processed"""
        if not self.completed_trades:
            return

        # Assign fees and variation margin to each trade individually
        for trade in self.completed_trades:
            # Find fees that should be assigned to this trade
            trade_fees = self._get_fees_for_trade_period(trade)

            # Find variation margin that occurred during this trade
            trade_margin = self._get_variation_margin_for_trade(trade)

            # Assign to trade
            trade.fees = trade_fees
            trade.net_profit = trade.gross_profit - trade.fees + trade_margin

    def _get_fees_for_trade_period(self, trade: Trade) -> float:
        """Get fees that should be assigned to a specific trade based on timing"""
        total_fees = 0.0

        # Convert trade times to original timezone for comparison
        entry_time_original = trade.entry_time - datetime.timedelta(
            hours=self.timezone_offset
        )
        exit_time_original = trade.exit_time - datetime.timedelta(
            hours=self.timezone_offset
        )

        # Look for unassigned fees that are close in time to this trade
        for fee in self.fees_buffer:
            if not fee["assigned"]:
                # Check if fee is within reasonable time window of the trade
                if (
                    entry_time_original <= fee["date"] <= exit_time_original
                    or
                    # 5 minutes
                    abs((fee["date"] - entry_time_original).total_seconds()) <= 300
                    or abs((fee["date"] - exit_time_original).total_seconds()) <= 300
                ):  # 5 minutes
                    total_fees += fee["amount"]
                    fee["assigned"] = True

        return total_fees

    def _get_variation_margin_for_trade(self, trade: Trade) -> float:
        """Get variation margin that occurred during a specific trade"""
        total_margin = 0.0

        # Convert trade times to original timezone for comparison
        entry_time_original = trade.entry_time - datetime.timedelta(
            hours=self.timezone_offset
        )
        exit_time_original = trade.exit_time - datetime.timedelta(
            hours=self.timezone_offset
        )

        # Look for unassigned margin operations that occurred during this trade
        for margin in self.margin_operations:
            if not margin["assigned"]:
                # Check if margin operation occurred during the trade period
                if entry_time_original <= margin["date"] <= exit_time_original:
                    total_margin += margin["amount"]
                    margin["assigned"] = True

        return total_margin

    def _process_single_operation(self, operation: Any):
        """Process a single operation"""
        if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
            self._process_buy_operation(operation)
        elif operation.operation_type == OperationType.OPERATION_TYPE_SELL:
            self._process_sell_operation(operation)
        elif operation.operation_type == OperationType.OPERATION_TYPE_BROKER_FEE:
            self._process_fee_operation(operation)
        elif operation.operation_type in [
            OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
            OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
        ]:
            self._process_margin_operation(operation)

    def _process_buy_operation(self, operation: Any):
        """Process a buy operation"""
        # Check if we have any open short positions that this buy can close
        buy_quantity = operation.quantity

        while buy_quantity > 0:
            # Find the oldest unprocessed short position
            short_position = self._find_oldest_short(operation.figi, buy_quantity)

            if not short_position:
                # No short position to close, this is a regular buy
                break

            # Calculate the quantity to close
            quantity_to_close = min(buy_quantity, short_position["quantity"])

            # Create a completed trade for the short position
            trade = self._create_trade(
                short_position, operation, quantity_to_close, "SHORT"
            )

            self.completed_trades.append(trade)

            # Update quantities
            buy_quantity -= quantity_to_close
            short_position["quantity"] -= quantity_to_close

            # Mark as processed if fully consumed
            if short_position["quantity"] == 0:
                short_position["processed"] = True

        # If there's remaining buy quantity, store it as a position
        if buy_quantity > 0:
            self.positions[operation.figi].append(
                {
                    "type": "BUY",
                    "operation": operation,
                    "quantity": buy_quantity,
                    "price": quotation_to_float(operation.price),
                    "payment": quotation_to_float(operation.payment),
                    "date": operation.date,
                    "processed": False,
                }
            )

    def _process_sell_operation(self, operation: Any):
        """Process a sell operation"""
        # Check if this is a short position first
        if not self.positions[operation.figi]:
            # This is a short sell - no prior buy positions
            self._handle_short_position(operation)
            return

        # Try to match with existing buy operations (FIFO)
        sell_quantity = operation.quantity
        sell_price = quotation_to_float(operation.price)

        while sell_quantity > 0:
            # Find the oldest unprocessed buy operation
            buy_operation = self._find_oldest_buy(operation.figi, sell_quantity)

            if not buy_operation:
                # No matching buy operation found, this might be a short position
                self._handle_short_position(operation)
                break

            # Calculate the quantity to close
            quantity_to_close = min(sell_quantity, buy_operation["quantity"])

            # Create a completed trade
            trade = self._create_trade(
                buy_operation, operation, quantity_to_close, "LONG"
            )

            self.completed_trades.append(trade)

            # Update quantities
            sell_quantity -= quantity_to_close
            buy_operation["quantity"] -= quantity_to_close

            # Mark as processed if fully consumed
            if buy_operation["quantity"] == 0:
                buy_operation["processed"] = True

    def _find_oldest_buy(self, figi: str, needed_quantity: int) -> Optional[Dict]:
        """Find the oldest unprocessed buy operation for a given figi"""
        for position in self.positions[figi]:
            if (
                position["type"] == "BUY"
                and not position["processed"]
                and position["quantity"] > 0
            ):
                return position
        return None

    def _find_oldest_short(self, figi: str, needed_quantity: int) -> Optional[Dict]:
        """Find the oldest unprocessed short position for a given figi"""
        for position in self.positions[figi]:
            if (
                position["type"] == "SELL"
                and not position["processed"]
                and position["quantity"] > 0
            ):
                return position
        return None

    def _handle_short_position(self, sell_operation: Any):
        """Handle short position (sell without prior buy)"""
        # Check if we have any buy operations for this figi that can close the short
        buy_operations = [
            p
            for p in self.positions[sell_operation.figi]
            if p["type"] == "BUY" and not p["processed"]
        ]

        if buy_operations:
            # We have buy operations that can close this short position
            return

        # This is a pure short position - store it for later matching
        self.positions[sell_operation.figi].append(
            {
                "type": "SELL",
                "operation": sell_operation,
                "quantity": sell_operation.quantity,
                "price": quotation_to_float(sell_operation.price),
                "payment": quotation_to_float(sell_operation.payment),
                "date": sell_operation.date,
                "processed": False,
            }
        )

    def _create_trade(
        self, buy_op: Dict, sell_op: Any, quantity: int, direction: str
    ) -> Trade:
        """Create a Trade object from buy and sell operations"""
        if direction == "LONG":
            # Standard long position: buy first, then sell
            buy_price = buy_op["price"]
            sell_price = quotation_to_float(sell_op.price)
            entry_time = buy_op["date"]
            exit_time = sell_op.date
            entry_operation_id = buy_op["operation"].id
            exit_operation_id = sell_op.id
        else:  # SHORT
            # Short position: sell first, then buy to close
            # Buy price is from the closing operation
            buy_price = quotation_to_float(sell_op.price)
            # Sell price is from the opening operation
            sell_price = buy_op["price"]
            # Entry time is when we opened the short
            entry_time = buy_op["date"]
            exit_time = sell_op.date  # Exit time is when we closed the short
            entry_operation_id = buy_op["operation"].id
            exit_operation_id = sell_op.id

        # Calculate gross profit
        if direction == "LONG":
            gross_profit = (sell_price - buy_price) * quantity
        else:  # SHORT
            gross_profit = (sell_price - buy_price) * quantity

        # Fees will be assigned later, set to 0 for now
        fees = 0.0

        # Calculate net profit (will be updated after fee assignment)
        net_profit = gross_profit - fees

        return Trade(
            trade_id=f"{entry_operation_id}_{exit_operation_id}",
            figi=sell_op.figi if direction == "LONG" else buy_op["operation"].figi,
            instrument_name=getattr(sell_op, "instrument_uid", sell_op.figi)
            if direction == "LONG"
            else buy_op["operation"].figi,
            entry_time=self.correct_timezone(entry_time),
            exit_time=self.correct_timezone(exit_time),
            entry_price=sell_price if direction == "SHORT" else buy_price,
            exit_price=buy_price if direction == "SHORT" else sell_price,
            quantity=quantity,
            direction=direction,
            gross_profit=gross_profit,
            fees=fees,
            net_profit=net_profit,
            entry_operation_id=entry_operation_id,
            exit_operation_id=exit_operation_id,
        )

    def _process_fee_operation(self, operation: Any):
        """Process fee operation"""
        self.fees_buffer.append(
            {
                "operation": operation,
                "amount": abs(quotation_to_float(operation.payment)),
                "date": operation.date,
                "assigned": False,
            }
        )

    def _process_margin_operation(self, operation: Any):
        """Process margin operation (variation margin)"""
        self.margin_operations.append(
            {
                "operation": operation,
                "amount": quotation_to_float(operation.payment),
                "date": operation.date,
                "assigned": False,
            }
        )

    def _get_fees_for_trade(self, buy_id: str, sell_id: str) -> float:
        """Get fees associated with a specific trade"""
        total_fees = 0.0

        # Look for fees that are close in time to the trade operations
        for fee in self.fees_buffer:
            if not fee["assigned"]:
                # Simple heuristic: assign fees to nearby trades
                # In a more sophisticated system, you might match fees by timestamp
                total_fees += fee["amount"]
                fee["assigned"] = True
                # Only assign one fee per trade for now
                break

        return total_fees

    def calculate_period_profit_real(
        self,
        operations: List[Any],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> float:
        """
        Calculate profit for a specific period using real data logic
        This matches the spreadsheet calculation method
        """
        # Ensure dates are timezone-aware if operations have timezone info
        if (
            operations
            and hasattr(operations[0], "date")
            and operations[0].date.tzinfo is not None
        ):
            # Operations have timezone info, ensure our dates do too
            if start_date.tzinfo is None:
                # Assume Moscow timezone (UTC+3)
                import pytz

                moscow_tz = pytz.timezone("Europe/Moscow")
                start_date = moscow_tz.localize(start_date)
            if end_date.tzinfo is None:
                import pytz

                moscow_tz = pytz.timezone("Europe/Moscow")
                end_date = moscow_tz.localize(end_date)

        # Filter operations for the period
        period_operations = [
            op for op in operations if start_date <= op.date <= end_date
        ]

        if not period_operations:
            return 0.0

        # Calculate period profit by summing all payments
        total_payment = 0.0

        for operation in period_operations:
            if operation.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
                OperationType.OPERATION_TYPE_BROKER_FEE,
                OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
            ]:
                payment = quotation_to_float(operation.payment)
                total_payment += payment

        return total_payment

    def calculate_period_profit(
        self,
        operations: List[Any],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        starting_balance: float = 0.0,
    ) -> PeriodProfit:
        """
        Calculate profit for a specific time period

        Args:
            operations: List of all operations
            start_date: Start of the period
            end_date: End of the period
            starting_balance: Starting balance for the period

        Returns:
            PeriodProfit object with detailed period analysis
        """
        # Filter operations for the period
        period_operations = [
            op for op in operations if start_date <= op.date <= end_date
        ]

        # Process operations for the period
        trades, total_profit, _ = self.process_operations(period_operations)

        # Calculate statistics
        total_fees = sum(trade.fees for trade in trades)
        net_profit = total_profit
        ending_balance = starting_balance + net_profit

        profit_percentage = (
            (net_profit / starting_balance * 100) if starting_balance > 0 else 0
        )

        winning_trades = len([t for t in trades if t.net_profit > 0])
        losing_trades = len([t for t in trades if t.net_profit < 0])

        return PeriodProfit(
            start_date=start_date,
            end_date=end_date,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_profit=total_profit,
            total_fees=total_fees,
            net_profit=net_profit,
            profit_percentage=profit_percentage,
            trades_count=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )

    def get_weekly_profit_analysis(self, operations: List[Any]) -> List[PeriodProfit]:
        """Get weekly profit analysis"""
        if not operations:
            return []

        # Sort operations by date
        sorted_ops = sorted(operations, key=lambda x: x.date)

        # Find the date range
        start_date = sorted_ops[0].date
        end_date = sorted_ops[-1].date

        # Generate weekly periods
        periods = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Find the Monday of the first week
        days_since_monday = current_date.weekday()
        week_start = current_date - datetime.timedelta(days=days_since_monday)

        starting_balance = 0.0

        while week_start <= end_date:
            week_end = week_start + datetime.timedelta(
                days=6, hours=23, minutes=59, seconds=59
            )

            if week_end > end_date:
                week_end = end_date

            period_profit = self.calculate_period_profit(
                operations, week_start, week_end, starting_balance
            )

            periods.append(period_profit)
            starting_balance = period_profit.ending_balance
            week_start += datetime.timedelta(days=7)

        return periods

    def get_monthly_profit_analysis(self, operations: List[Any]) -> List[PeriodProfit]:
        """Get monthly profit analysis"""
        if not operations:
            return []

        # Sort operations by date
        sorted_ops = sorted(operations, key=lambda x: x.date)

        # Find the date range
        start_date = sorted_ops[0].date
        end_date = sorted_ops[-1].date

        # Generate monthly periods
        periods = []
        current_year = start_date.year
        current_month = start_date.month

        starting_balance = 0.0

        while True:
            month_start = datetime.datetime(current_year, current_month, 1)

            # Calculate last day of month
            if current_month == 12:
                next_month = datetime.datetime(current_year + 1, 1, 1)
            else:
                next_month = datetime.datetime(current_year, current_month + 1, 1)

            month_end = next_month - datetime.timedelta(seconds=1)

            if month_start > end_date:
                break

            if month_end > end_date:
                month_end = end_date

            period_profit = self.calculate_period_profit(
                operations, month_start, month_end, starting_balance
            )

            periods.append(period_profit)
            starting_balance = period_profit.ending_balance

            # Move to next month
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1

        return periods

    def _group_operations_into_sessions(
        self, trading_operations: List[Any], starting_positions: Dict[str, int] = None
    ):
        """
        Group trading operations into trading sessions.

        Session logic:
        - Session starts with a SELL operation (entry into short position)
        - Session can have multiple SELL operations (pyramiding)
        - Session ends with BUY operation(s) that close the position
        - Sessions are created per FIGI

        Args:
            trading_operations: List of trading operations
            starting_positions: Dict mapping FIGI to starting position (default: empty positions)
        """
        if starting_positions is None:
            starting_positions = {}

        # Group operations by FIGI
        figi_operations = defaultdict(list)
        for op in trading_operations:
            figi_operations[op.figi].append(op)

        # Process each FIGI separately
        for figi, operations in figi_operations.items():
            starting_pos = starting_positions.get(figi, 0)
            self._create_sessions_for_figi(figi, operations, starting_pos)

    def _create_sessions_for_figi(
        self, figi: str, operations: List[Any], starting_position: int = 0
    ):
        """Create trading sessions for a specific FIGI using universal position tracking"""
        operations = sorted(operations, key=lambda x: x.date)

        current_position = starting_position  # Start with actual position instead of 0
        current_session = None

        for operation in operations:
            operation_qty = operation.quantity

            # Determine operation direction
            if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                # Buying increases position
                new_position = current_position + operation_qty
                current_session = self._process_position_change(
                    figi,
                    operation,
                    current_position,
                    new_position,
                    operation_qty,
                    True,
                    current_session,
                )
                current_position = new_position

            elif operation.operation_type == OperationType.OPERATION_TYPE_SELL:
                # Selling decreases position
                new_position = current_position - operation_qty
                current_session = self._process_position_change(
                    figi,
                    operation,
                    current_position,
                    new_position,
                    operation_qty,
                    False,
                    current_session,
                )
                current_position = new_position

        # If there's an active session, finalize it only if it's a completed round-trip
        if current_session is not None:
            # Only finalize if we have both buys and sells (completed round trip)
            if (
                current_session["total_quantity_bought"] > 0
                and current_session["total_quantity_sold"] > 0
            ):
                self._finalize_session(current_session)
                self.trading_sessions.append(current_session)
            # Note: Open positions are not included in completed sessions

    def _process_position_change(
        self,
        figi: str,
        operation: Any,
        old_position: int,
        new_position: int,
        operation_qty: int,
        is_buy: bool,
        current_session: Dict[str, Any],
    ):
        """Process position change and create/update sessions accordingly"""

        # Check if position crosses zero (session boundary)
        if (old_position > 0 and new_position < 0) or (
            old_position < 0 and new_position > 0
        ):
            # Position crosses zero - need to split the operation

            # Calculate quantity that closes current position
            closing_qty = abs(old_position)
            remaining_qty = operation_qty - closing_qty

            # Close current session with closing quantity
            if current_session is not None:
                if is_buy:
                    self._add_buy_to_session(current_session, operation, closing_qty)
                else:
                    self._add_sell_to_session(current_session, operation, closing_qty)

                self._finalize_session(current_session)
                self.trading_sessions.append(current_session)

            # Start new session with remaining quantity
            if remaining_qty > 0:
                new_session = self._start_new_session(figi, operation)
                if is_buy:
                    self._add_buy_to_session(new_session, operation, remaining_qty)
                else:
                    self._add_sell_to_session(new_session, operation, remaining_qty)
                current_session = new_session

        elif old_position == 0:
            # Starting from zero position - start new session
            current_session = self._start_new_session(figi, operation)
            if is_buy:
                self._add_buy_to_session(current_session, operation, operation_qty)
            else:
                self._add_sell_to_session(current_session, operation, operation_qty)

        else:
            # Continuing in same direction - add to current session
            if current_session is None:
                current_session = self._start_new_session(figi, operation)

            if is_buy:
                self._add_buy_to_session(current_session, operation, operation_qty)
            else:
                self._add_sell_to_session(current_session, operation, operation_qty)

        return current_session

    def _add_buy_to_session(
        self, session: Dict[str, Any], operation: Any, quantity: int
    ):
        """Add buy operation to session"""
        # Calculate proportional payment based on quantity
        total_payment = abs(quotation_to_float(operation.payment))
        proportional_payment = total_payment * quantity / operation.quantity

        # Create operation record
        op_record = {
            "id": operation.id,
            "type": operation.operation_type,
            "date": operation.date,
            "quantity": quantity,
            "price": quotation_to_float(operation.price),
            "payment": -proportional_payment,  # Negative for buy
        }

        session["operations"].append(op_record)
        session["total_quantity_bought"] += quantity
        session["total_buy_amount"] += proportional_payment
        session["end_time"] = operation.date

    def _add_sell_to_session(
        self, session: Dict[str, Any], operation: Any, quantity: int
    ):
        """Add sell operation to session"""
        # Calculate proportional payment based on quantity
        total_payment = abs(quotation_to_float(operation.payment))
        proportional_payment = total_payment * quantity / operation.quantity

        # Create operation record
        op_record = {
            "id": operation.id,
            "type": operation.operation_type,
            "date": operation.date,
            "quantity": quantity,
            "price": quotation_to_float(operation.price),
            "payment": proportional_payment,  # Positive for sell
        }

        session["operations"].append(op_record)
        session["total_quantity_sold"] += quantity
        session["total_sell_amount"] += proportional_payment
        session["end_time"] = operation.date

    def _start_new_session(self, figi: str, first_operation: Any) -> Dict[str, Any]:
        """Start a new trading session"""
        return {
            "session_id": f"{figi}_{first_operation.date.strftime('%Y%m%d_%H%M%S')}_{first_operation.id}",
            "figi": figi,
            "instrument_name": getattr(first_operation, "instrument_uid", figi),
            "start_time": first_operation.date,
            "end_time": first_operation.date,
            "operations": [],
            "total_quantity_sold": 0,
            "total_quantity_bought": 0,
            "total_sell_amount": 0.0,
            "total_buy_amount": 0.0,
            "direction": "UNKNOWN",  # Will be determined by first operation
        }

    def _convert_operation_to_dict(self, operation: Any) -> Dict[str, Any]:
        """Convert operation to dictionary for storage"""
        return {
            "id": operation.id,
            "type": operation.operation_type,
            "date": operation.date,
            "quantity": operation.quantity,
            "price": quotation_to_float(operation.price),
            "payment": quotation_to_float(operation.payment),
        }

    def _finalize_session(self, session: Dict[str, Any]):
        """Finalize session by calculating profit and assigning fees/margin"""
        # Determine session direction based on operations
        if session["total_quantity_sold"] > 0 and session["total_quantity_bought"] > 0:
            # Session has both sells and buys - it's a completed round trip
            if session["operations"][0]["type"] == OperationType.OPERATION_TYPE_SELL:
                session["direction"] = "SHORT"  # Started with sell
            else:
                session["direction"] = "LONG"  # Started with buy
        else:
            # Incomplete session - determine by what we have
            if session["total_quantity_sold"] > 0:
                session["direction"] = "SHORT"
            else:
                session["direction"] = "LONG"

        # Calculate gross profit
        # For completed sessions: profit = total_sell_amount - total_buy_amount
        session["gross_profit"] = (
            session["total_sell_amount"] - session["total_buy_amount"]
        )

        # Assign fees for this session
        session["fees"] = self._get_fees_for_session(session)

        # Assign variation margin for this session
        session["variation_margin"] = self._get_variation_margin_for_session(session)

        # Calculate net profit
        session["net_profit"] = (
            session["gross_profit"] - session["fees"] + session["variation_margin"]
        )

    def _get_fees_for_session(self, session: Dict[str, Any]) -> float:
        """Get fees that should be assigned to a specific session"""
        total_fees = 0.0

        # Convert session times to original timezone for comparison
        start_time_original = session["start_time"] - datetime.timedelta(
            hours=self.timezone_offset
        )
        end_time_original = session["end_time"] - datetime.timedelta(
            hours=self.timezone_offset
        )

        # Look for unassigned fees that are close in time to this session
        for fee in self.fees_buffer:
            if not fee["assigned"]:
                # Check if fee is within the session time window or very close
                fee_date = fee["date"]
                fee_figi = getattr(fee["operation"], "figi", None)

                time_match = (
                    start_time_original <= fee_date <= end_time_original
                    or
                    # 5 minutes
                    abs((fee_date - start_time_original).total_seconds()) <= 300
                    or abs((fee_date - end_time_original).total_seconds()) <= 300
                )  # 5 minutes

                # If fee has FIGI, check if it matches session FIGI, otherwise assign by time
                figi_match = (
                    fee_figi is None or fee_figi == session["figi"] or fee_figi == ""
                )

                if time_match and figi_match:
                    total_fees += fee["amount"]
                    fee["assigned"] = True

        return total_fees

    def _get_variation_margin_for_session(self, session: Dict[str, Any]) -> float:
        """Get variation margin that occurred during a specific session"""
        total_margin = 0.0

        # Convert session times to original timezone for comparison
        start_time_original = session["start_time"] - datetime.timedelta(
            hours=self.timezone_offset
        )
        end_time_original = session["end_time"] - datetime.timedelta(
            hours=self.timezone_offset
        )

        # Look for unassigned margin operations that occurred during this session
        for margin in self.margin_operations:
            if not margin["assigned"]:
                # Check if margin operation occurred during the session period
                margin_date = margin["date"]
                margin_figi = getattr(margin["operation"], "figi", None)

                time_match = start_time_original <= margin_date <= end_time_original

                # Variation margin typically doesn't have FIGI or has empty FIGI
                # so we assign by time only
                figi_match = (
                    margin_figi is None
                    or margin_figi == ""
                    or margin_figi == session["figi"]
                )

                if time_match and figi_match:
                    total_margin += margin["amount"]
                    margin["assigned"] = True

        return total_margin

    def _convert_sessions_to_trades(self):
        """Convert trading sessions to Trade objects for backward compatibility"""
        for session in self.trading_sessions:
            # For sessions, we'll create a single Trade object representing the entire session
            trade = self._create_trade_from_session(session)
            self.completed_trades.append(trade)

    def _create_trade_from_session(self, session: Dict[str, Any]) -> Trade:
        """Create a Trade object from a trading session"""
        # Calculate average prices
        avg_sell_price = (
            session["total_sell_amount"] / session["total_quantity_sold"]
            if session["total_quantity_sold"] > 0
            else 0
        )
        avg_buy_price = (
            session["total_buy_amount"] / session["total_quantity_bought"]
            if session["total_quantity_bought"] > 0
            else 0
        )

        # For display purposes, use the total quantity (should be equal for closed sessions)
        # or total_quantity_bought, should be same
        quantity = session["total_quantity_sold"]

        # Create session data
        session_data = TradingSession(
            session_id=session["session_id"],
            figi=session["figi"],
            instrument_name=session["instrument_name"],
            start_time=self.correct_timezone(session["start_time"]),
            end_time=self.correct_timezone(session["end_time"]),
            operations=session["operations"],
            total_quantity_sold=session["total_quantity_sold"],
            total_quantity_bought=session["total_quantity_bought"],
            total_sell_amount=session["total_sell_amount"],
            total_buy_amount=session["total_buy_amount"],
            gross_profit=session["gross_profit"],
            fees=session["fees"],
            variation_margin=session["variation_margin"],
            net_profit=session["net_profit"],
            direction=session["direction"],
        )

        # Create Trade object
        trade = Trade(
            trade_id=session["session_id"],
            figi=session["figi"],
            instrument_name=session["instrument_name"],
            entry_time=self.correct_timezone(session["start_time"]),
            exit_time=self.correct_timezone(session["end_time"]),
            entry_price=avg_sell_price,  # For SHORT: entry is sell price
            exit_price=avg_buy_price,  # For SHORT: exit is buy price
            quantity=quantity,
            direction=session["direction"],
            gross_profit=session["gross_profit"],
            fees=session["fees"],
            net_profit=session["net_profit"],
            entry_operation_id=session["operations"][0]["id"],
            exit_operation_id=session["operations"][-1]["id"],
            session_data=session_data,
            variation_margin=session["variation_margin"],
        )

        return trade

    def get_enhanced_profit_analysis(
        self, operations: List[Any], current_positions: Dict[str, int] = None
    ) -> Tuple[List[Trade], float, List[Any], Dict[str, int], Dict[str, Any]]:
        """
        Enhanced profit analysis with comprehensive position tracking

        This method provides the most accurate profit calculation by:
        1. Using current positions to calculate starting positions
        2. Providing detailed analysis of potential issues
        3. Offering recommendations for data quality

        Args:
            operations: List of operations to analyze
            current_positions: Current positions {FIGI: quantity}

        Returns:
            Tuple of (trades, total_profit, operations, starting_positions, analysis_report)
        """
        if not operations:
            return [], 0.0, [], {}, {}

        # Sort operations by date
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Calculate starting positions if current positions are provided
        if current_positions:
            starting_positions = self.calculate_starting_positions_from_current(
                sorted_operations, current_positions
            )
        else:
            starting_positions = self.auto_detect_starting_positions(sorted_operations)

        # Process with calculated starting positions
        trades, total_profit, processed_operations = (
            self.process_operations_with_starting_positions(
                sorted_operations, starting_positions
            )
        )

        # Generate analysis report
        analysis_report = self._generate_analysis_report(
            sorted_operations, starting_positions, trades, current_positions
        )

        return (
            trades,
            total_profit,
            processed_operations,
            starting_positions,
            analysis_report,
        )

    def _generate_analysis_report(
        self,
        operations: List[Any],
        starting_positions: Dict[str, int],
        trades: List[Trade],
        current_positions: Dict[str, int] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        from collections import defaultdict

        report = {
            "summary": {},
            "position_analysis": {},
            "data_quality": {},
            "recommendations": [],
        }

        # Summary
        report["summary"] = {
            "total_operations": len(operations),
            "total_trades": len(trades),
            "total_profit": sum(trade.net_profit for trade in trades),
            "instruments_traded": len(
                set(op.figi for op in operations if hasattr(op, "figi"))
            ),
            "starting_positions_count": len(starting_positions),
            "period_start": operations[0].date if operations else None,
            "period_end": operations[-1].date if operations else None,
        }

        # Position analysis
        position_analysis = defaultdict(dict)
        for figi, starting_pos in starting_positions.items():
            position_analysis[figi]["starting_position"] = starting_pos
            position_analysis[figi]["current_position"] = (
                current_positions.get(figi, 0) if current_positions else "unknown"
            )

            # Find first and last operations for this FIGI
            figi_ops = [
                op for op in operations if hasattr(op, "figi") and op.figi == figi
            ]
            if figi_ops:
                first_op = figi_ops[0]
                last_op = figi_ops[-1]
                position_analysis[figi]["first_operation"] = {
                    "type": "BUY"
                    if first_op.operation_type == OperationType.OPERATION_TYPE_BUY
                    else "SELL",
                    "quantity": first_op.quantity,
                    "date": first_op.date,
                }
                position_analysis[figi]["last_operation"] = {
                    "type": "BUY"
                    if last_op.operation_type == OperationType.OPERATION_TYPE_BUY
                    else "SELL",
                    "quantity": last_op.quantity,
                    "date": last_op.date,
                }
                position_analysis[figi]["total_operations"] = len(figi_ops)

        report["position_analysis"] = dict(position_analysis)

        # Data quality assessment
        quality_issues = []
        large_losses = [trade for trade in trades if trade.net_profit < -50000]
        if large_losses:
            quality_issues.append(
                f"Found {len(large_losses)} trades with unusually large losses (< -50,000)"
            )

        # Check for potential starting position issues
        for figi, analysis in position_analysis.items():
            if (
                analysis.get("first_operation", {}).get("type") == "SELL"
                and starting_positions.get(figi, 0) <= 0
            ):
                quality_issues.append(
                    f"FIGI {figi}: First operation is SELL but starting position is {starting_positions.get(figi, 0)}"
                )

        report["data_quality"] = {
            "issues_found": len(quality_issues),
            "issues": quality_issues,
            "data_completeness": "partial" if not current_positions else "complete",
        }

        # Recommendations
        recommendations = []
        if quality_issues:
            recommendations.append(
                "Consider using current positions to calculate more accurate starting positions"
            )
        if not current_positions:
            recommendations.append(
                "Provide current positions for the most accurate analysis"
            )
        if large_losses:
            recommendations.append(
                "Review trades with large losses - they may indicate missing position data"
            )

        report["recommendations"] = recommendations

        return report

    def validate_position_consistency(
        self,
        operations: List[Any],
        starting_positions: Dict[str, int],
        current_positions: Dict[str, int] = None,
    ) -> Dict[str, Any]:
        """
        Validate position consistency by simulating all operations

        Args:
            operations: List of operations
            starting_positions: Starting positions
            current_positions: Current positions (optional)

        Returns:
            Dict with validation results
        """
        if not operations:
            return {"valid": True, "issues": []}

        # Simulate position changes
        simulated_positions = starting_positions.copy()
        issues = []

        for op in sorted(operations, key=lambda x: x.date):
            if op.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                figi = op.figi
                quantity = op.quantity

                if figi not in simulated_positions:
                    simulated_positions[figi] = 0

                if op.operation_type == OperationType.OPERATION_TYPE_BUY:
                    simulated_positions[figi] += quantity
                else:  # SELL
                    simulated_positions[figi] -= quantity

        # Check consistency with current positions if provided
        if current_positions:
            for figi, expected_pos in current_positions.items():
                simulated_pos = simulated_positions.get(figi, 0)
                if simulated_pos != expected_pos:
                    issues.append(
                        f"FIGI {figi}: Expected {expected_pos}, got {simulated_pos}"
                    )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "final_simulated_positions": simulated_positions,
            "expected_positions": current_positions or {},
        }

    def get_position_history(
        self, operations: List[Any], starting_positions: Dict[str, int] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get position history for each FIGI throughout the operations

        Args:
            operations: List of operations
            starting_positions: Starting positions

        Returns:
            Dict mapping FIGI to list of position snapshots
        """
        if starting_positions is None:
            starting_positions = {}

        position_history = defaultdict(list)
        current_positions = starting_positions.copy()

        # Add initial positions
        for figi, pos in starting_positions.items():
            position_history[figi].append(
                {
                    "date": operations[0].date if operations else None,
                    "position": pos,
                    "operation_type": "INITIAL",
                    "operation_id": None,
                }
            )

        # Process each operation
        for op in sorted(operations, key=lambda x: x.date):
            if op.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                figi = op.figi
                quantity = op.quantity

                if figi not in current_positions:
                    current_positions[figi] = 0

                old_position = current_positions[figi]

                if op.operation_type == OperationType.OPERATION_TYPE_BUY:
                    current_positions[figi] += quantity
                else:  # SELL
                    current_positions[figi] -= quantity

                position_history[figi].append(
                    {
                        "date": op.date,
                        "position": current_positions[figi],
                        "position_change": current_positions[figi] - old_position,
                        "operation_type": "BUY"
                        if op.operation_type == OperationType.OPERATION_TYPE_BUY
                        else "SELL",
                        "operation_id": op.id,
                        "quantity": quantity,
                        "crosses_zero": (
                            old_position > 0 and current_positions[figi] <= 0
                        )
                        or (old_position < 0 and current_positions[figi] >= 0),
                    }
                )

        return dict(position_history)

    def detect_problematic_trades(
        self, trades: List[Trade], threshold: float = -10000
    ) -> List[Dict[str, Any]]:
        """
        Detect trades that might have calculation issues

        Args:
            trades: List of trades
            threshold: Profit threshold below which trades are considered problematic

        Returns:
            List of problematic trades with analysis
        """
        problematic = []

        for trade in trades:
            if trade.net_profit < threshold:
                issue_analysis = {
                    "trade": trade,
                    "issues": [],
                    "severity": "high" if trade.net_profit < -50000 else "medium",
                }

                # Check for common issues
                if trade.direction == "SHORT" and trade.entry_price < trade.exit_price:
                    issue_analysis["issues"].append(
                        "Short position with entry price < exit price"
                    )

                if trade.direction == "LONG" and trade.entry_price > trade.exit_price:
                    issue_analysis["issues"].append(
                        "Long position with entry price > exit price"
                    )

                if abs(trade.gross_profit) > 100000:
                    issue_analysis["issues"].append(
                        "Unusually large gross profit magnitude"
                    )

                if not issue_analysis["issues"]:
                    issue_analysis["issues"].append(
                        "Large loss with no obvious cause - check starting positions"
                    )

                problematic.append(issue_analysis)

        return problematic

    def process_operations_continuous(
        self, operations: List[Any], starting_positions: Dict[str, int] = None
    ) -> Tuple[List[Trade], float, List[Any]]:
        """
        Обрабатывает операции с непрерывной логикой - каждая операция участвует в сделке

        Args:
            operations: Список операций
            starting_positions: Начальные позиции {FIGI: количество}

        Returns:
            Tuple (trades, total_profit, processed_operations)
        """
        if not operations:
            return [], 0.0, []

        if starting_positions is None:
            starting_positions = {}

        self.reset()

        # Сортируем операции по времени
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Отделяем торговые операции от комиссий и вармаржи
        trading_operations = []
        for operation in sorted_operations:
            if operation.operation_type == OperationType.OPERATION_TYPE_BROKER_FEE:
                self._process_fee_operation(operation)
            elif operation.operation_type in [
                OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
            ]:
                self._process_margin_operation(operation)
            elif operation.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
            ]:
                trading_operations.append(operation)

        # Обрабатываем торговые операции непрерывно
        trades = self._process_continuous_trading(
            trading_operations, starting_positions
        )

        # Назначаем комиссии и вармаржу
        self._assign_fees_and_margin_to_trades(trades)

        # Рассчитываем общую прибыль
        total_profit = sum(trade.net_profit for trade in trades)

        return trades, total_profit, sorted_operations

    def _process_continuous_trading(
        self, operations: List[Any], starting_positions: Dict[str, int]
    ) -> List[Trade]:
        """
        Обрабатывает торговые операции непрерывно, создавая сделки при пересечении нулевой позиции

        Args:
            operations: Отсортированные торговые операции
            starting_positions: Начальные позиции

        Returns:
            Список завершенных сделок
        """
        if not operations:
            return []

        # Группируем операции по FIGI
        figi_operations = defaultdict(list)
        for op in operations:
            figi_operations[op.figi].append(op)

        all_trades = []

        # Обрабатываем каждый FIGI отдельно
        for figi, figi_ops in figi_operations.items():
            starting_pos = starting_positions.get(figi, 0)
            figi_trades = self._process_figi_continuous(figi, figi_ops, starting_pos)
            all_trades.extend(figi_trades)

        # Сортируем сделки по времени завершения
        all_trades.sort(key=lambda x: x.exit_time)

        return all_trades

    def _process_figi_continuous(
        self, figi: str, operations: List[Any], starting_position: int
    ) -> List[Trade]:
        """
        Обрабатывает операции для одного FIGI непрерывно

        Args:
            figi: FIGI инструмента
            operations: Операции для этого FIGI
            starting_position: Начальная позиция

        Returns:
            Список сделок для этого FIGI
        """
        if not operations:
            return []

        trades = []
        current_position = starting_position
        current_trade_operations = []  # Операции текущей сделки

        # Если начальная позиция не ноль, создаем первую "виртуальную" операцию
        if starting_position != 0:
            # Создаем виртуальную операцию открытия позиции
            first_op = operations[0]
            virtual_op = {
                "id": f"virtual_start_{figi}",
                "type": OperationType.OPERATION_TYPE_BUY
                if starting_position > 0
                else OperationType.OPERATION_TYPE_SELL,
                # Чуть раньше первой операции
                "date": first_op.date - datetime.timedelta(microseconds=1),
                "quantity": abs(starting_position),
                "price": 0.0,  # Цена неизвестна
                "payment": 0.0,  # Платеж неизвестен
                "virtual": True,
            }
            current_trade_operations.append(virtual_op)

        for operation in operations:
            # Добавляем операцию в текущую сделку
            op_dict = {
                "id": operation.id,
                "type": operation.operation_type,
                "date": operation.date,
                "quantity": operation.quantity,
                "price": quotation_to_float(operation.price),
                "payment": quotation_to_float(operation.payment),
                "virtual": False,
            }
            current_trade_operations.append(op_dict)

            # Обновляем позицию
            if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                new_position = current_position + operation.quantity
            else:  # SELL
                new_position = current_position - operation.quantity

            # Проверяем, пересекает ли позиция ноль
            if self._crosses_zero(current_position, new_position):
                # Создаем сделку
                trade = self._create_trade_from_operations(
                    figi, current_trade_operations, current_position, new_position
                )
                if trade:
                    trades.append(trade)

                # Начинаем новую сделку
                current_trade_operations = []

                # Если позиция не стала нулевой, добавляем операцию в новую сделку
                if new_position != 0:
                    current_trade_operations.append(op_dict)

            current_position = new_position

        # Если остались незавершенные операции, создаем открытую позицию (не включаем в сделки)
        # В соответствии с требованием, что сделки должны быть завершенными

        return trades

    def _crosses_zero(self, old_position: int, new_position: int) -> bool:
        """
        Проверяет, пересекает ли позиция ноль

        Args:
            old_position: Старая позиция
            new_position: Новая позиция

        Returns:
            True, если позиция пересекает ноль
        """
        # Позиция пересекает ноль если:
        # - была положительной и стала отрицательной
        # - была отрицательной и стала положительной
        # - была ненулевой и стала нулевой
        return (old_position > 0 and new_position <= 0) or (
            old_position < 0 and new_position >= 0
        )

    def _create_trade_from_operations(
        self, figi: str, operations: List[Dict], start_position: int, end_position: int
    ) -> Optional[Trade]:
        """
        Создает сделку из списка операций

        Args:
            figi: FIGI инструмента
            operations: Список операций сделки
            start_position: Начальная позиция
            end_position: Конечная позиция

        Returns:
            Объект Trade или None
        """
        if not operations:
            return None

        # Определяем направление сделки
        if start_position > 0:
            direction = "LONG"  # Закрываем длинную позицию
        elif start_position < 0:
            direction = "SHORT"  # Закрываем короткую позицию
        else:
            # Начинаем с нуля - определяем по первой операции
            first_op = operations[0]
            if first_op["type"] == OperationType.OPERATION_TYPE_BUY:
                direction = "LONG"
            else:
                direction = "SHORT"

        # Находим первую и последнюю реальные операции
        real_operations = [op for op in operations if not op.get("virtual", False)]
        if not real_operations:
            return None

        first_op = real_operations[0]
        last_op = real_operations[-1]

        # Рассчитываем количество сделки
        quantity = abs(start_position) if start_position != 0 else abs(end_position)
        if quantity == 0:
            # Рассчитываем как сумму всех операций
            total_buy_qty = sum(
                op["quantity"]
                for op in real_operations
                if op["type"] == OperationType.OPERATION_TYPE_BUY
            )
            total_sell_qty = sum(
                op["quantity"]
                for op in real_operations
                if op["type"] == OperationType.OPERATION_TYPE_SELL
            )
            quantity = min(total_buy_qty, total_sell_qty)

        if quantity == 0:
            return None

        # Рассчитываем средние цены
        buy_operations = [
            op
            for op in real_operations
            if op["type"] == OperationType.OPERATION_TYPE_BUY
        ]
        sell_operations = [
            op
            for op in real_operations
            if op["type"] == OperationType.OPERATION_TYPE_SELL
        ]

        if buy_operations and sell_operations:
            # Рассчитываем средневзвешенные цены
            total_buy_amount = sum(abs(op["payment"]) for op in buy_operations)
            total_buy_quantity = sum(op["quantity"] for op in buy_operations)
            avg_buy_price = (
                total_buy_amount / total_buy_quantity if total_buy_quantity > 0 else 0
            )

            total_sell_amount = sum(abs(op["payment"]) for op in sell_operations)
            total_sell_quantity = sum(op["quantity"] for op in sell_operations)
            avg_sell_price = (
                total_sell_amount / total_sell_quantity
                if total_sell_quantity > 0
                else 0
            )

            # Рассчитываем прибыль
            if direction == "LONG":
                entry_price = avg_buy_price
                exit_price = avg_sell_price
                gross_profit = (exit_price - entry_price) * quantity
            else:  # SHORT
                entry_price = avg_sell_price
                exit_price = avg_buy_price
                gross_profit = (entry_price - exit_price) * quantity

        elif buy_operations:
            # Только покупки - используем первую и последнюю
            entry_price = buy_operations[0]["price"]
            exit_price = buy_operations[-1]["price"]
            gross_profit = (exit_price - entry_price) * quantity
            direction = "LONG"

        elif sell_operations:
            # Только продажи - используем первую и последнюю
            entry_price = sell_operations[0]["price"]
            exit_price = sell_operations[-1]["price"]
            gross_profit = (entry_price - exit_price) * quantity
            direction = "SHORT"

        else:
            return None

        # Создаем сделку
        trade = Trade(
            trade_id=f"{figi}_{first_op['id']}_{last_op['id']}",
            figi=figi,
            instrument_name=figi,
            entry_time=self.correct_timezone(first_op["date"]),
            exit_time=self.correct_timezone(last_op["date"]),
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            direction=direction,
            gross_profit=gross_profit,
            fees=0.0,  # Будет назначена позже
            net_profit=gross_profit,  # Будет пересчитана после назначения комиссий
            entry_operation_id=first_op["id"],
            exit_operation_id=last_op["id"],
            variation_margin=0.0,  # Будет назначена позже
        )

        return trade

    def _assign_fees_and_margin_to_trades(self, trades: List[Trade]):
        """
        Назначает комиссии и вариационную маржу сделкам

        Args:
            trades: Список сделок
        """
        if not trades:
            return

        # Назначаем комиссии пропорционально времени сделок
        total_fees = sum(fee["amount"] for fee in self.fees_buffer)
        total_margin = sum(margin["amount"] for margin in self.margin_operations)

        if total_fees > 0:
            # Распределяем комиссии пропорционально прибыли сделок
            total_gross_profit = sum(abs(trade.gross_profit) for trade in trades)
            if total_gross_profit > 0:
                for trade in trades:
                    trade.fees = (
                        total_fees * abs(trade.gross_profit) / total_gross_profit
                    )
            else:
                # Если нет прибыли, распределяем равномерно
                fees_per_trade = total_fees / len(trades)
                for trade in trades:
                    trade.fees = fees_per_trade

        if total_margin != 0:
            # Распределяем вариационную маржу пропорционально времени
            for trade in trades:
                trade.variation_margin = total_margin / len(trades)

        # Пересчитываем чистую прибыль
        for trade in trades:
            trade.net_profit = trade.gross_profit - trade.fees + trade.variation_margin
