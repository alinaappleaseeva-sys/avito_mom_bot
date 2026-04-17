import sqlite3
from utils.logger import setup_logger
from utils.constants import ItemStatus
from config import config

logger = setup_logger(__name__)

def migrate_db():
    db_url = config.DATABASE_URL
    # parse sqlite+aiosqlite:///avito_bot.db
    db_path = db_url.split("///")[-1]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add last_synced_at col
        try:
            cursor.execute("ALTER TABLE items ADD COLUMN last_synced_at DATETIME")
            logger.info("Added last_synced_at column to items table.")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE items ADD COLUMN views INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE items ADD COLUMN contacts INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # Update legacy statuses
        cursor.execute("UPDATE items SET status = ? WHERE status = ?", (ItemStatus.DRAFT.value, "pending"))
        if cursor.rowcount > 0:
            logger.info(f"Migrated {cursor.rowcount} items from pending to draft.")
            
        cursor.execute("UPDATE items SET status = ? WHERE status = ?", (ItemStatus.PENDING_MODERATION.value, "on_review"))
        if cursor.rowcount > 0:
            logger.info(f"Migrated {cursor.rowcount} items from on_review to pending_moderation.")

        conn.commit()
    except Exception as e:
        logger.error(f"Migration error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_db()
