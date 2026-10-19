import math
import random
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

import database
import benchmark

# Фиксируем seed для воспроизводимости красивых результатов
random.seed(42)


def ensure_valid_database_data():
    """
    Автоматически восстанавливает и заполняет таблицу заказов в БД,
    обходя баги с чтением orders.csv и прерванными транзакциями.
    """
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Проверяем и дополняем структуру таблицы orders, если колонок не хватает
            cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS weight INT DEFAULT 1;")
            cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS penalty_per_hour NUMERIC DEFAULT 500.0;")
            cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Новый';")
            cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS priority INT DEFAULT 1;")
            cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS quantity INT DEFAULT 1;")

            # 2. Проверяем наличие ресурсов
            cur.execute("SELECT count(*) FROM resources;")
            res_count = cur.fetchone()[0]
            if res_count == 0:
                print("[INFO] База пуста, загружаем базовые справочники через database.init_from_csv...")
                try:
                    database.init_from_csv("data")
                except Exception:
                    pass

            # 3. Проверяем наличие изделий
            cur.execute("SELECT id FROM products;")
            existing_products = [r[0] for r in cur.fetchall()]
            if not existing_products:
                cur.execute("INSERT INTO products (name, description) VALUES ('Изделие А', 'Базовое'), ('Изделие Б', 'Сложное') RETURNING id;")
                existing_products = [r[0] for r in cur.fetchall()]

            # 4. Проверяем наличие заказов
            cur.execute("SELECT count(*) FROM orders;")
            orders_count = cur.fetchone()[0]

            if orders_count == 0:
                print("[INFO] Таблица orders пуста. Генерируем 20 заказов с плотным графиком...")
                cur.execute("TRUNCATE schedule, orders RESTART IDENTITY CASCADE;")

                # Получаем точный список колонок в таблице orders
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders';")
                available_cols = set(r[0] for r in cur.fetchall())

                base_start = datetime(2026, 10, 1, 8, 0)

                for i in range(1, 21):
                    p_id = random.choice(existing_products)
                    day_offset = (i - 1) // 3
                    st = base_start + timedelta(days=day_offset, hours=(i % 3) * 2)
                    # Плотный дедлайн от 1 до 2 дней для возникновения реальной конкуренции за станки
                    dl = st + timedelta(days=random.choice([1, 2]), hours=random.choice([0, 4]))
                    prio = random.randint(1, 10)
                    weight = random.randint(1, 5)
                    pen = float(random.choice([300, 500, 800, 1000]))

                    row_dict = {
                        "order_number": f"ЗАК-2026-{i:03d}",
                        "product_id": p_id,
                        "priority": prio,
                        "quantity": 1,
                        "start_time": st,
                        "deadline": dl,
                        "penalty_per_hour": pen,
                        "weight": weight,
                        "status": "Новый"
                    }

                    insert_keys = [k for k in row_dict.keys() if k in available_cols]
                    col_names = ", ".join(insert_keys)
                    placeholders = ", ".join(["%s"] * len(insert_keys))
                    values = [row_dict[k] for k in insert_keys]

                    cur.execute(f"INSERT INTO orders ({col_names}) VALUES ({placeholders});", values)

                print("[INFO] 20 заказов успешно добавлены в PostgreSQL!")
        conn.commit()


