"""Rebuild the school roster and the last-winter series from the raw downloads.

Usage:
    python3 tools/prepare_data.py frmSchoolList.html delhi_air_quality_2023_2025_hourly.csv out_dir

Inputs
  frmSchoolList.html   saved page from edudel.nic.in (school list with latitude and longitude)
  hourly csv           hourly PM2.5 with columns date, hour, pm2_5 (central Delhi model data)

Outputs (in out_dir)
  chosen.json          one senior-secondary school nearest to each target area
  last_season.json     school-hour (8:00 to 14:00) mean PM2.5 for each day, 1 Oct to 31 Dec, per year

Edit TARGETS to choose other areas. Paste the results into the SCHOOLS and LAST
variables in index.html, and the ids and coordinates into lambda/schools.json.
"""
import csv
import datetime as dt
import html
import json
import math
import os
import re
import sys

TARGETS = [("Anand Vihar", 28.6469, 77.3159), ("Rohini", 28.7160, 77.1130), ("Wazirpur", 28.6990, 77.1650),
           ("Mayur Vihar", 28.6080, 77.2950), ("Okhla", 28.5300, 77.2750), ("Punjabi Bagh", 28.6700, 77.1310),
           ("R K Puram", 28.5670, 77.1840), ("Dwarka", 28.5920, 77.0450), ("Vasant Kunj", 28.5230, 77.1550),
           ("Lodhi Road", 28.5920, 77.2270), ("Narela", 28.8530, 77.0900), ("Jahangirpuri", 28.7280, 77.1640)]


def cells(row):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]


def load_schools(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        d = cells(r)
        if len(d) >= 15 and d[0].isdigit():
            try:
                lat, lon = float(d[13]), float(d[14])
            except ValueError:
                continue
            if 28.3 < lat < 28.95 and 76.8 < lon < 77.45:
                out.append(dict(district=d[1], udise=d[4], name=d[6], addr=d[7], level=d[9], lat=lat, lon=lon))
    return out


def km(a, b, c, d):
    p = math.pi / 180
    return 6371 * math.hypot((c - a) * p, (d - b) * p * math.cos((a + c) / 2 * p))


def choose(schools):
    used, chosen = set(), []
    for name, la, lo in TARGETS:
        pool = [s for s in schools if "Sr" in s["level"] and s["udise"] not in used]
        best = min(pool, key=lambda s: km(la, lo, s["lat"], s["lon"]))
        used.add(best["udise"])
        chosen.append(dict(area=name, dist_km=round(km(la, lo, best["lat"], best["lon"]), 2), **best))
    return chosen


def last_season(csv_path):
    by = {}
    for r in csv.DictReader(open(csv_path, encoding="utf-8")):
        try:
            by.setdefault(r["date"][:10], {})[int(r["hour"])] = float(r["pm2_5"])
        except (ValueError, KeyError):
            continue
    out = {}
    for y in (2023, 2024, 2025):
        arr, d = [], dt.date(y, 10, 1)
        while d <= dt.date(y, 12, 31):
            hrs = by.get(d.isoformat(), {})
            w = [hrs[h] for h in range(8, 14) if h in hrs]
            arr.append(round(sum(w) / len(w), 1) if len(w) >= 4 else None)
            d += dt.timedelta(days=1)
        out[y] = arr
    return out


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    schools_html, hourly_csv, out_dir = sys.argv[1:]
    os.makedirs(out_dir, exist_ok=True)
    chosen = choose(load_schools(schools_html))
    json.dump(chosen, open(os.path.join(out_dir, "chosen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(last_season(hourly_csv), open(os.path.join(out_dir, "last_season.json"), "w"))
    for c in chosen:
        print("%-13s %.2f km  %s (%s)" % (c["area"], c["dist_km"], c["name"], c["udise"]))

