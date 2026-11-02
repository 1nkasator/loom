import os
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Параметры подключения к базе данных (PostgreSQL)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "loom_bd"),
    "user": os.getenv("DB_USER", "loom_user"),
    "password": os.getenv("DB_PASSWORD", "1234"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}


def get_connection():
    """Возвращает новое подключение к PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def parse_dt(dt_str: str) -> datetime:
    """Универсальный парсинг строкового представления даты и времени."""
    if isinstance(dt_str, datetime):
        return dt_str
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M"]
    clean_str = dt_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Неизвестный формат даты и времени: {dt_str}")


# =====================================================================
# 1. ИНИЦИАЛИЗАЦИЯ СТРУКТУРЫ БД ЧЕРЕЗ create_tables.sql
# =====================================================================

def init_db(sql_path: str = "create_tables.sql"):
    """
    Создает таблицы в БД, считывая DDL-скрипт из внешнего файла create_tables.sql.
    """
    if not os.path.exists(sql_path):
        # Поиск в директории текущего файла, если путь относительный
        alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), sql_path)
        if os.path.exists(alt_path):
            sql_path = alt_path
        else:
            raise FileNotFoundError(f"Файл DDL-скрипта не найден: {sql_path}")

    with open(sql_path, "r", encoding="utf-8") as f:
        ddl_script = f.read()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl_script)
        conn.commit()
    print(f"[INFO] Схема БД успешно проверена/инициализирована из файла: {sql_path}")


# =====================================================================
# 2. МОДУЛЬ ЧТЕНИЯ И ВАЛИДАЦИИ CSV-ФАЙЛОВ (ИЗОЛИРОВАН ОТ БД)
# =====================================================================

def read_products_csv(file_path: str) -> List[Dict[str, Any]]:
    """Чтение и валидация справочника изделий из CSV."""
    if not os.path.exists(file_path):
        return []
    records = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            try:
                prod_id = int(row["id"])
                name = row["name"].strip()
                if not name:
                    raise ValueError("Имя изделия не может быть пустым")
                desc = row.get("description", "").strip()
                records.append({"id": prod_id, "name": name, "description": desc})
            except Exception as e:
                print(f"[WARN] products.csv (строка {idx}): ошибка валидации ({e}), пропуск.")
    return records


def read_resources_csv(file_path: str) -> List[Dict[str, Any]]:
    """Чтение и валидация ресурсов (сотрудники, станки) из CSV."""
    if not os.path.exists(file_path):
        return []
    records = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            try:
                res_id = int(row["id"])
                name = row["name"].strip()
                cat = row["category"].strip().lower()
                if cat not in ("сотрудник", "станок"):
                    raise ValueError(f"Недопустимая категория ресурса: {cat}")
                rtype = row["type"].strip()
                prio = int(row.get("priority", 1))
                if not (1 <= prio <= 100):
                    raise ValueError(f"Приоритет должен быть от 1 до 100: {prio}")
                is_act = str(row.get("is_active", "True")).strip().lower() in ("true", "1", "t")
                records.append({
                    "id": res_id, "name": name, "category": cat,
                    "type": rtype, "priority": prio, "is_active": is_act
                })
            except Exception as e:
                print(f"[WARN] resources.csv (строка {idx}): ошибка валидации ({e}), пропуск.")
    return records


def read_operations_csv(file_path: str) -> List[Dict[str, Any]]:
    """Чтение и валидация технологических операций из CSV."""
    if not os.path.exists(file_path):
        return []
    records = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            try:
                op_id = int(row["id"])
                prod_id = int(row["product_id"])
                step = int(row["step_number"])
                if step <= 0:
                    raise ValueError("Номер шага должен быть > 0")
                name = row["name"].strip()
                duration = int(row["duration"])
                if duration <= 0:
                    raise ValueError("Длительность операции должна быть > 0")
                emp_type = row["required_emp_type"].strip()
                mach_type = row.get("required_mach_type", "").strip() or None
                records.append({
                    "id": op_id, "product_id": prod_id, "step_number": step,
                    "name": name, "duration": duration,
                    "required_emp_type": emp_type, "required_mach_type": mach_type
                })
            except Exception as e:
                print(f"[WARN] operations.csv (строка {idx}): ошибка валидации ({e}), пропуск.")
    return records


def read_orders_csv(file_path: str) -> List[Dict[str, Any]]:
    """Чтение и валидация заказов из CSV."""
    if not os.path.exists(file_path):
        return []
    records = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            try:
                order_id = int(row["id"]) if "id" in row and row["id"] else None
                order_num = row["order_number"].strip()
                prod_id = int(row["product_id"])
                prio = int(row.get("priority", 1))
                qty = int(row.get("quantity", 1))
                if qty <= 0:
                    raise ValueError("Количество изделий должно быть > 0")
                st = parse_dt(row["start_time"])
                dl = parse_dt(row["deadline"])
                if dl <= st:
                    raise ValueError("Дедлайн должен быть строго позже даты старта")
                penalty = float(row.get("penalty_per_hour", 0.0))
                if penalty < 0:
                    raise ValueError("Штраф не может быть отрицательным")
                weight = int(row.get("weight", 1))
                status = row.get("status", "Новый").strip()
                records.append({
                    "id": order_id, "order_number": order_num, "product_id": prod_id,
                    "priority": prio, "quantity": qty, "start_time": st, "deadline": dl,
                    "penalty_per_hour": penalty, "weight": weight, "status": status
                })
            except Exception as e:
                print(f"[WARN] orders.csv (строка {idx}): ошибка валидации ({e}), пропуск.")
    return records


# =====================================================================
# 3. CRUD ОПЕРАЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ (POSTGRESQL)
# =====================================================================

# --- Ресурсы (Resources) ---

def insert_resource(name: str, category: str, type_: str, priority: int = 1,
                    is_active: bool = True, res_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if res_id is not None:
                cur.execute(
                    """INSERT INTO resources (id, name, category, type, priority, is_active)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET 
                           name = EXCLUDED.name, category = EXCLUDED.category,
                           type = EXCLUDED.type, priority = EXCLUDED.priority, is_active = EXCLUDED.is_active
                       RETURNING id;""",
                    (res_id, name, category, type_, priority, is_active)
                )
            else:
                cur.execute(
                    """INSERT INTO resources (name, category, type, priority, is_active)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
                    (name, category, type_, priority, is_active)
                )
            return cur.fetchone()[0]


