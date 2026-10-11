"""Просмотр товара + добавление в корзину"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QPushButton, QTextEdit, QMessageBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from config import PRODUCTS_IMG_DIR, RESOURCES_DIR, STYLESHEET
from db import fetch_one, fetch_all
from utils.discount import get_discount_for_product, calculate_price_with_discount
from utils.messages import show_error, show_info


class ProductView(QDialog):
    """Форма просмотра товара + добавление в корзину."""

    def __init__(self, product_id: int, cart: list, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.cart = cart  # ссылка на список корзины

        self.setWindowTitle('Чудо Обувь — Просмотр товара')
        self.resize(700, 700)
        self.setStyleSheet(STYLESHEET)

        self._load_data()
        self._build_ui()

    def _load_data(self):
        """Загружает товар и доступные размеры из БД."""
        self.product = dict(fetch_one(
            "SELECT * FROM products WHERE id = %s",
            (self.product_id,)
        ))
        self.sizes = fetch_all(
            """SELECT s.id AS size_id, s.value, si.quantity_available
               FROM stock_items si
               JOIN sizes s ON s.id = si.size_id
               WHERE si.product_id = %s AND si.quantity_available > 0
               ORDER BY s.value""",
            (self.product_id,)
        )
        self.discount = get_discount_for_product(self.product_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Изображение
        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path = os.path.join(
            PRODUCTS_IMG_DIR,
            self.product.get('image_path') or ''
        )
        pix = QPixmap(path) if self.product.get('image_path') and os.path.exists(path) else QPixmap()
        if pix.isNull():
            pix = QPixmap(os.path.join(RESOURCES_DIR, 'picture.png'))
        img.setPixmap(pix.scaled(
            300, 300,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        layout.addWidget(img)

        # Текст
        layout.addWidget(QLabel(
            f"<b>{self.product.get('manufacturer', '')} | {self.product.get('name', '')}</b>"
        ))
        layout.addWidget(QLabel(f"Категория: {self.product.get('category', '')}"))
        layout.addWidget(QLabel(f"Состав: {self.product.get('composition', '')}"))

        desc = QTextEdit(self.product.get('description') or '')
        desc.setReadOnly(True)
        desc.setMaximumHeight(80)
        layout.addWidget(desc)

        # Цена
        final = calculate_price_with_discount(
            float(self.product['price']), self.discount
        )
        price_text = f"<b>Цена со скидкой: {final:.2f} ₽</b>"
        if self.discount > 0:
            price_text += f" <span style='color:#999;text-decoration:line-through;'>{float(self.product['price']):.2f} ₽</span>"
        layout.addWidget(QLabel(price_text))

        # Размер + количество
        row = QHBoxLayout()

        row.addWidget(QLabel('Размер:'))
        self.size_combo = QComboBox()
        if self.sizes:
            for s in self.sizes:
                self.size_combo.addItem(
                    f"{s['value']} (доступно: {s['quantity_available']})",
                    (s['size_id'], s['quantity_available'])
                )
        else:
            self.size_combo.addItem('Нет в наличии', None)
            self.size_combo.setEnabled(False)
        row.addWidget(self.size_combo)

        row.addWidget(QLabel('Кол-во:'))
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(1)
        row.addWidget(self.qty_spin)

        self.size_combo.currentIndexChanged.connect(self._update_max_qty)
        self._update_max_qty()

        layout.addLayout(row)

        # Кнопки
        btns = QHBoxLayout()

        add_btn = QPushButton('Добавить в заказ')
        add_btn.clicked.connect(self._add_to_cart)
        if not self.sizes:
            add_btn.setEnabled(False)
        btns.addWidget(add_btn)

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #D2F6E7;
                color: #333;
                border: 1px solid #70B2AF;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #BBEBD7; }
        """)
        back_btn.clicked.connect(self.reject)
        btns.addWidget(back_btn)

        layout.addLayout(btns)

    def _update_max_qty(self):
        data = self.size_combo.currentData()
        if data:
            self.qty_spin.setMaximum(data[1])
        else:
            self.qty_spin.setMaximum(0)

    def _add_to_cart(self):
        data = self.size_combo.currentData()
        if not data:
            show_error(self, 'Выберите доступный размер')
            return

        size_id, available = data
        qty = self.qty_spin.value()

        if qty <= 0 or qty > available:
            show_error(self, f'Количество должно быть от 1 до {available}')
            return

        final_price = calculate_price_with_discount(
            float(self.product['price']), self.discount
        )

        # Проверяем, есть ли товар с таким же размером уже в корзине
        for item in self.cart:
            if item['product_id'] == self.product_id and item['size_id'] == size_id:
                item['quantity'] += qty
                show_info(self, 'Количество в заказе увеличено')
                self.accept()
                return

        # Добавляем новую позицию
        size_text = self.size_combo.currentText().split(' ')[0]
        self.cart.append({
            'product_id': self.product_id,
            'name': self.product['name'],
            'manufacturer': self.product.get('manufacturer', ''),
            'size_id': size_id,
            'size_value': size_text,
            'quantity': qty,
            'price': final_price,
        })
        show_info(self, 'Товар добавлен в заказ')
        self.accept()