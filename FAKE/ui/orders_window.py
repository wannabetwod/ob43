"""Окно списка заказов (Менеджер / Администратор)"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

from config import STYLESHEET
from db import fetch_all
from utils.messages import show_error, show_info, confirm


class OrdersWindow(QDialog):
    """Список всех заказов. Менеджер/Админ могут открывать, создавать, удалять."""

    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle('Чудо Обувь — Управление заказами')
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_orders()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Заголовок
        title = QLabel('Список заказов')
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #70B2AF;"
        )
        layout.addWidget(title)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            '№', 'Дата заказа', 'Клиент', 'Сумма (руб.)'
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.doubleClicked.connect(self._open_order)
        layout.addWidget(self.table)

        # Кнопки
        btns = QHBoxLayout()

        open_btn = QPushButton('Открыть заказ')
        open_btn.clicked.connect(self._open_order)
        btns.addWidget(open_btn)

        create_btn = QPushButton('Создать заказ')
        create_btn.clicked.connect(self._create_order)
        btns.addWidget(create_btn)

        delete_btn = QPushButton('Удалить заказ')
        delete_btn.setStyleSheet(self._danger_style())
        delete_btn.clicked.connect(self._delete_order)
        btns.addWidget(delete_btn)

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet(self._secondary_style())
        back_btn.clicked.connect(self.reject)
        btns.addWidget(back_btn)

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

    def _danger_style(self) -> str:
        return """
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c9302c; }
        """

    def _load_orders(self):
        """Загружает список заказов с итоговой суммой."""
        rows = fetch_all("""
            SELECT
                o.id,
                o.order_date,
                o.client_name,
                COALESCE(SUM(oi.quantity * oi.price_at_moment), 0) AS total
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY o.order_date DESC, o.id DESC
        """)

        self.orders = [dict(r) for r in rows]
        self.table.setRowCount(0)

        for i, o in enumerate(self.orders):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(o['id'])))
            self.table.setItem(
                i, 1,
                QTableWidgetItem(str(o['order_date']))
            )
            self.table.setItem(i, 2, QTableWidgetItem(o['client_name']))
            self.table.setItem(
                i, 3,
                QTableWidgetItem(f"{float(o['total']):,.2f}".replace(',', ' '))
            )

    def _get_selected_order_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.orders[row]['id']

    def _open_order(self):
        order_id = self._get_selected_order_id()
        if order_id is None:
            show_error(self, 'Выберите заказ')
            return

        from ui.order_view import OrderViewWindow
        dialog = OrderViewWindow(
            order_id=order_id,
            user=self.user,
            parent=self
        )
        dialog.exec()
        self._load_orders()  # обновить список

    def _create_order(self):
        """Открывает форму создания нового заказа."""
        from ui.new_order_window import NewOrderWindow
        dialog = NewOrderWindow(user=self.user, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._load_orders()

    def _delete_order(self):
        order_id = self._get_selected_order_id()
        if order_id is None:
            show_error(self, 'Выберите заказ для удаления')
            return

        if not confirm(self, f'Удалить заказ №{order_id}?\nЭто действие необратимо.'):
            return

        from db import execute
        try:
            # ON DELETE CASCADE удалит позиции автоматически
            execute("DELETE FROM orders WHERE id = %s", (order_id,))
            show_info(self, f'Заказ №{order_id} удалён')
            self._load_orders()
        except Exception as e:
            show_error(self, f'Не удалось удалить заказ:\n{e}')