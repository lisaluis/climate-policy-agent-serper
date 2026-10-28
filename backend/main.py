import os
from urllib.parse import urlparse
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Climate Policy Agent API", version="1.0.0")
origin = os.getenv("FRONTEND_ORIGIN", "*").strip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origin == "*" else [x.strip() for x in origin.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    location: str = Field(default="India", max_length=100)
    max_results: int = Field(default=8, ge=3, le=10)

TRUSTED_HINTS = (
    ".gov.in", "cpcb.nic.in", "moef.gov.in", "pib.gov.in", "who.int",
    "ipcc.ch", "unep.org", "worldbank.org", "nature.com",
    "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov"
)

def source_hint(domain: str) -> str:
    domain = domain.lower()
    if any(x in domain for x in TRUSTED_HINTS):
        return "Prioritize for verification"
    if domain.endswith(".edu") or ".edu." in domain or domain.endswith(".ac.in"):
        return "Research / academic source"
    return "Needs source verification"

def search_web(query: str, limit: int) -> list[dict[str, Any]]:
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "SERPER_API_KEY is not configured on the backend.")
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "gl": "in", "hl": "en", "num": limit},
            timeout=25,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        raise HTTPException(502, f"Web search failed: {exc.__class__.__name__}") from exc
    results, seen = [], set()
    for item in data.get("organic", []):
        url, title = item.get("link", "").strip(), item.get("title", "").strip()
        if not url or not title:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        domain = parsed.netloc.lower().removeprefix("www.")
        dedupe_key = domain + parsed.path.rstrip("/")
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        results.append({
            "title": title, "url": url, "snippet": item.get("snippet", ""),
            "source": domain, "date": item.get("date"),
            "source_quality_hint": source_hint(domain)
        })
    return results[:limit]

def recommendations(question: str, location: str) -> list[dict[str, str]]:
    q = question.lower()
    items = []
    def add(title, action, stakeholders, priority, rationale):
        items.append({"title": title, "action": action, "stakeholders": stakeholders,
                      "priority": priority, "rationale": rationale})

    if any(x in q for x in ("air", "pollution", "pm2.5", "pm10", "emission", "smog", "transport", "vehicle")):
        add("Strengthen air-quality monitoring and public reporting",
            "Identify recurring hotspots, publish accessible local summaries and evaluate measured changes after interventions.",
            "CPCB and State Pollution Control Boards; municipal bodies", "High",
            "Monitoring helps target action; local measurements are needed before selecting specific controls.")
        add("Prioritize source-specific emission reduction",
            "Assess transport, road dust, industry, waste burning and other locally relevant sources; act on sources shown to contribute most.",
            "State and local governments; transport and industry regulators", "High",
            "A source inventory avoids one-size-fits-all policy. Verify local source contributions first.")
    if any(x in q for x in ("climate", "warming", "heat", "enso", "el niño", "rainfall", "drought", "flood", "weather")):
        add("Integrate climate risks into seasonal planning",
            "Combine weather outlooks with air-quality, health and environmental monitoring; define response triggers and review outcomes each season.",
            "IMD; disaster-management authorities; health and environment departments", "High",
            "Weather affects exposure and dispersion, but forecasts are not deterministic predictions.")
        add("Build adaptation into local plans",
            "Identify locally relevant climate risks and prioritize actions with clear owners, budgets and measurable outcomes.",
            "State departments; district administrations; local bodies", "Medium",
            "Appropriate interventions depend on local risk assessments and community needs.")
    if any(x in q for x in ("waste", "plastic", "burning", "landfill", "solid waste")):
        add("Prevent open waste burning and improve waste services",
            "Improve segregated collection, safe processing, enforcement and public reporting; track repeat burning locations.",
            "Municipal bodies; State Pollution Control Boards; waste operators", "High",
            "Enforcement should be paired with reliable waste collection and disposal alternatives.")
    if any(x in q for x in ("goa", "tourism", "coast", "beach", "mangrove", "biodiversity")) or "goa" in location.lower():
        add("Use Goa-specific environmental safeguards",
            "Assess tourism, traffic, waste, coastal development and ecosystem pressures by location; involve communities and publish site-level indicators.",
            "Government of Goa; local bodies; tourism and environment departments; communities", "High",
            "These are candidate priorities, not proof that each is dominant everywhere in Goa. Verify using current local evidence.")
    if not items:
        add("Establish an evidence baseline before choosing a policy",
            "Collect current environmental indicators, identify affected groups and major sources, compare existing measures, then set measurable targets.",
            "Relevant central and state departments; local authorities; researchers", "High",
            "The question is broad; policy selection should follow a baseline and evidence review.")
    seen, unique = set(), []
    for item in items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return unique[:5]

@app.get("/")
def root():
    return {"name": "Climate Policy Agent API", "status": "ok",
            "search_configured": bool(os.getenv("SERPER_API_KEY")), "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok", "search_configured": bool(os.getenv("SERPER_API_KEY"))}

@app.post("/api/ask")
def ask(request: AskRequest):
    query = f"{request.question} {request.location} climate air pollution environmental policy evidence government research"
    evidence = search_web(query, request.max_results)
    if not evidence:
        raise HTTPException(404, "No search results found. Try a more specific question.")
    return {
        "question": request.question, "location": request.location, "search_query": query,
        "evidence": evidence, "recommendations": recommendations(request.question, request.location),
        "limitations": [
            "Search snippets are not a substitute for reading the full source.",
            "Source-quality labels are heuristics, not proof that a claim is correct.",
            "Recommendations are transparent rule-based suggestions, not LLM-generated analysis.",
            "Verify publication dates, methods, local data and current laws before using a recommendation.",
            "This prototype does not calculate emissions reductions, costs or causal effects."
        ],
        "method": "Serper web search + source-quality hints + rule-based recommendations"
    }
