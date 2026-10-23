from pathlib import Path

from fastapi.testclient import TestClient
from main import app
from pytest import raises

client = TestClient(app)


def test_upload_files_contraints_violation():
    user = client.post(
        "/Login", data={"username": "normaluser@mail.com", "password": "1"}
    ).json()
    assert len(user["token"]) != 0
    print('assert len(user["token"]) != 0 is true')
    headers = {"Authorization": f"Bearer {user['token']}"}

    # 3 times to go back two directories
    base_path = Path(__file__).parent.parent.parent

    file_path1 = (base_path / "sample_data_for_testing/headers only file.csv").resolve()
    with (
        open(file_path1, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.csv", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error

    file_path2 = (
        base_path / "sample_data_for_testing/headers only file.xlsx"
    ).resolve()
    with (
        open(file_path2, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.xlsx", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error

    file_path3 = (
        base_path / "sample_data_for_testing/incorrect slide headers.csv"
    ).resolve()
    with (
        open(file_path3, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.csv", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error

    file_path4 = (
        base_path / "sample_data_for_testing/missing slide headers .csv"
    ).resolve()
    with (
        open(file_path4, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.csv", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error

    file_path6 = (base_path / "sample_data_for_testing/sample_empty.csv").resolve()
    with (
        open(file_path6, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.csv", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error

    file_path6 = (
        base_path
        / "sample_data_for_testing/prints with some missing serial numbers.csv"
    ).resolve()
    with (
        open(file_path6, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.csv", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error

    file_path6 = (
        base_path
        / "sample_data_for_testing/prints with some missing serial numbers.xlsx"
    ).resolve()
    with (
        open(file_path6, "rb") as f,
        raises(ValueError) as e_info,
    ):
        client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.xlsx", f)},
            headers=headers,
        )
    error = str(e_info.value)
    print("EXPECTED ERROR:", error)
    assert "ValueError" in error
