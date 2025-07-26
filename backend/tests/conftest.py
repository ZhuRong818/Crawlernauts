# backend/tests/conftest.py
import os
import tempfile
import pytest
from backend.app import create_app
from backend.models import db as _db, User

@pytest.fixture(scope="session")
def app():
    """Create a Flask app instance configured for tests."""
    db_fd, db_path = tempfile.mkstemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret"

    app = create_app(with_scheduler=False)

    with app.app_context():
        _db.create_all()

    yield app

    with app.app_context():
        _db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="session")
def client(app):
    """Flask test client."""
    with app.app_context():
        yield app.test_client()


@pytest.fixture(scope="session")
def api_headers(app):
    """Headers with an API key for authentication."""
    with app.app_context():
        user = User.query.filter_by(username="test@example.com").first()
        if not user:
            user = User(username="test@example.com")
            user.set_password("password")
            user.ensure_api_key()
            user.verified = True
            _db.session.add(user)
            _db.session.commit()
        return {
            "Authorization": f"Bearer {user.api_key}",
            "Content-Type": "application/json",
        }
