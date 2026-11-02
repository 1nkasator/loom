import csv
import io
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database
import benchmark
import optimizer

app = FastAPI(
    title="LOOM Manufacturing Scheduling API",
    description="REST API и веб-платформа оперативно-календарного планирования производства",
    version="2.0.0"
)

# Монтируем статические файлы для веб-интерфейса
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ===================== Pydantic-схемы валидации =====================

class ResourceCreate(BaseModel):
    name: str = Field(..., example="Токарно-винторезный станок 16К20")
    type: str = Field(..., example="токарный станок")
    category: str = Field(..., example="станок", description="'сотрудник' или 'станок'")
    priority: int = Field(default=1, ge=1, le=100)


class ProductCreate(BaseModel):
    name: str = Field(..., example="Муфта зубчатая")
    description: Optional[str] = Field(default="", example="Узел передачи крутящего момента")


class OrderCreate(BaseModel):
    order_number: str = Field(..., example="ЗАК-2026-999")
    product_id: int = Field(..., example=1)
    priority: int = Field(default=1, ge=1, le=100)
    quantity: int = Field(default=1, ge=1)
    start_time: datetime = Field(..., example="2026-10-01T08:00:00")
    deadline: datetime = Field(..., example="2026-10-02T16:00:00")
    penalty_per_hour: float = Field(default=0.0, ge=0.0)
    weight: int = Field(default=1, ge=1, le=5)


class ScheduleRunRequest(BaseModel):
    rule: str = Field(default="FIFO", description="Правило или алгоритм: FIFO, EDD, SPT, LPT, WSPT, ANNEALING")
    time_limit: Optional[float] = Field(default=3.0, ge=0.1, le=60.0, description="Лимит времени для алгоритма отжига (сек)")
    max_iterations: Optional[int] = Field(default=1500, ge=10, le=50000, description="Лимит итераций для отжига")


# ===================== ГЛАВНАЯ СТРАНИЦА (WEB UI) =====================

@app.get("/", response_class=HTMLResponse, summary="Главная страница веб-интерфейса")
def index():
    html_path = os.path.join("static", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Веб-интерфейс Loom загружается...</h1>"


# ===================== ЭНДПОИНТЫ API: РЕСУРСЫ =====================

@app.get("/api/resources", summary="Получить список всех ресурсов")
def get_resources():
    return database.get_resources()


@app.post("/api/resources", status_code=status.HTTP_201_CREATED, summary="Добавить ресурс")
def add_resource(res: ResourceCreate):
    cat = res.category.strip().lower()
    if cat not in ["сотрудник", "станок"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория ресурса должна быть 'сотрудник' или 'станок'"
        )
    new_id = database.insert_resource(
        name=res.name.strip(),
        category=cat,
        type_=res.type.strip(),
        priority=res.priority,
        is_active=True
    )
    return {"id": new_id, "name": res.name, "category": cat, "type": res.type, "priority": res.priority}


@app.delete("/api/resources/{res_id}", summary="Удалить ресурс")
def delete_resource_endpoint(res_id: int):
    resources = database.get_resources(only_active=False)
    if not any(r["id"] == res_id for r in resources):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ресурс с ID {res_id} не найден")
    database.delete_resource(res_id)
    return {"status": "success", "message": f"Ресурс {res_id} успешно удален"}


# ===================== ЭНДПОИНТЫ API: ИЗДЕЛИЯ И ОПЕРАЦИИ =====================

@app.get("/api/products", summary="Получить список всех изделий")
def get_products():
    return database.get_products()


@app.post("/api/products", status_code=status.HTTP_201_CREATED, summary="Добавить новое изделие")
def create_product(prod: ProductCreate):
    new_id = database.insert_product(name=prod.name.strip(), description=prod.description.strip())
    return {"id": new_id, "name": prod.name, "description": prod.description}


@app.get("/api/products/{product_id}/operations", summary="Получить операции техпроцесса изделия")
def get_product_operations(product_id: int):
    prods = database.get_products()
    if not any(p["id"] == product_id for p in prods):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Изделие с ID {product_id} не найдено")

    ops = database.get_operations(product_id=product_id)
    return ops


# ===================== ЭНДПОИНТЫ API: ЗАКАЗЫ =====================

@app.get("/api/orders", summary="Получить список всех заказов")
def get_orders():
    return database.get_orders()


@app.post("/api/orders", status_code=status.HTTP_201_CREATED, summary="Создать новый заказ")
def create_order(order: OrderCreate):
    if order.deadline <= order.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок 'закончить не позднее' (дедлайн) должен быть строго позже срока 'начать не ранее'"
        )

    prods = database.get_products()
    if not any(p["id"] == order.product_id for p in prods):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Указанный вид изделия (ID {order.product_id}) не существует в базе данных"
        )

    new_id = database.insert_order(
        order_number=order.order_number.strip(),
        product_id=order.product_id,
        priority=order.priority,
        quantity=order.quantity,
        start_time=order.start_time,
        deadline=order.deadline,
        penalty_per_hour=order.penalty_per_hour,
        weight=order.weight,
        status="Новый"
    )
    return {
        "id": new_id,
        "order_number": order.order_number,
        "product_id": order.product_id,
        "priority": order.priority,
        "start_time": order.start_time,
        "deadline": order.deadline
    }


