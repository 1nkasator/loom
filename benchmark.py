import os
import csv
import time
import random
from datetime import datetime, timedelta
import database

# Фиксируем seed для строгой повторяемости данных по заданию
random.seed(42)

WORK_START_HOUR = 8
WORK_END_HOUR = 16

# ==================== МОДЕЛИ ДАННЫХ ====================

class TimeSlot:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

class ResourceObj:
    def __init__(self, id: int, name: str, category: str, type_: str, priority: int):
        self.id = id
        self.name = name
        self.category = category
        self.type = type_
        self.priority = priority
        self.busy: list[TimeSlot] = []

class OperationObj:
    def __init__(self, id: int, product_id: int, step_number: int, name: str,
                 duration: int, emp_type: str, mach_type: str = ""):
        self.id = id
        self.product_id = product_id
        self.step_number = step_number
        self.name = name
        self.duration = duration
        self.emp_type = emp_type
        self.mach_type = mach_type or ""

class OrderObj:
    def __init__(self, id: int, order_number: str, product_id: int, priority: int,
                 quantity: int, start_time: datetime, deadline: datetime,
                 penalty_per_hour: float, weight: int):
        self.id = id
        self.order_number = order_number
        self.product_id = product_id
        self.priority = priority
        self.quantity = quantity
        self.start_time = start_time
        self.deadline = deadline
        self.penalty_per_hour = penalty_per_hour
        self.weight = weight
        self.operations: list[OperationObj] = []

    def total_duration(self) -> int:
        return sum(op.duration for op in self.operations)

# ==================== РАБОЧИЙ ГРАФИК (8:00 - 16:00) ====================

def normalize_to_workday(dt: datetime) -> datetime:
    if dt.hour < WORK_START_HOUR:
        return dt.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    elif dt.hour >= WORK_END_HOUR:
        nxt = dt + timedelta(days=1)
        return nxt.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    return dt

def get_workday_end(dt: datetime) -> datetime:
    return dt.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)

def find_free_slot(res: ResourceObj, from_dt: datetime, duration_hours: int):
    current = normalize_to_workday(from_dt)
    for _ in range(5000):
        w_end = get_workday_end(current)
        candidate_end = current + timedelta(hours=duration_hours)

        if candidate_end > w_end:
            nxt = current + timedelta(days=1)
            current = nxt.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
            continue

        conflict = False
        for slot in res.busy:
            if not (candidate_end <= slot.start or current >= slot.end):
                current = normalize_to_workday(slot.end)
                conflict = True
                break

        if conflict:
            continue
        return current
    return None

def insert_busy_slot(res: ResourceObj, slot: TimeSlot):
    idx = 0
    while idx < len(res.busy) and res.busy[idx].start < slot.start:
        idx += 1
    res.busy.insert(idx, slot)

# ==================== ПРАВИЛА ПРИОРИТЕТА ====================

def sort_orders(orders: list[OrderObj], rule: str) -> list[OrderObj]:
    rule = rule.upper()
    if rule == "FIFO":
        # По порядку поступления (по ID / номеру)
        return sorted(orders, key=lambda o: o.id)
    elif rule == "EDD":
        # Earliest Due Date: сначала самые срочные по дедлайну
        return sorted(orders, key=lambda o: o.deadline)
    elif rule == "SPT":
        # Shortest Processing Time: сначала короткие заказы
        return sorted(orders, key=lambda o: o.total_duration())
    elif rule == "LPT":
        # Longest Processing Time: сначала самые длительные заказы
        return sorted(orders, key=lambda o: -o.total_duration())
    elif rule == "WSPT":
        # Weighted Shortest Processing Time: по убыванию (вес / длительность)
        return sorted(orders, key=lambda o: -(o.weight / max(1, o.total_duration())))
    else:
        raise ValueError(f"Неизвестное правило приоритета: {rule}")

# ==================== ДВИЖОК ПЛАНИРОВАНИЯ ====================

