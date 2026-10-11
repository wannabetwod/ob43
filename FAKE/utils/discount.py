"""Расчёт скидки 25% для товаров без заказов за прошлый месяц"""
from datetime import date, timedelta
from db import fetch_one


def get_discount_for_product(product_id: int, reference_date: date = None) -> int:
    """
    Возвращает размер скидки в процентах (0 или 25).
    Скидка 25%, если за предыдущий календарный месяц не было заказов.
    """
    if reference_date is None:
        reference_date = date.today()

    first_of_month = reference_date.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    row = fetch_one(
        """SELECT COUNT(*) AS cnt FROM order_items oi
           JOIN orders o ON o.id = oi.order_id
           WHERE oi.product_id = %s
             AND o.order_date BETWEEN %s AND %s""",
        (product_id, last_month_start, last_month_end)
    )
    return 25 if row['cnt'] == 0 else 0


def calculate_price_with_discount(price: float, discount: int) -> float:
    """Цена со скидкой."""
    return round(price * (1 - discount / 100.0), 2)