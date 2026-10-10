
import json
import math
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).with_name("q-vercel-latency.json")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    TELEMETRY = json.load(f)


class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float = 180


def percentile95(values):
    values = sorted(values)
    if len(values) == 1:
        return values[0]

    position = 0.95 * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)

    return values[lower] + (
        values[upper] - values[lower]
    ) * (position - lower)


@app.post("/")
def analytics(request: AnalyticsRequest):
    results = {}

    for region in request.regions:
        records = [
            row for row in TELEMETRY
            if row["region"].lower() == region.lower()
        ]

        if not records:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0,
            }
            continue

        latencies = [float(row["latency_ms"]) for row in records]
        uptimes = [float(row["uptime_pct"]) for row in records]

        results[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                latency > request.threshold_ms
                for latency in latencies
            ),
        }

    return results