@app.delete("/api/orders/{order_id}", summary="Удалить заказ")
def delete_order_endpoint(order_id: int):
    orders = database.get_orders()
    if not any(o["id"] == order_id for o in orders):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ с идентификатором {order_id} не найден"
        )

    database.delete_order(order_id)
    return {"status": "success", "message": f"Заказ {order_id} успешно удален"}


@app.post("/api/orders/import", summary="Импорт заказов из CSV-файла")
async def import_orders_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый формат файла. Требуется файл с расширением .csv"
        )

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1251", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    valid_prods = {p["id"] for p in database.get_products()}

    accepted = 0
    rejected = 0
    errors = []

    for row_idx, row in enumerate(reader, start=2):
        try:
            if "product_id" not in row or not row["product_id"]:
                raise ValueError("Отсутствует обязательное поле product_id")
            p_id = int(row["product_id"])
            if p_id not in valid_prods:
                raise ValueError(f"Изделие с ID {p_id} не существует в базе")

            st = database.parse_dt(row["start_time"])
            dl = database.parse_dt(row["deadline"])
            if dl <= st:
                raise ValueError("Дедлайн меньше или равен дате начала")

            ord_num = row.get("order_number", f"ИМП-{row_idx}").strip()
            prio = int(row.get("priority", 1))
            qty = int(row.get("quantity", 1))
            penalty = float(row.get("penalty_per_hour", 0.0))
            weight = int(row.get("weight", 1))

            database.insert_order(
                order_number=ord_num,
                product_id=p_id,
                priority=prio,
                quantity=qty,
                start_time=st,
                deadline=dl,
                penalty_per_hour=penalty,
                weight=weight,
                status="Новый"
            )
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(f"Строка {row_idx}: {str(e)}")

    return {
        "status": "completed",
        "total_processed": accepted + rejected,
        "accepted": accepted,
        "rejected": rejected,
        "errors": errors
    }


# ===================== ЭНДПОИНТЫ API: РАСПИСАНИЕ И ОПТИМИЗАЦИЯ =====================

