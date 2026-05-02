from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import MonthlyNote

router = APIRouter()


class NoteUpsert(BaseModel):
    month: str   # YYYY-MM
    note: str = ""


@router.get("/notes")
def list_notes(db: Session = Depends(get_db)):
    """Return all month notes as {month: note_text}."""
    return {n.month: n.note for n in db.query(MonthlyNote).all()}


@router.post("/notes")
def upsert_note(body: NoteUpsert, db: Session = Depends(get_db)):
    """Insert or update the note for a given month."""
    existing = db.query(MonthlyNote).filter(MonthlyNote.month == body.month).first()
    if existing:
        existing.note = body.note
        existing.updated_at = datetime.utcnow()
    else:
        db.add(MonthlyNote(month=body.month, note=body.note))
    db.commit()
    return {"month": body.month, "note": body.note}
