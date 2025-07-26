# backend/models.py
from datetime import datetime, timedelta
import secrets
import random

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(150), unique=True, nullable=False)  # email
    password_hash = db.Column(db.String(256), nullable=False)
    api_key       = db.Column(db.String(32), unique=True)
    verified      = db.Column(db.Boolean, default=False)

    crawl_jobs    = db.relationship("CrawlJob", backref="owner", lazy="dynamic")
    crawl_results = db.relationship("CrawlResult", backref="owner", lazy="dynamic")

    def set_password(self, plain_password: str):
        self.password_hash = generate_password_hash(
            plain_password,
            method="pbkdf2:sha256",
            salt_length=16
        )

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self.password_hash, plain_password)

    @staticmethod
    def generate_api_key():
        return secrets.token_hex(16)

    def ensure_api_key(self):
        if not self.api_key:
            self.api_key = User.generate_api_key()

    def as_simple(self):
        return {"username": self.username, "apiKey": self.api_key}

    def __repr__(self):
        return f"<User {self.username}>"


class CrawlJob(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"))
    name             = db.Column(db.String(80), nullable=True)
    url              = db.Column(db.String, nullable=False)
    extraction_mode  = db.Column(db.String(10))
    extraction_value = db.Column(db.String(120))
    next_run_at      = db.Column(db.DateTime, nullable=True)
    recurring        = db.Column(db.Boolean, default=False)
    frequency        = db.Column(db.String(10))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        status = "Scheduled"
        if self.recurring:
            status = f"Recurring ({self.frequency})"
        if self.next_run_at is None:
            status = "Completed" if not self.recurring else status
        elif self.next_run_at <= datetime.utcnow():
            status = "Completed" if not self.recurring else status
        return {
            "id": self.id,
            "name": self.name or "(untitled)",
            "url": self.url,
            "extractionMode": self.extraction_mode,
            "extractionValue": self.extraction_value,
            "dateTime": self.next_run_at.isoformat() if self.next_run_at else None,
            "recurring": self.recurring,
            "frequency": self.frequency,
            "status": status
        }

    def __repr__(self):
        return f"<CrawlJob {self.id}: {self.url}>"

    crawl_results = db.relationship(
        "CrawlResult",
        backref="job",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class CrawlResult(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"))
    job_id = db.Column(
        db.Integer,
        db.ForeignKey("crawl_job.id", ondelete="CASCADE"),
        nullable=False
    )
    url              = db.Column(db.String, nullable=False)
    extraction_mode  = db.Column(db.String(10))
    extraction_value = db.Column(db.String(120))
    data             = db.Column(db.PickleType)
    ran_at           = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CrawlResult {self.id} for {self.url} @ {self.ran_at}>"


class VerificationCode(db.Model):
    __tablename__ = "verification_code"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    code       = db.Column(db.String(6), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    user       = db.relationship("User", backref=db.backref("codes", cascade="all,delete-orphan"))

    @staticmethod
    def generate_for(user, ttl_minutes=1):
        token = f"{random.randint(0, 999999):06d}"
        now   = datetime.utcnow()
        vc    = VerificationCode(user=user, code=token,
                                 created_at=now,
                                 expires_at=now + timedelta(minutes=ttl_minutes))
        db.session.add(vc)
        db.session.commit()
        return vc

    @staticmethod
    def validate(user, submitted_code):
        vc = VerificationCode.query.filter_by(user_id=user.id, code=submitted_code).first()
        if not vc or vc.expires_at < datetime.utcnow():
            return False
        db.session.delete(vc)
        user.verified = True
        db.session.commit()
        return True


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role      = db.Column(db.String(20), nullable=False)
    content   = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='chat_messages')
