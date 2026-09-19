import sys
import os
import json
from typing import List, Optional

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QMessageBox,
                             QSpinBox, QComboBox, QListWidget, QProgressBar,
                             QTabWidget, QGroupBox, QFileDialog, QScrollArea,
                             QHeaderView, QSplitter, QAbstractItemView,
                             QDialog, QDialogButtonBox, QDoubleSpinBox, QInputDialog,
                             QTreeWidget, QTreeWidgetItem, QDateEdit, QTimeEdit,
                             QListWidgetItem)
from PyQt5.QtCore import QDateTime, Qt, QTime, QRect, QDate, QSettings
from PyQt5.QtGui import QPainter, QColor, QFont, QPen

# ========================== QSS (ТЕМНАЯ ТЕМА) ==========================
DARK_THEME_QSS = """
/* Общие настройки */
QWidget {
    background-color: #1e1e1e;
    color: #dfdfdf;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px 12px;
    color: #dfdfdf;
}
QPushButton:hover { background-color: #333333; border: 1px solid #4CAF50; color: #4CAF50; }
QPushButton:pressed { background-color: #4CAF50; color: #ffffff; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QDateEdit, QTimeEdit {
    background-color: #252526;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 5px;
    color: #dfdfdf;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 1px solid #4CAF50;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: 1px solid #3e3e42;
}
QComboBox::down-arrow {
    image: url('data:image/svg+xml;utf8,<svg width="12" height="12" viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg"><polygon points="2,4 10,4 6,9" fill="%23dfdfdf"/></svg>');
}
QComboBox QAbstractItemView {
    background-color: #252526;
    border: 1px solid #4CAF50;
    selection-background-color: #4CAF50;
}
QListWidget, QTreeWidget { background-color: #252526; border: 1px solid #3e3e42; border-radius: 4px; outline: 0; }
QListWidget::item, QTreeWidget::item { padding: 5px; }
QListWidget::item:hover, QTreeWidget::item:hover { background-color: #2d2d2d; }
QListWidget::item:selected, QTreeWidget::item:selected { background-color: #4CAF50; color: #ffffff; }
QTabWidget::pane { border: 1px solid #3e3e42; border-radius: 4px; top: -1px; }
QTabBar::tab { background-color: #252526; color: #888888; padding: 8px 20px; border: 1px solid #3e3e42; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #1e1e1e; color: #4CAF50; border-top: 2px solid #4CAF50; }
QTabBar::tab:hover:!selected { background-color: #2d2d2d; color: #dfdfdf; }
QGroupBox { border: 1px solid #3e3e42; border-radius: 6px; margin-top: 15px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 5px; color: #4CAF50; }
QProgressBar { background-color: #252526; border: 1px solid #3e3e42; border-radius: 4px; text-align: center; color: #dfdfdf; }
QProgressBar::chunk { background-color: #4CAF50; border-radius: 3px; }
QScrollBar:vertical, QScrollBar:horizontal { background-color: #1e1e1e; width: 10px; height: 10px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background-color: #444444; border-radius: 5px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background-color: #4CAF50; }
QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; }
QHeaderView::section { background-color: #252526; color: #dfdfdf; padding: 5px; border: none; border-right: 1px solid #3e3e42; border-bottom: 1px solid #3e3e42; font-weight: bold; }
QSplitter::handle { background-color: #3e3e42; }
"""


# ========================== ЛИЦЕНЗИРОВАНИЕ (АНТИ-ПИРАТСТВО) ==========================
class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Активация продукта Loom")
        self.setFixedSize(450, 160)
        layout = QVBoxLayout(self)

        self.info_label = QLabel(
            "Программа не активирована.\n"
            "Пожалуйста, введите лицензионный ключ для продолжения:\n"
            "(Для тестирования введи ключ: XXXX-XXXX-XXXX)"
        )
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX")

        self.btn = QPushButton("Активировать программу")
        self.btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn.clicked.connect(self.check_key)

        layout.addWidget(self.info_label)
        layout.addWidget(self.key_input)
        layout.addStretch()
        layout.addWidget(self.btn)

    def check_key(self):
        key = self.key_input.text().strip()
        if key == "MAXX-2026-WORK":
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка активации", "Неверный или истекший лицензионный ключ!")


def verify_license():
    settings = QSettings("MyCompany", "PlannerPro")
    is_activated = settings.value("is_activated", False, type=bool)

    if not is_activated:
        dlg = LicenseDialog()
        dlg.setStyleSheet(DARK_THEME_QSS)
        if dlg.exec_() == QDialog.Accepted:
            settings.setValue("is_activated", True)
            return True
        else:
            return False
    return True


# -------------------------- Модели ---------------------------------

class TimeSlot:
    def __init__(self, start: QDateTime, end: QDateTime):
        self.start = start
        self.end = end


class Resource:
    def __init__(self, id: int, name: str, type_: str, category: str, priority: int):
        self.id = id
        self.name = name
        self.type = type_
        self.category = category
        self.priority = priority
        self.busy: List[TimeSlot] = []


class Process:
    def __init__(self, id: int, name: str, duration: int, emp_type: str, mach_type: str = ""):
        self.id = id
        self.name = name
        self.duration = duration
        self.emp_type = emp_type
        self.mach_type = mach_type


class Product:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.processes: List[Process] = []

    def total_duration(self) -> int:
        return sum(p.duration for p in self.processes)


class Order:
    def __init__(self, id: int, name: str, priority: int, start: QDateTime,
                 deadline: QDateTime, product: Product, penalty_per_hour: float = 0.0):
        self.id = id
        self.name = name
        self.priority = priority
        self.start = start
        self.deadline = deadline
        self.product = product
        self.penalty_per_hour = penalty_per_hour
        self.operations = product.processes.copy() if product else []


class ScheduleItem:
    def __init__(self, order_id: int, process_id: int, employee: str, machine: str,
                 start: QDateTime, end: QDateTime, success: bool, fail_reason: str = ""):
        self.orderId = order_id
        self.processId = process_id
        self.employee = employee
        self.machine = machine
        self.start = start
        self.end = end
        self.success = success
        self.fail_reason = fail_reason


# -------------------------- Рабочий день ---------------------------------

WORK_START_HOUR = 8
WORK_END_HOUR = 16


def normalize_to_workday(dt: QDateTime) -> QDateTime:
    if dt.time().hour() < WORK_START_HOUR:
        return QDateTime(dt.date(), QTime(WORK_START_HOUR, 0))
    elif dt.time().hour() >= WORK_END_HOUR:
        return QDateTime(dt.date().addDays(1), QTime(WORK_START_HOUR, 0))
    return dt


