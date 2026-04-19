"""
AI-Powered Development — interactive Gradio presentation.

Run:
    python app.py
Then open http://localhost:7860
"""

import gradio as gr

# ---------------------------------------------------------------------------
# Slide data
# ---------------------------------------------------------------------------
SLIDES = [
    {
        "tag":   "Welcome",
        "tag_color": "#ffd93d",
        "title": "Smarter Development with AI",
        "sub":   "Tools · Agents · MCP · Why GitHub Unlocks Everything",
        "image": "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1200&q=80",
        "image_alt": "Abstract AI neural network visualization",
        "image_pos":  "cover",
        "accent": "#ffd93d",
        "bg": "linear-gradient(135deg,#06001a 0%,#160033 50%,#001633 100%)",
        "items": [],
        "is_cover": True,
    },
    {
        "tag":   "01 · Foundation",
        "tag_color": "#ff6b6b",
        "title": "AI Amplifies Developers. It Does Not Replace Them.",
        "image": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=900&q=80",
        "image_alt": "Robot and human working side by side",
        "accent": "#ff6b6b",
        "bg": "linear-gradient(135deg,#1a0000 0%,#0a0014 100%)",
        "items": [
            ("Speed at scale", "Boilerplate, refactoring, docs, tests — all on demand"),
            ("You still own", "Intent, architecture, business context, every final decision"),
            ("Proven results", "Teams adopting AI tools ship 30–50 % faster with fewer defects"),
            ("Right analogy", "The compiler didn't replace devs — it freed them to think higher"),
            ("Real win", "Security review + PR that took 2 days now takes 10 minutes"),
        ],
    },
    {
        "tag":   "02 · Context",
        "tag_color": "#ffd93d",
        "title": "RAG — How AI Learns Your Codebase",
        "image": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=900&q=80",
        "image_alt": "Neural network connections and data flow",
        "accent": "#ffd93d",
        "bg": "linear-gradient(135deg,#001a33 0%,#002244 100%)",
        "cards": [
            ("✂️", "Chunking",             "Split code & docs into meaningful segments by function or token limit"),
            ("🔢", "Vector Search",        "Embed chunks as numbers — find semantically similar passages instantly"),
            ("🔀", "Hybrid Search",        "Combine vector similarity + keyword matching for higher precision"),
            ("🏆", "Re-ranking",           "A second model re-orders results by true relevance to the question"),
            ("🔄", "Query Reformulation",  "Rewrite the question before retrieval to improve match quality"),
            ("💡", "In Copilot Today",     "Open files + @workspace index are the retrieval layer — RAG is already running"),
        ],
    },
    {
        "tag":   "03 · Tools",
        "tag_color": "#4d96ff",
        "title": "GitHub Copilot vs Cursor vs OpenAI",
        "image": "https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?w=900&q=80",
        "image_alt": "Developer coding on multiple screens",
        "accent": "#4d96ff",
        "bg": "linear-gradient(135deg,#050510 0%,#0e0e2a 100%)",
        "table": {
            "headers": ["Feature", "GitHub Copilot", "Cursor", "OpenAI (ChatGPT)"],
            "rows": [
                ["IDE Integration",      "⭐⭐⭐⭐⭐ VS Code, JetBrains, Visual Studio", "⭐⭐⭐⭐ VS Code fork",  "❌ Web / API only"],
                ["Codebase Awareness",   "@workspace full index",                        "Full codebase default",  "Manual file upload"],
                ["Agent Automation",     ".agent.md + MCP tools",                        "Composer mode",          "Assistants API (no IDE)"],
                ["Enterprise SSO/Audit", "✅ Entra / SAML / audit logs",                 "Limited",                "❌ None"],
                ["Secret Scanning",      "✅ GitHub Advanced Security",                  "❌",                     "❌"],
                ["Best Fit For Us",      "✅ Our stack — ADO + GitHub",                  "~ Partial",              "❌ No integration"],
            ],
        },
    },
    {
        "tag":   "04 · Concepts",
        "tag_color": "#4d96ff",
        "title": "Copilot Agent ≈ OpenAI Agent — Same Loop, Different Surface",
        "image": "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=900&q=80",
        "image_alt": "AI robot thinking and processing",
        "accent": "#4d96ff",
        "bg": "linear-gradient(135deg,#000d22 0%,#001433 100%)",
        "split": {
            "left":  {
                "heading": "OpenAI Agent",
                "color": "#4d96ff",
                "items": [
                    "System prompt defines behaviour",
                    "Tool definitions via JSON schema",
                    "Function calls during reasoning loop",
                    "Threads store persistent memory",
                    "Runs in the cloud — no IDE context",
                ],
            },
            "right": {
                "heading": "Copilot Agent (.agent.md)",
                "color": "#6bcb77",
                "items": [
                    "Instructions frontmatter — same concept",
                    "MCP tool IDs instead of JSON schemas",
                    "MCP calls during the agentic loop",
                    "Conversation window as working memory",
                    "Runs inside your IDE — sees files, git, terminal",
                ],
            },
            "footer": "Both follow: Plan → Select Tool → Execute → Observe → Repeat",
        },
    },
    {
        "tag":   "05 · Building Blocks",
        "tag_color": "#c084fc",
        "title": "Skills · Prompts · Agents · Instructions",
        "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=900&q=80",
        "image_alt": "Architecture building blocks arranged neatly",
        "accent": "#c084fc",
        "bg": "linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%)",
        "items": [
            ("Instructions  copilot-instructions.md",
             "Always-on rules applied to every chat. Think: system prompt for the whole workspace."),
            ("Prompts  .prompt.md",
             "Reusable slash commands like /securityScan. Task templates invoked on demand."),
            ("Skills  SKILL.md",
             "Deep domain expertise loaded when relevant — e.g. SQL parameterization, KQL patterns."),
            ("Agents  .agent.md",
             "Autonomous multi-step workflows with scoped tool access and a defined goal."),
            ("Analogy",
             "Instructions = office policy · Prompts = SOPs · Skills = specialist manuals · Agents = automated team member"),
        ],
    },
    {
        "tag":   "06 · Platform",
        "tag_color": "#6bcb77",
        "title": "MCP — Model Context Protocol",
        "image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=900&q=80",
        "image_alt": "Server rack with glowing network cables",
        "accent": "#6bcb77",
        "bg": "linear-gradient(135deg,#060e06 0%,#001a08 100%)",
        "sub": "Open standard (Anthropic, 2024). Think USB-C: one universal connector for any tool and any AI model.",
        "items": [
            ("How it works",  "AI model speaks MCP → server exposes tools → AI calls them during reasoning"),
            ("No lock-in",    "Any IDE or agent supporting MCP can invoke our tools — zero vendor lock-in"),
            ("Our server",    "integration_platform_mcp_server.py"),
            ("Tools today",   "run_pipeline · scan_security · analyze_repo · generate_tests"),
            ("Future tools",  "ServiceNow, SonarQube, Jira — plug in with zero AI code changes"),
        ],
    },
    {
        "tag":   "07 · Our Project",
        "tag_color": "#ffd93d",
        "title": "Security Pipeline — From Chat to Pull Request",
        "image": "https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?w=900&q=80",
        "image_alt": "CI/CD pipeline automation dashboard",
        "accent": "#ffd93d",
        "bg": "linear-gradient(135deg,#0d0d0d 0%,#150527 100%)",
        "pipeline": [
            ("💬", "1", "Invoke",        "Repo URL + branch + PBI number. Nothing else."),
            ("🔍", "2", "Clone & Scan",  "Clone repo, run Bandit + Semgrep across all files."),
            ("🔧", "3", "Auto-Fix",      "Parameterize SQL, remove secrets, patch path traversal."),
            ("📊", "4", "HTML Report",   "Severity-graded report with diff view."),
            ("🚀", "5", "Open PR",       "Commit fixes, open Pull Request automatically."),
        ],
        "footer": "169 automated tests · Zero manual steps · Auth via GCM — no PAT required",
    },
    {
        "tag":   "08 · Business Case",
        "tag_color": "#ff6b6b",
        "title": "ADO Only vs GitHub + Copilot Enterprise",
        "image": "https://images.unsplash.com/photo-1556075798-4825dfaaf498?w=900&q=80",
        "image_alt": "Two paths diverging — old vs modern approach",
        "accent": "#ff6b6b",
        "bg": "linear-gradient(135deg,#0d0200 0%,#001a06 100%)",
        "versus": {
            "left": {
                "heading": "⚠️ ADO Only (Today)",
                "color": "#ff6b6b",
                "bg": "rgba(255,107,107,.06)",
                "border": "rgba(255,107,107,.25)",
                "items": [
                    "Code completion only — no workspace agents",
                    "No MCP: the pipeline CANNOT run",
                    "Every security audit = hours of manual work",
                    "No GitHub Advanced Security integration",
                    "No secret scanning on commits",
                    "No org-wide policies or audit logs",
                ],
            },
            "right": {
                "heading": "✅ GitHub + Copilot Enterprise",
                "color": "#6bcb77",
                "bg": "rgba(107,203,119,.06)",
                "border": "rgba(107,203,119,.25)",
                "items": [
                    "Full agent automation — what we built today",
                    "MCP extends to any internal tool",
                    "Security PR auto-created: 2 days → 10 minutes",
                    "GitHub Advanced Security — built in",
                    "Secret scanning blocks credentials before merge",
                    "One prevented incident > years of licence cost",
                ],
            },
        },
    },
    {
        "tag":   "09 · The Ask ✨",
        "tag_color": "#ffd93d",
        "title": "What We Need From You",
        "image": "https://images.unsplash.com/photo-1552664730-d307ca884978?w=900&q=80",
        "image_alt": "Business meeting with team presenting to managers",
        "accent": "#ffd93d",
        "bg": "linear-gradient(135deg,#0f0c29 0%,#1e1b4b 100%)",
        "ask": [
            ("1", "GitHub repository access for the team — mirror or migration from ADO"),
            ("2", "GitHub Copilot Enterprise licence — org policies, audit logs, Advanced Security"),
            ("3", "30-day pilot — measure: PRs auto-created, vulnerabilities caught, hours saved"),
            ("4", "Success metric: pipeline runs on 5 real production repos before pilot ends"),
        ],
        "roi": "💰  One prevented data breach = years of Copilot Enterprise subscription cost",
    },
]

