"""
StartupSphere — AI Routes (Groq-powered, OpenAI-compatible)
/ai/analyze  → Quick AI analysis (used inline in submit-idea)
/ai/generate → AI idea generator
"""

import os, json, re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/ai", tags=["AI"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = "llama-3.3-70b-versatile"  # Free tier, strong reasoning model


# ── Request Models ─────────────────────────────
class IdeaAnalysisRequest(BaseModel):
    title:         str
    category:      str
    problem:       str
    solution:      str
    target:        Optional[str] = ""
    revenue_model: Optional[str] = ""
    tech_stack:    Optional[str] = ""
    idea_id:       Optional[int] = None


class IdeaGenerateRequest(BaseModel):
    keywords:  str
    category:  Optional[str] = ""
    audience:  Optional[str] = ""


# ── Helper: call Groq (OpenAI-compatible client) ──
def _call_groq(prompt: str, max_tokens: int = 1200) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# ── Helper: run idea analysis via Groq ─────────
def _run_ai_analysis(title, category, problem, solution, target, revenue_model, tech_stack) -> dict:
    prompt = f"""You are an expert startup analyst. Analyze this startup idea and return ONLY a valid JSON object (no markdown, no backticks, no extra text before or after).

Startup Idea:
- Title: {title}
- Category: {category}
- Problem: {problem}
- Solution: {solution}
- Target Audience: {target or 'Not specified'}
- Revenue Model: {revenue_model or 'Not specified'}
- Tech Stack: {tech_stack or 'Not specified'}

Return this EXACT JSON structure:
{{
  "overall_score": <number 1-100>,
  "verdict": "<2-3 sentence overall assessment>",
  "innovation_score": <number 1-100>,
  "feasibility_score": <number 1-100>,
  "market_score": <number 1-100>,
  "idea_summary": "<1-2 sentence summary of what this idea does>",
  "market_potential": "<2-3 sentences about market size and demand>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
  "opportunities": ["<opportunity 1>", "<opportunity 2>"],
  "threats": ["<threat 1>", "<threat 2>"],
  "suggested_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "ai_recommendation": "<final 2-3 sentence recommendation for the founder>"
}}"""

    raw = _call_groq(prompt, max_tokens=1200)
    clean = re.sub(r'```json|```', '', raw).strip()
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse JSON from AI output: {raw[:300]}")
    return json.loads(match.group())


# ── QUICK AI ANALYSIS (inline in submit-idea) ──
@router.post("/analyze")
def analyze_idea(
    request: IdeaAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        result = _run_ai_analysis(
            title=request.title,
            category=request.category,
            problem=request.problem,
            solution=request.solution,
            target=request.target,
            revenue_model=request.revenue_model,
            tech_stack=request.tech_stack,
        )

        if request.idea_id:
            idea = db.query(models.Idea).filter(
                models.Idea.id == request.idea_id,
                models.Idea.author_id == current_user.id
            ).first()
            if idea:
                idea.ai_analysis = result
                db.commit()
                print(f"[AI] Saved analysis for idea #{request.idea_id}")

        return {"success": True, "report": result}

    except Exception as e:
        print(f"[AI ANALYZE ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ── AI IDEA GENERATOR ──────────────────────────
@router.post("/generate")
def generate_startup_idea(
    request: IdeaGenerateRequest,
    current_user: models.User = Depends(get_current_user)
):
    try:
        prompt = f"""Generate a detailed, innovative startup idea based on these inputs:
- Keywords: {request.keywords}
- Category: {request.category or 'Any'}
- Target Audience: {request.audience or 'General'}

Return ONLY valid JSON (no markdown, no backticks):
{{
  "title": "<catchy startup name>",
  "tagline": "<one-line description>",
  "category": "<category>",
  "problem": "<clear problem statement 2-3 sentences>",
  "solution": "<innovative solution 2-3 sentences>",
  "target_audience": "<specific target users>",
  "revenue_model": "<how it makes money>",
  "tech_stack": "<recommended technologies>",
  "unique_factor": "<what makes this different>",
  "first_steps": ["<step 1>", "<step 2>", "<step 3>"]
}}"""

        raw = _call_groq(prompt, max_tokens=1000)
        clean = re.sub(r'```json|```', '', raw).strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse JSON: {raw[:300]}")
        idea = json.loads(match.group())
        return {"success": True, "idea": idea}

    except Exception as e:
        print(f"[AI Generate ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")