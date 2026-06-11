from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EntryStatus(StrEnum):
    RECEIVED = "received"
    TRANSCRIBED = "transcribed"
    DRAFT_GENERATED = "draft_generated"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    first_name: Mapped[str | None] = mapped_column(String(120))
    username: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entries: Mapped[list["DailyEntry"]] = relationship(back_populates="user")
    reports: Mapped[list["WeeklyReport"]] = relationship(back_populates="user")


class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20))
    raw_text: Mapped[str] = mapped_column(Text)
    transcription: Mapped[str | None] = mapped_column(Text)
    improved_text: Mapped[str | None] = mapped_column(Text)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[EntryStatus] = mapped_column(String(40), default=EntryStatus.RECEIVED)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    iso_week: Mapped[str] = mapped_column(String(10), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="entries")
    revisions: Mapped[list["EntryRevision"]] = relationship(back_populates="entry")


class EntryRevision(Base):
    __tablename__ = "entry_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("daily_entries.id"), index=True)
    instruction: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entry: Mapped[DailyEntry] = relationship(back_populates="revisions")


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    __table_args__ = (UniqueConstraint("user_id", "iso_week", name="uq_weekly_report_user_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    iso_week: Mapped[str] = mapped_column(String(10), index=True)
    report_text: Mapped[str] = mapped_column(Text)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="reports")
