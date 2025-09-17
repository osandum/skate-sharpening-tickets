#!/usr/bin/env python
"""Test database migration from old to new schema."""
import os
import sqlite3
from werkzeug.security import generate_password_hash

def create_old_database(db_path):
    """Create database with old schema."""
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create old schema tables (without email and is_active)
    cursor.execute('''
        CREATE TABLE sharpener (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE ticket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            brand VARCHAR(255) NOT NULL,
            color VARCHAR(255) NOT NULL,
            size VARCHAR(10) NOT NULL,
            code VARCHAR(10) NOT NULL UNIQUE,
            status VARCHAR(20) DEFAULT 'unpaid',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            paid_at DATETIME,
            completed_at DATETIME,
            sharpener_id INTEGER,
            payment_intent_id VARCHAR(255),
            FOREIGN KEY (sharpener_id) REFERENCES sharpener(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comments TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES ticket(id)
        )
    ''')

    # Add test data
    cursor.execute('''
        INSERT INTO sharpener (name, password) VALUES (?, ?)
    ''', ('Alice', generate_password_hash('alice123')))

    cursor.execute('''
        INSERT INTO sharpener (name, password) VALUES (?, ?)
    ''', ('Bob', generate_password_hash('bob456')))

    conn.commit()
    conn.close()
    print(f"Created old schema database at {db_path}")
    return db_path

def apply_migration(db_path):
    """Apply migration to add invitation system fields."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add email column to sharpener table
    cursor.execute("ALTER TABLE sharpener ADD COLUMN email VARCHAR(255)")

    # Add is_active column to sharpener table
    cursor.execute("ALTER TABLE sharpener ADD COLUMN is_active BOOLEAN DEFAULT 1")

    # Update existing rows with placeholder emails
    cursor.execute("UPDATE sharpener SET email = name || '@example.com' WHERE email IS NULL")
    cursor.execute("UPDATE sharpener SET is_active = 1 WHERE is_active IS NULL")

    # Create invitation table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) NOT NULL UNIQUE,
            token VARCHAR(100) NOT NULL UNIQUE,
            used BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Applied migration to {db_path}")

def verify_migration(db_path):
    """Verify the migration was successful."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check sharpener table structure
    cursor.execute("PRAGMA table_info(sharpener)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]

    print("\nSharpener table columns after migration:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

    # Check if new columns exist
    assert 'email' in column_names, "email column not found"
    assert 'is_active' in column_names, "is_active column not found"

    # Check sharpener data
    cursor.execute("SELECT name, email, is_active FROM sharpener")
    sharpeners = cursor.fetchall()

    print("\nSharpener data after migration:")
    for s in sharpeners:
        print(f"  - {s[0]}: email={s[1]}, active={s[2]}")

    # Check invitation table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invitation'")
    invitation_table = cursor.fetchone()
    assert invitation_table is not None, "invitation table not found"

    print("\n✅ Migration successful!")

    conn.close()

if __name__ == "__main__":
    db_path = "test_migration_demo.db"

    print("Step 1: Creating database with old schema")
    create_old_database(db_path)

    print("\nStep 2: Applying migration")
    apply_migration(db_path)

    print("\nStep 3: Verifying migration")
    verify_migration(db_path)

    print("\n" + "="*50)
    print("To use Flask-Migrate for future migrations:")
    print("1. flask db migrate -m 'Description of changes'")
    print("2. Review the generated migration file")
    print("3. flask db upgrade")
    print("\nFor existing production databases:")
    print("1. Backup the database first!")
    print("2. Run: DATABASE_URL=sqlite:///prod.db flask db stamp base")
    print("3. Run: DATABASE_URL=sqlite:///prod.db flask db upgrade")