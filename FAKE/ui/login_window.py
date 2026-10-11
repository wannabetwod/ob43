"""Окно авторизации по логину """
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from config import RESOURCES_DIR, STYLESHEET
from db import fetch_one
from utils.messages import show_error


class LoginWindow(QDialog):
    """Окно входа. Возвращает user_data при успехе."""

    def __init__(self):
        super().__init__()
        self.user = None
        self.setWindowTitle('Чудо Обувь — Вход')
        self.resize(420, 380)
        self.setStyleSheet(STYLESHEET)

        icon_path = os.path.join(RESOURCES_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        # Логотип
        logo_path = os.path.join(RESOURCES_DIR, 'logo.png')
        if os.path.exists(logo_path):
            logo = QLabel()
            logo.setPixmap(QPixmap(logo_path).scaledToHeight(
                120, Qt.TransformationMode.SmoothTransformation
            ))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo)

        # Заголовок
        title = QLabel('Вход в систему')
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #70B2AF;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        # Поле логина
        layout.addWidget(QLabel('Логин:'))
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('Введите логин')
        self.login_input.returnPressed.connect(self._try_login)
        layout.addWidget(self.login_input)

        layout.addSpacing(20)

        # Кнопки
        btn_layout = QHBoxLayout()

        login_btn = QPushButton('Войти')
        login_btn.clicked.connect(self._try_login)
        btn_layout.addWidget(login_btn)

        guest_btn = QPushButton('Вход для гостя')
        guest_btn.setStyleSheet("""
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
        guest_btn.clicked.connect(self._guest_login)
        btn_layout.addWidget(guest_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _try_login(self):
        login = self.login_input.text().strip()
        if not login:
            show_error(self, 'Введите логин')
            return

        row = fetch_one(
            """SELECT u.id, u.last_name, u.first_name, u.middle_name,
                      u.login, r.name AS role_name
               FROM users u
               JOIN roles r ON r.id = u.role_id
               WHERE u.login = %s""",
            (login,)
        )

        if not row:
            show_error(self, f'Пользователь с логином «{login}» не найден')
            return

        # Собираем данные о пользователе
        self.user = {
            'id': row['id'],
            'login': row['login'],
            'role_name': row['role_name'],
            'full_name': ' '.join(filter(None, [
                row['last_name'], row['first_name'], row['middle_name']
            ])),
        }
        self.accept()

    def _guest_login(self):
        """Вход без авторизации."""
        self.user = {
            'id': None,
            'login': None,
            'role_name': 'Неавторизованный',
            'full_name': 'Гость',
        }
        self.accept()

    def get_user(self):
        return self.user