import io

from fastapi.testclient import TestClient


def _upload(client: TestClient, files: list[tuple[str, bytes, str]]):
    return client.post(
        "/api/v1/convert/images-to-pdf",
        files=[
            ("files", (name, io.BytesIO(content), content_type))
            for name, content, content_type in files
        ],
    )


def test_convert_single_image_success_end_to_end(
    client_with_tmp_storage: TestClient, sample_jpg_bytes: bytes
) -> None:
    response = _upload(client_with_tmp_storage, [("photo.jpg", sample_jpg_bytes, "image/jpeg")])
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "completed"
    assert status_body["progress"] == 100
    # Single image: named after the source file, not the generic "images.pdf".
    assert status_body["filename"] == "photo.pdf"
    assert status_body["download_url"] == f"/api/v1/convert/jobs/{job_id}/download"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.headers["content-disposition"].endswith('photo.pdf"')
    assert download_response.content[:5] == b"%PDF-"
    assert len(download_response.content) > 500

    # Automatic cleanup: job and its output file are gone after download.
    followup = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}")
    assert followup.status_code == 404


def test_convert_multiple_images_combined_into_one_pdf(
    client_with_tmp_storage: TestClient,
    sample_jpg_bytes: bytes,
    sample_png_bytes: bytes,
    sample_webp_bytes: bytes,
) -> None:
    response = _upload(
        client_with_tmp_storage,
        [
            ("first.jpg", sample_jpg_bytes, "image/jpeg"),
            ("second.png", sample_png_bytes, "image/png"),
            ("third.webp", sample_webp_bytes, "image/webp"),
        ],
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_body = client_with_tmp_storage.get(f"/api/v1/convert/jobs/{job_id}").json()
    assert status_body["status"] == "completed"
    # Multiple images: generic combined filename, not any single source name.
    assert status_body["filename"] == "images.pdf"

    download_response = client_with_tmp_storage.get(status_body["download_url"])
    assert download_response.status_code == 200
    assert download_response.content[:5] == b"%PDF-"


def test_convert_rejects_unsupported_file_type(client_with_tmp_storage: TestClient) -> None:
    response = _upload(client_with_tmp_storage, [("notes.txt", b"just some text", "text/plain")])
    assert response.status_code == 400
    assert "JPG" in response.json()["detail"]


def test_convert_rejects_corrupted_image(
    client_with_tmp_storage: TestClient, corrupted_image_bytes: bytes
) -> None:
    response = _upload(
        client_with_tmp_storage, [("broken.jpg", corrupted_image_bytes, "image/jpeg")]
    )
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"]


def test_convert_rejects_if_any_image_in_batch_is_invalid(
    client_with_tmp_storage: TestClient, sample_jpg_bytes: bytes
) -> None:
    # First file valid, second invalid — the whole batch should be rejected,
    # not partially processed.
    response = _upload(
        client_with_tmp_storage,
        [
            ("good.jpg", sample_jpg_bytes, "image/jpeg"),
            ("bad.gif", b"not an image", "image/gif"),
        ],
    )
    assert response.status_code == 400
