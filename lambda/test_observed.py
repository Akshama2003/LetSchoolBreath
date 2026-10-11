"""Offline check of observed.py using fake OpenAQ responses. Run: python3 lambda/test_observed.py"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import observed  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
midnight = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)


def fake_get(path, params):
    if path == "/locations":
        return {"results": [
            {"id": 1, "name": "Far PM10 only", "coordinates": {"latitude": 28.65, "longitude": 77.31},
             "sensors": [{"id": 10, "parameter": {"name": "pm10"}}]},
            {"id": 2, "name": "Near station", "coordinates": {"latitude": 28.66, "longitude": 77.32},
             "sensors": [{"id": 20, "parameter": {"name": "pm25"}}]},
            {"id": 3, "name": "Farther station", "coordinates": {"latitude": 28.90, "longitude": 77.50},
             "sensors": [{"id": 30, "parameter": {"name": "pm25"}}]},
        ]}
    if path == "/sensors/20/hours":
        res = []
        for h in range(0, 6):
            t = (midnight + timedelta(hours=h)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            res.append({"value": 100 + h, "parameter": {"units": "µg/m³"},
                        "period": {"datetimeFrom": {"utc": t}}})
        res.append({"value": -999, "parameter": {"units": "µg/m³"},
                    "period": {"datetimeFrom": {"utc": t}}})
        return {"results": res}
    raise AssertionError("unexpected call " + path)


with mock.patch.object(observed, "_get", fake_get):
    body = observed.build()

assert body["source"] == "openaq"
s1 = body["schools"]["s1"]
assert s1["station"] == "Near station", s1
assert s1["distanceKm"] < 3, s1
assert s1["hours"][0] == 100.0 and s1["hours"][5] == 105.0, s1["hours"]
assert s1["hours"][6] is None, "future hours stay empty"
assert len(s1["hours"]) == 24
os.environ.pop("OPENAQ_API_KEY", None)
assert observed.handler({}, None)["statusCode"] == 503
print("observed.py OK:", len(body["schools"]), "schools matched;", json.dumps(s1)[:90], "...")

