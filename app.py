import csv
import io
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import database
import benchmark

app = FastAPI(
    title="LOOM Manufacturing Scheduling API",
    description="REST API оперативно-календарного планирования производства",
    version="1.0.0"
)


# ===================== Pydantic-схемы валидации =====================

class ResourceCreate(BaseModel):
    name: str = Field(..., example="Токарно-винторезный станок 16К20")
    type: str = Field(..., example="токарный станок")
    category: str = Field(..., example="станок", description="'сотрудник' или 'станок'")
    priority: int = Field(default=1, ge=1, le=100)


class OrderCreate(BaseModel):
    order_number: str = Field(..., example="ЗАК-2026-999")
    product_id: int = Field(..., example=1)
    priority: int = Field(default=1, ge=1, le=100)
    start_time: datetime = Field(..., example="2026-10-01T08:00:00")
    deadline: datetime = Field(..., example="2026-10-02T16:00:00")
    penalty_per_hour: float = Field(default=0.0, ge=0.0)
    weight: int = Field(default=1, ge=1, le=5)


class ScheduleRunRequest(BaseModel):
    rule: str = Field(default="FIFO", description="Правило приоритета: FIFO, EDD, SPT, LPT, WSPT")


# ===================== ЭНДПОИНТЫ API =====================

# 1. Справочники и ресурсы (GET / POST)
@app.get("/api/resources", summary="Получить список всех ресурсов")
def get_resources():
    return database.get_resources()


@app.post("/api/resources", status_code=status.HTTP_201_CREATED, summary="Добавить ресурс")
def add_resource(res: ResourceCreate):
    if res.category not in ["сотрудник", "станок"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория ресурса должна быть 'сотрудник' или 'станок'"
        )
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO resources (name, type, category, priority)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, type, category, priority;
            """, (res.name, res.type, res.category, res.priority))
            new_res = cur.fetchone()
    return new_res


# 2. Изделия и операции
@app.get("/api/products", summary="Получить список всех изделий")
def get_products():
    return database.get_products()


@app.get("/api/products/{product_id}/operations", summary="Получить операции изделия")
def get_product_operations(product_id: int):
    # Проверяем наличие изделия
    prods = database.get_products()
    if not any(p["id"] == product_id for p in prods):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Изделие с ID {product_id} не найдено")

    all_ops = database.get_operations()
    ops = [op for op in all_ops if op["product_id"] == product_id]
    return sorted(ops, key=lambda x: x["step_number"])


# 3. Заказы (GET / POST / DELETE)
@app.get("/api/orders", summary="Получить список всех заказов")
def get_orders():
    return database.get_orders()


@app.post("/api/orders", status_code=status.HTTP_201_CREATED, summary="Создать новый заказ")
def create_order(order: OrderCreate):
    # Валидация: дедлайн строго позже старта
    if order.deadline <= order.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дедлайн должен быть строго позже времени начала"
        )

    # Валидация: изделие существует в БД
    prods = database.get_products()
    if not any(p["id"] == order.product_id for p in prods):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Изделие с ID {order.product_id} не существует в базе данных"
        )

    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders (order_number, product_id, priority, start_time, deadline, penalty_per_hour, weight)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """, (order.order_number, order.product_id, order.priority, order.start_time, order.deadline, order.penalty_per_hour, order.weight))
            new_order = cur.fetchone()
    return new_order


@app.delete("/api/orders/{order_id}", summary="Удалить заказ")
def delete_order(order_id: int):
    orders = database.get_orders()
    if not any(o["id"] == order_id for o in orders):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ с ID {order_id} не найден"
        )

    database.delete_order(order_id)
    return {"status": "success", "message": f"Заказ {order_id} успешно удален"}


# 4. Импорт заказов из CSV (POST /api/orders/import)
@app.post("/api/orders/import", summary="Импорт заказов из CSV-файла")
async def import_orders_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл должен иметь расширение .csv"
        )

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    valid_prods = {p["id"] for p in database.get_products()}

    accepted = 0
    rejected = 0
    errors = []

    with database.get_connection() as conn:
        with conn.cursor() as cur:
            for row_idx, row in enumerate(reader, start=1):
                try:
                    p_id = int(row["product_id"])
                    if p_id not in valid_prods:
                        raise ValueError(f"Изделие {p_id} не найдено")

                    s_time = datetime.fromisoformat(row["start_time"].replace(" ", "T"))
                    d_time = datetime.fromisoformat(row["deadline"].replace(" ", "T"))
                    if d_time <= s_time:
                        raise ValueError("Дедлайн раньше начала")

                    cur.execute("""
                        INSERT INTO orders (order_number, product_id, priority, start_time, deadline, penalty_per_hour, weight)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        row.get("order_number", f"ИМП-{row_idx}"),
                        p_id,
                        int(row.get("priority", 1)),
                        s_time,
                        d_time,
                        float(row.get("penalty_per_hour", 0.0)),
                        int(row.get("weight", 1))
                    ))
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


# 5. Расписание: расчет, просмотр и экспорт
@app.post("/api/schedule/run", summary="Запуск построения расписания")
def run_schedule_endpoint(req: ScheduleRunRequest):
    rule = req.rule.upper()
    if rule not in ["FIFO", "EDD", "SPT", "LPT", "WSPT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимое правило. Используйте: FIFO, EDD, SPT, LPT, WSPT"
        )

    resources, orders = benchmark.load_objects_from_db()
    if not resources or not orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно данных (ресурсов или заказов) для планирования"
        )

    sorted_orders = benchmark.sort_orders(orders, rule)
    records, end_times = benchmark.run_schedule(resources, sorted_orders)
    metrics = benchmark.evaluate_schedule(sorted_orders, end_times)

    # Сохраняем в PostgreSQL и в CSV
    database.save_schedule(records)
    database.export_schedule_to_csv("schedule.csv")

    return {
        "status": "success",
        "rule_applied": rule,
        "operations_count": len(records),
        "total_penalty": metrics["penalty"],
        "metrics": metrics
    }


@app.get("/api/schedule", summary="Получить текущее расписание из БД")
def get_current_schedule():
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id, o.order_number, op.name AS operation_name,
                       r_emp.name AS employee_name, r_mach.name AS machine_name,
                       s.start_time, s.end_time, s.is_success, s.fail_reason
                FROM schedule s
                JOIN orders o ON s.order_id = o.id
                JOIN operations op ON s.operation_id = op.id
                JOIN resources r_emp ON s.employee_id = r_emp.id
                LEFT JOIN resources r_mach ON s.machine_id = r_mach.id
                ORDER BY s.start_time;
            """)
            items = cur.fetchall()

    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расписание еще не построено")
    return items


@app.get("/api/schedule/export", summary="Скачать расписание в виде CSV-файла")
def export_schedule_file():
    filepath = "schedule.csv"
    if not os.path.exists(filepath):
        database.export_schedule_to_csv(filepath)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл расписания отсутствует")

    return FileResponse(
        path=filepath,
        filename="schedule.csv",
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=schedule.csv"}
    )