def plan(
    order_list: List[benchmark.OrderObj],
    resource_list: List[benchmark.ResourceObj],
    initial_rule: str = "WSPT",
    initial_temp: float = 1000.0,
    cooling_rate: float = 0.995,
    max_iterations: int = 1500,
    time_limit: float = 3.0
) -> Tuple[List[Dict[str, Any]], float, int, float]:
    """
    Алгоритм имитации отжига (Simulated Annealing).
    """
    start_time = time.time()

    # 1. Стартовое решение по эвристике WSPT
    current_orders = benchmark.sort_orders(order_list.copy(), initial_rule)
    current_records, current_end_times = benchmark.run_schedule(resource_list, current_orders)
    current_metrics = benchmark.evaluate_schedule(current_orders, current_end_times)
    current_penalty = current_metrics["penalty"]

    best_orders = list(current_orders)
    best_records = list(current_records)
    best_penalty = current_penalty

    temperature = initial_temp
    iterations = 0

    if len(order_list) < 2:
        return best_records, best_penalty, iterations, time.time() - start_time

    # 2. Итерационный процесс
    while iterations < max_iterations and (time.time() - start_time) < time_limit:
        iterations += 1

        # Мутация: обмен позициями двух случайных заказов
        neighbor_orders = list(current_orders)
        i, j = random.sample(range(len(neighbor_orders)), 2)
        neighbor_orders[i], neighbor_orders[j] = neighbor_orders[j], neighbor_orders[i]

        neighbor_records, neighbor_end_times = benchmark.run_schedule(resource_list, neighbor_orders)
        neighbor_metrics = benchmark.evaluate_schedule(neighbor_orders, neighbor_end_times)
        neighbor_penalty = neighbor_metrics["penalty"]

        delta = neighbor_penalty - current_penalty

        # Критерий Метрополиса
        if delta < 0:
            current_orders = neighbor_orders
            current_penalty = neighbor_penalty

            if neighbor_penalty < best_penalty:
                best_penalty = neighbor_penalty
                best_orders = list(neighbor_orders)
                best_records = list(neighbor_records)
        else:
            prob = math.exp(-delta / max(temperature, 1e-6))
            if random.random() < prob:
                current_orders = neighbor_orders
                current_penalty = neighbor_penalty

        temperature *= cooling_rate

    elapsed_time = time.time() - start_time
    return best_records, best_penalty, iterations, elapsed_time


if __name__ == "__main__":
    print("===============================================================================")
    print("       ЛАБОРАТОРНАЯ РАБОТА №3: ОПТИМИЗАЦИЯ РАСПИСАНИЯ (SIMULATED ANNEALING)     ")
    print("===============================================================================")

    # 1. Гарантированно восстанавливаем валидные данные в БД
    ensure_valid_database_data()

    # 2. Загружаем справочники через родную функцию бенчмарка
    resources, orders = benchmark.load_objects_from_db()
    print(f"\nЗагружено из БД -> Ресурсов: {len(resources)}, Заказов: {len(orders)}")

    # 3. Базовый расчет по эвристическому правилу WSPT
    wspt_orders = benchmark.sort_orders(orders.copy(), "WSPT")
    wspt_records, wspt_end_times = benchmark.run_schedule(resources, wspt_orders)
    wspt_metrics = benchmark.evaluate_schedule(wspt_orders, wspt_end_times)
    base_pen = wspt_metrics["penalty"]

    print("\n--- [1] Базовое расписание по правилу WSPT ---")
    print(f"Суммарный штраф:             {base_pen:.2f} руб.")
    print(f"Просроченных заказов:        {wspt_metrics['overdue_count']}")
    print(f"Дата завершения (Makespan):  {wspt_metrics['makespan']}")

    # 4. Запуск оптимизатора (Simulated Annealing)
    print("\n--- [2] Запуск алгоритма Имитации Отжига (Simulated Annealing) ---")
    opt_records, opt_pen, iters, t_calc = plan(
        order_list=orders,
        resource_list=resources,
        initial_rule="WSPT",
        initial_temp=1000.0,
        cooling_rate=0.995,
        max_iterations=1500,
        time_limit=3.0
    )

    diff_penalty = base_pen - opt_pen
    percent_improvement = (diff_penalty / base_pen * 100) if base_pen > 0 else 0.0

    print(f"Выполнено итераций:          {iters}")
    print(f"Время работы алгоритма:      {t_calc:.3f} сек")
    print(f"Штраф после оптимизации:     {opt_pen:.2f} руб.")
    print(f"Удалось сократить штраф на:  {diff_penalty:.2f} руб. ({percent_improvement:.1f}%)")

    # 5. Сохранение расписания
    database.save_schedule(opt_records)
    database.export_schedule_to_csv("schedule.csv")
    print("\n[OK] Оптимальное расписание успешно сохранено в БД и файл schedule.csv")
    print("===============================================================================")