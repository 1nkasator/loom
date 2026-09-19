CREATE TABLE resources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(20) NOT NULL,
    type VARCHAR(50) NOT NULL,
    priority INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_resource_category CHECK (category IN ('сотрудник', 'станок')),
    CONSTRAINT chk_resource_priority CHECK (priority BETWEEN 1 AND 100)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE operations (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    duration INT NOT NULL,
    required_emp_type VARCHAR(50) NOT NULL,
    required_mach_type VARCHAR(50),
    CONSTRAINT chk_operation_step CHECK (step_number > 0),
    CONSTRAINT chk_operation_duration CHECK (duration > 0),
    CONSTRAINT uq_product_step UNIQUE (product_id, step_number)
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(100) NOT NULL UNIQUE,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    priority INT NOT NULL DEFAULT 1,
    quantity INT NOT NULL DEFAULT 1,
    start_time TIMESTAMP NOT NULL,
    deadline TIMESTAMP NOT NULL,
    penalty_per_hour NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(30) NOT NULL DEFAULT 'Новый',
    CONSTRAINT chk_order_priority CHECK (priority BETWEEN 1 AND 100),
    CONSTRAINT chk_order_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_penalty CHECK (penalty_per_hour >= 0.00),
    CONSTRAINT chk_order_dates CHECK (deadline > start_time),
    CONSTRAINT chk_order_status CHECK (status IN ('Новый', 'Запланирован', 'В работе', 'Завершен', 'Просрочен'))
);

CREATE TABLE schedule (
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