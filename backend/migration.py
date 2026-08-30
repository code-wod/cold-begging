"""Migration script: add recipient groups to an existing database.

Every recipient now belongs to a recipient group (owned by the same user).
This script:

  1. Creates the new `recipient_groups` table (create_all is safe on existing DBs).
  2. Adds the `recipients.group_id` column if it does not exist.
  3. Creates an `Uncategorized` group for every user that has recipients, then
     backfills `group_id` for existing recipients (no recipient is deleted).
  4. Creates the lookup indexes (`recipient_groups.user_id`,
     `recipients.group_id`, `recipients.user_id + group_id`).
  5. On PostgreSQL only, sets `group_id` NOT NULL after the backfill.

Run it once after upgrading the models:

    python -m backend.migration

Safe to run multiple times — every step checks before applying. `init_db()`
(create_all) will NOT add columns to existing tables, so existing databases must
run this script before the app serves group-aware traffic.
"""
import logging

from sqlalchemy import inspect, text

from backend import models  # noqa: F401  (ensures tables are registered)
from backend.database import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('migration')

DEFAULT_GROUP_NAME = 'Uncategorized'


def _column_exists(table_name, column_name):
    inspector = inspect(engine)
    return column_name in {c['name'] for c in inspector.get_columns(table_name)}


def _table_exists(table_name):
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def run():
    db = SessionLocal()
    try:
        with engine.connect() as conn:
            is_postgres = conn.dialect.name == 'postgresql'

            print('1. Repairing obsolete legacy recipient-group tables')
            # An abandoned "paid lead catalog" draft shipped these tables and
            # columns. If `recipient_groups` predates this migration it has a
            # catalog shape (slug/price, no user_id) that conflicts with the
            # user-owned group model — keep its rows under a legacy name (never
            # silently destroy data) and let create_all recreate the new shape.
            if _table_exists('recipient_groups') and not _column_exists('recipient_groups', 'user_id'):
                for legacy in ('recipient_group_items', 'recipient_access'):
                    if _table_exists(legacy):
                        conn.exec_driver_sql(f'DROP TABLE {legacy}')
                        print(f'  Dropped obsolete table: {legacy}')
                conn.exec_driver_sql('ALTER TABLE recipient_groups RENAME TO recipient_groups_legacy')
                print('  Renamed legacy recipient_groups -> recipient_groups_legacy')

            print('2. Creating new tables (recipient_groups)')
            Base.metadata.create_all(bind=engine)

            print('3. Adding recipients.group_id')
            if not _column_exists('recipients', 'group_id'):
                conn.exec_driver_sql('ALTER TABLE recipients ADD COLUMN group_id INTEGER')
            else:
                print('  Column already exists — skipping')

            print('4. Creating default groups and backfilling existing recipients')
            if _column_exists('recipients', 'user_id'):
                conn.execute(
                    text(
                        """
                        INSERT INTO recipient_groups (user_id, name, created_at, updated_at)
                        SELECT DISTINCT r.user_id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        FROM recipients r
                        WHERE NOT EXISTS (
                            SELECT 1 FROM recipient_groups g
                            WHERE g.user_id = r.user_id AND g.name = :name
                        )
                        """
                    ),
                    {'name': DEFAULT_GROUP_NAME},
                )
                conn.execute(
                    text(
                        """
                        UPDATE recipients
                        SET group_id = (
                            SELECT g.id FROM recipient_groups g
                            WHERE g.user_id = recipients.user_id
                            ORDER BY CASE WHEN g.name = :name THEN 0 ELSE 1 END, g.id
                            LIMIT 1
                        )
                        WHERE group_id IS NULL
                        """
                    ),
                    {'name': DEFAULT_GROUP_NAME},
                )
            else:
                print('  No recipients table — skipping backfill')

            print('5. Enforcing NOT NULL and FK on PostgreSQL')
            if is_postgres and _column_exists('recipients', 'group_id'):
                conn.exec_driver_sql(
                    'ALTER TABLE recipients ALTER COLUMN group_id SET NOT NULL'
                )
                fks = inspect(engine).get_foreign_keys('recipients')
                if not any(fk.get('referred_table') == 'recipient_groups' for fk in fks):
                    conn.exec_driver_sql(
                        'ALTER TABLE recipients ADD CONSTRAINT '
                        'fk_recipients_group_id_recipient_groups '
                        'FOREIGN KEY (group_id) REFERENCES recipient_groups (id)'
                    )
                    print('  Added foreign key recipients.group_id -> recipient_groups.id')

            print('6. Creating indexes')
            statements = [
                'CREATE INDEX IF NOT EXISTS ix_recipient_groups_user_id ON recipient_groups (user_id)',
                'CREATE INDEX IF NOT EXISTS ix_recipients_group_id ON recipients (group_id)',
                'CREATE INDEX IF NOT EXISTS ix_recipient_user_group ON recipients (user_id, group_id)',
            ]
            for statement in statements:
                conn.exec_driver_sql(statement)

            conn.commit()

        groups = db.execute(text(
            'SELECT COUNT(*) FROM recipient_groups'
        )).scalar()
        recipients = db.execute(text(
            'SELECT COUNT(*) FROM recipients WHERE group_id IS NULL'
        )).scalar()
        print(f'  Done. {groups or 0} group(s); {recipients or 0} recipients still unassigned.')
    finally:
        db.close()


if __name__ == '__main__':
    run()