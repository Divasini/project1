"""
StartupSphere — CrewAI Multi-Agent Idea Analyzer
=================================================
5 specialized AI agents analyze a startup idea from
different angles and produce a comprehensive report.

Agents:
  1. Market Research Agent    → TAM/SAM/SOM, trends
  2. Idea Validator Agent     → Problem-solution fit
  3. Competitor Scout Agent   → Competition landscape
  4. Business Analyst Agent   → Revenue, GTM, risks
  5. Report Writer Agent      → Final investor report
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai import LLM

load_dotenv()

# ── Claude LLM via CrewAI ──
claude_llm = LLM(
    model="claude-sonnet-4-6",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)


def run_crew_analysis(
    title: str,
    category: str,
    problem: str,
    solution: str,
    target: str = "",
    revenue_model: str = "",
    tech_stack: str = ""
) -> dict:
    """
    Run the full CrewAI multi-agent analysis on a startup idea.
    Returns a structured dict with all agent findings.
    """

    idea_context = f"""
Startup Idea Details:
- Title: {title}
- Category: {category}
- Problem: {problem}
- Solution: {solution}
- Target Audience: {target or 'Not specified'}
- Revenue Model: {revenue_model or 'Not specified'}
- Tech Stack: {tech_stack or 'Not specified'}
"""

    # ─────────────────────────────────────────────
    # AGENTS
    # ─────────────────────────────────────────────

    market_researcher = Agent(
        role="Market Research Specialist",
        goal="Analyze the market opportunity, size, and growth potential for startup ideas",
        backstory="""You are a seasoned market research analyst with 15 years of experience
        evaluating startup opportunities. You specialize in calculating TAM/SAM/SOM,
        identifying market trends, and assessing demand signals. You provide data-driven
        insights that help founders understand their market opportunity.""",
        llm=claude_llm,
        verbose=False,
        allow_delegation=False,
    )

    idea_validator = Agent(
        role="Startup Idea Validator",
        goal="Validate the problem-solution fit and unique value proposition of startup ideas",
        backstory="""You are a startup mentor who has evaluated over 500 startup ideas.
        You have a sharp eye for identifying whether a startup truly solves a real pain point,
        whether the solution is unique, and whether the target audience is well-defined.
        You score ideas on problem-solution fit and provide actionable validation feedback.""",
        llm=claude_llm,
        verbose=False,
        allow_delegation=False,
    )

    competitor_scout = Agent(
        role="Competitive Intelligence Analyst",
        goal="Map the competitive landscape and identify differentiation opportunities",
        backstory="""You are a competitive intelligence expert who tracks startups and
        established companies across all industries. You identify direct and indirect
        competitors, analyze their strengths and weaknesses, and help founders find
        their unique competitive advantage.""",
        llm=claude_llm,
        verbose=False,
        allow_delegation=False,
    )

    business_analyst = Agent(
        role="Business Strategy Analyst",
        goal="Evaluate revenue models, go-to-market strategies, and business risks",
        backstory="""You are a business strategist with an MBA and 10 years of consulting
        experience working with early-stage startups. You analyze revenue model viability,
        suggest go-to-market strategies, identify key risks, and provide actionable
        business recommendations.""",
        llm=claude_llm,
        verbose=False,
        allow_delegation=False,
    )

    report_writer = Agent(
        role="Startup Report Writer",
        goal="Synthesize all analysis into a clear, compelling investor-ready startup report",
        backstory="""You are an expert startup writer who has written hundreds of pitch
        reports and investment memos. You take complex analysis from multiple experts
        and synthesize it into clear, structured reports that founders can use for
        pitching to investors and making strategic decisions.""",
        llm=claude_llm,
        verbose=False,
        allow_delegation=False,
    )

    # ─────────────────────────────────────────────
    # TASKS
    # ─────────────────────────────────────────────

    market_research_task = Task(
        description=f"""Analyze the market opportunity for this startup idea:

{idea_context}

Provide:
1. Estimated TAM (Total Addressable Market) with reasoning
2. SAM (Serviceable Addressable Market)
3. SOM (Serviceable Obtainable Market for year 1-3)
4. Key market trends supporting or challenging this idea
5. Market growth rate and trajectory
6. A market opportunity score (1-10)

Be specific with numbers and reasoning. Format as clear sections.""",
        agent=market_researcher,
        expected_output="Market analysis with TAM/SAM/SOM figures, trends, and opportunity score"
    )

    validation_task = Task(
        description=f"""Validate the problem-solution fit for this startup idea:

{idea_context}

