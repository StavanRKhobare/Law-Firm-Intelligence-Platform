"""Documents and evidence. Metadata is in PostgreSQL; file bytes are in MongoDB GridFS."""
import hashlib
from datetime import date
from typing import Optional
from urllib.parse import quote

import gridfs
from bson.errors import InvalidId
from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..core.audit import record
from ..core.permissions import case_scope, require_case
from ..core.security import get_current_active_user
from ..database import get_db, get_mongo_db
from ..models.models import Evidence, Lawyer, LegalCase, utcnow
from ..models.user import User
from ..schemas.evidence import (
    DOCUMENT_CATEGORIES,
    EVIDENCE_STATUSES,
    EvidenceResponse,
    EvidenceUpdate,
    PaginatedEvidence,
)

router = APIRouter()
BUCKET = "evidence_fs"
STORAGE_DOWN = "File storage (MongoDB) is not reachable. Ask an admin to check that it is running."


def file_store() -> gridfs.GridFS:
    return gridfs.GridFS(get_mongo_db(), collection=BUCKET)


def delete_stored_file(file_id: str) -> None:
    """Best effort: a missing file or an unreachable store must not undo the database change."""
    try:
        file_store().delete(ObjectId(file_id))
    except (PyMongoError, InvalidId) as e:
        print(f"Could not delete stored file {file_id}: {e}")


def evidence_response(evidence: Evidence) -> EvidenceResponse:
    response = EvidenceResponse.model_validate(evidence)
    response.has_file = evidence.mongo_id is not None
    if evidence.legal_case:
        response.case_number = evidence.legal_case.case_number
        response.case_title = evidence.legal_case.matter_title
    if evidence.lawyer:
        response.lawyer_name = f"{evidence.lawyer.fname} {evidence.lawyer.lname}"
    return response


def get_evidence_or_404(db: Session, evidence_id: int) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Document {evidence_id} not found")
    return evidence


async def store_file(evidence: Evidence, file: UploadFile, user: User) -> None:
    """Check the file, write it to GridFS, and fill in the metadata columns."""
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=415, detail=f"Files of type {file.content_type} are not accepted")
    content = await file.read(settings.MAX_FILE_SIZE + 1)
    if len(content) > settings.MAX_FILE_SIZE:
        limit_mb = settings.MAX_FILE_SIZE // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"The file is larger than the {limit_mb} MB limit")
    if not content:
        raise HTTPException(status_code=400, detail="The file is empty")
    digest = hashlib.sha256(content).hexdigest()
    name = (file.filename or "document")[:255]
    try:
        file_id = file_store().put(
            content,
            filename=name,
            metadata={
                "case_id": evidence.case_id,
                "evidence_id": evidence.evidence_id,
                "content_type": file.content_type,
                "sha256": digest,
            },
        )
    except PyMongoError:
        raise HTTPException(status_code=503, detail=STORAGE_DOWN)
    evidence.mongo_id = str(file_id)
    evidence.file_name = name
    evidence.content_type = file.content_type
    evidence.file_size = len(content)
    evidence.sha256 = digest
    evidence.uploaded_by = user.user_id
    evidence.uploaded_at = utcnow()


def check_status_and_category(status_value: str, category: str) -> None:
    if status_value not in EVIDENCE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(EVIDENCE_STATUSES)}")
    if category not in DOCUMENT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(DOCUMENT_CATEGORIES)}")


