"""
Универсальный импорт данных для БД "Чудо Обувь"
Задания 1.7, 1.8, 1.9 — без pandas, только openpyxl + psycopg2

Запуск: python3 sql/import_all.py
"""
import os
import sys
import openpyxl
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, DATA_DIR


# ============================================================
# Нормализация: убираем неразрывные пробелы и т.п.
# ============================================================
def normalize(text):
    """Убирает все виды пробелов (обычный, \\xa0, \\t и др.) и приводит к нижнему регистру."""
    if text is None:
        return ''
    text = str(text)
    for ch in ['\xa0', '\u2009', '\u202f', '\t', '\u200b', '\u2007', '\u2008']:
        text = text.replace(ch, ' ')
    text = ' '.join(text.split())
    return text.strip().lower()


# ============================================================
# Утилита: чтение xlsx-файла
# ============================================================
def read_xlsx(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Нет файла: {path}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    return [r for r in rows if r[0] is not None]


# ============================================================
# Поиск товара с нормализацией
# ============================================================
def find_product(cur, name, manufacturer):
    """Ищет товар с нормализацией пробелов и регистра."""
    if name is None:
        return None

    norm_name = normalize(name)
    norm_manuf = normalize(manufacturer)

    cur.execute("SELECT id, name, manufacturer FROM products")
    all_products = cur.fetchall()

    # 1. Точное совпадение + производитель
    for pid, pname, pmanuf in all_products:
        if normalize(pname) == norm_name and normalize(pmanuf) == norm_manuf:
            return pid

    # 2. Только по имени
    for pid, pname, pmanuf in all_products:
        if normalize(pname) == norm_name:
            return pid

    # 3. products.name НАЧИНАЕТСЯ с name
    for pid, pname, pmanuf in all_products:
        if normalize(pname).startswith(norm_name):
            return pid

    # 4. name СОДЕРЖИТСЯ в products.name
    for pid, pname, pmanuf in all_products:
        if norm_name in normalize(pname):
            return pid

    # 5. products.name СОДЕРЖИТСЯ в name
    for pid, pname, pmanuf in all_products:
        if normalize(pname) and normalize(pname) in norm_name:
            return pid

    return None


# ============================================================
# Поиск размера
# ============================================================
def find_size(cur, value):
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(',', '.').strip()
        v = float(value)
    except (ValueError, TypeError):
        return None
    cur.execute("SELECT id FROM sizes WHERE value = %s", (v,))
    row = cur.fetchone()
    return row[0] if row else None


# ============================================================
# 1. Размеры
# ============================================================
def import_sizes(cur):
    rows = read_xlsx('Sizes_import.xlsx')
    count = 0
    seen = set()
    for row in rows:
        value = row[0]
        if value is None:
            continue
        try:
            v = float(str(value).replace(',', '.').strip())
        except (ValueError, TypeError):
            continue
        if v in seen:
            continue
        seen.add(v)
        cur.execute(
            "INSERT INTO sizes (value) VALUES (%s) ON CONFLICT (value) DO NOTHING",
            (v,)
        )
        if cur.rowcount > 0:
            count += 1
    print(f"  Sizes: {count}")


# ============================================================
# 2. Товары
# ============================================================
def import_products(cur):
    rows = read_xlsx('Products_import.xlsx')
    count = 0
    for row in rows:
        if row[3] is None:
            continue
        cur.execute(
            """INSERT INTO products
               (category, subcategory, name, manufacturer, image_path,
                description, composition, price)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                str(row[0]).strip() if row[0] else None,
                str(row[1]).strip() if row[1] else None,
                str(row[3]).strip(),
                str(row[4]).strip() if row[4] else None,
                str(row[2]).strip() if row[2] else None,
                str(row[5]).strip() if row[5] else None,
                str(row[6]).strip() if row[6] else None,
                float(row[7]) if row[7] is not None else 0,
            )
        )
        count += 1
    print(f"  Products: {count}")


# ============================================================
# 3. Пользователи
# ============================================================
def import_users(cur):
    rows = read_xlsx('Users_import.xlsx')
    count = 0
    skipped = 0
    for row in rows:
        if row[3] is None:
            continue
        cur.execute("SELECT id FROM roles WHERE name = %s", (str(row[4]).strip(),))
        role = cur.fetchone()
        if not role:
            skipped += 1
            print(f"    ⚠️ Роль не найдена: {row[4]!r}")
            continue
        cur.execute(
            """INSERT INTO users (last_name, first_name, middle_name, login, role_id)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (login) DO NOTHING""",
            (
                str(row[0]).strip() if row[0] else None,
                str(row[1]).strip() if row[1] else None,
                str(row[2]).strip() if row[2] else None,
                str(row[3]).strip(),
                role[0]
            )
        )
        if cur.rowcount > 0:
            count += 1
    print(f"  Users: {count} (пропущено: {skipped})")


# ============================================================
# 4. Остатки
# ============================================================
def import_stock_items(cur):
    rows = read_xlsx('Stock_Items_import.xlsx')
    count = 0
    skipped = 0
    for row in rows:
        if row[0] is None:
            continue
        pid = find_product(cur, row[0], row[1])
        if not pid:
            skipped += 1
            print(f"    ⚠️ Товар не найден: {row[0]!r} / {row[1]!r}")
            continue
        sid = find_size(cur, row[2])
        if not sid:
            skipped += 1
            print(f"    ⚠️ Размер не найден: {row[2]!r}")
            continue
        cur.execute(
            """INSERT INTO stock_items (product_id, size_id, quantity_available)
               VALUES (%s, %s, %s)
               ON CONFLICT (product_id, size_id)
               DO UPDATE SET quantity_available = EXCLUDED.quantity_available""",
            (pid, sid, int(row[3]))
        )
        count += 1
    print(f"  Stock_Items: {count} (пропущено: {skipped})")


# ============================================================
# 5. Заказы и позиции
# ============================================================
def import_orders(cur):
    rows = read_xlsx('Orders_import.xlsx')
    orders_dict = {}
    for r in rows:
        if r[0] is None:
            continue
        num = r[0]
        if num not in orders_dict:
            orders_dict[num] = {'header': r, 'items': []}
        orders_dict[num]['items'].append(r)

    count_orders = 0
    count_items = 0
    skipped = 0

    for num, data in orders_dict.items():
        header = data['header']
        order_date = header[1]
        fio = header[2]

        cur.execute(
            """SELECT id FROM users
               WHERE TRIM(last_name || ' ' || first_name || ' ' || COALESCE(middle_name, '')) = %s
               LIMIT 1""",
            (str(fio).strip(),)
        )
        user = cur.fetchone()
        user_id = user[0] if user else 1

        cur.execute(
            """INSERT INTO orders (order_date, user_id, client_name)
               VALUES (%s, %s, %s) RETURNING id""",
            (order_date, user_id, str(fio).strip())
        )
        order_id = cur.fetchone()[0]
        count_orders += 1

        for it in data['items']:
            pid = find_product(cur, it[4], it[5])
            if not pid:
                skipped += 1
                print(f"    ⚠️ Товар не найден: {it[4]!r} / {it[5]!r}")
                continue
            sid = find_size(cur, it[6])
            if not sid:
                skipped += 1
                print(f"    ⚠️ Размер не найден: {it[6]!r}")
                continue
            cur.execute(
                """INSERT INTO order_items
                   (order_id, product_id, size_id, quantity, price_at_moment)
                   VALUES (%s, %s, %s, %s, %s)""",
                (order_id, pid, sid, int(it[7]), float(it[8]))
            )
            count_items += 1

    print(f"  Orders: {count_orders}")
    print(f"  Order_Items: {count_items} (пропущено: {skipped})")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("Импорт данных в БД Чудо Обувь")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        print("\n[1/5] Размеры...")
        import_sizes(cur)
        print("\n[2/5] Товары...")
        import_products(cur)
        print("\n[3/5] Пользователи...")
        import_users(cur)
        print("\n[4/5] Остатки...")
        import_stock_items(cur)
        print("\n[5/5] Заказы...")
        import_orders(cur)

        conn.commit()
        print("\n" + "=" * 60)
        print("🎉 Готово!")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()