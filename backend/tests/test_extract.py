import pytest
from backend.routes_api import _extract

def test_extract_tag(monkeypatch):
    html = "<html><body><a href='https://x'>X</a></body></html>"

    class FakeResp:
        text = html
        def raise_for_status(self):
            # fake no-op
            pass

    # stub out requests.get → our FakeResp instance
    monkeypatch.setattr(
        "backend.routes_api.requests.get",
        lambda *a, **k: FakeResp()
    )

    rows, err = _extract("http://dummy", "tag", "a")
    assert err is None
    assert rows == [{"content": "X", "url": "https://x"}]
