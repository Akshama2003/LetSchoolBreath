"""Saans Schools: observed PM2.5 from the nearest OpenAQ station for each school.

GET /observed returns, per school id, the nearest station that measures PM2.5
within 25 km and today's hourly PM2.5 values (India time, 24 slots, None where
no reading exists yet). The OpenAQ key stays here, never in the browser.

Standard library only, so there is nothing to package.
"""
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.openaq.org/v3"
IST = timezone(timedelta(hours=5, minutes=30))
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_SECONDS = 1800

_cache = {"at": 0.0, "body": None}


def _schools():
    with open(os.path.join(HERE, "schools.json"), encoding="utf-8") as f:
        return json.load(f)


def _get(path, params):
    url = API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"X-API-Key": os.environ["OPENAQ_API_KEY"], "User-Agent": "saans-schools/1.0"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_pm25(lat, lon):
    """Nearest location within 25 km that has a PM2.5 sensor, or None."""
    data = _get(
        "/locations",
        {"coordinates": "%.4f,%.4f" % (lat, lon), "radius": 25000, "limit": 100},
    )
    best = None
    for loc in data.get("results", []):
        c = loc.get("coordinates") or {}
        if c.get("latitude") is None or c.get("longitude") is None:
            continue
        sensor = next(
            (s for s in loc.get("sensors", []) if (s.get("parameter") or {}).get("name") == "pm25"),
            None,
        )
        if not sensor:
            continue
        km = haversine_km(lat, lon, c["latitude"], c["longitude"])
        if best is None or km < best["km"]:
            best = {"sensor": sensor["id"], "name": loc.get("name") or "station %s" % loc.get("id"), "km": km}
    return best


def today_hours(sensor_id):
    """Hourly PM2.5 for today in India time as a 24-slot list."""
    now = datetime.now(IST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    data = _get(
        "/sensors/%s/hours" % sensor_id,
        {
            "datetime_from": start.astimezone(timezone.utc).strftime(fmt),
            "datetime_to": now.astimezone(timezone.utc).strftime(fmt),
            "limit": 48,
        },
    )
    hours = [None] * 24
    for r in data.get("results", []):
        value = r.get("value")
        units = ((r.get("parameter") or {}).get("units") or "").lower().replace("µ", "u").replace("μ", "u")
        stamp = ((r.get("period") or {}).get("datetimeFrom") or {}).get("utc")
        if value is None or value < 0 or not stamp or ("ug/m" not in units and units):
            continue
        t = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(IST)
        if t.date() == start.date():
            hours[t.hour] = round(float(value), 1)
    return hours


def build():
    out = {}
    by_sensor = {}
    for s in _schools():
        try:
            st = nearest_pm25(s["lat"], s["lon"])
            if not st:
                continue
            if st["sensor"] not in by_sensor:
                by_sensor[st["sensor"]] = today_hours(st["sensor"])
            hours = by_sensor[st["sensor"]]
            if any(v is not None for v in hours):
                out[s["id"]] = {"station": st["name"], "distanceKm": round(st["km"], 1), "hours": hours}
        except Exception as exc:  # one failing school must not break the rest
            print("school %s failed: %s" % (s.get("id"), exc))
    return {
        "source": "openaq",
        "updated": datetime.now(IST).isoformat(timespec="minutes"),
        "schools": out,
    }


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "public, max-age=900"},
        "body": json.dumps(body),
    }


def handler(event, context):
    if not os.environ.get("OPENAQ_API_KEY"):
        return _response(503, {"error": "OPENAQ_API_KEY is not set"})
    if _cache["body"] and time.time() - _cache["at"] < CACHE_SECONDS:
        return _response(200, _cache["body"])
    try:
        body = build()
    except Exception as exc:
        print("observed failed: %s" % exc)
        return _response(502, {"error": "OpenAQ request failed"})
    _cache.update(at=time.time(), body=body)
    return _response(200, body)

