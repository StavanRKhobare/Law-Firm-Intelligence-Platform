"""
API Router for Evidence
Handles evidence management including file uploads to MongoDB
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from datetime import date, datetime, timezone
import io

from ..database import get_db, get_mongo_db
from ..models.models import Evidence, Lawyer, LegalCase
from ..schemas.evidence import (
    EvidenceCreate,
    EvidenceUpdate,
    EvidenceResponse,
    EvidenceDetailed,
    EvidenceList,
    PaginatedEvidence,
    FileInfo,
    EVIDENCE_STATUSES,
)

router = APIRouter()


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_evidence_or_404(db: Session, evidence_id: int) -> Evidence:
    """Get evidence by ID or raise 404"""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID {evidence_id} not found"
        )
    return evidence


def get_file_from_mongo(mongo_id: str):
    """Get file from MongoDB by ID"""
    try:
        from bson.objectid import ObjectId
        mongo_db = get_mongo_db()
        
        file_doc = mongo_db.evidence_files.find_one({"_id": ObjectId(mongo_id)})
        if not file_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in MongoDB"
            )
        return file_doc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MongoDB ID: {str(e)}"
        )


# ============================================
# CRUD ENDPOINTS
# ============================================

@router.post("/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    description: Optional[str] = Form(None),
    filed_date: date = Form(...),
    status_value: str = Form("Received", alias="status"),
    lawyer_id: Optional[int] = Form(None),
    case_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Create new evidence (optionally with file upload). Send the fields as multipart form data.
    
    - **description**: Description of the evidence
    - **filed_date**: Date the item was filed or received
    - **status**: Evidence status (Received/Under Review/Filed/Produced)
    - **lawyer_id**: ID of the lawyer who filed the item
    - **case_id**: ID of the matter
    - **file**: Optional file upload (image, PDF, video, etc.)
    """
    if status_value not in EVIDENCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(EVIDENCE_STATUSES)}"
        )

    # Verify case exists
    case = db.query(LegalCase).filter(LegalCase.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Matter with ID {case_id} not found"
        )
    
    # Verify officer exists if provided
    if lawyer_id:
        officer = db.query(Lawyer).filter(Lawyer.lawyer_id == lawyer_id).first()
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lawyer with ID {lawyer_id} not found"
            )
    
    # Validate collection date is not after case date
    if filed_date < case.date_cause:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence date cannot be before the cause of action"
        )
    
    mongo_id = None
    
    # Upload file to MongoDB if provided
    if file:
        try:
            mongo_db = get_mongo_db()
            
            # Read file content
            file_content = await file.read()
            
            # Create document in MongoDB
            file_doc = {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(file_content),
                "upload_date": datetime.now(timezone.utc),
                "file_data": file_content,
                "evidence_description": description,
                "case_id": case_id,
            }
            
            result = mongo_db.evidence_files.insert_one(file_doc)
            mongo_id = str(result.inserted_id)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to MongoDB: {str(e)}"
            )
    
    # Create evidence record
    new_evidence = Evidence(
        description=description,
        filed_date=filed_date,
        mongo_id=mongo_id,
        status=status_value,
        lawyer_id=lawyer_id,
        case_id=case_id,
    )
    
    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)
    
    return new_evidence


