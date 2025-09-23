import pytest
from py_protos import filestore_pb2

from app.main import FileStoreServicer


@pytest.fixture
def servicer():
    return FileStoreServicer()


def test_upload_file_success(servicer):
    def request_iterator():
        yield filestore_pb2.FileChunk(filename="test.txt", content=b"Hello, ", is_last=False)
        yield filestore_pb2.FileChunk(filename="test.txt", content=b"World!", is_last=True)

    response = servicer.UploadFile(request_iterator(), None)

    assert response.success is True
    assert "File uploaded successfully" in response.message
    assert response.file_id != ""


def test_upload_file_no_filename(servicer):
    def request_iterator():
        yield filestore_pb2.FileChunk(filename="", content=b"content", is_last=True)

    response = servicer.UploadFile(request_iterator(), None)

    assert response.success is False
    assert "No filename provided" in response.message
    assert response.file_id == ""