def get_workday_end(dt: QDateTime) -> QDateTime:
    return QDateTime(dt.date(), QTime(WORK_END_HOUR, 0))


def calculate_estimated_end(start_dt: QDateTime, duration_hours: int) -> QDateTime:
    current = normalize_to_workday(start_dt)
    remaining_hours = float(duration_hours)

    while remaining_hours > 0:
        work_end = get_workday_end(current)
        hours_today = current.secsTo(work_end) / 3600.0

        if remaining_hours <= hours_today:
            current = current.addSecs(int(remaining_hours * 3600))
            remaining_hours = 0
        else:
            remaining_hours -= hours_today
            current = QDateTime(current.date().addDays(1), QTime(WORK_START_HOUR, 0))
    return current


# -------------------------- Планировщик ------------------------------

def insert_busy_slot(res: Resource, slot: TimeSlot):
    i = 0
    while i < len(res.busy) and res.busy[i].start < slot.start:
        i += 1
    res.busy.insert(i, slot)


def find_free_slot(res: Resource, from_dt: QDateTime, duration_hours: int) -> Optional[QDateTime]:
    if duration_hours <= 0:
        return None
    current = normalize_to_workday(from_dt)
    max_iter = 10000
    for _ in range(max_iter):
        work_end = get_workday_end(current)
        end_candidate = current.addSecs(duration_hours * 3600)

        if end_candidate > work_end:
            current = QDateTime(current.date().addDays(1), QTime(WORK_START_HOUR, 0))
            continue

        conflict = False
        for slot in res.busy:
            if not (end_candidate <= slot.start or current >= slot.end):
                current = normalize_to_workday(slot.end)
                conflict = True
                break

        if conflict:
            continue

        return current
    return None


class Scheduler:
    def __init__(self, resources: List[Resource], orders: List[Order]):
        self.resources = resources
        self.orders = orders

    def schedule(self) -> tuple[List[ScheduleItem], float]:
        result = []
        working_res = [Resource(r.id, r.name, r.type, r.category, r.priority) for r in self.resources]
        for wr in working_res:
            wr.busy = []

        sorted_orders = sorted(self.orders, key=lambda o: (-o.priority, o.deadline))
        total_penalty = 0.0

        for order in sorted_orders:
            ops = order.operations
            current = normalize_to_workday(order.start)
            order_failed = False
            order_end = order.start

            for op in ops:
                if order_failed:
                    result.append(ScheduleItem(order.id, op.id, "НЕ НАЗНАЧЕНО", "-",
                                               current, current, False, "Предыдущая операция не назначена"))
                    continue

                if not op.emp_type or op.emp_type.strip() == "":
                    result.append(ScheduleItem(order.id, op.id, "НЕТ ТРЕБОВАНИЯ", "-",
                                               current, current, False, "Не указан тип сотрудника"))
                    order_failed = True
                    continue

                best_emp_idx = -1
                best_mach_idx = -1
                best_start = None
                best_score = float("-inf")
                fail_reason = ""

                req_emp = op.emp_type.strip().lower()
                req_mach = op.mach_type.strip().lower() if op.mach_type else ""

                for e_idx, emp in enumerate(working_res):
                    if emp.category != "сотрудник" or emp.type.strip().lower() != req_emp:
                        continue

                    emp_free = find_free_slot(emp, current, op.duration)

                    if emp_free is None:
                        continue

                    if not req_mach:
                        start = emp_free
                        end = start.addSecs(op.duration * 3600)

                        score = emp.priority * 1000 - start.toSecsSinceEpoch()
                        if score > best_score:
                            best_score = score
                            best_emp_idx = e_idx
                            best_mach_idx = -1
                            best_start = start
                    else:
                        for m_idx, mach in enumerate(working_res):
                            if mach.category != "станок" or mach.type.strip().lower() != req_mach:
                                continue

                            current_joint = current
                            joint_start = None
                            for _ in range(100):
                                ef = find_free_slot(emp, current_joint, op.duration)
                                if not ef: break
                                mf = find_free_slot(mach, current_joint, op.duration)
                                if not mf: break

                                if ef == mf:
                                    joint_start = ef
                                    break
                                elif ef > mf:
                                    current_joint = ef
                                else:
                                    current_joint = mf

                            if joint_start is None:
                                continue

                            start = joint_start
                            end = start.addSecs(op.duration * 3600)

                            score = emp.priority * 1000 + mach.priority * 500 - start.toSecsSinceEpoch()
                            if score > best_score:
                                best_score = score
                                best_emp_idx = e_idx
                                best_mach_idx = m_idx
                                best_start = start

                if best_emp_idx == -1 or best_start is None:
                    if not any(r.category == "сотрудник" and r.type.strip().lower() == req_emp for r in working_res):
                        fail_reason = f"Нет сотрудника типа '{op.emp_type}'"
                    elif req_mach and not any(
                            r.category == "станок" and r.type.strip().lower() == req_mach for r in working_res):
                        fail_reason = f"Нет станка типа '{op.mach_type}'"
                    else:
                        fail_reason = "Невозможно найти свободное время"
                    result.append(ScheduleItem(order.id, op.id, fail_reason, "-",
                                               current, current, False, fail_reason))
                    order_failed = True
                    continue

                start = best_start
                end = start.addSecs(op.duration * 3600)
                insert_busy_slot(working_res[best_emp_idx], TimeSlot(start, end))
                if best_mach_idx != -1:
                    insert_busy_slot(working_res[best_mach_idx], TimeSlot(start, end))

                emp_name = working_res[best_emp_idx].name
                mach_name = working_res[best_mach_idx].name if best_mach_idx != -1 else "нет"
                result.append(ScheduleItem(order.id, op.id, emp_name, mach_name, start, end, True))

                current = end
                # ФИКС: Используем строгий if вместо встроенного max() для надежности расчета дедлайна
                if end > order_end:
                    order_end = end

            # РАСЧЕТ ШТРАФА ПО ФОРМУЛЕ
            if not order_failed and ops and order_end > order.deadline:
                overdue_hours = order.deadline.secsTo(order_end) / 3600.0
                if overdue_hours > 0:
                    penalty = overdue_hours * order.penalty_per_hour
                    total_penalty += penalty

        return result, total_penalty


# -------------------------- Диалог выбора продукта --------------------