@router.get("/", response_model=PaginatedEvidence)
async def get_evidence_list(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    case_id: Optional[int] = Query(None, description="Filter by case ID"),
    lawyer_id: Optional[int] = Query(None, description="Filter by lawyer ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    has_file: Optional[bool] = Query(None, description="Filter by file presence"),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of evidence with filters
    
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 10, max: 100)
    - **case_id**: Filter by matter ID
    - **lawyer_id**: Filter by lawyer ID
    - **status**: Filter by evidence status
    - **has_file**: Filter by file attachment (true/false)
    """
    # Base query
    query = db.query(Evidence)
    
    # Apply filters
    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    
    if lawyer_id:
        query = query.filter(Evidence.lawyer_id == lawyer_id)
    
    if status:
        query = query.filter(Evidence.status == status)
    
    if has_file is not None:
        if has_file:
            query = query.filter(Evidence.mongo_id.isnot(None))
        else:
            query = query.filter(Evidence.mongo_id.is_(None))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    offset = (page - 1) * size
    pages = (total + size - 1) // size
    
    # Get paginated results
    evidence_list = query.options(
        joinedload(Evidence.lawyer),
        joinedload(Evidence.legal_case)
    ).offset(offset).limit(size).all()
    
    # Format response
    items = []
    for evidence in evidence_list:
        lawyer_name = None
        if evidence.lawyer:
            lawyer_name = f"{evidence.lawyer.fname} {evidence.lawyer.lname}"
        
        case_title = evidence.legal_case.matter_title if evidence.legal_case else None
        
        items.append(EvidenceList(
            evidence_id=evidence.evidence_id,
            description=evidence.description,
            filed_date=evidence.filed_date,
            status=evidence.status,
            case_title=case_title,
            lawyer_name=lawyer_name,
            has_file=evidence.mongo_id is not None,
        ))
    
    return PaginatedEvidence(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{evidence_id}", response_model=EvidenceDetailed)
async def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about specific evidence
    
    - **evidence_id**: ID of the evidence
    """
    evidence = db.query(Evidence).options(
        joinedload(Evidence.lawyer),
        joinedload(Evidence.legal_case)
    ).filter(Evidence.evidence_id == evidence_id).first()
    
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID {evidence_id} not found"
        )
    
    # Get file info from MongoDB if exists
    file_info = None
    if evidence.mongo_id:
        try:
            file_doc = get_file_from_mongo(evidence.mongo_id)
            file_info = FileInfo(
                filename=file_doc.get("filename", "unknown"),
                content_type=file_doc.get("content_type", "application/octet-stream"),
                size=file_doc.get("size", 0),
                upload_date=str(file_doc.get("upload_date", "")),
                mongo_id=evidence.mongo_id,
            )
        except:
            pass
    
    return EvidenceDetailed(
        evidence_id=evidence.evidence_id,
        description=evidence.description,
        filed_date=evidence.filed_date,
        mongo_id=evidence.mongo_id,
        status=evidence.status,
        lawyer_id=evidence.lawyer_id,
        case_id=evidence.case_id,
        lawyer=evidence.lawyer,
        legal_case=evidence.legal_case,
        has_file=evidence.mongo_id is not None,
        file_info=file_info,
    )


@router.put("/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: int,
    evidence_data: EvidenceUpdate,
    db: Session = Depends(get_db),
):
    """
    Update existing evidence
    
    - **evidence_id**: ID of the evidence to update
    - Only provided fields will be updated
    """
    evidence = get_evidence_or_404(db, evidence_id)
    
    # Verify officer exists if being updated
    if evidence_data.lawyer_id is not None:
        officer = db.query(Lawyer).filter(
            Lawyer.lawyer_id == evidence_data.lawyer_id
        ).first()
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lawyer with ID {evidence_data.lawyer_id} not found"
            )
    
    # Update fields
    update_data = evidence_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(evidence, field, value)
    
    db.commit()
    db.refresh(evidence)
    
    return evidence


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: int,
    delete_file: bool = Query(True, description="Also delete file from MongoDB"),
    db: Session = Depends(get_db),
):
    """
    Delete evidence
    
    - **evidence_id**: ID of the evidence to delete
    - **delete_file**: If true, also deletes associated file from MongoDB
    """
    evidence = get_evidence_or_404(db, evidence_id)
    
    # Delete file from MongoDB if requested and exists
    if delete_file and evidence.mongo_id:
        try:
            from bson.objectid import ObjectId
            mongo_db = get_mongo_db()
            mongo_db.evidence_files.delete_one({"_id": ObjectId(evidence.mongo_id)})
        except Exception as e:
            # Log error but continue with deletion
            print(f"Error deleting file from MongoDB: {str(e)}")
    
    db.delete(evidence)
    db.commit()
    
    return None


# ============================================
# FILE MANAGEMENT ENDPOINTS
# ============================================