TOTAL = len(SLIDES)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
/* ---- global ---- */
body, .gradio-container {
    background: #0d1117 !important;
    color: #e6edf3;
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
}
.gradio-container { max-width: 100% !important; padding: 0 !important; }
footer { display: none !important; }

/* ---- slide card ---- */
.slide-card {
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 8px 60px rgba(0,0,0,.7);
    min-height: 560px;
    position: relative;
}

/* ---- hero image banner ---- */
.hero-img {
    width: 100%;
    height: 240px;
    object-fit: cover;
    object-position: center;
    display: block;
    filter: brightness(.75) saturate(1.15);
}

/* ---- progress bar ---- */
.progress-wrap {
    height: 5px;
    background: rgba(255,255,255,.08);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 18px;
}
.progress-fill {
    height: 100%;
    background: linear-gradient(90deg,#ff6b6b,#ffd93d,#6bcb77,#4d96ff);
    border-radius: 3px;
    transition: width .3s ease;
}

/* ---- nav buttons ---- */
.nav-row button {
    background: rgba(255,255,255,.07) !important;
    border: 1px solid rgba(255,255,255,.15) !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
    font-size: 0.95rem !important;
    padding: 10px 28px !important;
    transition: all .2s !important;
}
.nav-row button:hover {
    border-color: #ffd93d !important;
    background: rgba(255,217,61,.12) !important;
    color: #ffd93d !important;
}

/* ---- counter ---- */
#counter-display { font-size: 0.8rem; color: rgba(255,255,255,.4); text-align: center; padding-top: 6px; }

/* ---- table ---- */
.cmp-table { width:100%; border-collapse:collapse; font-size:.82rem; margin-top:.5rem; }
.cmp-table thead tr { background:rgba(77,150,255,.18); }
.cmp-table th { padding:.6rem 1rem; text-align:left; color:#ffd93d; font-weight:700; white-space:nowrap; }
.cmp-table td { padding:.55rem 1rem; border-top:1px solid rgba(255,255,255,.07); color:rgba(255,255,255,.8); vertical-align:top; }
.cmp-table td:first-child { color:#4d96ff; font-weight:600; white-space:nowrap; }
.cmp-table tr:hover td { background:rgba(255,255,255,.04); }
.win { color:#6bcb77 !important; font-weight:700 !important; }

/* ---- pipeline steps ---- */
.pipe { display:flex; gap:0; margin-top:1rem; }
.pipe-step { flex:1; background:rgba(255,255,255,.045); border:1px solid rgba(255,255,255,.1); padding:1rem .8rem; text-align:center; position:relative; }
.pipe-step:first-child { border-radius:12px 0 0 12px; }
.pipe-step:last-child  { border-radius:0 12px 12px 0; }
.pipe-step:not(:last-child)::after { content:"›"; position:absolute; right:-13px; top:50%; transform:translateY(-50%); font-size:1.6rem; color:#ffd93d; z-index:2; font-weight:700; }
.pipe-num  { width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#ff6b6b,#ffd93d);color:#000;font-weight:800;font-size:.75rem;display:inline-grid;place-items:center;margin-bottom:.4rem; }
.pipe-lbl  { font-size:.74rem; font-weight:700; color:#ffd93d; margin-bottom:.3rem; }
.pipe-desc { font-size:.63rem; color:rgba(255,255,255,.5); line-height:1.4; }

/* ---- cards grid ---- */
.cards-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem; margin-top:.8rem; }
.card-item { background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.11); border-radius:12px; padding:.9rem 1rem; }
.card-ico  { font-size:1.4rem; margin-bottom:.4rem; }
.card-ttl  { font-size:.72rem; font-weight:700; color:#ffd93d; text-transform:uppercase; letter-spacing:.05em; margin-bottom:.3rem; }
.card-bdy  { font-size:.69rem; color:rgba(255,255,255,.6); line-height:1.45; }

/* ---- bullet list ---- */
.blist { list-style:none; display:flex; flex-direction:column; gap:.45rem; margin-top:.6rem; }
.blist li { font-size:.84rem; padding:.55rem 1rem; border-radius:8px; border-left:3px solid; background:rgba(255,255,255,.04); color:rgba(255,255,255,.82); line-height:1.5; }
.blist li b { color:#fff; }

/* ---- split columns ---- */
.split-cols { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:.8rem; }
.split-col  { border-radius:12px; padding:1.1rem 1.2rem; border:1px solid rgba(255,255,255,.1); }

/* ---- versus ---- */
.vs-cols { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:.8rem; }
.vs-col  { border-radius:12px; padding:1.1rem 1.2rem; }
.vs-head { font-size:.95rem; font-weight:800; margin-bottom:.8rem; }
.vs-item { font-size:.78rem; padding:.42rem .8rem; border-radius:6px; margin-bottom:.35rem; background:rgba(255,255,255,.03); line-height:1.45; }

/* ---- ask cards ---- */
.ask-list { display:flex; flex-direction:column; gap:.8rem; margin-top:.9rem; }
.ask-item { display:flex; align-items:flex-start; gap:1rem; padding:.9rem 1.1rem; border-radius:12px; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.11); }
.ask-num  { flex-shrink:0; width:2rem; height:2rem; border-radius:50%; background:linear-gradient(135deg,#ffd93d,#ff6b6b); color:#000; font-weight:900; font-size:.88rem; display:grid; place-items:center; }
.ask-txt  { font-size:.88rem; color:rgba(255,255,255,.85); line-height:1.55; padding-top:.12rem; }
.roi-box  { margin-top:1rem; padding:.85rem 1.2rem; border-radius:10px; background:rgba(107,203,119,.1); border:1px solid rgba(107,203,119,.28); color:#6bcb77; font-size:.88rem; font-weight:600; text-align:center; }

/* ---- inner content padding ---- */
.slide-body { padding: 1.6rem 2rem 1.4rem; }

/* ---- tag pill ---- */
.tag-pill { display:inline-block; font-size:.64rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; padding:.22rem .85rem; border-radius:20px; margin-bottom:.7rem; }

/* ---- slide title ---- */
.slide-title { font-size:clamp(1.2rem,2.5vw,1.85rem); font-weight:800; color:#fff; line-height:1.18; margin-bottom:.6rem; }
.slide-sub   { font-size:.84rem; color:rgba(255,255,255,.55); line-height:1.6; margin-bottom:.7rem; }

/* ---- cover special ---- */
.cover-inner { padding:2.5rem 2.5rem 2rem; text-align:center; }
.cover-inner h1 {
    font-size:clamp(1.8rem,4vw,3rem); font-weight:900; line-height:1.08; margin-bottom:1rem;
    background:linear-gradient(135deg,#ff6b6b 0%,#ffd93d 35%,#6bcb77 65%,#4d96ff 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.cover-inner .csub { font-size:1rem; color:rgba(255,255,255,.6); margin-bottom:0; }
"""


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _tag_html(text: str, color: str) -> str:
    return (
        f'<span class="tag-pill" style="'
        f'color:{color};background:rgba(255,255,255,.06);'
        f'border:1px solid {color}44">{text}</span>'
    )


def _hero(url: str, alt: str) -> str:
    return f'<img class="hero-img" src="{url}" alt="{alt}" loading="lazy">'


def _bullet_list(items: list, accent: str) -> str:
    lis = "".join(
        f'<li style="border-color:{accent}"><b>{k}:</b> {v}</li>'
        for k, v in items
    )
    return f'<ul class="blist">{lis}</ul>'


def _cards(cards: list) -> str:
    items = "".join(
        f'<div class="card-item">'
        f'<div class="card-ico">{ico}</div>'
        f'<div class="card-ttl">{ttl}</div>'
        f'<div class="card-bdy">{bdy}</div>'
        f'</div>'
        for ico, ttl, bdy in cards
    )
    return f'<div class="cards-grid">{items}</div>'


def _table(headers: list, rows: list) -> str:
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        win_cls = ' class="win"' if row[0] == "Best Fit For Us" else ""
        tds = "".join(f'<td{win_cls}>{c}</td>' for c in row)
        trs += f"<tr>{tds}</tr>"
    return (
        f'<div style="overflow-x:auto;border-radius:10px;border:1px solid rgba(255,255,255,.09)">'
        f'<table class="cmp-table">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{trs}</tbody>'
        f'</table></div>'
    )


def _split(data: dict) -> str:
    def col(side: dict) -> str:
        lis = "".join(
            f'<div class="vs-item" style="border-left:3px solid {side["color"]}40">{i}</div>'
            for i in side["items"]
        )
        return (
            f'<div class="split-col" style="background:{side.get("bg","rgba(255,255,255,.04)")};'
            f'border-color:{side["color"]}33">'
            f'<div style="font-size:.92rem;font-weight:800;color:{side["color"]};margin-bottom:.8rem">{side["heading"]}</div>'
            f'{lis}</div>'
        )
    footer = (
        f'<p style="text-align:center;font-size:.72rem;color:rgba(255,255,255,.3);margin-top:.9rem">'
        f'{data["footer"]}</p>'
    ) if data.get("footer") else ""
    return f'<div class="split-cols">{col(data["left"])}{col(data["right"])}</div>{footer}'


def _versus(data: dict) -> str:
    def side(s: dict) -> str:
        lis = "".join(
            f'<div class="vs-item" style="border-left:3px solid {s["color"]}55">{i}</div>'
            for i in s["items"]
        )
        return (
            f'<div class="vs-col" style="background:{s["bg"]};border:1px solid {s["border"]}">'
            f'<div class="vs-head" style="color:{s["color"]}">{s["heading"]}</div>'
            f'{lis}</div>'
        )
    return f'<div class="vs-cols">{side(data["left"])}{side(data["right"])}</div>'


def _pipeline(steps: list, footer: str) -> str:
    items = "".join(
        f'<div class="pipe-step">'
        f'<div class="pipe-num">{num}</div>'
        f'<div style="font-size:1.3rem;margin-bottom:.35rem">{ico}</div>'
        f'<div class="pipe-lbl">{lbl}</div>'
        f'<div class="pipe-desc">{desc}</div>'
        f'</div>'
        for ico, num, lbl, desc in steps
    )
    foot = (
        f'<p style="text-align:center;font-size:.7rem;color:rgba(255,255,255,.3);margin-top:.9rem">'
        f'{footer}</p>'
    ) if footer else ""
    return f'<div class="pipe">{items}</div>{foot}'


def _ask(items: list, roi: str) -> str:
    cards = "".join(
        f'<div class="ask-item">'
        f'<div class="ask-num">{n}</div>'
        f'<div class="ask-txt">{t}</div>'
        f'</div>'
        for n, t in items
    )
    roi_box = f'<div class="roi-box">{roi}</div>' if roi else ""
    return f'<div class="ask-list">{cards}</div>{roi_box}'


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_slide(idx: int) -> str:
    s = SLIDES[idx]
    accent    = s.get("accent", "#4d96ff")
    bg        = s.get("bg", "#0d1117")
    tag_html  = _tag_html(s["tag"], s["tag_color"])
    hero      = _hero(s["image"], s.get("image_alt", ""))

    # ---- cover ----
    if s.get("is_cover"):
        body = (
            f'<div class="cover-inner">'
            f'{tag_html}'
            f'<h1>{s["title"]}</h1>'
            f'<p class="csub">{s["sub"]}</p>'
            f'</div>'
        )
        return (
            f'<div class="slide-card" style="background:{bg}">'
            f'{hero}'
            f'{body}'
            f'</div>'
        )

    # ---- body content ----
    title = f'<div class="slide-title">{s["title"]}</div>'
    sub   = f'<div class="slide-sub">{s["sub"]}</div>' if s.get("sub") else ""

    if "cards" in s:
        content = _cards(s["cards"])
    elif "table" in s:
        content = _table(s["table"]["headers"], s["table"]["rows"])
    elif "split" in s:
        content = _split(s["split"])
    elif "versus" in s:
        content = _versus(s["versus"])
    elif "pipeline" in s:
        content = _pipeline(s["pipeline"], s.get("footer", ""))
    elif "ask" in s:
        content = _ask(s["ask"], s.get("roi", ""))
    else:
        content = _bullet_list(s.get("items", []), accent)

    body = (
        f'<div class="slide-body">'
        f'{tag_html}'
        f'{title}'
        f'{sub}'
        f'{content}'
        f'</div>'
    )

    return (
        f'<div class="slide-card" style="background:{bg}">'
        f'{hero}'
        f'{body}'
        f'</div>'
    )


def progress_html(idx: int) -> str:
    pct = round((idx + 1) / TOTAL * 100)
    return (
        f'<div class="progress-wrap">'
        f'<div class="progress-fill" style="width:{pct}%"></div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Gradio app
# ---------------------------------------------------------------------------

def go_prev(idx):
    new = max(0, idx - 1)
    return render_slide(new), progress_html(new), f"{new + 1} / {TOTAL}", gr.update(interactive=new > 0), gr.update(interactive=new < TOTAL - 1), new


def go_next(idx):
    new = min(TOTAL - 1, idx + 1)
    return render_slide(new), progress_html(new), f"{new + 1} / {TOTAL}", gr.update(interactive=new > 0), gr.update(interactive=new < TOTAL - 1), new


with gr.Blocks(title="Smarter Development with AI") as demo:

    state = gr.State(0)

    with gr.Column(elem_classes="deck-wrap"):

        # progress bar
        prog = gr.HTML(progress_html(0))

        # slide
        slide = gr.HTML(render_slide(0))

        # nav row
        with gr.Row(elem_classes="nav-row"):
            btn_prev = gr.Button("← Prev", interactive=False, scale=1)
            ctr      = gr.Markdown(f"1 / {TOTAL}", elem_id="counter-display")
            btn_next = gr.Button("Next →", interactive=True,  scale=1)

    outputs = [slide, prog, ctr, btn_prev, btn_next, state]
    btn_prev.click(go_prev, inputs=[state], outputs=outputs)
    btn_next.click(go_next, inputs=[state], outputs=outputs)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True, css=CUSTOM_CSS)
