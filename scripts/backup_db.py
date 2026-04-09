import shutil
import datetime
import os
from pathlib import Path

def backup_database():
    db_file = Path("avito_bot.db")
    backup_dir = Path("backups")
    
    if not db_file.exists():
        print(f"Database file {db_file} not found. Nothing to backup.")
        return

    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"avito_bot_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename
    
    shutil.copy2(db_file, backup_path)
    print(f"Successfully backed up database to {backup_path}")

if __name__ == "__main__":
    backup_database()