@router.post("/{evidence_id}/upload-file")
async def upload_file_to_evidence(
    evidence_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload or replace file for existing evidence
    
    - **evidence_id**: ID of the evidence
    - **file**: File to upload
    """
    evidence = get_evidence_or_404(db, evidence_id)
    
    try:
        mongo_db = get_mongo_db()
        
        # Delete old file if exists
        if evidence.mongo_id:
            try:
                from bson.objectid import ObjectId
                mongo_db.evidence_files.delete_one({"_id": ObjectId(evidence.mongo_id)})
            except:
                pass
        
        # Read and upload new file
        file_content = await file.read()
        
        file_doc = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(file_content),
            "upload_date": datetime.now(timezone.utc),
            "file_data": file_content,
            "evidence_id": evidence_id,
            "case_id": evidence.case_id,
        }
        
        result = mongo_db.evidence_files.insert_one(file_doc)
        mongo_id = str(result.inserted_id)
        
        # Update evidence record
        evidence.mongo_id = mongo_id
        db.commit()
        
        return {
            "message": "File uploaded successfully",
            "evidence_id": evidence_id,
            "mongo_id": mongo_id,
            "filename": file.filename,
            "size": len(file_content),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/{evidence_id}/download-file")
async def download_evidence_file(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """
    Download file associated with evidence
    
    - **evidence_id**: ID of the evidence
    """
    evidence = get_evidence_or_404(db, evidence_id)
    
    if not evidence.mongo_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file attached to this evidence"
        )
    
    try:
        file_doc = get_file_from_mongo(evidence.mongo_id)
        
        file_data = file_doc.get("file_data")
        filename = file_doc.get("filename", "evidence_file")
        content_type = file_doc.get("content_type", "application/octet-stream")
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.delete("/{evidence_id}/delete-file", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence_file(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete file from evidence (keeps evidence record)
    
    - **evidence_id**: ID of the evidence
    """
    evidence = get_evidence_or_404(db, evidence_id)
    
    if not evidence.mongo_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file attached to this evidence"
        )
    
    try:
        from bson.objectid import ObjectId
        mongo_db = get_mongo_db()
        
        result = mongo_db.evidence_files.delete_one({"_id": ObjectId(evidence.mongo_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in MongoDB"
            )
        
        # Clear mongo_id from evidence
        evidence.mongo_id = None
        db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


# ============================================
# ADDITIONAL ENDPOINTS
# ============================================

@router.get("/case/{case_id}/list", response_model=List[EvidenceList])
async def get_case_evidence(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all evidence for a specific case
    
    - **case_id**: ID of the matter
    """
    # Verify case exists
    case = db.query(LegalCase).filter(LegalCase.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Matter with ID {case_id} not found"
        )
    
    evidence_list = db.query(Evidence).options(
        joinedload(Evidence.lawyer),
        joinedload(Evidence.legal_case)
    ).filter(Evidence.case_id == case_id).all()
    
    return [
        EvidenceList(
            evidence_id=e.evidence_id,
            description=e.description,
            filed_date=e.filed_date,
            status=e.status,
            case_title=e.legal_case.matter_title,
            lawyer_name=f"{e.lawyer.fname} {e.lawyer.lname}" if e.lawyer else None,
            has_file=e.mongo_id is not None,
        )
        for e in evidence_list
    ]


@router.patch("/{evidence_id}/status", response_model=EvidenceResponse)
async def update_evidence_status(
    evidence_id: int,
    new_status: str = Query(..., description="New status"),
    db: Session = Depends(get_db),
):
    """
    Update only the status of evidence
    
    - **evidence_id**: ID of the evidence
    - **new_status**: New status (Collected/Analyzed/In Storage/Presented in Court)
    """
    allowed_statuses = ["Received", "Under Review", "Filed", "Produced"]
    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"
        )
    
    evidence = get_evidence_or_404(db, evidence_id)
    evidence.status = new_status
    
    db.commit()
    db.refresh(evidence)
    
    return evidence


@router.get("/statistics/summary", response_model=dict)
async def get_evidence_statistics(
    db: Session = Depends(get_db),
):
    """
    Get overall evidence statistics
    """
    total = db.query(func.count(Evidence.evidence_id)).scalar()
    
    with_files = db.query(func.count(Evidence.evidence_id)).filter(
        Evidence.mongo_id.isnot(None)
    ).scalar()
    
    # Status distribution
    received = db.query(func.count(Evidence.evidence_id)).filter(
        Evidence.status == "Received"
    ).scalar()
    
    under_review = db.query(func.count(Evidence.evidence_id)).filter(
        Evidence.status == "Under Review"
    ).scalar()
    
    filed = db.query(func.count(Evidence.evidence_id)).filter(
        Evidence.status == "Filed"
    ).scalar()
    
    produced = db.query(func.count(Evidence.evidence_id)).filter(
        Evidence.status == "Produced"
    ).scalar()
    
    return {
        "total_evidence": total or 0,
        "with_files": with_files or 0,
        "without_files": (total or 0) - (with_files or 0),
        "status_distribution": {
            "received": received or 0,
            "under_review": under_review or 0,
            "filed": filed or 0,
            "produced": produced or 0,
        },
    }