class SelectProductDialog(QDialog):
    def __init__(self, products: List[Product], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите изделие")
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        for p in products:
            self.combo.addItem(f"{p.name} (ID:{p.id})", p.id)
        layout.addWidget(QLabel("Изделие:"))
        layout.addWidget(self.combo)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected_product_id(self):
        return self.combo.currentData()


# -------------------------- Виджет Ганта ---------------------------------

class GanttWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.schedule = []
        self.pairs = []
        self.scale = 1.0
        self.base_width = 800
        self.setMouseTracking(True)

    def zoom_in(self):
        self.scale *= 1.25
        self.setMinimumWidth(int(self.base_width * self.scale))
        self.update()

    def zoom_out(self):
        self.scale = max(0.5, self.scale / 1.25)
        self.setMinimumWidth(int(self.base_width * self.scale))
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def set_schedule(self, schedule: List[ScheduleItem]):
        self.schedule = schedule
        self.pairs = []
        for item in self.schedule:
            if not item.success: continue
            pair = (item.employee, item.machine)
            if pair not in self.pairs:
                self.pairs.append(pair)

        row_height = 40
        header_height = 30
        needed_height = header_height + len(self.pairs) * row_height + 40
        self.setMinimumHeight(max(300, needed_height))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        if not self.schedule or not self.pairs:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных для отображения")
            return

        global_min = None
        global_max = None
        for item in self.schedule:
            if not item.success:
                continue
            if global_min is None or item.start < global_min:
                global_min = item.start
            if global_max is None or item.end > global_max:
                global_max = item.end

        if global_min is None or global_max is None or global_min >= global_max:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет успешных операций в расписании")
            return

        total_secs = global_min.secsTo(global_max)
        if total_secs <= 0:
            total_secs = 3600

        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()

        max_text_width = 0
        for emp, mach in self.pairs:
            label = f"{emp} / {mach}" if mach and mach != "нет" else emp
            max_text_width = max(max_text_width, fm.boundingRect(label).width())

        left_margin = max(250, max_text_width + 30)
        right_margin = 50
        chart_width = self.width() - left_margin - right_margin
        row_height = 40
        header_height = 30

        painter.setFont(QFont("Segoe UI", 8))
        for i in range(6):
            x = left_margin + i * chart_width // 5
            dt = global_min.addSecs(i * total_secs // 5)
            painter.setPen(QPen(QColor("#3e3e42"), 1, Qt.DashLine))
            painter.drawLine(x, header_height, x, self.height())
            painter.setPen(QColor("#dfdfdf"))
            painter.drawText(x - 15, 20, dt.toString("dd.MM HH:mm"))

        painter.setFont(font)
        for i, (emp, mach) in enumerate(self.pairs):
            y = header_height + i * row_height
            rect = QRect(5, y, left_margin - 15, row_height)
            label = f"{emp} / {mach}" if mach and mach != "нет" else emp
            painter.setPen(QColor("#dfdfdf"))
            painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, label)
            painter.setPen(QPen(QColor("#2d2d2d"), 1))
            painter.drawLine(0, y + row_height, self.width(), y + row_height)

        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        for item in self.schedule:
            if not item.success: continue

            pair = (item.employee, item.machine)
            if pair not in self.pairs: continue

            row_idx = self.pairs.index(pair)
            start_secs = global_min.secsTo(item.start)
            end_secs = global_min.secsTo(item.end)

            x1 = left_margin + int(start_secs * chart_width / total_secs)
            x2 = left_margin + int(end_secs * chart_width / total_secs)
            y = header_height + row_idx * row_height + 6

            rect = QRect(x1, y, max(2, x2 - x1), row_height - 12)

            painter.fillRect(rect, QColor("#4CAF50"))
            painter.setPen(QPen(QColor("#2E7D32"), 1))
            painter.drawRect(rect)

            painter.setPen(QColor("#ffffff"))
            text = f"З.{item.orderId}\n{item.start.toString('HH:mm')}-{item.end.toString('HH:mm')}"
            painter.drawText(rect, Qt.AlignCenter, text)


# -------------------------- Главное окно ---------------------------------

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loom: Планировщик производства")
        self.resize(1200, 900)

        self.resources: List[Resource] = []
        self.products: List[Product] = []
        self.process_templates: List[Process] = []
        self.orders: List[Order] = []
        self.schedule_result: List[ScheduleItem] = []
        self.current_penalty = 0.0
        self.current_selected_product = None

        self.emp_types = ["фрезеровщик", "токарь", "слесарь", "сварщик", "оператор ЧПУ"]
        self.mach_types = ["фрезерный станок", "токарный станок", "сверлильный станок", "ЧПУ"]

        self.initUI()
        self.updateAllLists()
        self.auto_load()

    def get_config_path(self):
        return os.path.join(os.path.dirname(sys.argv[0]), "autosave_config.json")

    def _create_save_data(self):
        return {
            "emp_types": self.emp_types,
            "mach_types": self.mach_types,
            "resources": [{"id": r.id, "name": r.name, "type": r.type, "category": r.category, "priority": r.priority}
                          for r in self.resources],
            "process_templates": [
                {"id": p.id, "name": p.name, "duration": p.duration, "emp_type": p.emp_type, "mach_type": p.mach_type}
                for p in self.process_templates],
            "products": [{"id": prod.id, "name": prod.name, "process_ids": [p.id for p in prod.processes]} for prod in
                         self.products],
            "orders": [{"id": o.id, "name": o.name, "priority": o.priority, "start": o.start.toString(Qt.ISODate),
                        "deadline": o.deadline.toString(Qt.ISODate), "product_id": o.product.id,
                        "penalty_per_hour": o.penalty_per_hour} for o in self.orders]
        }

    def auto_save(self):
        try:
            with open(self.get_config_path(), "w", encoding="utf-8") as f:
                json.dump(self._create_save_data(), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка автосохранения: {e}")

    def saveToJson(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить конфигурацию", "", "JSON (*.json)")
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self._create_save_data(), f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Сохранение", "Конфигурация успешно сохранена!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить файл:\n{e}")

    def _load_data_dict(self, data):
        if "emp_types" in data:
            self.emp_types = data["emp_types"]
        if "mach_types" in data:
            self.mach_types = data["mach_types"]

        self.resources = [Resource(r["id"], r["name"], r["type"], r["category"], r["priority"]) for r in
                          data.get("resources", [])]

        self.process_templates = []
        proc_map = {}
        for p in data.get("process_templates", []):
            proc = Process(p["id"], p["name"], p["duration"], p["emp_type"], p.get("mach_type", ""))
            self.process_templates.append(proc)
            proc_map[proc.id] = proc

        self.products = []
        for p in data.get("products", []):
            prod = Product(p["id"], p["name"])
            prod.processes = [proc_map[pid] for pid in p.get("process_ids", []) if pid in proc_map]
            self.products.append(prod)

        self.orders = []
        for o in data.get("orders", []):
            s = QDateTime.fromString(o["start"], Qt.ISODate)
            d = QDateTime.fromString(o["deadline"], Qt.ISODate)
            prod = next((p for p in self.products if p.id == o["product_id"]), None)
            if prod:
                self.orders.append(Order(o["id"], o["name"], o["priority"], s, d, prod, o.get("penalty_per_hour", 0.0)))

        self.updateAllLists()
        self.updateTypeCombo(self.res_category_combo.currentText())

    def auto_load(self):
        path = self.get_config_path()
        if not os.path.exists(path): return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._load_data_dict(json.load(f))
        except Exception as e:
            print(f"Ошибка автозагрузки: {e}")

    def loadFromJson(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Загрузить конфигурацию", "", "JSON (*.json)")
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                self._load_data_dict(json.load(f))
            QMessageBox.information(self, "Загрузка", "Конфигурация успешно загружена!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось загрузить файл:\n{e}")

    def closeEvent(self, event):
        self.auto_save()
        event.accept()

    def _get_free_id(self, items):
        used = {item.id for item in items}
        free = 1
        while free in used:
            free += 1
        return free

    def initUI(self):
        tabs = QTabWidget(self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tabs)
        self.setLayout(main_layout)

        # --- Ресурсы ---
        res_tab = QWidget()
        res_layout = QVBoxLayout(res_tab)
        add_res_box = QGroupBox("Добавить ресурс")
        add_res_layout = QHBoxLayout(add_res_box)

        self.res_name_edit = QLineEdit()
        self.res_name_edit.setPlaceholderText("ФИО / Название")

        self.res_category_combo = QComboBox()
        self.res_category_combo.addItems(["сотрудник", "станок"])
        self.res_category_combo.currentTextChanged.connect(self.onResourceCategoryChanged)

        self.res_type_combo = QComboBox()
        self.res_type_combo.setEditable(True)
        self.updateTypeCombo(self.res_category_combo.currentText())

        add_type_btn = QPushButton("+")
        add_type_btn.setFixedWidth(30)
        add_type_btn.setToolTip("Добавить пресет")

        del_type_btn = QPushButton("-")
        del_type_btn.setFixedWidth(30)
        del_type_btn.setToolTip("Удалить выбранный пресет")

        type_layout = QHBoxLayout()
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(4)
        type_layout.addWidget(self.res_type_combo)
        type_layout.addWidget(add_type_btn)
        type_layout.addWidget(del_type_btn)

        self.res_priority_spin = QSpinBox()
        self.res_priority_spin.setRange(1, 100)

        add_res_btn = QPushButton("Добавить")

        add_res_layout.addWidget(self.res_name_edit)
        add_res_layout.addWidget(self.res_category_combo)
        add_res_layout.addLayout(type_layout)
        add_res_layout.addWidget(self.res_priority_spin)
        add_res_layout.addWidget(add_res_btn)

        res_layout.addWidget(add_res_box)

        self.res_search = QLineEdit()
        self.res_search.setPlaceholderText("Поиск по ресурсам...")
        self.res_search.textChanged.connect(self.filterResources)
        res_layout.addWidget(self.res_search)

        self.resource_list = QListWidget()
        self.resource_list.setSortingEnabled(True)
        del_res_btn = QPushButton("Удалить выбранный")
        res_layout.addWidget(self.resource_list)
        res_layout.addWidget(del_res_btn)
        tabs.addTab(res_tab, "Ресурсы")

        add_type_btn.clicked.connect(self.addResourceType)
        del_type_btn.clicked.connect(self.deleteResourceType)
        add_res_btn.clicked.connect(self.addResource)
        del_res_btn.clicked.connect(self.deleteResource)

        # --- Техпроцесс ---
        tech_tab = QWidget()
        tech_layout = QHBoxLayout(tech_tab)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        lbl_prod = QLabel("Изделия")
        lbl_prod.setStyleSheet("font-weight: bold; color: #4CAF50;")
        left_layout.addWidget(lbl_prod)

        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("Поиск изделий...")
        self.prod_search.textChanged.connect(self.filterProducts)
        left_layout.addWidget(self.prod_search)

        self.product_list = QListWidget()
        self.product_list.setSortingEnabled(True)
        self.product_list.itemSelectionChanged.connect(self.onProductSelected)
        left_layout.addWidget(self.product_list)

        prod_btn_layout = QHBoxLayout()
        add_prod_btn = QPushButton("Добавить")
        del_prod_btn = QPushButton("Удалить")
        prod_btn_layout.addWidget(add_prod_btn)
        prod_btn_layout.addWidget(del_prod_btn)
        left_layout.addLayout(prod_btn_layout)

        right_splitter = QSplitter(Qt.Vertical)
        proc_templ_widget = QWidget()
        proc_templ_layout = QVBoxLayout(proc_templ_widget)

        lbl_templ = QLabel("Шаблоны техпроцессов")
        lbl_templ.setStyleSheet("font-weight: bold; color: #4CAF50;")
        proc_templ_layout.addWidget(lbl_templ)

        self.templ_search = QLineEdit()
        self.templ_search.setPlaceholderText("Поиск шаблонов...")
        self.templ_search.textChanged.connect(self.filterTemplates)
        proc_templ_layout.addWidget(self.templ_search)

        self.process_template_list = QListWidget()
        self.process_template_list.setSortingEnabled(True)
        proc_templ_layout.addWidget(self.process_template_list)
        templ_btn_layout = QHBoxLayout()
        add_templ_btn = QPushButton("Добавить")
        del_templ_btn = QPushButton("Удалить")
        templ_btn_layout.addWidget(add_templ_btn)
        templ_btn_layout.addWidget(del_templ_btn)
        proc_templ_layout.addLayout(templ_btn_layout)

        prod_proc_widget = QWidget()
        prod_proc_layout = QVBoxLayout(prod_proc_widget)

        lbl_proc = QLabel("Техпроцессы изделия (порядок)")
        lbl_proc.setStyleSheet("font-weight: bold; color: #4CAF50;")
        prod_proc_layout.addWidget(lbl_proc)

        self.product_process_list = QListWidget()
        self.product_process_list.setSelectionMode(QAbstractItemView.SingleSelection)
        prod_proc_layout.addWidget(self.product_process_list)

        order_btn_layout = QHBoxLayout()
        move_up_btn = QPushButton("↑")
        move_down_btn = QPushButton("↓")
        add_to_prod_btn = QPushButton("← Добавить в изделие")
        remove_from_prod_btn = QPushButton("Удалить из изделия")
        order_btn_layout.addWidget(move_up_btn)
        order_btn_layout.addWidget(move_down_btn)
        order_btn_layout.addWidget(add_to_prod_btn)
        order_btn_layout.addWidget(remove_from_prod_btn)
        prod_proc_layout.addLayout(order_btn_layout)

        self.total_time_label = QLabel("Общее время: 0 ч")
        prod_proc_layout.addWidget(self.total_time_label)

        right_splitter.addWidget(proc_templ_widget)
        right_splitter.addWidget(prod_proc_widget)
        right_splitter.setSizes([200, 200])

        tech_layout.addWidget(left_widget, 1)
        tech_layout.addWidget(right_splitter, 2)
        tabs.addTab(tech_tab, "Техпроцесс")

        add_prod_btn.clicked.connect(self.addProduct)
        del_prod_btn.clicked.connect(self.deleteProduct)
        add_templ_btn.clicked.connect(self.addProcessTemplate)
        del_templ_btn.clicked.connect(self.deleteProcessTemplate)
        add_to_prod_btn.clicked.connect(self.addProcessToProduct)
        remove_from_prod_btn.clicked.connect(self.removeProcessFromProduct)
        move_up_btn.clicked.connect(self.moveProcessUp)
        move_down_btn.clicked.connect(self.moveProcessDown)

        # --- Заказы ---
        ord_tab = QWidget()
        ord_layout = QVBoxLayout(ord_tab)
        add_ord_box = QGroupBox("Добавить заказ")
        add_ord_layout = QVBoxLayout(add_ord_box)

        self.order_name_edit = QLineEdit()
        self.order_name_edit.setPlaceholderText("Название заказа")

        prio_layout = QHBoxLayout()
        prio_layout.addWidget(QLabel("Приоритет:"))
        self.order_priority_spin = QSpinBox()
        self.order_priority_spin.setRange(1, 100)
        prio_layout.addWidget(self.order_priority_spin)

        penalty_layout = QHBoxLayout()
        penalty_layout.addWidget(QLabel("Штраф за час просрочки:"))
        self.penalty_spin = QDoubleSpinBox()
        self.penalty_spin.setRange(0, 100000)
        self.penalty_spin.setSuffix(" руб./час")
        penalty_layout.addWidget(self.penalty_spin)

        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Количество шт.:"))
        self.order_qty_spin = QSpinBox()
        self.order_qty_spin.setRange(1, 9999)
        qty_layout.addWidget(self.order_qty_spin)

        dt_layout = QHBoxLayout()
        dt_layout.addWidget(QLabel("Начало:"))

        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setTimeRange(QTime(8, 0), QTime(16, 0))

        dt_layout.addWidget(self.start_date)
        dt_layout.addWidget(self.start_time)

        dt_layout.addWidget(QLabel("   Дедлайн:"))

        self.dl_date = QDateEdit(QDate.currentDate().addDays(1))
        self.dl_date.setCalendarPopup(True)
        self.dl_time = QTimeEdit(QTime(16, 0))
        self.dl_time.setTimeRange(QTime(8, 0), QTime(16, 0))

        dt_layout.addWidget(self.dl_date)
        dt_layout.addWidget(self.dl_time)

        self.select_product_btn = QPushButton("Выбрать изделие")
        self.selected_product_label = QLabel("Изделие не выбрано")
        self.selected_product_label.setStyleSheet("color: #888888;")

        add_ord_btn = QPushButton("Добавить заказ")
        add_ord_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        add_ord_layout.addWidget(self.order_name_edit)
        add_ord_layout.addLayout(prio_layout)
        add_ord_layout.addLayout(penalty_layout)
        add_ord_layout.addLayout(qty_layout)
        add_ord_layout.addLayout(dt_layout)
        add_ord_layout.addWidget(self.select_product_btn)
        add_ord_layout.addWidget(self.selected_product_label)
        add_ord_layout.addWidget(add_ord_btn)

        ord_layout.addWidget(add_ord_box)

        self.ord_search = QLineEdit()
        self.ord_search.setPlaceholderText("Поиск заказов...")
        self.ord_search.textChanged.connect(self.filterOrders)
        ord_layout.addWidget(self.ord_search)

        self.order_list = QListWidget()
        self.order_list.setSortingEnabled(True)
        del_ord_btn = QPushButton("Удалить выбранный")
        ord_layout.addWidget(self.order_list)
        ord_layout.addWidget(del_ord_btn)
        tabs.addTab(ord_tab, "Заказы")

        self.select_product_btn.clicked.connect(self.chooseProductForOrder)
        add_ord_btn.clicked.connect(self.addOrder)
        del_ord_btn.clicked.connect(self.deleteOrder)
        self.order_list.itemDoubleClicked.connect(self.showOrderDetails)

        # --- Расписание ---
        plan_tab = QWidget()
        plan_layout = QVBoxLayout(plan_tab)
        btn_layout = QHBoxLayout()
        run_btn = QPushButton("Построить расписание")
        run_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_btn = QPushButton("Сохранить конфигурацию")
        load_btn = QPushButton("Загрузить конфигурацию")
        btn_layout.addWidget(run_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(load_btn)
        plan_layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        plan_layout.addWidget(self.progress)

        self.sched_search = QLineEdit()
        self.sched_search.setPlaceholderText("Поиск в таблице расписания...")
        self.sched_search.textChanged.connect(self.filterSchedule)
        plan_layout.addWidget(self.sched_search)

        self.schedule_tree = QTreeWidget()
        self.schedule_tree.setColumnCount(7)
        self.schedule_tree.setHeaderLabels(
            ["Откр.", "Заказ / Операция", "Дата", "Ресурс", "Приоритет", "Начало", "Окончание"])
        self.schedule_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.schedule_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.schedule_tree.itemChanged.connect(self.onTreeItemChanged)
        plan_layout.addWidget(self.schedule_tree)

        self.penalty_label = QLabel("Общий штраф: 0 руб.")
        self.penalty_label.setStyleSheet("color: #ff5252; font-weight: bold;")
        plan_layout.addWidget(self.penalty_label)

        # Диаграмма Ганта
        gantt_ctrl_layout = QHBoxLayout()
        zoom_in_btn = QPushButton("Увеличить (+)")
        zoom_out_btn = QPushButton("Уменьшить (-)")
        gantt_ctrl_layout.addWidget(zoom_out_btn)
        gantt_ctrl_layout.addWidget(zoom_in_btn)
        info_lbl = QLabel("   (Ctrl + Колесико - масштаб. Просто колесико - прокрутка вниз)")
        info_lbl.setStyleSheet("color: #888888;")
        gantt_ctrl_layout.addWidget(info_lbl)
        gantt_ctrl_layout.addStretch()
        plan_layout.addLayout(gantt_ctrl_layout)

        self.gantt = GanttWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #3e3e42; border-radius: 4px; }")
        scroll.setWidget(self.gantt)
        plan_layout.addWidget(scroll)

        zoom_in_btn.clicked.connect(self.gantt.zoom_in)
        zoom_out_btn.clicked.connect(self.gantt.zoom_out)

        tabs.addTab(plan_tab, "Расписание")

        run_btn.clicked.connect(self.runScheduling)
        save_btn.clicked.connect(self.saveToJson)
        load_btn.clicked.connect(self.loadFromJson)

    # -------------------- Управление пресетами --------------------
    def addResourceType(self):
        category = self.res_category_combo.currentText()
        text, ok = QInputDialog.getText(self, "Новый пресет", f"Введите новый тип для категории '{category}':")
        if ok and text.strip():
            new_type = text.strip()
            if category == "сотрудник":
                if new_type not in self.emp_types:
                    self.emp_types.append(new_type)
            else:
                if new_type not in self.mach_types:
                    self.mach_types.append(new_type)

            self.updateTypeCombo(category)
            self.res_type_combo.setCurrentText(new_type)

    def deleteResourceType(self):
        category = self.res_category_combo.currentText()
        current_type = self.res_type_combo.currentText()
        if not current_type: return

        reply = QMessageBox.question(self, "Удаление", f"Удалить тип '{current_type}' из пресетов?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if category == "сотрудник":
                if current_type in self.emp_types:
                    self.emp_types.remove(current_type)
            else:
                if current_type in self.mach_types:
                    self.mach_types.remove(current_type)

            self.updateTypeCombo(category)

    # -------------------- Фильтры (Поиск) --------------------
    def filterList(self, text, list_widget):
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def filterResources(self, text):
        self.filterList(text, self.resource_list)

    def filterProducts(self, text):
        self.filterList(text, self.product_list)

    def filterTemplates(self, text):
        self.filterList(text, self.process_template_list)

    def filterOrders(self, text):
        self.filterList(text, self.order_list)

    def filterSchedule(self, text):
        text = text.lower()
        for i in range(self.schedule_tree.topLevelItemCount()):
            top_item = self.schedule_tree.topLevelItem(i)
            top_match = text in top_item.text(1).lower()

            child_match = False
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                match = False
                for col in range(1, 7):
                    if text in child.text(col).lower():
                        match = True
                        break
                child.setHidden(not match and not top_match)
                if match:
                    child_match = True

            top_item.setHidden(not top_match and not child_match)

    # -------------------- Вспомогательные методы --------------------
    def onResourceCategoryChanged(self, category: str):
        self.updateTypeCombo(category)

    def updateTypeCombo(self, category: str):
        self.res_type_combo.clear()
        if category == "сотрудник":
            self.res_type_combo.addItems(self.emp_types)
        else:
            self.res_type_combo.addItems(self.mach_types)
        self.res_type_combo.setCurrentIndex(-1)

    def updateAllLists(self):
        self.updateResourceList()
        self.updateProcessTemplateList()
        self.updateProductList()
        self.updateOrderList()

    # -------------------- Ресурсы --------------------
    def addResource(self):
        name = self.res_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя ресурса")
            return
        type_ = self.res_type_combo.currentText().strip()
        if not type_:
            QMessageBox.warning(self, "Ошибка", "Выберите или введите тип ресурса")
            return
        category = self.res_category_combo.currentText()
        new_id = self._get_free_id(self.resources)
        res = Resource(new_id, name, type_, category, self.res_priority_spin.value())
        self.resources.append(res)
        self.updateResourceList()
        self.res_name_edit.clear()
        self.res_type_combo.setCurrentIndex(-1)
        self.res_priority_spin.setValue(1)

    def deleteResource(self):
        item = self.resource_list.currentItem()
        if not item: return
        res_id = item.data(Qt.UserRole)
        self.resources = [r for r in self.resources if r.id != res_id]
        self.updateResourceList()

    def updateResourceList(self):
        self.resource_list.clear()
        for r in self.resources:
            item = QListWidgetItem(f"ID{r.id}: {r.name} ({r.category}), тип {r.type}, приор.{r.priority}")
            item.setData(Qt.UserRole, r.id)
            self.resource_list.addItem(item)
        self.filterResources(self.res_search.text())

    # -------------------- Техпроцесс: продукты --------------------
    def addProduct(self):
        name, ok = QInputDialog.getText(self, "Новое изделие", "Название изделия:")
        if ok and name.strip():
            new_id = self._get_free_id(self.products)
            prod = Product(new_id, name.strip())
            self.products.append(prod)
            self.updateProductList()

    def deleteProduct(self):
        item = self.product_list.currentItem()
        if not item: return
        prod_id = item.data(Qt.UserRole)
        product_to_delete = next((p for p in self.products if p.id == prod_id), None)
        if not product_to_delete: return

        used_in_orders = [o for o in self.orders if o.product == product_to_delete]
        if used_in_orders:
            order_ids = ", ".join(str(o.id) for o in used_in_orders)
            QMessageBox.warning(self, "Невозможно удалить",
                                f"Изделие '{product_to_delete.name}' используется в заказах: {order_ids}.\n"
                                "Сначала удалите эти заказы.")
            return

        self.products = [p for p in self.products if p.id != prod_id]
        self.updateProductList()
        self.product_list.clearSelection()
        self.product_process_list.clear()
        self.total_time_label.setText("Общее время: 0 ч")

    def onProductSelected(self):
        item = self.product_list.currentItem()
        if item:
            prod_id = item.data(Qt.UserRole)
            prod = next((p for p in self.products if p.id == prod_id), None)
            if prod:
                self.updateProductProcessList(prod)
        else:
            self.product_process_list.clear()
            self.total_time_label.setText("Общее время: 0 ч")

    def updateProductProcessList(self, prod: Product):
        self.product_process_list.clear()
        for proc in prod.processes:
            self.product_process_list.addItem(f"{proc.name} ({proc.duration} ч)")
        self.total_time_label.setText(f"Общее время: {prod.total_duration()} ч")

    def _refresh_product_list_item(self, prod: Product):
        """Вспомогательная функция для обновления текста изделия в списке без перезагрузки"""
        for i in range(self.product_list.count()):
            item = self.product_list.item(i)
            if item.data(Qt.UserRole) == prod.id:
                item.setText(
                    f"ID{prod.id}: {prod.name} | операций: {len(prod.processes)} | время: {prod.total_duration()} ч")
                break

    def updateProductList(self):
        self.product_list.clear()
        for p in self.products:
            item = QListWidgetItem(f"ID{p.id}: {p.name} | операций: {len(p.processes)} | время: {p.total_duration()} ч")
            item.setData(Qt.UserRole, p.id)
            self.product_list.addItem(item)
        self.filterProducts(self.prod_search.text())

    # -------------------- Техпроцесс: шаблоны процессов --------------------
    def addProcessTemplate(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Новый техпроцесс")
        layout = QVBoxLayout(dialog)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название")
        dur_spin = QSpinBox()
        dur_spin.setRange(1, 1000)
        dur_spin.setSuffix(" ч")
        emp_combo = QComboBox()
        emp_combo.setEditable(True)
        emp_combo.addItems(self.emp_types)
        mach_combo = QComboBox()
        mach_combo.setEditable(True)
        mach_combo.addItem("")
        mach_combo.addItems(self.mach_types)

        layout.addWidget(QLabel("Название:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("Длительность (ч):"))
        layout.addWidget(dur_spin)
        layout.addWidget(QLabel("Тип сотрудника:"))
        layout.addWidget(emp_combo)
        layout.addWidget(QLabel("Тип станка (опционально):"))
        layout.addWidget(mach_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Введите название")
                return
            emp = emp_combo.currentText().strip()
            if not emp:
                QMessageBox.warning(self, "Ошибка", "Укажите тип сотрудника")
                return
            mach = mach_combo.currentText().strip()
            new_id = self._get_free_id(self.process_templates)
            proc = Process(new_id, name, dur_spin.value(), emp, mach)
            self.process_templates.append(proc)
            self.updateProcessTemplateList()

    def deleteProcessTemplate(self):
        item = self.process_template_list.currentItem()
        if not item: return
        proc_id = item.data(Qt.UserRole)
        proc_to_delete = next((p for p in self.process_templates if p.id == proc_id), None)
        if not proc_to_delete: return

        used_in_products = [p for p in self.products if proc_to_delete in p.processes]
        if used_in_products:
            product_names = ", ".join(p.name for p in used_in_products)
            QMessageBox.warning(self, "Невозможно удалить",
                                f"Техпроцесс '{proc_to_delete.name}' используется в изделиях: {product_names}.\n"
                                "Сначала удалите его из изделий.")
            return

        self.process_templates = [p for p in self.process_templates if p.id != proc_id]
        self.updateProcessTemplateList()

    def updateProcessTemplateList(self):
        self.process_template_list.clear()
        for p in self.process_templates:
            mach = p.mach_type if p.mach_type else "нет"
            item = QListWidgetItem(f"ID{p.id}: {p.name} ({p.duration} ч), сотр.{p.emp_type}, станок.{mach}")
            item.setData(Qt.UserRole, p.id)
            self.process_template_list.addItem(item)
        self.filterTemplates(self.templ_search.text())

    # -------------------- Связь продукта и процессов --------------------
    def addProcessToProduct(self):
        prod_item = self.product_list.currentItem()
        templ_item = self.process_template_list.currentItem()
        if not prod_item:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие")
            return
        if not templ_item:
            QMessageBox.warning(self, "Ошибка", "Выберите шаблон техпроцесса")
            return

        prod = next((p for p in self.products if p.id == prod_item.data(Qt.UserRole)), None)
        proc = next((p for p in self.process_templates if p.id == templ_item.data(Qt.UserRole)), None)
        if prod and proc:
            prod.processes.append(proc)
            self.updateProductProcessList(prod)
            self._refresh_product_list_item(prod)

    def removeProcessFromProduct(self):
        prod_item = self.product_list.currentItem()
        proc_row = self.product_process_list.currentRow()
        if not prod_item or proc_row < 0:
            return
        prod = next((p for p in self.products if p.id == prod_item.data(Qt.UserRole)), None)
        if prod:
            prod.processes.pop(proc_row)
            self.updateProductProcessList(prod)
            self._refresh_product_list_item(prod)

    def moveProcessUp(self):
        prod_item = self.product_list.currentItem()
        proc_row = self.product_process_list.currentRow()
        if not prod_item or proc_row <= 0:
            return
        prod = next((p for p in self.products if p.id == prod_item.data(Qt.UserRole)), None)
        if prod:
            prod.processes[proc_row], prod.processes[proc_row - 1] = prod.processes[proc_row - 1], prod.processes[
                proc_row]
            self.updateProductProcessList(prod)
            self.product_process_list.setCurrentRow(proc_row - 1)
            self._refresh_product_list_item(prod)

    def moveProcessDown(self):
        prod_item = self.product_list.currentItem()
        proc_row = self.product_process_list.currentRow()
        if not prod_item: return
        prod = next((p for p in self.products if p.id == prod_item.data(Qt.UserRole)), None)
        if prod and proc_row >= 0 and proc_row < len(prod.processes) - 1:
            prod.processes[proc_row], prod.processes[proc_row + 1] = prod.processes[proc_row + 1], prod.processes[
                proc_row]
            self.updateProductProcessList(prod)
            self.product_process_list.setCurrentRow(proc_row + 1)
            self._refresh_product_list_item(prod)

    # -------------------- Заказы --------------------
    def chooseProductForOrder(self):
        if not self.products:
            QMessageBox.warning(self, "Нет изделий", "Сначала добавьте изделия во вкладке 'Техпроцесс'")
            return
        dlg = SelectProductDialog(self.products, self)
        dlg.setStyleSheet(self.styleSheet())
        if dlg.exec_() == QDialog.Accepted:
            prod_id = dlg.get_selected_product_id()
            prod = next((p for p in self.products if p.id == prod_id), None)
            if prod:
                self.current_selected_product = prod
                self.selected_product_label.setText(
                    f"Выбрано: {prod.name} (общее время 1 шт: {prod.total_duration()} ч)")
                self.selected_product_label.setStyleSheet("color: #4CAF50;")
            else:
                self.current_selected_product = None
                self.selected_product_label.setText("Изделие не выбрано")
                self.selected_product_label.setStyleSheet("color: #888888;")

    def addOrder(self):
        name = self.order_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название заказа")
            return

        prod = self.current_selected_product
        if not prod:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие")
            return

        if not prod.processes:
            QMessageBox.warning(self, "Ошибка", "У выбранного изделия нет техпроцессов")
            return

        s = QDateTime(self.start_date.date(), self.start_time.time())
        d = QDateTime(self.dl_date.date(), self.dl_time.time())

        if s >= d:
            QMessageBox.warning(self, "Ошибка", "Дата начала должна быть раньше дедлайна")
            return

        qty = self.order_qty_spin.value()
        total_dur_one = prod.total_duration()
        total_dur_all = total_dur_one * qty
        est_end = calculate_estimated_end(s, total_dur_all)

        if est_end > d:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Внимание: Возможен срыв дедлайна")
            msg.setText(
                f"Чистое время работы для {qty} шт: <b>{total_dur_all} ч</b>.<br>"
                f"Пессимистичный прогноз готовности (без учета конвейера): <b>{est_end.toString('dd.MM HH:mm')}</b>.<br>"
                f"Это на <b>{(d.secsTo(est_end) / 3600.0):.1f} ч</b> позже дедлайна!<br><br>"
                "Внимание: Умный алгоритм может успеть быстрее за счет распараллеливания станков.<br>"
                "Всё равно добавить партию?"
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            if msg.exec_() == QMessageBox.No:
                return

        penalty = self.penalty_spin.value()
        for i in range(qty):
            new_id = self._get_free_id(self.orders)
            order_name = f"{name} [{i + 1}/{qty}]" if qty > 1 else name
            order = Order(new_id, order_name, self.order_priority_spin.value(), s, d, prod, penalty)
            self.orders.append(order)

        self.updateOrderList()

        self.order_name_edit.clear()
        self.order_priority_spin.setValue(1)
        self.penalty_spin.setValue(0)
        self.order_qty_spin.setValue(1)
        self.start_date.setDate(QDate.currentDate())
        self.start_time.setTime(QTime(8, 0))
        self.dl_date.setDate(QDate.currentDate().addDays(1))
        self.dl_time.setTime(QTime(16, 0))
        self.current_selected_product = None
        self.selected_product_label.setText("Изделие не выбрано")
        self.selected_product_label.setStyleSheet("color: #888888;")

    def deleteOrder(self):
        item = self.order_list.currentItem()
        if not item: return
        ord_id = item.data(Qt.UserRole)
        self.orders = [o for o in self.orders if o.id != ord_id]
        self.updateOrderList()

    def showOrderDetails(self, item):
        ord_id = item.data(Qt.UserRole)
        order = next((o for o in self.orders if o.id == ord_id), None)
        if order:
            ops_text = "\n".join([f"{i + 1}. {op.name} ({op.duration} ч)" for i, op in enumerate(order.operations)])
            QMessageBox.information(self, f"Заказ '{order.name}'",
                                    f"Изделие: {order.product.name}\nОперации:\n{ops_text}")

    def updateOrderList(self):
        self.order_list.clear()
        for o in self.orders:
            item = QListWidgetItem(
                f"Заказ {o.id}: {o.name} (приор.{o.priority}) | {o.start.toString('dd.MM HH:mm')} - {o.deadline.toString('dd.MM HH:mm')} | изделие: {o.product.name}")
            item.setData(Qt.UserRole, o.id)
            self.order_list.addItem(item)
        self.filterOrders(self.ord_search.text())

    # -------------------- Планирование --------------------
    def runScheduling(self):
        if not self.resources or not self.orders:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один ресурс и один заказ")
            return

        self.progress.setRange(0, 0)
        QApplication.processEvents()

        sched = Scheduler(self.resources, self.orders)
        self.schedule_result, self.current_penalty = sched.schedule()

        self.progress.setRange(0, 100)
        self.progress.setValue(100)

        self.penalty_label.setText(f"Общий штраф за просрочку: {self.current_penalty:.2f} руб.")
        self.populateScheduleTree()

    def populateScheduleTree(self):
        self.schedule_tree.blockSignals(True)
        self.schedule_tree.clear()

        orders_map = {}
        for item in self.schedule_result:
            if item.orderId not in orders_map:
                orders_map[item.orderId] = []
            orders_map[item.orderId].append(item)

        for order in self.orders:
            if order.id in orders_map:
                items = orders_map[order.id]

                top_item = QTreeWidgetItem(self.schedule_tree)
                top_item.setFlags(top_item.flags() | Qt.ItemIsUserCheckable)
                top_item.setCheckState(0, Qt.Checked)
                top_item.setData(0, Qt.UserRole, order.id)
                top_item.setText(1, f"Заказ {order.id}: {order.name}")
                top_item.setText(4, str(order.priority))

                for item in items:
                    op_name = ""
                    for op in order.operations:
                        if op.id == item.processId:
                            op_name = op.name
                            break

                    child = QTreeWidgetItem(top_item)
                    child.setText(1, f"  └ {op_name}")
                    child.setText(2, item.start.toString("dd.MM.yyyy") if item.start else "—")

                    if item.success:
                        res_str = f"{item.employee} / {item.machine}" if item.machine != "нет" else item.employee
                    else:
                        res_str = item.fail_reason if item.fail_reason else "НЕ НАЗНАЧЕНО"

                    child.setText(3, res_str)
                    child.setText(5, item.start.toString("HH:mm") if item.start else "—")
                    child.setText(6, item.end.toString("HH:mm") if item.success and item.end else "—")

                    if not item.success:
                        for col in range(7):
                            child.setBackground(col, QColor("#4a1c1c"))

                top_item.setExpanded(True)

        self.schedule_tree.blockSignals(False)
        self.updateGanttVisibility()
        self.filterSchedule(self.sched_search.text())

    def onTreeItemChanged(self, item, column):
        if column == 0 and item.parent() is None:
            self.updateGanttVisibility()

    def updateGanttVisibility(self):
        visible_order_ids = set()
        for i in range(self.schedule_tree.topLevelItemCount()):
            item = self.schedule_tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                visible_order_ids.add(item.data(0, Qt.UserRole))

        filtered_schedule = [item for item in self.schedule_result if item.orderId in visible_order_ids]
        self.gantt.set_schedule(filtered_schedule)


# -------------------------- Запуск ---------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet(DARK_THEME_QSS)

    if verify_license():
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)