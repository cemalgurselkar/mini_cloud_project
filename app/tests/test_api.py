import socket
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import main
from db import Base, get_db


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(main, "engine", test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    test_engine.dispose()


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_notes_crud(client: TestClient) -> None:
    create_response = client.post(
        "/notes",
        json={"title": "First note", "content": "Hello"},
    )
    assert create_response.status_code == 201
    note_id = create_response.json()["id"]

    assert client.get("/notes").json()[0]["title"] == "First note"
    assert client.get(f"/notes/{note_id}").status_code == 200

    update_response = client.put(
        f"/notes/{note_id}",
        json={"title": "Updated note", "content": "Updated content"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated note"

    assert client.delete(f"/notes/{note_id}").status_code == 204
    assert client.get(f"/notes/{note_id}").status_code == 404


def test_whoami(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "gethostname", lambda: "app1")

    response = client.get("/whoami")

    assert response.status_code == 200
    assert response.json() == {"hostname": "app1"}
