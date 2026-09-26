#!/usr/bin/env python3
"""
Migration: Add email verification columns to recipients table.

Run this script to add verification_status, verification_reason, and verified_at
columns to an existing recipients table.

Usage:
    cd /path/to/cold-begging
    python backend/migrate_add_verification.py
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'cold_email.db')

COLUMNS_TO_ADD = [
    ("verification_status", "VARCHAR(20) DEFAULT 'not_verified'"),
    ("verification_reason", "TEXT DEFAULT ''"),
    ("verified_at", "DATETIME"),
]

INDEX_NAME = 'ix_recipient_user_verification'
INDEX_COLUMNS = '(user_id, verification_status)'


def migrate():
    if not os.path.exists(DB_PATH):
        print(f'Database not found at {DB_PATH}')
        print('Tables will be created automatically on first startup.')
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute('PRAGMA table_info(recipients)')
    existing_cols = {row[1] for row in cursor.fetchall()}

    added = 0
    for col_name, col_def in COLUMNS_TO_ADD:
        if col_name not in existing_cols:
            cursor.execute(f'ALTER TABLE recipients ADD COLUMN {col_name} {col_def}')
            print(f'  Added column: {col_name}')
            added += 1
        else:
            print(f'  Column already exists: {col_name}')

    # Add index
    try:
        cursor.execute(f'CREATE INDEX {INDEX_NAME} ON recipients {INDEX_COLUMNS}')
        print(f'  Created index: {INDEX_NAME}')
    except sqlite3.OperationalError:
        print(f'  Index already exists: {INDEX_NAME}')

    conn.commit()
    conn.close()

    if added > 0:
        print(f'\nMigration complete. Added {added} column(s).')
    else:
        print('\nNo changes needed. Database is up to date.')


if __name__ == '__main__':
    migrate()
