from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_upload_invoice() -> None:
    # Create test files
    file1 = BytesIO(b"test invoice content 1")
    file2 = BytesIO(b"test invoice content 2")

    response = client.post(
        "/upload",
        data={"ticket_number": "INC0123456"},
        files=[
            ("files", ("invoice1.pdf", file1, "application/pdf")),
            ("files", ("invoice2.pdf", file2, "application/pdf")),
        ],
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "Files uploaded successfully"
    assert json_response["ticket_number"] == "INC0123456"
    assert json_response["files_received"] == 2
    assert json_response["filenames"] == ["invoice1.pdf", "invoice2.pdf"]


def test_upload_invoice_missing_ticket() -> None:
    file1 = BytesIO(b"test content")

    response = client.post(
        "/upload",
        files=[("files", ("test.pdf", file1, "application/pdf"))],
    )

    assert response.status_code == 422  # Validation error


def test_upload_invoice_missing_files() -> None:
    response = client.post(
        "/upload",
        data={"ticket_number": "INC0123456"},
    )

    assert response.status_code == 422  # Validation error