Provide:
1. Problem severity score (1-10): How painful is this problem?
2. Solution effectiveness score (1-10): How well does the solution address the problem?
3. Target audience clarity score (1-10): How well-defined is the target user?
4. Unique value proposition analysis: What makes this truly different?
5. 3 strengths of this idea
6. 3 key concerns or weaknesses
7. Overall validation score (1-10)

Be honest and constructive.""",
        agent=idea_validator,
        expected_output="Validation scores, strengths, weaknesses, and UVP analysis"
    )

    competitor_task = Task(
        description=f"""Map the competitive landscape for this startup idea:

{idea_context}

Provide:
1. 3-5 direct competitors (name, what they do, estimated size)
2. 2-3 indirect competitors or substitutes
3. Competitive advantages this idea has
4. Competitive gaps or vulnerabilities
5. Differentiation strategy recommendation
6. Competitive threat level (Low/Medium/High) with reasoning

Be specific about real companies where possible.""",
        agent=competitor_scout,
        expected_output="Competitor analysis with direct/indirect competitors and differentiation strategy"
    )

    business_task = Task(
        description=f"""Analyze the business viability of this startup idea:

{idea_context}

Provide:
1. Revenue model assessment: Is the proposed model viable? Alternatives?
2. Recommended go-to-market strategy (3 specific steps)
3. Key metrics to track (3-5 KPIs)
4. Top 3 risks with mitigation strategies
5. Estimated time to first revenue
6. Funding requirements estimate (bootstrappable vs needs investment?)
7. Business viability score (1-10)""",
        agent=business_analyst,
        expected_output="Business analysis with GTM strategy, risks, KPIs, and viability score"
    )

    report_task = Task(
        description=f"""You have received analysis from 4 expert agents about this startup idea:

{idea_context}

Using all the analysis provided (market research, validation, competitor analysis, business analysis),
write a comprehensive startup analysis report.

The report must include:
1. Executive Summary (2-3 sentences)
2. Overall Startup Score (1-100) — weighted average of all expert scores
3. Market Opportunity (from market researcher)
4. Idea Validation (from validator)
5. Competitive Landscape (from competitor scout)
6. Business Strategy (from business analyst)
7. Top 5 Actionable Recommendations
8. Investment Readiness Level: Pre-seed / Seed / Not ready (with reasoning)

Format as JSON with this EXACT structure (return ONLY valid JSON, no markdown):
{{
  "overall_score": <number 1-100>,
  "investment_readiness": "<Pre-seed|Seed|Not ready>",
  "executive_summary": "<2-3 sentences>",
  "market": {{
    "tam": "<estimated TAM>",
    "sam": "<estimated SAM>",
    "som": "<estimated SOM>",
    "trends": ["<trend 1>", "<trend 2>", "<trend 3>"],
    "opportunity_score": <1-10>
  }},
  "validation": {{
    "problem_score": <1-10>,
    "solution_score": <1-10>,
    "audience_score": <1-10>,
    "overall_score": <1-10>,
    "strengths": ["<s1>", "<s2>", "<s3>"],
    "weaknesses": ["<w1>", "<w2>", "<w3>"]
  }},
  "competition": {{
    "direct_competitors": ["<comp 1>", "<comp 2>", "<comp 3>"],
    "competitive_advantage": "<key differentiator>",
    "threat_level": "<Low|Medium|High>"
  }},
  "business": {{
    "gtm_steps": ["<step 1>", "<step 2>", "<step 3>"],
    "top_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
    "kpis": ["<kpi 1>", "<kpi 2>", "<kpi 3>"],
    "viability_score": <1-10>,
    "funding_needed": "<Bootstrappable|Pre-seed|Seed>"
  }},
  "recommendations": ["<rec 1>", "<rec 2>", "<rec 3>", "<rec 4>", "<rec 5>"]
}}""",
        agent=report_writer,
        expected_output="Complete JSON startup analysis report",
        context=[market_research_task, validation_task, competitor_task, business_task]
    )

    # ─────────────────────────────────────────────
    # CREW
    # ─────────────────────────────────────────────

    crew = Crew(
        agents=[
            market_researcher,
            idea_validator,
            competitor_scout,
            business_analyst,
            report_writer,
        ],
        tasks=[
            market_research_task,
            validation_task,
            competitor_task,
            business_task,
            report_task,
        ],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    # Parse the JSON from the report writer's output
    import json, re
    raw = str(result)
    # Strip markdown if present
    clean = re.sub(r'```json|```', '', raw).strip()
    # Find JSON object
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        return json.loads(match.group())
    else:
        raise ValueError(f"Could not parse JSON from CrewAI output: {raw[:500]}")