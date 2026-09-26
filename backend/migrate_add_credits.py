"""
Migration: Add email_credits column to users and create credit_transactions table.

Run from repo root:
  cd backend && python migrate_add_credits.py

Safe to run multiple times (checks before adding).
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / 'cold_email.db'


def migrate():
    if not DB_PATH.exists():
        print(f'Database not found at {DB_PATH}, skipping migration.')
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 1. Add email_credits column to users table
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN email_credits INTEGER NOT NULL DEFAULT 50')
        print('✓ Added email_credits column to users table')
    except sqlite3.OperationalError as e:
        if 'duplicate column' in str(e):
            print('• email_credits column already exists')
        else:
            raise

    # 2. Create credit_transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            type VARCHAR(32) NOT NULL,
            amount INTEGER NOT NULL,
            reference_id VARCHAR(255) DEFAULT '',
            description TEXT DEFAULT '',
            balance_after INTEGER NOT NULL,
            created_at DATETIME,
            PRIMARY KEY (id)
        )
    ''')
    print('✓ credit_transactions table ready')

    # 3. Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_credit_transactions_user_id ON credit_transactions (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_credit_transaction_user_type ON credit_transactions (user_id, type)')
    print('✓ Indexes created')

    # 4. Grant 50 free credits to existing users who don't have any transactions
    cursor.execute('SELECT id FROM users')
    user_ids = [row[0] for row in cursor.fetchall()]

    granted_count = 0
    for uid in user_ids:
        cursor.execute(
            'SELECT COUNT(*) FROM credit_transactions WHERE user_id = ? AND type = ?',
            (uid, 'FREE_GRANT'),
        )
        if cursor.fetchone()[0] == 0:
            # Check current credits
            cursor.execute('SELECT email_credits FROM users WHERE id = ?', (uid,))
            current = cursor.fetchone()[0] or 0

            # Set to 50 if not already
            if current < 50:
                cursor.execute('UPDATE users SET email_credits = 50 WHERE id = ?', (uid,))

            # Record the grant
            cursor.execute(
                'INSERT INTO credit_transactions (user_id, type, amount, reference_id, description, balance_after, created_at) '
                "VALUES (?, 'FREE_GRANT', 50, '', 'Welcome! 50 free email credits', 50, datetime('now'))",
                (uid,),
            )
            granted_count += 1

    if granted_count:
        print(f'✓ Granted 50 free credits to {granted_count} existing user(s)')
    else:
        print('• All users already have free credits')

    conn.commit()
    conn.close()
    print('\nMigration complete!')


if __name__ == '__main__':
    migrate()
