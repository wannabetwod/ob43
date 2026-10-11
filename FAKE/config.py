"""Конфигурация приложения Чудо Обувь"""
import os

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
PRODUCTS_IMG_DIR = os.path.join(RESOURCES_DIR, 'products')

# БД
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chudo_obuv',
    'user': 'postgres',
    'password': '12345678',   # ← замени на свой
}

# Стиль (по Прил. 3)
COLOR_BG_MAIN = '#FFFFFF'
COLOR_BG_SECONDARY = '#D2F6E7'
COLOR_ACCENT = '#70B2AF'
COLOR_LOW_STOCK = '#ff8080'
FONT_FAMILY = 'Calibri'

STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG_MAIN};
    font-family: '{FONT_FAMILY}';
    font-size: 13px;
}}
QPushButton {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}}
QPushButton:hover {{ background-color: #5a9a97; }}
QPushButton:disabled {{ background-color: #cccccc; color: #666; }}
QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background-color: {COLOR_BG_SECONDARY};
    border: 1px solid #a0d0c0;
    border-radius: 4px;
    padding: 6px;
}}
QTableWidget {{ background-color: white; gridline-color: #dddddd; }}
QHeaderView::section {{
    background-color: {COLOR_ACCENT};
    color: white;
    padding: 6px;
    border: none;
    font-weight: bold;
}}
QLabel {{ color: #333; }}
"""