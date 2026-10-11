"""Главное окно: каталог товаров"""
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QLineEdit, QComboBox, QPushButton
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from config import RESOURCES_DIR, STYLESHEET
from db import fetch_all
from ui.product_card import ProductCard
from utils.discount import get_discount_for_product


class MainWindow(QMainWindow):
    def __init__(self, user: dict = None):
        super().__init__()
        self.user = user
        self.cart = []  # корзина
        self.setWindowTitle('Чудо Обувь — Каталог')
        self.resize(1200, 800)
        self.setStyleSheet(STYLESHEET)

        # Иконка приложения
        icon_path = os.path.join(RESOURCES_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()
        self._load_products()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Шапка ---
        header = QHBoxLayout()

        # Логотип
        logo_path = os.path.join(RESOURCES_DIR, 'logo.png')
        if os.path.exists(logo_path):
            logo = QLabel()
            pix = QPixmap(logo_path).scaledToHeight(
                60, Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(pix)
            header.addWidget(logo)

        header.addStretch()

        # ФИО
        if self.user:
            fio = QLabel(self.user.get('full_name', ''))
            fio.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
            header.addWidget(fio)

        # Корзина (только для авторизованных)
        if self.user and self.user.get('id'):
            self.cart_btn = QPushButton('Корзина')
            self.cart_btn.clicked.connect(self._open_cart)
            header.addWidget(self.cart_btn)

        # Управление заказами (только для Менеджера/Админа)
        if self.user and self.user.get('role_name') in ('Администратор', 'Менеджер'):
            orders_btn = QPushButton('Управление заказами')
            orders_btn.clicked.connect(self._open_orders)
            header.addWidget(orders_btn)

        # Выход
        if self.user:
            logout_btn = QPushButton('Выйти')
            logout_btn.clicked.connect(self._logout)
            header.addWidget(logout_btn)

        layout.addLayout(header)

        # --- Панель фильтров (для авторизованных) ---
        self.filter_panel = self._build_filter_panel()
        layout.addWidget(self.filter_panel)

        # --- Скролл с карточками ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll, 1)

    def _build_filter_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            "background-color: #D2F6E7; border-radius: 6px; padding: 6px;"
        )
        layout = QHBoxLayout(panel)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Поиск по наименованию или описанию...')
        self.search_input.textChanged.connect(self._apply_filters)
        layout.addWidget(QLabel('Поиск:'))
        layout.addWidget(self.search_input, 2)

        # Фильтр по категории
        self.category_combo = QComboBox()
        self.category_combo.addItem('Все категории', None)
        self.category_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(QLabel('Категория:'))
        layout.addWidget(self.category_combo, 1)

        # Сортировка
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['Без сортировки', 'Цена ↑', 'Цена ↓'])
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(QLabel('Сортировка:'))
        layout.addWidget(self.sort_combo, 1)

        # Для неавторизованных — скрыть
        panel.setVisible(self.user is not None)
        return panel

    # ---------- Данные ----------
    def _load_products(self):
        query = """
            SELECT p.*, COALESCE(SUM(si.quantity_available), 0) AS total_quantity
            FROM products p
            LEFT JOIN stock_items si ON si.product_id = p.id
            GROUP BY p.id
            ORDER BY p.name
        """
        self.all_products = [dict(r) for r in fetch_all(query)]

        # Заполнить категории
        categories = sorted({p['category'] for p in self.all_products})
        for cat in categories:
            self.category_combo.addItem(cat, cat)

        self._apply_filters()

    def _apply_filters(self):
        products = list(self.all_products)

        # Фильтр по категории
        cat = self.category_combo.currentData()
        if cat:
            products = [p for p in products if p['category'] == cat]

        # Поиск
        text = self.search_input.text().strip().lower()
        if text:
            products = [
                p for p in products
                if text in p['name'].lower()
                or text in (p.get('description') or '').lower()
            ]

        # Сортировка
        sort_mode = self.sort_combo.currentText()
        if sort_mode == 'Цена ↑':
            products.sort(key=lambda p: float(p['price']))
        elif sort_mode == 'Цена ↓':
            products.sort(key=lambda p: float(p['price']), reverse=True)

        self._render_products(products)

    def _render_products(self, products: list):
        # Очистить старые карточки
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not products:
            self.cards_layout.addWidget(QLabel('Товары не найдены'))
            return

        for p in products:
            discount = get_discount_for_product(p['id'])
            card = ProductCard(p, discount)
            card.clicked.connect(self._open_product)
            self.cards_layout.addWidget(card)

    # ---------- Переходы ----------
    def _open_product(self, product_id: int):
        """Открывает форму просмотра товара."""
        if not self.user or not self.user.get('id'):
            from utils.messages import show_info
            show_info(self, 'Для оформления заказа войдите в систему')
            return
        from ui.product_view import ProductView
        dialog = ProductView(product_id, self.cart, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._update_cart_button()

    def _open_cart(self):
        """Открывает окно корзины."""
        from ui.cart_widget import CartWindow
        dialog = CartWindow(self.user, self.cart, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._load_products()
            self._update_cart_button()

    def _update_cart_button(self):
        """Обновляет счётчик на кнопке корзины."""
        if hasattr(self, 'cart_btn') and self.cart:
            total_qty = sum(item['quantity'] for item in self.cart)
            self.cart_btn.setText(f'Корзина ({total_qty})')
        elif hasattr(self, 'cart_btn'):
            self.cart_btn.setText('Корзина')

    def _logout(self):
        """Выход и возврат к окну авторизации."""
        from ui.login_window import LoginWindow
        self.close()
        login = LoginWindow()
        if login.exec() == login.DialogCode.Accepted:
            new_window = MainWindow(user=login.get_user())
            new_window.show()
            self._new_window = new_window


    def _open_orders(self):
        """Открывает окно управления заказами."""
        from ui.orders_window import OrdersWindow
        dialog = OrdersWindow(user=self.user, parent=self)
        dialog.exec()
        self._load_products()  # обновить каталог