def run_schedule(resources: list[ResourceObj], orders: list[OrderObj]):
    working_res = [ResourceObj(r.id, r.name, r.category, r.type, r.priority) for r in resources]
    schedule_records = []
    order_end_times = {}

    for order in orders:
        current = normalize_to_workday(order.start_time)
        order_failed = False
        max_end = current

        for op in order.operations:
            if order_failed:
                schedule_records.append({
                    "order_id": order.id, "operation_id": op.id,
                    "employee_id": working_res[0].id, "machine_id": None,
                    "start_time": current, "end_time": current,
                    "is_success": False, "fail_reason": "Срыв предыдущего этапа"
                })
                continue

            req_emp = op.emp_type.strip().lower()
            req_mach = op.mach_type.strip().lower() if op.mach_type else ""

            best_emp_idx = -1
            best_mach_idx = -1
            best_start = None
            best_score = float("-inf")

            for e_idx, emp in enumerate(working_res):
                if emp.category != "сотрудник" or emp.type.strip().lower() != req_emp:
                    continue

                emp_free = find_free_slot(emp, current, op.duration)
                if not emp_free:
                    continue

                if not req_mach:
                    st = emp_free
                    score = emp.priority * 1000 - int(st.timestamp())
                    if score > best_score:
                        best_score = score
                        best_emp_idx = e_idx
                        best_mach_idx = -1
                        best_start = st
                else:
                    for m_idx, mach in enumerate(working_res):
                        if mach.category != "станок" or mach.type.strip().lower() != req_mach:
                            continue

                        cur_joint = current
                        joint_start = None
                        for _ in range(50):
                            ef = find_free_slot(emp, cur_joint, op.duration)
                            mf = find_free_slot(mach, cur_joint, op.duration)
                            if not ef or not mf: break
                            if ef == mf:
                                joint_start = ef
                                break
                            cur_joint = max(ef, mf)

                        if joint_start:
                            score = emp.priority * 1000 + mach.priority * 500 - int(joint_start.timestamp())
                            if score > best_score:
                                best_score = score
                                best_emp_idx = e_idx
                                best_mach_idx = m_idx
                                best_start = joint_start

            if best_emp_idx == -1 or not best_start:
                schedule_records.append({
                    "order_id": order.id, "operation_id": op.id,
                    "employee_id": working_res[0].id, "machine_id": None,
                    "start_time": current, "end_time": current,
                    "is_success": False, "fail_reason": "Дефицит мощностей"
                })
                order_failed = True
                continue

            start_t = best_start
            end_t = start_t + timedelta(hours=op.duration)
            insert_busy_slot(working_res[best_emp_idx], TimeSlot(start_t, end_t))
            if best_mach_idx != -1:
                insert_busy_slot(working_res[best_mach_idx], TimeSlot(start_t, end_t))

            schedule_records.append({
                "order_id": order.id,
                "operation_id": op.id,
                "employee_id": working_res[best_emp_idx].id,
                "machine_id": working_res[best_mach_idx].id if best_mach_idx != -1 else None,
                "start_time": start_t,
                "end_time": end_t,
                "is_success": True,
                "fail_reason": None
            })
            current = end_t
            if end_t > max_end:
                max_end = end_t

        order_end_times[order.id] = max_end

    return schedule_records, order_end_times

# ==================== МЕТРИКИ ОЦЕНКИ ====================

def evaluate_schedule(orders: list[OrderObj], order_end_times: dict):
    total_weighted_penalty = 0.0
    overdue_count = 0
    max_lateness_hours = 0.0
    last_end_time = datetime.min

    for order in orders:
        end_t = order_end_times.get(order.id, order.start_time)
        if end_t > last_end_time:
            last_end_time = end_t

        if end_t > order.deadline:
            lateness = (end_t - order.deadline).total_seconds() / 3600.0
            if lateness > 0:
                overdue_count += 1
                total_weighted_penalty += lateness * order.weight
                if lateness > max_lateness_hours:
                    max_lateness_hours = lateness

    return {
        "penalty": round(total_weighted_penalty, 2),
        "overdue_count": overdue_count,
        "max_lateness": round(max_lateness_hours, 2),
        "makespan": last_end_time.strftime("%d.%m %H:%M") if last_end_time != datetime.min else "-"
    }

# ==================== ГЕНЕРАТОР НАБОРОВ ====================

