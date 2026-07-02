import io

from fastapi.testclient import TestClient


def test_upload_file(client: TestClient) -> None:
    file_content = b"hello formatflow"
    response = client.post(
        "/api/v1/upload",
        files={"file": ("sample.txt", io.BytesIO(file_content), "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "sample.txt"
    assert body["size_bytes"] == len(file_content)
    assert body["file_id"]
