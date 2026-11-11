"""Create the GridFS bucket that stores evidence files, with validation and indexes."""
BUCKET = "evidence_fs"

FILES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["filename", "length", "metadata"],
        "properties": {
            "filename": {"bsonType": "string"},
            "length": {"bsonType": ["int", "long"], "minimum": 0},
            "metadata": {
                "bsonType": "object",
                "required": ["case_id", "content_type", "sha256"],
                "properties": {
                    "case_id": {"bsonType": ["int", "long"]},
                    "evidence_id": {"bsonType": ["int", "long", "null"]},
                    "content_type": {"bsonType": "string"},
                    "sha256": {"bsonType": "string"},
                },
            },
        },
    }
}


def upgrade(db):
    existing = db.list_collection_names()
    if f"{BUCKET}.files" not in existing:
        db.create_collection(f"{BUCKET}.files", validator=FILES_VALIDATOR, validationAction="error")
    files = db[f"{BUCKET}.files"]
    # GridFS needs this index and would otherwise create it on first write.
    files.create_index([("filename", 1), ("uploadDate", 1)])
    files.create_index("metadata.case_id")
    files.create_index("metadata.evidence_id")
    files.create_index("metadata.sha256")
    db[f"{BUCKET}.chunks"].create_index([("files_id", 1), ("n", 1)], unique=True)


def downgrade(db):
    db.drop_collection(f"{BUCKET}.files")
    db.drop_collection(f"{BUCKET}.chunks")
