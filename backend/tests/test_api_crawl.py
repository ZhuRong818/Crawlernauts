import json
import pytest

@pytest.fixture(autouse=True)
def stub_extract(monkeypatch):
    """Prevent real HTTP; always return a known payload."""
    def fake_extract(url, mode, value, limit=30):
        return [{"fake": "data"}], None
    monkeypatch.setattr("backend.routes_api._extract", fake_extract)


def test_crawl_now(client, api_headers):
    payload = {
        "url":   "https://example.com",
        "mode":  "tag",
        "value": "a"
    }
    resp = client.post("/api/crawl",
                       headers=api_headers,
                       data=json.dumps(payload))

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["msg"] == "ok"
    assert data["data"] == [{"fake": "data"}]
    assert isinstance(data["result_id"], int)
    assert isinstance(data["job_id"],    int)
