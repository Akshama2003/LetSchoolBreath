# Saans Schools — hackathon demo

A school-day decision dashboard for Delhi air pollution. Open `index.html` to see how forecast PM2.5 can become a school-hour risk estimate, simple actions, and a parent-message draft. It uses a live CAMS forecast when available, with a built-in sample fallback. The 12 school names and locations are drawn from a Delhi Directorate of Education list.

## What the demo uses

| Part | Status |
| --- | --- |
| Hourly PM2.5 and the 5-day outlook | Intended live feed: CAMS ENSEMBLE via Open-Meteo, no key; falls back to sample values. |
| Station readings | Optional. OpenAQ through the Lambda in `lambda/`. Needs an OpenAQ key. |
| 12 school names, areas, UDISE codes, coordinates | Real. From the Delhi Directorate of Education school list. |
| Enrolment per school | **Placeholder.** The DoE list has no enrolment. Replace with UDISE+ figures. |
| Asthma counts | **Population-level planning estimate**, 7.9% of placeholder enrollment. Not a school record or individual student list. |
| Last-winter strips | Real past days from hourly model data for central Delhi (single point), not station readings. |
| Fire detections | Not included; remove any reference to counts until NASA FIRMS or CREAMS is integrated. |
| SMS sending | Simulated. Nothing is sent; recipient counts are placeholders. |

This is a prototype decision aid, not an official closure system. Its “AQI” uses hourly PM2.5 only; official CPCB AQI uses averaging periods and multiple pollutants, so treat these bands as rough estimates. Operational thresholds and advice need review with school and public-health partners. The PM2.5 bands used (0-30, 31-60, 61-90, 91-120, 121-250, 250+) match the CPCB "About AQI" table.

## Dataset needed to make this credible

- **School roster:** verified IDs, addresses and coordinates (already present; recheck before public use).
- **Enrollment:** current UDISE+ or school-provided totals by school and grade; replace invented placeholder counts.
- **Health vulnerability:** do not infer school-specific asthma records from national prevalence. For a prototype, omit student counts or show only a clearly labeled aggregate planning estimate; avoid collecting health data.
- **Air quality:** timestamped measurements, sensor coordinates, units and quality flags; CAMS/Open-Meteo forecasts with model run time and forecast horizon.
- **Actions and policy:** current CAQM/GRAP orders plus school-approved response steps. Validate thresholds with public-health and education experts.
- **Optional fire context:** NASA FIRMS detections with date, location and confidence; define an upwind radius and avoid implying causation.

## Simple roadmap

1. **Now — clarify the demo:** distinguish sample from live readings and walk through one school's decision.
2. **Data quality:** verify coordinates, replace placeholder enrollment, and inspect station/forecast timestamps and units.
3. **Pilot:** compare forecasts with nearby stations and have schools/public-health partners review actions.
4. **Deploy:** host the static page; add Lambda + API Gateway only if station readings add value.
5. **Notifications:** real SMS needs pilot validation, consent, secure contacts, monitoring and opt-out. Current recipient counts and delivery animation are demo-only.

## Run it now (no backend)

Open `index.html` in a browser, or serve the folder:

    python3 -m http.server 8000

The top pill reports live forecast status or sample values. The first view also labels illustrative values; verify status in the demo browser.

## Add real station readings (optional)

1. Get a free OpenAQ API key at explore.openaq.org. **Do not put the key in `index.html`.** It goes only into the deploy command below, so it stays on the server.
2. Install the AWS SAM CLI, then from this folder:

       sam build
       sam deploy --guided --parameter-overrides OpenAQKey=YOUR_KEY

3. Copy the `ObservedUrl` output into `index.html`:

       var CONFIG = { observedUrl: 'https://xxxx.execute-api.ap-south-1.amazonaws.com/observed' };

4. Reload. The pill now reads "Live forecast + N stations". Each school with a PM2.5 station within 25 km shows that station's measured hours instead of the model.

The Lambda has an offline fake-response test. Its real API path has not been verified with a live key; check it before relying on station readings.

## Host it

Zip `index.html` and drag it into AWS Amplify Hosting (manual deploy), or upload it to an S3 bucket with static website hosting.

## Honest demo notes

- Live browser forecast and OpenAQ integration were not verified in this environment. Keep the source status visible and be ready to show the sample fallback.
- Open-Meteo is free for non-commercial use and asks for attribution. The page footer credits it when live forecasts load.
- School coordinates come from the DoE list. Confirm a couple on a map before the demo.
- Do not present sample counts as real school enrollment or student health records.

## Change the schools

`python3 tools/prepare_data.py frmSchoolList.html delhi_air_quality_2023_2025_hourly.csv out/` picks the nearest senior-secondary school to each target area in the script and rebuilds the last-winter series. Paste the results into `SCHOOLS` and `LAST` in `index.html`, and the ids and coordinates into `lambda/schools.json`.

## Files

    index.html               the whole site (no build step)
    template.yaml            AWS SAM template for the optional Lambda and HTTP API
    lambda/observed.py       nearest-station lookup, OpenAQ key stays server-side
    lambda/schools.json      school ids and coordinates used by the Lambda
    lambda/test_observed.py  offline test with fake OpenAQ responses
    tools/prepare_data.py    rebuilds the roster and last-winter data from the raw downloads

