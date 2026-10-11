"""Форма создания нового заказа (Менеджер / Администратор)"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QSpinBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt

from config import STYLESHEET
from db import fetch_all, fetch_one, execute, execute_returning
from utils.discount import get_discount_for_product, calculate_price_with_discount
from utils.messages import show_error, show_info, confirm


class NewOrderWindow(QDialog):
    """Создание нового заказа из каталога."""

    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.user = user
        self.cart = []  # [{'product_id', 'name', 'size_id', 'size_value', 'quantity', 'price'}]

        self.setWindowTitle('Чудо Обувь — Новый заказ')
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_products()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel('Создание нового заказа')
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #70B2AF;"
        )
        layout.addWidget(title)

        # Клиент
        client_row = QHBoxLayout()
        client_row.addWidget(QLabel('Клиент (ФИО):'))
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText('Иванов Иван Иванович')
        client_row.addWidget(self.client_input, 2)
        layout.addLayout(client_row)

        # Поиск товаров
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel('Поиск:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Введите название...')
        self.search_input.textChanged.connect(self._filter_products)
        search_row.addWidget(self.search_input, 1)
        layout.addLayout(search_row)

        # Список товаров + корзина
        main_row = QHBoxLayout()

        # Товары
        products_layout = QVBoxLayout()
        products_layout.addWidget(QLabel('Каталог:'))
        self.products_list = QListWidget()
        self.products_list.itemDoubleClicked.connect(self._add_product)
        products_layout.addWidget(self.products_list)
        main_row.addLayout(products_layout, 1)

        # Кнопки + корзина
        center_layout = QVBoxLayout()
        center_layout.addStretch()
        add_btn = QPushButton('→')
        add_btn.setFixedWidth(50)
        add_btn.clicked.connect(self._add_product)
        center_layout.addWidget(add_btn)
        remove_btn = QPushButton('←')
        remove_btn.setFixedWidth(50)
        remove_btn.setStyleSheet(self._secondary_style())
        remove_btn.clicked.connect(self._remove_item)
        center_layout.addWidget(remove_btn)
        center_layout.addStretch()
        main_row.addLayout(center_layout)

        # Корзина
        cart_layout = QVBoxLayout()
        cart_layout.addWidget(QLabel('Позиции заказа:'))
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels([
            'Наименование', 'Размер', 'Кол-во', 'Цена', 'Сумма'
        ])
        self.cart_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        cart_layout.addWidget(self.cart_table)

        self.total_label = QLabel('Итого: 0.00 руб.')
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        cart_layout.addWidget(self.total_label)

        main_row.addLayout(cart_layout, 1)
        layout.addLayout(main_row)

        # Кнопки
        btns = QHBoxLayout()
        save_btn = QPushButton('Сохранить заказ')
        save_btn.clicked.connect(self._save_order)
        btns.addWidget(save_btn)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet(self._secondary_style())
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        layout.addLayout(btns)

    def _secondary_style(self) -> str:
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

    def _load_products(self):
        self.all_products = [dict(r) for r in fetch_all(
            "SELECT id, name, manufacturer, price FROM products ORDER BY name"
        )]
        self._filter_products()

    def _filter_products(self):
        text = self.search_input.text().strip().lower()
        self.products_list.clear()

        for p in self.all_products:
            if text and text not in p['name'].lower():
                continue
            item = QListWidgetItem(
                f"{p['manufacturer']} | {p['name']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.products_list.addItem(item)

    def _add_product(self):
        """Добавляет выбранный товар в заказ (с выбором размера)."""
        current = self.products_list.currentItem()
        if not current:
            show_error(self, 'Выберите товар из каталога')
            return

        p = current.data(Qt.ItemDataRole.UserRole)

        # Загружаем доступные размеры
        sizes = fetch_all("""
            SELECT s.id AS size_id, s.value, si.quantity_available
            FROM stock_items si
            JOIN sizes s ON s.id = si.size_id
            WHERE si.product_id = %s AND si.quantity_available > 0
            ORDER BY s.value
        """, (p['id'],))

        if not sizes:
            show_error(self, f"Товар «{p['name']}» нет в наличии")
            return

        # Открываем диалог выбора размера и количества
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle('Выбор размера и количества')
        dlg.setStyleSheet(STYLESHEET)
        form = QFormLayout(dlg)

        size_combo = QComboBox()
        for s in sizes:
            size_combo.addItem(
                f"{s['value']} (доступно: {s['quantity_available']})",
                (s['size_id'], s['quantity_available'], s['value'])
            )
        form.addRow('Размер:', size_combo)

        qty_spin = QSpinBox()
        qty_spin.setMinimum(1)
        qty_spin.setMaximum(sizes[0]['quantity_available'])
        form.addRow('Количество:', qty_spin)

        def update_max():
            data = size_combo.currentData()
            if data:
                qty_spin.setMaximum(data[1])
        size_combo.currentIndexChanged.connect(update_max)

        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bbox.accepted.connect(dlg.accept)
        bbox.rejected.connect(dlg.reject)
        form.addRow(bbox)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        size_id, available, size_value = size_combo.currentData()
        qty = qty_spin.value()
        if qty <= 0 or qty > available:
            show_error(self, f'Количество должно быть от 1 до {available}')
            return

        discount = get_discount_for_product(p['id'])
        price = calculate_price_with_discount(float(p['price']), discount)

        self.cart.append({
            'product_id': p['id'],
            'name': p['name'],
            'size_id': size_id,
            'size_value': size_value,
            'quantity': qty,
            'price': price,
        })
        self._refresh_cart()

    def _remove_item(self):
        row = self.cart_table.currentRow()
        if row < 0:
            show_error(self, 'Выберите позицию в заказе')
            return
        self.cart.pop(row)
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_table.setRowCount(0)
        total = 0.0

        for i, item in enumerate(self.cart):
            subtotal = item['price'] * item['quantity']
            total += subtotal

            self.cart_table.insertRow(i)
            self.cart_table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.cart_table.setItem(i, 1, QTableWidgetItem(str(item['size_value'])))
            self.cart_table.setItem(i, 2, QTableWidgetItem(str(item['quantity'])))
            self.cart_table.setItem(i, 3, QTableWidgetItem(f"{item['price']:.2f}"))
            self.cart_table.setItem(i, 4, QTableWidgetItem(f"{subtotal:.2f}"))

        self.total_label.setText(
            f"Итого: {total:,.2f} руб.".replace(',', ' ')
        )

    def _save_order(self):
        client = self.client_input.text().strip()
        if not client:
            show_error(self, 'Введите ФИО клиента')
            return
        if not self.cart:
            show_error(self, 'Добавьте товары в заказ')
            return

        if not confirm(self, 'Сохранить заказ?'):
            return

        try:
            order_id = execute_returning(
                """INSERT INTO orders (order_date, user_id, client_name)
                   VALUES (CURRENT_DATE, %s, %s) RETURNING id""",
                (self.user['id'], client)
            )

            for item in self.cart:
                # Уменьшаем остаток
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

            show_info(self, f'Заказ №{order_id} создан')
            self.accept()

        except Exception as e:
            show_error(self, f'Не удалось создать заказ:\n{e}')