
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime, timezone
from uuid import uuid4

from app.database import (
    Base,
    engine,
    SessionLocal,
    get_db,
    initialize_database
)

from app.schemas import SessionCreate, SessionResponse


# Database Model
from sqlalchemy import Column, String, DateTime, JSON


class SupportSession(Base):

    __tablename__ = "sessions"

    session_id = Column(
        String,
        primary_key=True,
        index=True
    )

    interaction_mode = Column(String, nullable=False)

    product_name = Column(String, nullable=False)
    product_context = Column(String, nullable=False)

    customer_scenario = Column(String, nullable=False)
    persona = Column(String, nullable=False)

    emotional_progression = Column(JSON, nullable=True)
    replay_transcript = Column(JSON, nullable=True)

    status = Column(
        String,
        nullable=False,
        default="created"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = Column(
        DateTime,
        nullable=True
    )


# Initialize application
app = FastAPI(
    title="Session Configuration Module API",
    description="Backend API for configuring customer support sessions",
    version="1.0.0"
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup_event():
    initialize_database()


@app.get("/")
def home():
    return {
        "message": "Session Configuration Module API is running",
        "status": "success"
    }


# CREATE SESSION
@app.post(
    "/api/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db)
):

    try:
        new_session = SupportSession(
            session_id=str(uuid4()),

            interaction_mode=session_data.interaction_mode,

            product_name=session_data.product_name,
            product_context=session_data.product_context,

            customer_scenario=session_data.customer_scenario,
            persona=session_data.persona,

            emotional_progression=session_data.emotional_progression,
            replay_transcript=session_data.replay_transcript,

            status="created",

            created_at=datetime.now(timezone.utc)
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        return new_session

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create session"
        )


# GET ALL SESSIONS
@app.get(
    "/api/sessions",
    response_model=list[SessionResponse]
)
def get_all_sessions(
    db: Session = Depends(get_db)
):

    try:
        sessions = (
            db.query(SupportSession)
            .order_by(SupportSession.created_at.desc())
            .all()
        )

        return sessions

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve sessions"
        )


# GET SINGLE SESSION
@app.get(
    "/api/sessions/{session_id}",
    response_model=SessionResponse
)
def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):

    session = (
        db.query(SupportSession)
        .filter(SupportSession.session_id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return session
