#!/usr/bin/env python3
"""
Проверка данных за апрель 2024
"""

import asyncio
import datetime
import logging
from app.client import client
from app.settings import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)-5s] %(asctime)-19s %(name)s:%(lineno)d: %(message)s"
)
logger = logging.getLogger(__name__)


async def check_april_data():
    """Проверяет данные за апрель 2024"""

    try:
        # Инициализируем клиент
        await client.ainit()

        logger.info("=== ПРОВЕРКА ДАННЫХ ЗА АПРЕЛЬ 2024 ===")

        # Тест: Проверка данных за апрель 2024
        logger.info("\nПроверка данных за апрель 2024")

        start_date = datetime.datetime(2024, 4, 1)
        end_date = datetime.datetime(2024, 4, 30, 23, 59, 59)

        # Добавляем timezone
        import pytz
        start_date = pytz.UTC.localize(start_date)
        end_date = pytz.UTC.localize(end_date)

        try:
            operations_april = await client.get_all_operations_for_period(
                account_id=settings.account_id,
                start_date=start_date,
                end_date=end_date
            )

            logger.info(f"Операций за апрель 2024: {len(operations_april)}")

            if operations_april:
                logger.info("✅ Данные за апрель 2024 доступны!")
                logger.info("Операции за апрель 2024:")
                for i, op in enumerate(operations_april):
                    # Правильная обработка атрибутов операции
                    op_type = getattr(op, 'type', getattr(
                        op, 'operation_type', 'unknown'))
                    op_amount = getattr(
                        op, 'amount', getattr(op, 'payment', 0))

                    # Конвертируем MoneyValue в число если нужно
                    if hasattr(op_amount, 'units') and hasattr(op_amount, 'nano'):
                        amount_value = op_amount.units + op_amount.nano / 1e9
                    else:
                        amount_value = float(op_amount) if op_amount else 0

                    logger.info(
                        f"  {i+1}. {op.date} - {op_type} - {amount_value:,.2f} ₽")
            else:
                logger.info("❌ Нет операций за апрель 2024 в API")

        except Exception as e:
            logger.error(f"❌ Ошибка при получении операций за апрель: {e}")
            import traceback
            traceback.print_exc()

        # Дополнительная проверка: сравнение с мартом и маем
        logger.info("\nДополнительная проверка:")

        # Март 2024
        start_date_march = datetime.datetime(2024, 3, 1)
        end_date_march = datetime.datetime(2024, 3, 31, 23, 59, 59)
        start_date_march = pytz.UTC.localize(start_date_march)
        end_date_march = pytz.UTC.localize(end_date_march)

        try:
            operations_march = await client.get_all_operations_for_period(
                account_id=settings.account_id,
                start_date=start_date_march,
                end_date=end_date_march
            )
            logger.info(f"Операций за март 2024: {len(operations_march)}")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении операций за март: {e}")

        # Май 2024 (уже знаем, что данных нет)
        start_date_may = datetime.datetime(2024, 5, 1)
        end_date_may = datetime.datetime(2024, 5, 31, 23, 59, 59)
        start_date_may = pytz.UTC.localize(start_date_may)
        end_date_may = pytz.UTC.localize(end_date_may)

        try:
            operations_may = await client.get_all_operations_for_period(
                account_id=settings.account_id,
                start_date=start_date_may,
                end_date=end_date_may
            )
            logger.info(f"Операций за май 2024: {len(operations_may)}")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении операций за май: {e}")

        logger.info("\n=== ПРОВЕРКА ЗАВЕРШЕНА ===")

    except Exception as e:
        logger.error(f"Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_april_data())
