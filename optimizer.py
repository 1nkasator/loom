 
import math
import random
import time
from typing import List, Tuple, Dict, Any

# Импортируем симулятор планирования из уже готового модуля benchmark.py
import benchmark


def plan(
    order_list: List[Any],
    resource_list: List[Any],
    initial_rule: str = "WSPT",
    initial_temp: float = 1000.0,
    cooling_rate: float = 0.995,
    max_iterations: int = 1500,
    time_limit: float = 5.0
) -> Tuple[List[Dict[str, Any]], float, int, float]:
    """
    Основная функция планирования на основе алгоритма Имитации Отжига (Simulated Annealing).
    
    Параметры:
        order_list: список заказов
        resource_list: список ресурсов
        initial_rule: эвристика начального приближения ("WSPT", "EDD", "FIFO", "SPT")
        initial_temp: начальная температура (T0)
        cooling_rate: коэффициент охлаждения (alpha)
        max_iterations: максимальное количество итераций
        time_limit: ограничение времени работы в секундах (по ТЗ)
        
    Возвращает:
        (best_records, best_penalty, iterations_done, elapsed_time)
    """
    start_time = time.time()
    
    # 1. Стартовое решение через правило приоритета
    current_orders = benchmark.sort_orders(order_list.copy(), initial_rule)
    current_records, current_penalty = benchmark.run_schedule(resource_list, current_orders)
    
    best_orders = list(current_orders)
    best_records = list(current_records)
    best_penalty = current_penalty
    
    temperature = initial_temp
    iterations = 0
    
    # Если заказов меньше двух, переставлять нечего
    if len(order_list) < 2:
        elapsed = time.time() - start_time
        return best_records, best_penalty, iterations, elapsed

    # 2. Основной цикл отжига с ограничением по итерациям И по времени (ТЗ)
    while iterations < max_iterations and (time.time() - start_time) < time_limit:
        iterations += 1
        
        # Генерируем соседнее решение: меняем местами 2 случайных заказа
        neighbor_orders = list(current_orders)
        i, j = random.sample(range(len(neighbor_orders)), 2)
        neighbor_orders[i], neighbor_orders[j] = neighbor_orders[j], neighbor_orders[i]
        
        # Оцениваем расписание соседа
        neighbor_records, neighbor_penalty = benchmark.run_schedule(resource_list, neighbor_orders)
        
        delta = neighbor_penalty - current_penalty
        
        # Если стало лучше (штраф уменьшился) — принимаем сразу
        if delta < 0:
            current_orders = neighbor_orders
            current_penalty = neighbor_penalty
            
            # Запоминаем глобальный рекорд
            if neighbor_penalty < best_penalty:
                best_penalty = neighbor_penalty
                best_orders = list(neighbor_orders)
                best_records = list(neighbor_records)
        else:
            # Если стало хуже — принимаем с вероятностью exp(-delta / T)
            probability = math.exp(-delta / max(temperature, 1e-6))
            if random.random() < probability:
                current_orders = neighbor_orders
                current_penalty = neighbor_penalty
        
        # Охлаждение
        temperature *= cooling_rate

    elapsed_time = time.time() - start_time
    return best_records, best_penalty, iterations, elapsed_time


# -------------------------------------------------------------
# Тестовый прогон: запуск файла напрямую через "python optimizer.py"
# -------------------------------------------------------------
if __name__ == "__main__":
    print("=== ТЕСТ АЛГОРИТМА ИМИТАЦИИ ОТЖИГА (SIMULATED ANNEALING) ===")
    
    # Загружаем объекты из БД
    resources, orders = benchmark.load_objects_from_db()
    
    print(f"Всего ресурсов: {len(resources)}, заказов: {len(orders)}")
    
    # 1. Расчёт по простому правилу WSPT (базовая линия)
    wspt_orders = benchmark.sort_orders(orders.copy(), "WSPT")
    _, wspt_pen = benchmark.run_schedule(resources, wspt_orders)
    print(f"\nБазовый штраф по правилу WSPT: {wspt_pen:.2f} руб.")
    
    # 2. Оптимизация отжигом (лимит 3 секунды)
    print("\nЗапуск Simulated Annealing (лимит 3.0 сек)...")
    records, opt_pen, iters, t_calc = plan(orders, resources, initial_rule="WSPT", time_limit=3.0)
    
    diff = wspt_pen - opt_pen
    percent = (diff / wspt_pen * 100) if wspt_pen > 0 else 0.0
    
    print(f"Штраф после оптимизации:       {opt_pen:.2f} руб.")
    print(f"Выполнено итераций:            {iters}")
    print(f"Затраченное время:             {t_calc:.3f} сек")
    print(f"Удалось выиграть:              {diff:.2f} руб. ({percent:.1f}%)")