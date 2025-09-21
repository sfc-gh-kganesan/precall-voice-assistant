from io import BytesIO
from unittest.mock import Mock, patch

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


@patch("app.main.filestore_pb2_grpc.FileStoreStub")
@patch("app.main.grpc.insecure_channel")
def test_upload_file_success(mock_channel, mock_stub_class) -> None:
    # Mock the gRPC response
    mock_response = Mock()
    mock_response.success = True
    mock_response.message = "File uploaded successfully"
    mock_response.file_id = "test-file-id-123"

    mock_stub = Mock()
    mock_stub.UploadFile.return_value = mock_response
    mock_stub_class.return_value = mock_stub

    mock_channel_instance = Mock()
    mock_channel.return_value = mock_channel_instance

    # Create test file
    test_file = BytesIO(b"test file content")

    response = client.post(
        "/upload-file",
        files=[("file", ("test.txt", test_file, "text/plain"))],
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["message"] == "File uploaded successfully"
    assert json_response["file_id"] == "test-file-id-123"

    # Verify gRPC client was called correctly
    mock_channel.assert_called_once_with("localhost:50051")
    mock_stub_class.assert_called_once_with(mock_channel_instance)
    mock_stub.UploadFile.assert_called_once()
    mock_channel_instance.close.assert_called_once()


@patch("app.main.filestore_pb2_grpc.FileStoreStub")
@patch("app.main.grpc.insecure_channel")
def test_upload_file_grpc_error(mock_channel, mock_stub_class) -> None:
    # Mock gRPC failure
    mock_stub = Mock()
    mock_stub.UploadFile.side_effect = Exception("gRPC connection failed")
    mock_stub_class.return_value = mock_stub

    mock_channel_instance = Mock()
    mock_channel.return_value = mock_channel_instance

    # Create test file
    test_file = BytesIO(b"test file content")

    response = client.post(
        "/upload-file",
        files=[("file", ("test.txt", test_file, "text/plain"))],
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is False
    assert "Failed to upload file" in json_response["message"]
    assert json_response["file_id"] == ""


def test_upload_file_no_filename() -> None:
    # Create file without filename
    test_file = BytesIO(b"test file content")

    response = client.post(
        "/upload-file",
        files=[("file", ("", test_file, "text/plain"))],
    )

    assert response.status_code == 400
    assert "No filename provided" in response.json()["detail"]
