"""Move files stored inside evidence_files documents (16 MB limit) into GridFS.

Each file keeps its _id, so evidence.mongo_id in PostgreSQL stays valid.
"""
import hashlib

import gridfs

BUCKET = "evidence_fs"
INLINE_LIMIT = 15 * 1024 * 1024


def upgrade(db):
    fs = gridfs.GridFS(db, collection=BUCKET)
    legacy = db.evidence_files
    for doc in legacy.find({"file_data": {"$exists": True}}):
        data = bytes(doc["file_data"])
        if not fs.exists(doc["_id"]):
            fs.put(
                data,
                _id=doc["_id"],
                filename=doc.get("filename", "file"),
                metadata={
                    "case_id": doc.get("case_id", 0),
                    "evidence_id": doc.get("evidence_id"),
                    "content_type": doc.get("content_type") or "application/octet-stream",
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            )
        legacy.delete_one({"_id": doc["_id"]})
    if legacy.count_documents({}) == 0:
        db.drop_collection("evidence_files")


def downgrade(db):
    """Put files that fit back into evidence_files. Larger files stay in GridFS, and are reported."""
    fs = gridfs.GridFS(db, collection=BUCKET)
    skipped = []
    for grid_file in fs.find():
        if grid_file.length > INLINE_LIMIT:
            skipped.append(str(grid_file._id))
            continue
        meta = grid_file.metadata or {}
        db.evidence_files.insert_one({
            "_id": grid_file._id,
            "filename": grid_file.filename,
            "content_type": meta.get("content_type"),
            "size": grid_file.length,
            "upload_date": grid_file.upload_date,
            "file_data": grid_file.read(),
            "evidence_id": meta.get("evidence_id"),
            "case_id": meta.get("case_id"),
        })
        fs.delete(grid_file._id)
    if skipped:
        print(f"  left in GridFS, too large for inline storage: {', '.join(skipped)}")
