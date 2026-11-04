"""API routes for clients."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..database import get_db
from ..models.models import Client, ClientPhoneNo, CaseClient
from ..schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientDetailed,
    ClientList, PaginatedClients, CaseBrief,
)

router = APIRouter()
ACTIVE = ("Filed", "Hearing", "Pending")


def get_client_or_404(db: Session, client_id: int) -> Client:
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return client


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    payload = data.model_dump(exclude={"phone_numbers"})
    client = Client(**payload)
    db.add(client)
    db.flush()
    # dict.fromkeys drops repeats; (client_id, phoneno) is the table's primary key
    for number in dict.fromkeys(data.phone_numbers or []):
        db.add(ClientPhoneNo(client_id=client.client_id, phoneno=number))
    db.commit()
    db.refresh(client)
    return client


@router.get("/", response_model=PaginatedClients)
async def get_clients(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Client)
    if search:
        query = query.filter(or_(
            Client.fname.ilike(f"%{search}%"),
            Client.lname.ilike(f"%{search}%"),
            Client.email.ilike(f"%{search}%"),
        ))
    total = query.count()
    pages = (total + size - 1) // size
    clients = query.offset((page - 1) * size).limit(size).all()
    items = []
    for client in clients:
        total_cases = db.query(func.count(CaseClient.case_id)).filter(
            CaseClient.client_id == client.client_id
        ).scalar() or 0
        items.append(ClientList(
            client_id=client.client_id,
            fname=client.fname,
            lname=client.lname,
            email=client.email,
            notes=client.notes,
            total_cases=total_cases,
        ))
    return PaginatedClients(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{client_id}", response_model=ClientDetailed)
async def get_client(client_id: int, db: Session = Depends(get_db)):
    client = get_client_or_404(db, client_id)
    cases = sorted(client.cases, key=lambda c: c.date_cause, reverse=True)
    return ClientDetailed(
        client_id=client.client_id,
        fname=client.fname,
        lname=client.lname,
        email=client.email,
        address=client.address,
        sex=client.sex,
        notes=client.notes,
        phone_numbers=[p.phoneno for p in client.phone_numbers],
        total_cases=len(cases),
        active_cases=sum(1 for c in cases if c.status in ACTIVE),
        disposed_cases=sum(1 for c in cases if c.status == "Disposed"),
        recent_cases=[
            CaseBrief(case_id=c.case_id, matter_title=c.matter_title, case_number=c.case_number, status=c.status)
            for c in cases[:5]
        ],
    )


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_db)):
    client = get_client_or_404(db, client_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = get_client_or_404(db, client_id)
    db.delete(client)
    db.commit()


@router.post("/{client_id}/phones", status_code=status.HTTP_201_CREATED)
async def add_phone(client_id: int, phoneno: str = Query(...), db: Session = Depends(get_db)):
    get_client_or_404(db, client_id)
    if db.query(ClientPhoneNo).filter(ClientPhoneNo.client_id == client_id, ClientPhoneNo.phoneno == phoneno).first():
        raise HTTPException(status_code=400, detail="Phone number already recorded for this client")
    db.add(ClientPhoneNo(client_id=client_id, phoneno=phoneno))
    db.commit()
    return {"client_id": client_id, "phoneno": phoneno}


@router.delete("/{client_id}/phones/{phoneno}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_phone(client_id: int, phoneno: str, db: Session = Depends(get_db)):
    row = db.query(ClientPhoneNo).filter(
        ClientPhoneNo.client_id == client_id,
        ClientPhoneNo.phoneno == phoneno,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Phone number not found")
    db.delete(row)
    db.commit()


@router.get("/{client_id}/cases", response_model=List[CaseBrief])
async def get_client_cases(client_id: int, db: Session = Depends(get_db)):
    client = get_client_or_404(db, client_id)
    return [
        CaseBrief(case_id=c.case_id, matter_title=c.matter_title, case_number=c.case_number, status=c.status)
        for c in sorted(client.cases, key=lambda c: c.date_cause, reverse=True)
    ]