@router.post("/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    description: Optional[str] = Form(None),
    filed_date: date = Form(...),
    status_value: str = Form("Received", alias="status"),
    category: str = Form("Evidence"),
    lawyer_id: Optional[int] = Form(None),
    case_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Add a document to a matter, with or without a file. Send as multipart form data."""
    check_status_and_category(status_value, category)
    case = require_case(db, user, case_id, "work")
    if lawyer_id and not db.get(Lawyer, lawyer_id):
        raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")
    if filed_date < case.date_cause:
        raise HTTPException(status_code=400, detail="The document date cannot be before the cause of action")
    if filed_date > date.today():
        raise HTTPException(status_code=400, detail="The document date cannot be in the future")

    evidence = Evidence(
        description=description,
        filed_date=filed_date,
        status=status_value,
        category=category,
        lawyer_id=lawyer_id or user.lawyer_id,
        case_id=case_id,
    )
    db.add(evidence)
    db.flush()
    if file:
        await store_file(evidence, file, user)
    record(db, user, "document_added", "document", evidence.evidence_id, case_id, {"file": evidence.file_name})
    try:
        db.commit()
    except Exception:
        db.rollback()
        if evidence.mongo_id:
            delete_stored_file(evidence.mongo_id)
        raise
    db.refresh(evidence)
    return evidence_response(evidence)


@router.get("/", response_model=PaginatedEvidence)
async def get_evidence_list(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    case_id: Optional[int] = None,
    lawyer_id: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    has_file: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Documents on the matters the user may open."""
    query = db.query(Evidence).join(LegalCase, Evidence.case_id == LegalCase.case_id)
    scope = case_scope(user)
    if scope is not None:
        query = query.filter(scope)
    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    if lawyer_id:
        query = query.filter(Evidence.lawyer_id == lawyer_id)
    if status:
        query = query.filter(Evidence.status == status)
    if category:
        query = query.filter(Evidence.category == category)
    if has_file is not None:
        query = query.filter(Evidence.mongo_id.isnot(None) if has_file else Evidence.mongo_id.is_(None))
    if search:
        query = query.filter(Evidence.description.ilike(f"%{search}%") | Evidence.file_name.ilike(f"%{search}%"))
    total = query.count()
    rows = query.options(joinedload(Evidence.lawyer), joinedload(Evidence.legal_case)).order_by(
        Evidence.filed_date.desc(), Evidence.evidence_id.desc()
    ).offset((page - 1) * size).limit(size).all()
    return PaginatedEvidence(
        items=[evidence_response(e) for e in rows],
        total=total, page=page, size=size, pages=(total + size - 1) // size,
    )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    evidence = get_evidence_or_404(db, evidence_id)
    require_case(db, user, evidence.case_id)
    return evidence_response(evidence)


@router.put("/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: int,
    data: EvidenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    evidence = get_evidence_or_404(db, evidence_id)
    case = require_case(db, user, evidence.case_id, "work")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("lawyer_id") and not db.get(Lawyer, changes["lawyer_id"]):
        raise HTTPException(status_code=404, detail=f"Lawyer {changes['lawyer_id']} not found")
    filed_date = changes.get("filed_date")
    if filed_date and (filed_date < case.date_cause or filed_date > date.today()):
        raise HTTPException(status_code=400, detail="The document date must be between the cause of action and today")
    for field, value in changes.items():
        setattr(evidence, field, value)
    record(db, user, "document_updated", "document", evidence_id, evidence.case_id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(evidence)
    return evidence_response(evidence)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    evidence = get_evidence_or_404(db, evidence_id)
    require_case(db, user, evidence.case_id, "edit")
    file_id = evidence.mongo_id
    record(db, user, "document_deleted", "document", evidence_id, evidence.case_id, {
        "file": evidence.file_name, "sha256": evidence.sha256, "description": evidence.description,
    })
    db.delete(evidence)
    db.commit()
    if file_id:
        delete_stored_file(file_id)


@router.post("/{evidence_id}/upload-file", response_model=EvidenceResponse)
async def upload_file_to_evidence(
    evidence_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Attach a file to a document, replacing any file already there."""
    evidence = get_evidence_or_404(db, evidence_id)
    require_case(db, user, evidence.case_id, "work")
    previous = evidence.mongo_id
    await store_file(evidence, file, user)
    record(db, user, "file_uploaded", "document", evidence_id, evidence.case_id, {
        "file": evidence.file_name, "sha256": evidence.sha256, "replaced": bool(previous),
    })
    db.commit()
    if previous:
        delete_stored_file(previous)
    db.refresh(evidence)
    return evidence_response(evidence)


@router.get("/{evidence_id}/download-file")
async def download_evidence_file(
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    evidence = get_evidence_or_404(db, evidence_id)
    require_case(db, user, evidence.case_id)
    if not evidence.mongo_id:
        raise HTTPException(status_code=404, detail="No file is attached to this document")
    try:
        stored = file_store().get(ObjectId(evidence.mongo_id))
    except gridfs.errors.NoFile:
        raise HTTPException(status_code=404, detail="The file is missing from storage")
    except PyMongoError:
        raise HTTPException(status_code=503, detail=STORAGE_DOWN)
    record(db, user, "file_downloaded", "document", evidence_id, evidence.case_id, {"file": evidence.file_name})
    db.commit()
    name = evidence.file_name or stored.filename or "document"
    return StreamingResponse(
        stored,
        media_type=evidence.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@router.delete("/{evidence_id}/delete-file", response_model=EvidenceResponse)
async def delete_evidence_file(
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Remove the attached file and keep the document record."""
    evidence = get_evidence_or_404(db, evidence_id)
    require_case(db, user, evidence.case_id, "edit")
    if not evidence.mongo_id:
        raise HTTPException(status_code=404, detail="No file is attached to this document")
    file_id = evidence.mongo_id
    record(db, user, "file_deleted", "document", evidence_id, evidence.case_id, {"file": evidence.file_name, "sha256": evidence.sha256})
    evidence.mongo_id = evidence.file_name = evidence.content_type = evidence.file_size = evidence.sha256 = None
    evidence.uploaded_by = evidence.uploaded_at = None
    db.commit()
    delete_stored_file(file_id)
    db.refresh(evidence)
    return evidence_response(evidence)