@app.post("/api/schedule/run", summary="Запуск построения и оптимизации расписания")
def run_schedule_endpoint(req: ScheduleRunRequest):
    rule = req.rule.strip().upper()
    valid_methods = ["FIFO", "EDD", "SPT", "LPT", "WSPT", "ANNEALING", "SA", "SIMULATED_ANNEALING", "ОТЖИГ"]
    if rule not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый метод планирования. Доступны: FIFO, EDD, SPT, LPT, WSPT, ANNEALING"
        )

    resources, orders = benchmark.load_objects_from_db()
    if not resources or not orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно данных в базе: отсутствуют активные ресурсы или заказы"
        )

    # 1. Если выбрана оптимизация Имитацией Отжига (Simulated Annealing)
    if rule in ["ANNEALING", "SA", "SIMULATED_ANNEALING", "ОТЖИГ"]:
        best_records, best_pen, iters, t_calc = optimizer.plan(
            order_list=orders,
            resource_list=resources,
            initial_rule="WSPT",
            time_limit=req.time_limit or 3.0,
            max_iterations=req.max_iterations or 1500
        )
        database.save_schedule(best_records)
        database.export_schedule_to_csv("schedule.csv")

        # Пересчет метрик для лучшего расписания
        best_orders = [o for o in orders]
        _, end_times = benchmark.run_schedule(resources, best_orders)
        metrics = benchmark.evaluate_schedule(best_orders, end_times)
        metrics["penalty"] = round(best_pen, 2)

        return {
            "status": "success",
            "method": "Имитация отжига (Simulated Annealing)",
            "operations_count": len(best_records),
            "iterations": iters,
            "calculation_time_sec": round(t_calc, 3),
            "metrics": metrics
        }

    # 2. Иначе используем конструктивную эвристику (правило приоритета)
    t0 = datetime.now()
    sorted_orders = benchmark.sort_orders(orders, rule)
    records, end_times = benchmark.run_schedule(resources, sorted_orders)
    metrics = benchmark.evaluate_schedule(sorted_orders, end_times)
    t_elapsed = (datetime.now() - t0).total_seconds()

    database.save_schedule(records)
    database.export_schedule_to_csv("schedule.csv")

    return {
        "status": "success",
        "method": f"Правило приоритета ({rule})",
        "operations_count": len(records),
        "calculation_time_sec": round(t_elapsed, 4),
        "metrics": metrics
    }


@app.get("/api/schedule", summary="Получить текущее сохраненное расписание из БД")
def get_current_schedule():
    items = database.get_last_schedule()
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Расписание еще ни разу не строилось либо таблица пуста"
        )
    return items


@app.get("/api/schedule/timeline", summary="Форматированные данные для диаграммы vis.js Timeline")
def get_timeline_data():
    items = database.get_last_schedule()
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расписание отсутствует")

    # Формируем группы (по оборудованию и сотрудникам)
    groups = []
    group_ids = set()

    # Сначала оборудование, затем сотрудники
    for it in items:
        mach = it.get("machine_name")
        if mach and mach != "Вручную":
            g_id = f"mach_{mach}"
            if g_id not in group_ids:
                group_ids.add(g_id)
                groups.append({"id": g_id, "content": f"🛠️ {mach}", "type": "станок"})

    for it in items:
        emp = it["employee_name"]
        g_id = f"emp_{emp}"
        if g_id not in group_ids:
            group_ids.add(g_id)
            groups.append({"id": g_id, "content": f"👤 {emp}", "type": "сотрудник"})

    # Формируем блоки операций
    timeline_items = []
    for it in items:
        is_overdue = it["end_time"] > it["deadline"]
        cls = "item-overdue" if is_overdue else "item-ontime"
        content_text = f"<b>{it['order_number']}</b> #{it['step_number']}: {it['operation_name']}"
        tooltip = (
            f"Заказ: {it['order_number']}<br>"
            f"Операция: {it['operation_name']}<br>"
            f"Сотрудник: {it['employee_name']}<br>"
            f"Станок: {it['machine_name']}<br>"
            f"Начало: {it['start_time'].strftime('%d.%m %H:%M')}<br>"
            f"Конец: {it['end_time'].strftime('%d.%m %H:%M')}<br>"
            f"Статус: {'⚠️ Просрочен' if is_overdue else '✅ В срок'}"
        )

        # Размещаем на дорожке станка, если есть, иначе на дорожке сотрудника
        mach = it.get("machine_name")
        target_group = f"mach_{mach}" if mach and mach != "Вручную" else f"emp_{it['employee_name']}"

        timeline_items.append({
            "id": it["id"],
            "group": target_group,
            "content": content_text,
            "start": it["start_time"].isoformat(),
            "end": it["end_time"].isoformat(),
            "className": cls,
            "title": tooltip
        })

    return {"groups": groups, "items": timeline_items}


@app.get("/api/schedule/export", summary="Выгрузить расписание в виде файла CSV")
def export_schedule_file():
    filepath = "schedule.csv"
    if not os.path.exists(filepath):
        database.export_schedule_to_csv(filepath)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл расписания отсутствует. Сначала запустите расчет расписания."
        )

    return FileResponse(
        path=filepath,
        filename="schedule.csv",
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=schedule.csv"}
    )
