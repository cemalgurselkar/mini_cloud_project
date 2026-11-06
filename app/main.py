import socket
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import Base, engine, get_db
from models import Note
from schemas import NoteCreate, NoteResponse, NoteUpdate


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(note_data: NoteCreate, db: Session = Depends(get_db)) -> Note:
    note = Note(**note_data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.get("/notes", response_model=list[NoteResponse])
def list_notes(db: Session = Depends(get_db)) -> list[Note]:
    return list(db.scalars(select(Note).order_by(Note.id)).all())


@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int,
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    note.title = note_data.title
    note.content = note_data.content
    db.commit()
    db.refresh(note)
    return note


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db)) -> Response:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return {"status": "ok"}


@app.get("/whoami")
def whoami() -> dict[str, str]:
    return {"hostname": socket.gethostname()}

