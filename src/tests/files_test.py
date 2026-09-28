import json

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_files():
    user = client.post(
        "/Login", data={"username": "normaluser@mail.com", "password": "1"}
    ).json()
    # print("token:", token)
    assert len(user["token"]) != 0
    headers = {"Authorization": f"Bearer {user['token']}"}

    with open(
        "/home/ryan/Documents/lkcnhm/BHCAIS/sample data/LKCNHM Print Catalog_100 value sample _JT.xlsx",
        "rb",
    ) as print_file:
        response = client.post(
            "/UploadFiles",
            params={
                "user_id": user["user_id"],
                "token": user["token"],
            },
            files={"files": ("file1.xlsx", print_file)},
            headers=headers,
        )
        assert response.status_code == 200
    print("response of file upload", response)
    response = client.get(
        "/GetCatalogue",
        params={
            "catalogue_name": "print",
            "filter_str": "",
            "sort_by": "",
            "descending": False,
            "rows_per_page": 10,
            "current_page_number": 1,
            "token": user["token"],
        },
        headers=headers,  # required or else it will say "not authenticated"
    )
    results = json.loads(response.text)["results"]
    print("total length of results from GetCatalogue", len(results))
    assert response.status_code == 200
