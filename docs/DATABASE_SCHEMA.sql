-- Versi SQL referensi.
-- Implementasi utama ada di app/database/models.py

CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY,
    name VARCHAR(255),
    major VARCHAR(255),
    semester INTEGER,
    timezone VARCHAR(100) DEFAULT 'Asia/Jakarta',
    reminder_preference TEXT DEFAULT 'H-1 dan 2 jam sebelum deadline',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    course VARCHAR(255),
    description TEXT,
    deadline TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(50) DEFAULT 'normal',
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    user_id BIGINT NOT NULL,
    remind_at TIMESTAMP NOT NULL,
    message TEXT,
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE course_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    course VARCHAR(255) NOT NULL,
    day_of_week VARCHAR(50),
    start_time VARCHAR(50),
    end_time VARCHAR(50),
    room VARCHAR(255),
    lecturer VARCHAR(255),
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    importance INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