def generate_datasets():
    sizes = {"small": 5, "medium": 15, "large": 30}
    base_start = datetime(2026, 10, 1, 8, 0)

    for set_name, count in sizes.items():
        folder = os.path.join("data", set_name)
        os.makedirs(folder, exist_ok=True)

        # Копируем неизменные справочники
        for f_name in ["resources.csv", "products.csv", "operations.csv"]:
            src = os.path.join("data", f_name)
            dst = os.path.join(folder, f_name)
            if os.path.exists(src):
                with open(src, "r", encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
                    fout.write(fin.read())

        # Генерируем заказы с random.seed(42)
        orders_file = os.path.join(folder, "orders.csv")
        with open(orders_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "order_number", "product_id", "priority", "quantity",
                             "start_time", "deadline", "penalty_per_hour", "weight", "status"])
            for i in range(1, count + 1):
                p_id = random.choice([1, 2, 3])
                day_offset = (i - 1) // 3
                start_dt = base_start + timedelta(days=day_offset)
                # Дедлайн от 1 до 3 рабочих дней
                deadline_dt = start_dt + timedelta(days=random.randint(1, 3), hours=random.choice([0, 4, 8]))
                prio = random.randint(1, 10)
                weight = random.randint(1, 5)
                penalty = float(random.choice([300, 500, 800, 1000]))

                writer.writerow([
                    i, f"ЗАК-2026-{i:03d}", p_id, prio, 1,
                    start_dt.strftime("%Y-%m-%d %H:%M"),
                    deadline_dt.strftime("%Y-%m-%d %H:%M"),
                    f"{penalty:.2f}", weight, "Новый"
                ])
    print("[INFO] Наборы данных (small: 5, medium: 15, large: 30) успешно сгенерированы в папке data/.")

# ==================== ОСНОВНОЙ ПРОГОН (15 ТЕСТОВ) ====================

def load_objects_from_db():
    raw_res = database.get_resources()
    raw_prods = database.get_products()
    raw_ops = database.get_operations()
    raw_ords = database.get_orders()

    resources = [ResourceObj(r["id"], r["name"], r["category"], r["type"], r["priority"]) for r in raw_res]
    ops_by_prod = {}
    for o in raw_ops:
        p_id = o["product_id"]
        if p_id not in ops_by_prod:
            ops_by_prod[p_id] = []
        ops_by_prod[p_id].append(OperationObj(
            o["id"], o["product_id"], o["step_number"], o["name"],
            o["duration"], o["required_emp_type"], o["required_mach_type"]
        ))

    orders = []
    for ord_dict in raw_ords:
        obj = OrderObj(
            ord_dict["id"], ord_dict["order_number"], ord_dict["product_id"],
            ord_dict["priority"], ord_dict["quantity"],
            ord_dict["start_time"], ord_dict["deadline"],
            float(ord_dict["penalty_per_hour"]), int(ord_dict.get("weight", 1))
        )
        obj.operations = ops_by_prod.get(obj.product_id, []).copy()
        orders.append(obj)

    return resources, orders

def run_benchmark():
    generate_datasets()
    rules = ["FIFO", "EDD", "SPT", "LPT", "WSPT"]
    datasets = [("Малый (5)", "small"), ("Средний (15)", "medium"), ("Большой (30)", "large")]
    results_table = []

    last_schedule_to_save = None

    print("\n" + "=" * 110)
    print("ЗАПУСК СРАВНИТЕЛЬНОГО АНАЛИЗА 5 ПРАВИЛ ПРИОРИТЕТА НА 3 НАБОРАХ ДАННЫХ")
    print("=" * 110)

    for set_title, set_dir in datasets:
        # Перезагружаем БД текущим датасетом через database.py
        database.init_from_csv(data_dir=os.path.join("data", set_dir))
        resources, orders = load_objects_from_db()

        for rule in rules:
            t_start = time.perf_counter()
            ordered = sort_orders(orders, rule)
            sched_records, end_times = run_schedule(resources, ordered)
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            metrics = evaluate_schedule(ordered, end_times)
            last_schedule_to_save = sched_records

            results_table.append({
                "rule": rule,
                "dataset": set_title,
                "penalty": metrics["penalty"],
                "overdue_count": metrics["overdue_count"],
                "max_lateness": metrics["max_lateness"],
                "makespan": metrics["makespan"],
                "time_ms": f"{t_elapsed_ms:.2f}"
            })

    # Печать итоговой сводной таблицы из 15 строк
    print("\n" + "-" * 110)
    print(f"{'Правило':<8} | {'Набор данных':<14} | {'Взвеш. штраф':<14} | {'Просрочено':<11} | {'Макс. просрочка (ч)':<20} | {'Окончание':<12} | {'Время (мс)'}")
    print("-" * 110)
    for r in results_table:
        print(f"{r['rule']:<8} | {r['dataset']:<14} | {r['penalty']:<14} | {r['overdue_count']:<11} | {r['max_lateness']:<20} | {r['makespan']:<12} | {r['time_ms']}")
    print("-" * 110)

    if last_schedule_to_save:
        database.save_schedule(last_schedule_to_save)
        database.export_schedule_to_csv("schedule.csv")
        print("\n[INFO] Вывод последнего сохраненного расписания из базы данных:")
        database.print_schedule_table()

if __name__ == "__main__":
    run_benchmark()