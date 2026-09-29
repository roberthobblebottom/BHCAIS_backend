import json
from pathlib import Path

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_files():
    print("Testing these modules: upload files, get catalogue and download report")
    user = client.post(
        "/Login", data={"username": "normaluser@mail.com", "password": "1"}
    ).json()
    # print("token:", token)
    assert len(user["token"]) != 0
    print('assert len(user["token"]) != 0 is true')
    headers = {"Authorization": f"Bearer {user['token']}"}

    base_path = Path(
        __file__
    ).parent.parent.parent  # 3 times to go back two directories
    file_path = (
        base_path
        / "sample_data_for_testing/LKCNHM Print Catalog_100 value sample _JT.xlsx"
    ).resolve()
    with open(
        # "../../sample_data_for_testing/LKCNHM Print Catalog_100 value sample _JT.xlsx",
        file_path,
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
    print("asserted  response of file upload 200")
    response = client.get(
        "/GetCatalogue",
        params={
            "catalogue_name": "print",
            "filter_str": "place",
            "sort_by": "",
            "descending": False,
            "rows_per_page": 10,
            "current_page_number": 1,
            "token": user["token"],
        },
        headers=headers,  # required or else it will say "not authenticated"
    )
    results = json.loads(response.text)["results"]
    assert response.status_code == 200 and len(results) > 1
    print(
        "asserted status code  = 200 and total length of results from GetCatalogue is more than 1."
    )
    response = client.post(
        "/DownloadFiles",
        headers=headers,
        json={
            "search_terms": {"print": {"main_category": "place"}},
            "selected_catalogues": ["print"],
            "token": user["token"],
        },
    )  # must be json not data as the arguement
    catalog_name = ""
    results = {}
    for x in response.text.split("\n"):
        if x == "":
            continue
        x = json.loads(x)
        if next(iter(x.keys())) == "catalogue_name":
            catalog_name = next(iter(x.values()))
            results[catalog_name] = []
        else:
            assert catalog_name != ""
            results[catalog_name].append(x)
        # results = json.loads("[" + response.text[response.text.find("{") : -1] + "]")
    unique_cat = {
        r["main_category"] for r in results["print"] if r["main_category"] == "Place"
    }
    assert len(unique_cat) == 1 and next(iter(unique_cat)) == "Place"
    print("asserted the only unique main cat is placed")
