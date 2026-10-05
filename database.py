import os
import csv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Параметры подключения к базе данных
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "loom_bd"),
    "user": os.getenv("DB_USER", "loom_user"),
    "password": os.getenv("DB_PASSWORD", "1234"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    ddl_script = """
    CREATE TABLE IF NOT EXISTS resources (
        id SERIAL PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        category VARCHAR(20) NOT NULL CHECK (category IN ('сотрудник', 'станок')),
        type VARCHAR(50) NOT NULL,
        priority INT NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 100),
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    );

    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(150) NOT NULL UNIQUE,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS operations (
        id SERIAL PRIMARY KEY,
        product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        step_number INT NOT NULL CHECK (step_number > 0),
        name VARCHAR(150) NOT NULL,
        duration INT NOT NULL CHECK (duration > 0),
        required_emp_type VARCHAR(50) NOT NULL,
        required_mach_type VARCHAR(50),
        CONSTRAINT uq_product_step UNIQUE (product_id, step_number)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_number VARCHAR(100) NOT NULL UNIQUE,
        product_id INT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
        priority INT NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 100),
        quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
        start_time TIMESTAMP NOT NULL,
        deadline TIMESTAMP NOT NULL,
        penalty_per_hour NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (penalty_per_hour >= 0),
        weight INT NOT NULL DEFAULT 1 CHECK (weight BETWEEN 1 AND 5),
        status VARCHAR(30) NOT NULL DEFAULT 'Новый',
        CONSTRAINT chk_order_dates CHECK (deadline > start_time)
    );

    CREATE TABLE IF NOT EXISTS schedule (
        id SERIAL PRIMARY KEY,
        order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        operation_id INT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
        employee_id INT NOT NULL REFERENCES resources(id) ON DELETE RESTRICT,
        machine_id INT REFERENCES resources(id) ON DELETE RESTRICT,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        is_success BOOLEAN NOT NULL DEFAULT TRUE,
        fail_reason VARCHAR(255),
        CONSTRAINT chk_schedule_times CHECK (end_time > start_time)
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl_script)


def parse_dt(dt_str):
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            pass
    raise ValueError(f"Неизвестный формат даты: {dt_str}")


def init_from_csv(data_dir="data"):
    init_db()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM products;")
            if cur.fetchone()[0] > 0:
                print("[INFO] База данных уже содержит данные. Пропуск инициализации.")
                return

    print("[INFO] База пуста. Начинаем загрузку из CSV...")

    # 1. Загрузка Products
    prod_path = os.path.join(data_dir, "products.csv")
    if os.path.exists(prod_path):
        with open(prod_path, mode="r", encoding="utf-8") as f, get_connection() as conn:
            reader = csv.DictReader(f)
            with conn.cursor() as cur:
                for row_idx, r in enumerate(reader, start=2):
                    try:
                        cur.execute(
                            "INSERT INTO products (id, name, description) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING;",
                            (int(r["id"]), r["name"].strip(), r.get("description", "").strip())
                        )
                    except Exception as e:
                        print(f"[WARN] products.csv (строка {row_idx}): пропуск записи — {e}")

    # 2. Загрузка Resources
    res_path = os.path.join(data_dir, "resources.csv")
    if os.path.exists(res_path):
        with open(res_path, mode="r", encoding="utf-8") as f, get_connection() as conn:
            reader = csv.DictReader(f)
            with conn.cursor() as cur:
                for row_idx, r in enumerate(reader, start=2):
                    try:
                        is_act = r.get("is_active", "True").strip().lower() in ("true", "1", "t")
                        cur.execute(
                            """INSERT INTO resources (id, name, category, type, priority, is_active)
                               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;""",
                            (int(r["id"]), r["name"].strip(), r["category"].strip(),
                             r["type"].strip(), int(r["priority"]), is_act)
                        )
                    except Exception as e:
                        print(f"[WARN] resources.csv (строка {row_idx}): пропуск записи — {e}")

    # 3. Загрузка Operations
    op_path = os.path.join(data_dir, "operations.csv")
    if os.path.exists(op_path):
        with open(op_path, mode="r", encoding="utf-8") as f, get_connection() as conn:
            reader = csv.DictReader(f)
            with conn.cursor() as cur:
                for row_idx, r in enumerate(reader, start=2):
                    try:
                        mach = r.get("required_mach_type", "").strip() or None
                        cur.execute(
                            """INSERT INTO operations (id, product_id, step_number, name, duration, required_emp_type, required_mach_type)
                               VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;""",
                            (int(r["id"]), int(r["product_id"]), int(r["step_number"]),
                             r["name"].strip(), int(r["duration"]), r["required_emp_type"].strip(), mach)
                        )
                    except Exception as e:
                        print(f"[WARN] operations.csv (строка {row_idx}): пропуск записи — {e}")

    # 4. Загрузка Orders
    ord_path = os.path.join(data_dir, "orders.csv")
    if os.path.exists(ord_path):
        with open(ord_path, mode="r", encoding="utf-8") as f, get_connection() as conn:
            reader = csv.DictReader(f)
            with conn.cursor() as cur:
                for row_idx, r in enumerate(reader, start=2):
                    try:
                        s_time = parse_dt(r["start_time"])
                        d_time = parse_dt(r["deadline"])
                        weight = int(r.get("weight", 1))
                        cur.execute(
                            """INSERT INTO orders (id, order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight, status)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;""",
                            (int(r["id"]), r["order_number"].strip(), int(r["product_id"]),
                             int(r["priority"]), int(r.get("quantity", 1)), s_time, d_time,
                             float(r.get("penalty_per_hour", 0.0)), weight, r.get("status", "Новый").strip())
                        )
                    except Exception as e:
                        print(f"[WARN] orders.csv (строка {row_idx}): пропуск записи — {e}")

    # Выравнивание счетчиков SERIAL
    with get_connection() as conn:
        with conn.cursor() as cur:
            for tbl in ["products", "resources", "operations", "orders"]:
                cur.execute(f"SELECT setval('{tbl}_id_seq', COALESCE((SELECT MAX(id) FROM {tbl}), 1));")
    print("[INFO] Инициализация базы данных успешно завершена.")


# ==================== CRUD ОПЕРАЦИИ ====================

def get_resources():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resources WHERE is_active = TRUE ORDER BY id;")
            return cur.fetchall()


def get_products():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM products ORDER BY id;")
            return cur.fetchall()


def get_operations(product_id=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if product_id is not None:
                cur.execute("SELECT * FROM operations WHERE product_id = %s ORDER BY step_number;", (product_id,))
            else:
                cur.execute("SELECT * FROM operations ORDER BY product_id, step_number;")
            return cur.fetchall()


def get_orders():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT o.*, p.name AS product_name 
                FROM orders o 
                JOIN products p ON o.product_id = p.id 
                ORDER BY o.id;
            """)
            return cur.fetchall()


