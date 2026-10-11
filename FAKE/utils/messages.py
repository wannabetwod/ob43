"""Диалоговые окна обратной связи."""
from PyQt6.QtWidgets import QMessageBox


def show_error(parent, text, title='Ошибка'):
    """Критическая ошибка."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.exec()


def show_warning(parent, text, title='Предупреждение'):
    """Предупреждение."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.exec()


def show_info(parent, text, title='Информация'):
    """Информационное сообщение."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.exec()


def confirm(parent, text, title='Подтверждение') -> bool:
    """Запрос подтверждения (Да/Нет)."""
    reply = QMessageBox.question(
        parent, title, text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes