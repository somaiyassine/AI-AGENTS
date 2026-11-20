# AGENT 3 : MULTI-AGENT ORCHESTRATION
# lahne na3mlou barcha agents ykhdmou m3a ba3dhhom:
# - sequential: researcher >> writer >> editor (kol wa7ed y3adi l khedma lel eli ba3dou)
# - parallel: 3 analysts ykhdmou fi nafs l wa9t w ba3d wa7ed yjama3 les resultats
# - nested: l team parallel + l pipeline sequential m3a ba3dhhom
# - worker: nkhaliw l pipeline ykhdem ka worker yestana fel khedma eli tjih mel server
# w l rapport final yetsajel fi fichier markdown fel dossier reports/
import logging
import os
import re
import warnings
from pathlib import Path

from dotenv import load_dotenv

# nsaktou les warnings mta3 Pydantic eli ytal3ou men Firecrawl
# lezem na3mlouha 9bal ma yetaamel import lel SDK
warnings.filterwarnings("ignore", message='Field name "json" in .* shadows an attribute')

from agentspan.agents import Agent, AgentRuntime, run, tool


load_dotenv(override=True)
logging.basicConfig(level=logging.WARNING, force=True)
logging.disable(logging.INFO)

# les modes eli ynajem l user ya5tar menhom
MODES = {"sequential", "parallel", "nested", "worker"}
# l dossier eli nsajlou fih les rapports
REPORTS_DIR = Path("reports")
# n9assou l contenu mta3 l page l 4000 caractere bech ma n3abiwch l context mta3 l LLM
MAX_PAGE_CHARS = 4000


# tool ta3mel recherche fel web b Firecrawl
# credentials=["FIRECRAWL_API_KEY"]: l tool test7a9 l key hedha bech tekhdem
@tool(credentials=["FIRECRAWL_API_KEY"])
def search_web(query: str, limit: int = 5) -> list[dict]:
    """Search the web with Firecrawl. Returns a list of {title, url, description}."""
    # l import dakhel l function bech Firecrawl ma yet7mel ken wa9t nest7a9ouh
    from firecrawl import Firecrawl

    fc = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    response = fc.search(query, limit=limit)
    # nraj3ou ken l titre, l url w l description mta3 kol resultat
    return [
        {"title": r.title or "", "url": r.url or "", "description": r.description or ""}
        for r in (response.web or [])
    ]


# tool tjib l contenu mta3 page web w traj3ou markdown
@tool(credentials=["FIRECRAWL_API_KEY"])
def fetch_page(url: str) -> str:
    """Fetch a web page as markdown via Firecrawl. Truncated for the LLM context."""
    from firecrawl import Firecrawl

    fc = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    document = fc.scrape(url, formats=["markdown"])
    markdown = document.markdown or ""
    # n9assou l contenu ken twil, w ken fergh nraj3ou message
    return markdown[:MAX_PAGE_CHARS] if markdown else f"No content found at {url}."


# ---------- les agents mta3 l pipeline sequential ----------

# l researcher: ylawej fel web, y9ra les pages, w yekteb notes m3a les sources
researcher = Agent(
    name="researcher",
    model="google_gemini/gemini-2.5-flash",
    instructions=(
        "Research the topic thoroughly. Call search_web first, then fetch_page on "
        "the most relevant results. Write factual notes citing each claim. "
        "Always end your output with a '## Sources' section listing every URL you "
        "actually fetched, one per line, as markdown links: '- [title](url)'."
    ),
    tools=[search_web, fetch_page],
)

# l writer: yekhou les notes w y7awelhom l article mnadhem (ma 3andouch tools)
writer = Agent(
    name="writer",
    model="google_gemini/gemini-2.5-flash",
    instructions=(
        "Turn research notes into a clear, well-structured article. "
        "Preserve the '## Sources' section verbatim at the end."
    ),
)

# l editor: ysalla7 w y7assen l article, w ma ymessech les Sources
editor = Agent(
    name="editor",
    model="google_gemini/gemini-2.5-flash",
    instructions=(
        "Polish the article for publication. Improve clarity and tighten writing. "
        "Do not modify or remove the '## Sources' section."
    ),
)

# ---------- les analysts mta3 l team parallel ----------

# analyst y7allel l marche w l adoption
market_analyst = Agent(
    name="market",
    model="google_gemini/gemini-2.5-flash",
    instructions="Analyze market opportunity and adoption trends.",
)

# analyst y7allel les risques (technique, securite, operationnel)
risk_analyst = Agent(
    name="risk",
    model="google_gemini/gemini-2.5-flash",
    instructions="Analyze technical, security, and operational risks.",
)

# analyst y7allel l business model w l jeneb l financier
financial_analyst = Agent(
    name="financial",
    model="google_gemini/gemini-2.5-flash",
    instructions="Analyze business model and financial impact.",
)

# l team: agent "chef" 3andou 3 sub-agents
# strategy="parallel": les 3 analysts ykhdmou fi nafs l wa9t, w ba3d l chef yjama3 les resultats fi brief wa7ed
analysis_team = Agent(
    name="analysis_team",
    model="google_gemini/gemini-2.5-flash",
    instructions="Synthesize the analyst outputs into one concise brief.",
    agents=[market_analyst, risk_analyst, financial_analyst],
    strategy="parallel",
)

# l operateur ">>" yorbot les agents fi chaine: l output mta3 wa7ed ywali input lel eli ba3dou
publish_pipeline = researcher >> writer >> editor
# nested: l team parallel lowel, w ba3d l pipeline sequential
nested_pipeline = analysis_team >> researcher >> writer >> editor


# t7awel l topic l esm fichier ndhif (7rouf sghar, ar9am w "-"), maximum 60 caractere
def slugify(text: str) -> str:
    """Convert a topic into a safe filename slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "report"


# t7awel l output mta3 l agent (dict wala string) l markdown ndhif
def render_output(output) -> str:
    """Render the agent's output dict (or string) as clean markdown."""
    if isinstance(output, str):
        return output
    if not isinstance(output, dict):
        return str(output)

    sections = []
    # l resultat principal (mathalan l brief wala l article final)
    main = output.get("result")
    if main:
        sections.append(str(main).strip())

    # les resultats mta3 les sub-agents (fel parallel: market, risk, financial)
    # kol wa7da n7ottouha fi section wa7adha b titre
    sub_results = output.get("subResults") or {}
    for name, body in sub_results.items():
        if body:
            sections.append(f"## {name.title()}\n\n{str(body).strip()}")

    # nfar9ou bin les sections b "---"
    return "\n\n---\n\n".join(sections) if sections else str(output)


# tsajel l rapport fi reports/<mode>-<slug>.md w traja3 l path
def save_report(mode: str, topic: str, output) -> Path:
    """Write the final report to reports/<mode>-<slug>.md and return the path."""
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{mode}-{slugify(topic)}.md"
    body = render_output(output)
    path.write_text(f"# {topic}\n\n_Mode: {mode}_\n\n{body}\n")
    return path


# tekhtar l pipeline 7asb l mode, tkhadmou 3al topic, w tsajel l rapport
def run_pipeline(mode: str, topic: str) -> None:
    pipelines = {
        "sequential": publish_pipeline,
        "parallel": analysis_team,
        "nested": nested_pipeline,
    }
    with AgentRuntime() as runtime:
        result = run(pipelines[mode], topic, runtime=runtime)
        # l execution ID tnajem tlawej bih 3al run fel UI mta3 agentspan
        print("Execution ID:", result.execution_id)
        print("Status:", result.status)
        path = save_report(mode, topic, result.output)
        print(f"Report saved to {path}")


# mode worker: ma nab3thou 7atta topic, ama nkhaliw l process yestana w ykhdem
# les tasks mta3 l nested_pipeline eli yab3athhom l server (blocking=True ya3ni yo93ed cha3el)
def serve_worker() -> None:
    with AgentRuntime() as runtime:
        runtime.serve(nested_pipeline, blocking=True)


# nas2lou l user 3al mode lin ya5tar wa7ed s7i7 (par defaut: nested)
def prompt_mode() -> str:
    while True:
        choice = input(f"Mode {sorted(MODES)}: ").strip().lower() or "nested"
        if choice in MODES:
            return choice
        print(f"Invalid mode. Pick one of {sorted(MODES)}.")


if __name__ == "__main__":
    mode = prompt_mode()
    if mode == "worker":
        serve_worker()
    else:
        # ken ma kteb 7atta topic, nekhdhou topic par defaut
        topic = input("Topic: ").strip() or "AI agents in production in 2026"
        run_pipeline(mode, topic)
