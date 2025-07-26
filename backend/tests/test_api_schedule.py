import json
import datetime as dt

def test_schedule_future_date(client, api_headers):
    # two hours from now, truncated to minutes
    future = (dt.datetime.utcnow() + dt.timedelta(hours=2)) \
             .isoformat(timespec="minutes")

    payload = {
        "url":      "https://example.com",
        "mode":     "tag",
        "value":    "a",
        "name":     "sched-ok",
        "dateTime": future
    }
    resp = client.post("/api/schedule",
                       headers=api_headers,
                       data=json.dumps(payload))

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["msg"] == "scheduled"
    assert isinstance(data["job_id"], int)