def get_resources(only_active: bool = True) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if only_active:
                cur.execute("SELECT * FROM resources WHERE is_active = TRUE ORDER BY id;")
            else:
                cur.execute("SELECT * FROM resources ORDER BY id;")
            return cur.fetchall()


def delete_resource(res_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resources WHERE id = %s;", (res_id,))


# --- Изделия (Products) ---

def insert_product(name: str, description: str = "", prod_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if prod_id is not None:
                cur.execute(
                    """INSERT INTO products (id, name, description) VALUES (%s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
                       RETURNING id;""",
                    (prod_id, name, description)
                )
            else:
                cur.execute(
                    """INSERT INTO products (name, description) VALUES (%s, %s)
                       ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                       RETURNING id;""",
                    (name, description)
                )
            return cur.fetchone()[0]


def get_products() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM products ORDER BY id;")
            return cur.fetchall()


def delete_product(prod_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s;", (prod_id,))


# --- Операции техпроцесса (Operations) ---

def insert_operation(product_id: int, step_number: int, name: str, duration: int,
                     required_emp_type: str, required_mach_type: Optional[str] = None,
                     op_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if op_id is not None:
                cur.execute(
                    """INSERT INTO operations (id, product_id, step_number, name, duration, required_emp_type, required_mach_type)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET
                           product_id = EXCLUDED.product_id, step_number = EXCLUDED.step_number,
                           name = EXCLUDED.name, duration = EXCLUDED.duration,
                           required_emp_type = EXCLUDED.required_emp_type, required_mach_type = EXCLUDED.required_mach_type
                       RETURNING id;""",
                    (op_id, product_id, step_number, name, duration, required_emp_type, required_mach_type)
                )
            else:
                cur.execute(
                    """INSERT INTO operations (product_id, step_number, name, duration, required_emp_type, required_mach_type)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (product_id, step_number) DO UPDATE SET
                           name = EXCLUDED.name, duration = EXCLUDED.duration,
                           required_emp_type = EXCLUDED.required_emp_type, required_mach_type = EXCLUDED.required_mach_type
                       RETURNING id;""",
                    (product_id, step_number, name, duration, required_emp_type, required_mach_type)
                )
            return cur.fetchone()[0]


def get_operations(product_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if product_id is not None:
                cur.execute("SELECT * FROM operations WHERE product_id = %s ORDER BY step_number;", (product_id,))
            else:
                cur.execute("SELECT * FROM operations ORDER BY product_id, step_number;")
            return cur.fetchall()


def delete_operation(op_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM operations WHERE id = %s;", (op_id,))


# --- Заказы (Orders) ---

def insert_order(order_number: str, product_id: int, priority: int, quantity: int,
                 start_time: datetime, deadline: datetime, penalty_per_hour: float = 0.0,
                 weight: int = 1, status: str = "Новый", order_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if order_id is not None:
                cur.execute(
                    """INSERT INTO orders (id, order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET
                           order_number = EXCLUDED.order_number, product_id = EXCLUDED.product_id,
                           priority = EXCLUDED.priority, quantity = EXCLUDED.quantity,
                           start_time = EXCLUDED.start_time, deadline = EXCLUDED.deadline,
                           penalty_per_hour = EXCLUDED.penalty_per_hour, weight = EXCLUDED.weight, status = EXCLUDED.status
                       RETURNING id;""",
                    (order_id, order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight, status)
                )
            else:
                cur.execute(
                    """INSERT INTO orders (order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (order_number) DO UPDATE SET
                           product_id = EXCLUDED.product_id, priority = EXCLUDED.priority,
                           quantity = EXCLUDED.quantity, start_time = EXCLUDED.start_time,
                           deadline = EXCLUDED.deadline, penalty_per_hour = EXCLUDED.penalty_per_hour,
                           weight = EXCLUDED.weight, status = EXCLUDED.status
                       RETURNING id;""",
                    (order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight, status)
                )
            return cur.fetchone()[0]


# Для обратной совместимости с существующим кодом main.py / app.py
def add_order(order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour=0.0, weight=1):
    return insert_order(order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight)


def get_orders() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT o.*, p.name AS product_name 
                FROM orders o 
                JOIN products p ON o.product_id = p.id 
                ORDER BY o.id;
            """)
            return cur.fetchall()


def delete_order(order_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = %s;", (order_id,))


# --- Расписание (Schedule) ---

def clear_schedule():
    """Полная очистка таблицы расписания со сбросом автоинкремента."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE schedule RESTART IDENTITY;")
        conn.commit()


def save_schedule(schedule_items: List[Dict[str, Any]]):
    """
    Атомарное транзакционное сохранение расписания.
    Сначала очищает таблицу schedule, затем вставляет все элементы в одной транзакции.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE schedule RESTART IDENTITY;")
            insert_query = """
                INSERT INTO schedule (order_id, operation_id, employee_id, machine_id, start_time, end_time, is_success, fail_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            for item in schedule_items:
                cur.execute(
                    insert_query,
                    (
                        item["order_id"],
                        item["operation_id"],
                        item["employee_id"],
                        item.get("machine_id"),
                        item["start_time"],
                        item["end_time"],
                        item.get("is_success", True),
                        item.get("fail_reason")
                    )
                )
        conn.commit()


def get_last_schedule() -> List[Dict[str, Any]]:
    """Получение сохраненного расписания из БД с подробными наименованиями."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    s.id,
                    o.order_number,
                    o.deadline,
                    op.step_number,
                    op.name AS operation_name,
                    emp.name AS employee_name,
                    COALESCE(mach.name, 'Вручную') AS machine_name,
                    s.start_time,
                    s.end_time,
                    s.is_success,
                    s.fail_reason
                FROM schedule s
                JOIN orders o ON s.order_id = o.id
                JOIN operations op ON s.operation_id = op.id
                JOIN resources emp ON s.employee_id = emp.id
                LEFT JOIN resources mach ON s.machine_id = mach.id
                ORDER BY o.order_number, op.step_number;
            """
            cur.execute(query)
            return cur.fetchall()


# =====================================================================
# 4. ФУНКЦИЯ ПЕРВИЧНОЙ ИНИЦИАЛИЗАЦИИ БАЗЫ ИЗ CSV
# =====================================================================

def init_from_csv(data_dir: str = "data", force_reload: bool = False):
    """
    Инициализирует структуру БД (через create_tables.sql) и наполняет таблицы данными из CSV.
    Разделяет чтение CSV и запись в БД через CRUD-функции.
    Если force_reload=True, предварительно очищает таблицы.
    """
    init_db()

    with get_connection() as conn:
        with conn.cursor() as cur:
            if force_reload:
                cur.execute("TRUNCATE TABLE schedule, orders, operations, products, resources RESTART IDENTITY CASCADE;")
                conn.commit()
            else:
                cur.execute("SELECT COUNT(*) FROM products;")
                if cur.fetchone()[0] > 0:
                    print("[INFO] База данных уже содержит данные. Пропуск инициализации.")
                    return

    print(f"[INFO] Наполнение БД из CSV (директория: {data_dir})...")

    # 1. Читаем и записываем продукты
    prod_file = os.path.join(data_dir, "products.csv")
    products = read_products_csv(prod_file)
    for p in products:
        insert_product(name=p["name"], description=p["description"], prod_id=p["id"])

    # 2. Читаем и записываем ресурсы
    res_file = os.path.join(data_dir, "resources.csv")
    resources = read_resources_csv(res_file)
    for r in resources:
        insert_resource(
            name=r["name"], category=r["category"], type_=r["type"],
            priority=r["priority"], is_active=r["is_active"], res_id=r["id"]
        )

    # 3. Читаем и записываем операции техпроцессов
    ops_file = os.path.join(data_dir, "operations.csv")
    operations = read_operations_csv(ops_file)
    for op in operations:
        insert_operation(
            product_id=op["product_id"], step_number=op["step_number"],
            name=op["name"], duration=op["duration"],
            required_emp_type=op["required_emp_type"],
            required_mach_type=op["required_mach_type"], op_id=op["id"]
        )

    # 4. Читаем и записываем заказы
    ord_file = os.path.join(data_dir, "orders.csv")
    orders = read_orders_csv(ord_file)
    for o in orders:
        insert_order(
            order_number=o["order_number"], product_id=o["product_id"],
            priority=o["priority"], quantity=o["quantity"],
            start_time=o["start_time"], deadline=o["deadline"],
            penalty_per_hour=o["penalty_per_hour"], weight=o["weight"],
            status=o["status"], order_id=o["id"]
        )

    # Синхронизация автоинкрементных счетчиков (SERIAL)
    with get_connection() as conn:
        with conn.cursor() as cur:
            for tbl in ["products", "resources", "operations", "orders"]:
                cur.execute(f"SELECT setval('{tbl}_id_seq', COALESCE((SELECT MAX(id) FROM {tbl}), 1));")
        conn.commit()

    print("[INFO] База данных успешно инициализирована данными из CSV.")


# =====================================================================
# 5. КОНСОЛЬНЫЙ ВЫВОД И ЭКСПОРТ В CSV
# =====================================================================

def print_schedule_table():
    """Выводит последнее сохраненное расписание в консоль в виде форматированной таблицы."""
    rows = get_last_schedule()
    if not rows:
        print("[INFO] Расписание в базе данных отсутствует.")
        return

    print("\n" + "=" * 125)
    print(f"{'Заказ':<14} | {'Шаг':<4} | {'Операция':<35} | {'Сотрудник':<28} | {'Станок':<24} | {'Старт':<16} | {'Финиш':<16} | {'Статус'}")
    print("=" * 125)
    for r in rows:
        is_overdue = "Просрочен" if r["end_time"] > r["deadline"] else "В срок"
        st = r["start_time"].strftime("%d.%m %H:%M")
        et = r["end_time"].strftime("%d.%m %H:%M")
        print(f"{r['order_number']:<14} | {r['step_number']:<4} | {r['operation_name'][:35]:<35} | {r['employee_name'][:28]:<28} | {r['machine_name'][:24]:<24} | {st:<16} | {et:<16} | {is_overdue}")
    print("=" * 125 + "\n")


def export_schedule_to_csv(filename: str = "schedule.csv"):
    """Экспорт последнего сохраненного расписания в CSV-файл."""
    rows = get_last_schedule()
    if not rows:
        print("[WARN] Нет данных расписания для экспорта.")
        return

    with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Заказ", "Шаг", "Операция", "Сотрудник", "Станок",
            "Время начала", "Время окончания", "Признак просрочки"
        ])
        for r in rows:
            is_overdue = "Просрочен" if r["end_time"] > r["deadline"] else "В срок"
            writer.writerow([
                r["order_number"],
                r["step_number"],
                r["operation_name"],
                r["employee_name"],
                r["machine_name"],
                r["start_time"].strftime("%Y-%m-%d %H:%M"),
                r["end_time"].strftime("%Y-%m-%d %H:%M"),
                is_overdue
            ])
    print(f"[INFO] Расписание успешно выгружено в файл: {filename}")
