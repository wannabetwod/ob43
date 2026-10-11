"""Корзина + оформление заказа"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

from config import STYLESHEET
from db import execute, execute_returning
from utils.messages import show_error, show_info, confirm, show_warning


class CartWindow(QDialog):
    """Окно корзины. Оформляет заказ в БД."""

    def __init__(self, user: dict, cart: list, parent=None):
        super().__init__(parent)
        self.user = user
        self.cart = cart

        self.setWindowTitle('Чудо Обувь — Корзина')
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel('Корзина и оформление заказа')
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #70B2AF;"
        )
        layout.addWidget(title)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Наименование', 'Производитель',
            'Размер', 'Кол-во', 'Сумма (руб.)'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Итог
        self.total_label = QLabel('Итого к оплате: 0.00 руб.')
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.total_label)

        # Кнопки
        btns = QHBoxLayout()

        remove_btn = QPushButton('Удалить позицию')
        remove_btn.clicked.connect(self._remove_selected)
        btns.addWidget(remove_btn)

        clear_btn = QPushButton('Очистить')
        clear_btn.setStyleSheet(self._secondary_btn_style())
        clear_btn.clicked.connect(self._clear_cart)
        btns.addWidget(clear_btn)

        checkout_btn = QPushButton('Оформить заказ')
        checkout_btn.clicked.connect(self._checkout)
        btns.addWidget(checkout_btn)

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet(self._secondary_btn_style())
        back_btn.clicked.connect(self.reject)
        btns.addWidget(back_btn)

        layout.addLayout(btns)

    def _secondary_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #D2F6E7;
                color: #333;
                border: 1px solid #70B2AF;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #BBEBD7; }
        """

    def _refresh_table(self):
        """Обновляет таблицу и итоговую сумму."""
        self.table.setRowCount(0)
        total = 0.0

        for i, item in enumerate(self.cart):
            subtotal = item['price'] * item['quantity']
            total += subtotal

            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(item['product_id'])))
            self.table.setItem(i, 1, QTableWidgetItem(item['name']))
            self.table.setItem(i, 2, QTableWidgetItem(item.get('manufacturer', '')))
            self.table.setItem(i, 3, QTableWidgetItem(str(item['size_value'])))
            self.table.setItem(i, 4, QTableWidgetItem(str(item['quantity'])))
            self.table.setItem(i, 5, QTableWidgetItem(f"{subtotal:.2f}"))

        self.total_label.setText(f"Итого к оплате: {total:,.2f} руб.".replace(',', ' '))

    def _remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            show_warning(self, 'Выберите строку для удаления')
            return
        self.cart.pop(row)
        self._refresh_table()

    def _clear_cart(self):
        if not self.cart:
            return
        if confirm(self, 'Очистить всю корзину?'):
            self.cart.clear()
            self._refresh_table()

    def _checkout(self):
        if not self.cart:
            show_error(self, 'Корзина пуста')
            return

        if not self.user or not self.user.get('id'):
            show_error(self, 'Для оформления заказа нужна авторизация')
            return

        if not confirm(self, 'Оформить заказ?'):
            return

        try:
            # 1. Создаём заказ
            order_id = execute_returning(
                """INSERT INTO orders (order_date, user_id, client_name)
                   VALUES (CURRENT_DATE, %s, %s) RETURNING id""",
                (self.user['id'], self.user['full_name'])
            )

            # 2. Добавляем позиции + уменьшаем остатки
            for item in self.cart:
                # Проверяем остаток на момент оформления
                row = execute(
                    """UPDATE stock_items
                       SET quantity_available = quantity_available - %s
                       WHERE product_id = %s AND size_id = %s
                         AND quantity_available >= %s""",
                    (item['quantity'], item['product_id'],
                     item['size_id'], item['quantity'])
                )
                if row == 0:
                    raise Exception(
                        f"Недостаточно товара: {item['name']} (размер {item['size_value']})"
                    )

                execute(
                    """INSERT INTO order_items
                       (order_id, product_id, size_id, quantity, price_at_moment)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (order_id, item['product_id'], item['size_id'],
                     item['quantity'], item['price'])
                )

            show_info(self, f'Заказ №{order_id} успешно оформлен!')
            self.cart.clear()
            self.accept()

        except Exception as e:
            show_error(self, f'Не удалось оформить заказ:\n{e}')