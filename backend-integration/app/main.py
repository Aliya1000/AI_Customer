
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import (
    Column, String, DateTime, JSON, Text,
    ForeignKey, inspect
)

from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, Field

from app.database import (
    Base,
    engine,
    get_db,
    initialize_database
)

from app.schemas import SessionCreate, SessionResponse


# =====================================================
# SUPPORT SESSION MODEL
# =====================================================

class SupportSession(Base):

    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)

    interaction_mode = Column(String, nullable=False)

    product_name = Column(String, nullable=False)
    product_context = Column(String, nullable=False)

    customer_scenario = Column(String, nullable=False)
    persona = Column(String, nullable=False)

    emotional_progression = Column(JSON, nullable=True)
    replay_transcript = Column(JSON, nullable=True)

    status = Column(String, nullable=False, default="created")

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = Column(DateTime, nullable=True)


# =====================================================
# SUPPORT MESSAGE MODEL
# Supports existing database column names too.
# =====================================================

existing_tables = inspect(engine).get_table_names()

existing_message_columns = set()

if "messages" in existing_tables:
    existing_message_columns = {
        column["name"]
        for column in inspect(engine).get_columns("messages")
    }

MESSAGE_TEXT_COLUMN = (
    "message_text"
    if "message_text" in existing_message_columns
    else "content"
    if "content" in existing_message_columns
    else "message_text"
)

MESSAGE_TIME_COLUMN = (
    "timestamp"
    if "timestamp" in existing_message_columns
    else "created_at"
    if "created_at" in existing_message_columns
    else "timestamp"
)


class SupportMessage(Base):

    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, index=True)

    session_id = Column(
        String,
        ForeignKey("sessions.session_id"),
        nullable=False,
        index=True
    )

    sender = Column(String, nullable=False)

    message_text = Column(
        MESSAGE_TEXT_COLUMN,
        Text,
        nullable=False
    )

    timestamp = Column(
        MESSAGE_TIME_COLUMN,
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )


# =====================================================
# MESSAGE REQUEST SCHEMA
# =====================================================

class MessageCreate(BaseModel):

    sender: Literal["employee", "customer"]

    message_text: str = Field(..., min_length=1)


# =====================================================
# APPLICATION
# =====================================================

app = FastAPI(
    title="Session Configuration Module API",
    description="Backend API for customer support session configuration and conversation",
    version="1.0.0"
)


# =====================================================
# CORS
# =====================================================

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


# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
def startup_event():
    initialize_database()


# =====================================================
# HOME
# =====================================================

@app.get("/")
def home():

    return {
        "message": "Session Configuration Module API is running",
        "status": "success"
    }


# =====================================================
# CREATE SESSION
# =====================================================

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
        db.flush()

        # Save initial customer scenario as first message
        initial_message = SupportMessage(
            message_id="MSG-" + uuid4().hex[:12],
            session_id=new_session.session_id,
            sender="customer",
            message_text=session_data.customer_scenario,
            timestamp=datetime.now(timezone.utc)
        )

        db.add(initial_message)

        db.commit()
        db.refresh(new_session)

        return new_session

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create session"
        )


# =====================================================
# GET ALL SESSIONS
# =====================================================

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


# =====================================================
# GET SINGLE SESSION
# =====================================================

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


# =====================================================
# SERIALIZE MESSAGE
# =====================================================

def serialize_message(message):

    return {
        "message_id": message.message_id,
        "session_id": message.session_id,
        "sender": message.sender,
        "message_text": message.message_text,
        "timestamp": message.timestamp
    }


# =====================================================
# SEND MESSAGE
# POST /api/sessions/{session_id}/messages
# =====================================================

@app.post("/api/sessions/{session_id}/messages")
def send_message(
    session_id: str,
    message_data: MessageCreate,
    db: Session = Depends(get_db)
):

    try:

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

        message_text = message_data.message_text.strip()

        if not message_text:

            raise HTTPException(
                status_code=422,
                detail="Message cannot be empty"
            )

        saved_message = SupportMessage(
            message_id="MSG-" + uuid4().hex[:12],
            session_id=session_id,
            sender=message_data.sender,
            message_text=message_text,
            timestamp=datetime.now(timezone.utc)
        )

        db.add(saved_message)
        db.flush()

        simulated_customer_reply = None

        # Basic simulator fallback.
        # Actual AI customer simulation belongs to the AI pipeline.

        if (
            session.interaction_mode == "simulator"
            and message_data.sender == "employee"
        ):

            reply = SupportMessage(
                message_id="MSG-" + uuid4().hex[:12],
                session_id=session_id,
                sender="customer",
                message_text=(
                    "Thank you for your response. "
                    "Could you please explain the next steps "
                    "and expected resolution time?"
                ),
                timestamp=datetime.now(timezone.utc)
            )

            db.add(reply)
            db.flush()

            simulated_customer_reply = serialize_message(reply)

        session.status = "active"
        session.updated_at = datetime.now(timezone.utc)

        db.commit()

        db.refresh(saved_message)

        return {
            "saved_message": serialize_message(saved_message),

            "simulated_customer_reply": simulated_customer_reply,

            # Actual six-agent pipeline is connected separately
            "agent_outputs": None
        }

    except HTTPException:

        db.rollback()
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to save message"
        )


# =====================================================
# GET SESSION CONVERSATION
# GET /api/sessions/{session_id}/messages
# =====================================================

@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(
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

    messages = (
        db.query(SupportMessage)
        .filter(SupportMessage.session_id == session_id)
        .order_by(SupportMessage.timestamp.asc())
        .all()
    )

    return [
        serialize_message(message)
        for message in messages
    ]
