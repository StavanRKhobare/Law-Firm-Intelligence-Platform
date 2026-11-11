"""Run MongoDB migrations. From backend/:

    python -m mongo_migrations upgrade          apply everything not yet applied
    python -m mongo_migrations downgrade        undo the most recent migration
    python -m mongo_migrations status           show what has been applied

Applied migrations are recorded in the schema_migrations collection.
"""
import argparse
import importlib
import pkgutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

from app.config import settings


def discover():
    package_dir = str(Path(__file__).parent)
    names = sorted(m.name for m in pkgutil.iter_modules([package_dir]) if m.name.startswith("m0"))
    return [(name, importlib.import_module(f"mongo_migrations.{name}")) for name in names]


def main():
    parser = argparse.ArgumentParser(description="MongoDB migrations")
    parser.add_argument("command", choices=["upgrade", "downgrade", "status"])
    args = parser.parse_args()

    db = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)[settings.MONGODB_DB]
    log = db.schema_migrations
    applied = {d["_id"] for d in log.find()}
    migrations = discover()

    if args.command == "status":
        for name, _ in migrations:
            print(f"{'applied' if name in applied else 'pending'}  {name}")
    elif args.command == "upgrade":
        pending = [m for m in migrations if m[0] not in applied]
        if not pending:
            print("Already up to date")
        for name, module in pending:
            print(f"Applying {name}")
            module.upgrade(db)
            log.insert_one({"_id": name, "applied_at": datetime.now(timezone.utc)})
    else:
        done = [m for m in migrations if m[0] in applied]
        if not done:
            print("Nothing to undo")
            return 0
        name, module = done[-1]
        print(f"Undoing {name}")
        module.downgrade(db)
        log.delete_one({"_id": name})
    return 0


if __name__ == "__main__":
    sys.exit(main())
