#!/usr/bin/env python3
"""
Database migration script for invitation system.
Adds email and is_active columns to sharpener table and creates invitation table.
"""
import sqlite3
import os
from datetime import datetime

def migrate_database(db_path='instance/skate_tickets.db'):
    """Migrate existing database to support invitation system"""

    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. No migration needed.")
        return

    # Backup the database first
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(sharpener)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_needed = []

        if 'email' not in columns:
            migrations_needed.append('email')
        if 'is_active' not in columns:
            migrations_needed.append('is_active')

        # Check if invitation table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invitation'")
        invitation_exists = cursor.fetchone() is not None

        if not invitation_exists:
            migrations_needed.append('invitation_table')

        if not migrations_needed:
            print("✅ Database is already up to date!")
            return

        print(f"🔄 Applying migrations: {', '.join(migrations_needed)}")

        # Add email column
        if 'email' in migrations_needed:
            cursor.execute("ALTER TABLE sharpener ADD COLUMN email VARCHAR(255)")
            print("✅ Added email column to sharpener table")

            # Set placeholder emails for existing users
            cursor.execute("SELECT id, username FROM sharpener WHERE email IS NULL")
            existing_users = cursor.fetchall()

            for user_id, username in existing_users:
                placeholder_email = f"{username}@example.com"
                cursor.execute("UPDATE sharpener SET email = ? WHERE id = ?", (placeholder_email, user_id))

            if existing_users:
                print(f"✅ Set placeholder emails for {len(existing_users)} existing users")
                print("⚠️  IMPORTANT: Update these placeholder emails to real addresses!")
                for user_id, username in existing_users:
                    print(f"   - User '{username}': {username}@example.com")

        # Add is_active column
        if 'is_active' in migrations_needed:
            cursor.execute("ALTER TABLE sharpener ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("✅ Added is_active column to sharpener table")

        # Create invitation table
        if 'invitation_table' in migrations_needed:
            cursor.execute("""
                CREATE TABLE invitation (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    token VARCHAR(100) NOT NULL UNIQUE,
                    used BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL
                )
            """)
            print("✅ Created invitation table")

        # Make email column unique (requires recreation for SQLite)
        if 'email' in migrations_needed:
            print("🔄 Making email column unique...")

            # Create new table with proper constraints
            cursor.execute("""
                CREATE TABLE sharpener_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    phone VARCHAR(20) NOT NULL,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Copy data to new table
            cursor.execute("""
                INSERT INTO sharpener_new (id, name, email, phone, username, password_hash, is_active, created_at)
                SELECT id, name, email, phone, username, password_hash, is_active, created_at
                FROM sharpener
            """)

            # Drop old table and rename new one
            cursor.execute("DROP TABLE sharpener")
            cursor.execute("ALTER TABLE sharpener_new RENAME TO sharpener")

            print("✅ Made email column unique")

        conn.commit()
        print("✅ Migration completed successfully!")

        # Show current schema
        cursor.execute("PRAGMA table_info(sharpener)")
        print("\n📋 Updated sharpener table schema:")
        for row in cursor.fetchall():
            print(f"   - {row[1]} ({row[2]})")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        print(f"💾 Database restored from backup: {backup_path}")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()