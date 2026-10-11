"""Карточка товара в каталоге (по макету из КИМ)"""
import os
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from config import PRODUCTS_IMG_DIR, RESOURCES_DIR, COLOR_LOW_STOCK


class ProductCard(QFrame):
    """Карточка одной модели обуви."""

    clicked = pyqtSignal(int)  # сигнал с product_id

    def __init__(self, product: dict, discount: int, parent=None):
        super().__init__(parent)
        self.product_id = product['id']
        self.setFrameShape(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(product, discount)

    def _build_ui(self, p: dict, discount: int):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # --- Изображение ---
        img_label = QLabel()
        img_label.setFixedSize(140, 140)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = self._load_pixmap(p.get('image_path'))
        img_label.setPixmap(pixmap.scaled(
            140, 140,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        layout.addWidget(img_label)

        # --- Информация ---
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title = QLabel(f"{p.get('manufacturer', '')} | {p.get('name', '')}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #333;")
        info_layout.addWidget(title)

        info_layout.addWidget(QLabel(f"Категория: {p.get('category', '')}"))

        # ВАЖНО: total_qty определяется ЗДЕСЬ
        total_qty = int(p.get('total_quantity', 0))

        qty_label = QLabel(f"Количество: {total_qty}")
        if total_qty <= 3:
            qty_label.setStyleSheet(f"color: {COLOR_LOW_STOCK}; font-weight: bold;")
        info_layout.addWidget(qty_label)

        comp = (p.get('composition') or '')[:80]
        info_layout.addWidget(QLabel(f"Состав: {comp}..."))
        info_layout.addStretch()

        layout.addLayout(info_layout, 1)

        # --- Цена ---
        price_layout = QVBoxLayout()
        price_layout.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        price = float(p['price'])
        final_price = price * (1 - discount / 100.0)
        price_label = QLabel(f"{final_price:,.2f} ₽".replace(',', ' '))
        price_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #70B2AF;"
        )
        price_layout.addWidget(price_label)

        if discount > 0:
            old = QLabel(f"{price:,.2f} ₽".replace(',', ' '))
            old.setStyleSheet(
                "text-decoration: line-through; color: #999; font-size: 12px;"
            )
            price_layout.addWidget(old)

        layout.addLayout(price_layout)

        # --- Стиль карточки (единый) ---
        if total_qty <= 3:
            # Подсветка низкого остатка
            self.setStyleSheet("""
                ProductCard {
                    border: 1px solid #ff8080;
                    border-radius: 6px;
                    background-color: rgba(255, 128, 128, 40);
                }
                ProductCard:hover { border-color: #70B2AF; }
            """)
        else:
            # Обычная карточка
            self.setStyleSheet("""
                ProductCard {
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    background-color: white;
                }
                ProductCard:hover { border-color: #70B2AF; }
            """)

    def _load_pixmap(self, image_name: str) -> QPixmap:
        """Загружает картинку товара или заглушку."""
        if image_name:
            path = os.path.join(PRODUCTS_IMG_DIR, image_name)
            if os.path.exists(path):
                return QPixmap(path)
        stub = os.path.join(RESOURCES_DIR, 'picture.png')
        return QPixmap(stub) if os.path.exists(stub) else QPixmap()

    def mousePressEvent(self, event):
        """Клик по карточке — испускаем сигнал."""
        self.clicked.emit(self.product_id)