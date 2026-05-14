import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'health.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS Patient (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             VARCHAR(100) NOT NULL,
            age              INTEGER,
            gender           VARCHAR(10),
            blood_group      VARCHAR(10),
            emergency_contact VARCHAR(20)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS Category (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(30) NOT NULL UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS Record (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            patient_id  INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            file_name   VARCHAR(150) NOT NULL,
            file_path   VARCHAR(255) NOT NULL,
            file_type   VARCHAR(30),
            FOREIGN KEY (patient_id)  REFERENCES Patient(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES Category(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS CurrentMedicine (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id    INTEGER NOT NULL,
            medicine_text TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS PastDisease (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id   INTEGER NOT NULL,
            disease_name VARCHAR(100) NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS Allergy (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id   INTEGER NOT NULL,
            allergy_name VARCHAR(100) NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
        )
    """)

    # Seed default categories
    default_categories = ['Prescription', 'Lab Report', 'Scan', 'Other']
    for cat in default_categories:
        c.execute("INSERT OR IGNORE INTO Category(name) VALUES(?)", (cat,))

    conn.commit()
    conn.close()
    print("✅ Database initialized.")
