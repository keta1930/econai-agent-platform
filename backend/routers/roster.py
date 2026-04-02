import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import STORAGE_DIR
from database import get_db
from auth.deps import require_admin
from models.roster import StudentRoster
from models.submission import Submission
from models.user import User
from schemas.roster import (
    RosterAddRequest, RosterBatchRequest,
    RosterItem, RosterListResponse, RosterBatchResponse,
)

router = APIRouter(
    prefix="/api/admin/roster",
    tags=["roster"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=RosterListResponse)
def list_roster(db: Session = Depends(get_db)):
    entries = db.query(StudentRoster).all()
    registered_ids = {
        u.id for u in db.query(User.id).filter(User.role == "student").all()
    }
    items = [
        RosterItem(
            student_id=e.student_id,
            registered=e.student_id in registered_ids,
        )
        for e in entries
    ]
    return RosterListResponse(items=items, total=len(items))


@router.post("", status_code=status.HTTP_201_CREATED)
def add_student(req: RosterAddRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(StudentRoster)
        .filter(StudentRoster.student_id == req.student_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学号已在名单中",
        )
    entry = StudentRoster(student_id=req.student_id)
    db.add(entry)
    db.commit()
    return {"student_id": req.student_id}


@router.post("/batch", response_model=RosterBatchResponse)
def batch_import(req: RosterBatchRequest, db: Session = Depends(get_db)):
    existing_ids = {
        r.student_id
        for r in db.query(StudentRoster.student_id)
        .filter(StudentRoster.student_id.in_(req.student_ids))
        .all()
    }
    added = 0
    duplicates = 0
    for sid in req.student_ids:
        if sid in existing_ids:
            duplicates += 1
        else:
            db.add(StudentRoster(student_id=sid))
            existing_ids.add(sid)
            added += 1
    db.commit()
    return RosterBatchResponse(added=added, duplicates=duplicates)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: str, db: Session = Depends(get_db)):
    entry = (
        db.query(StudentRoster)
        .filter(StudentRoster.student_id == student_id)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学号不在名单中",
        )
    # Cascade: delete submissions, user, roster entry, then clean up files
    submissions = db.query(Submission).filter(Submission.student_id == student_id).all()
    file_paths = [Path(STORAGE_DIR) / s.file_path for s in submissions if s.file_path]
    db.query(Submission).filter(Submission.student_id == student_id).delete()
    db.query(User).filter(User.id == student_id).delete()
    db.delete(entry)
    db.commit()
    for fp in file_paths:
        if fp.exists():
            fp.unlink()