def add_order(order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour=0.0, weight=1):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO orders (order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
                (order_number, product_id, priority, quantity, start_time, deadline, penalty_per_hour, weight)
            )
            return cur.fetchone()[0]


def delete_order(order_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = %s;", (order_id,))


# ==================== СОХРАНЕНИЕ И ВЫГРУЗКА РАСПИСАНИЯ ====================

def save_schedule(schedule_items):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Очистка предыдущего расчета
            cur.execute("TRUNCATE TABLE schedule RESTART IDENTITY;")

            insert_query = """
                INSERT INTO schedule (order_id, operation_id, employee_id, machine_id, start_time, end_time, is_success, fail_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            for item in schedule_items:
                cur.execute(insert_query, (
                    item["order_id"],
                    item["operation_id"],
                    item["employee_id"],
                    item["machine_id"],
                    item["start_time"],
                    item["end_time"],
                    item["is_success"],
                    item.get("fail_reason")
                ))


def get_last_schedule():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    s.id,
                    o.order_number,
                    op.name AS operation_name,
                    op.step_number,
                    emp.name AS employee_name,
                    COALESCE(mach.name, 'Вручную') AS machine_name,
                    s.start_time,
                    s.end_time,
                    s.is_success,
                    o.deadline,
                    (s.end_time > o.deadline) AS is_overdue
                FROM schedule s
                JOIN orders o ON s.order_id = o.id
                JOIN operations op ON s.operation_id = op.id
                JOIN resources emp ON s.employee_id = emp.id
                LEFT JOIN resources mach ON s.machine_id = mach.id
                ORDER BY o.order_number, op.step_number;
            """)
            return cur.fetchall()


def print_schedule_table():
    items = get_last_schedule()
    if not items:
        print("В базе нет сохраненного расписания.")
        return

    print("-" * 115)
    print(
        f"{'Заказ':<15} | {'Шаг':<4} | {'Операция':<30} | {'Сотрудник':<20} | {'Станок':<18} | {'Старт':<12} | {'Финиш':<12} | {'Просрочка'}")
    print("-" * 115)
    for it in items:
        st = it['start_time'].strftime('%d.%m %H:%M')
        et = it['end_time'].strftime('%d.%m %H:%M')
        overdue_str = "ДА" if it['is_overdue'] else "Нет"
        print(
            f"{it['order_number']:<15} | {it['step_number']:<4} | {it['operation_name'][:28]:<30} | {it['employee_name'][:18]:<20} | {it['machine_name'][:16]:<18} | {st:<12} | {et:<12} | {overdue_str}")
    print("-" * 115)


def export_schedule_to_csv(filename="schedule.csv"):
    items = get_last_schedule()
    with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Заказ", "Шаг", "Операция", "Сотрудник", "Станок", "Время начала", "Время окончания", "Признак просрочки"])
        for it in items:
            writer.writerow([
                it["order_number"],
                it["step_number"],
                it["operation_name"],
                it["employee_name"],
                it["machine_name"],
                it["start_time"].strftime("%Y-%m-%d %H:%M"),
                it["end_time"].strftime("%Y-%m-%d %H:%M"),
                "Просрочен" if it["is_overdue"] else "В срок"
            ])
    print(f"[INFO] Расписание успешно выгружено в файл {filename}")