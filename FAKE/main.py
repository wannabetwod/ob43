"""Точка входа: приложение Чудо Обувь"""
import sys
from PyQt6.QtWidgets import QApplication

from config import STYLESHEET
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)

    # 1. Окно авторизации
    login = LoginWindow()
    if login.exec() != login.DialogCode.Accepted:
        # Пользователь закрыл окно — выходим
        sys.exit(0)

    user = login.get_user()

    # 2. Главное окно (каталог)
    window = MainWindow(user=user)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()