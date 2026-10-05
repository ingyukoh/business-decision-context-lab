"""Read-only prediction service; historical LLM outputs are labelled as recorded."""
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt
from lab import ROOT, context, predict, reviewed_output

app = FastAPI(title="Business Decision Context Lab")


class Inputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    TV: StrictFloat | StrictInt
    radio: StrictFloat | StrictInt
    newspaper: StrictFloat | StrictInt


@app.get("/health")
def health():
    return {"status": "ok", "mode": "read-only independent prototype"}


@app.post("/predict")
def prediction(x: Inputs):
    try:
        return {"result": predict(x.model_dump()), "semantic_context": context()}
    except (ValueError, AssertionError) as e:
        raise HTTPException(422, str(e))


@app.get("/report")
def report():
    return json.loads((ROOT / "results/report.json").read_text())


@app.get("/recorded-examples")
def recorded_examples():
    return [{"row_id": c["row_id"], "context": c["context"],
             **reviewed_output(c["output"], c["prediction"])}
            for c in report()["cases"]]


@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "docs/index.html").read_text()
