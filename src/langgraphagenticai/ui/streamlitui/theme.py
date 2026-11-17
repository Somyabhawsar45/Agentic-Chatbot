"""
Netra design system — black + electric blue.

All styling lives here. Streamlit containers created with `key="..."` get a CSS
class `st-key-...`, which is how the cards, nav items and buttons below are
targeted without fragile DOM selectors.
"""

def html_block(markup: str) -> str:
    """
    Flatten an HTML snippet onto one line before giving it to st.markdown.

    Markdown treats a line indented by 4+ spaces after a blank line as a CODE BLOCK,
    which is how stray "</div>" boxes appeared on screen. One line = no surprises.
    """
    return " ".join(line.strip() for line in markup.splitlines() if line.strip())


FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,400,0,0" />
"""

CSS = """
<style>
:root{
    --bg:#0a0a0a;
    --bg-raised:#0f0f10;
    --surface:#121214;
    --surface-2:#16161a;
    --sidebar-bg:#0c0c0d;
    --accent:#4f8ef7;
    --accent-2:#7aa9ff;
    --accent-soft:#0d1d3a;
    --accent-glow:rgba(79,142,247,0.18);
    --border:#1e1e22;
    --border-strong:#2a2a30;
    --text:#e8e8ea;
    --text-2:#b4b4ba;
    --text-3:#8a8a92;
    --text-4:#66666e;
    --danger:#e86a6a;
    --radius:14px;
}

/* ---------- BASE ---------- */
html, body, .stApp, [class*="css"]{ font-family:'Inter', sans-serif !important; }
.stApp{
    background:
        radial-gradient(1100px 480px at 50% -12%, rgba(79,142,247,0.11), transparent 62%),
        var(--bg) !important;
    color: var(--text);
}
header[data-testid="stHeader"]{ background: transparent !important; }
[data-testid="stBottomBlockContainer"], [data-testid="stBottom"]{ background: var(--bg) !important; }
#MainMenu, footer, .stAppDeployButton, [data-testid="stAppDeployButton"]{ display:none !important; }
.block-container{ padding-top: 2.2rem !important; max-width: 980px; }

::-webkit-scrollbar{ width:8px; height:8px; }
::-webkit-scrollbar-thumb{ background:#1f1f24; border-radius:8px; }
::-webkit-scrollbar-thumb:hover{ background:#2c2c33; }

.material-symbols-outlined{
    font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 20;
    vertical-align: middle; font-size:18px;
}

/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"]{
    background: var(--sidebar-bg) !important;
    border-right: 1px solid var(--border) !important;
}
/* fixed width only while open: forcing it on a collapsed sidebar left a 264px gap beside the chat */
section[data-testid="stSidebar"][data-collapsed="false"]{ width: 264px !important; min-width: 264px !important; }
section[data-testid="stSidebar"] > div{ background: transparent !important; padding-top: .6rem; }
section[data-testid="stSidebar"] hr{ border-color: var(--border); margin: 12px 0; }

.sidebar-label{
    font-size:10.5px; font-weight:600; letter-spacing:.09em; text-transform:uppercase;
    color: var(--text-4); margin: 18px 0 6px 6px;
}
.sidebar-logo-wrap{ padding: 4px 6px 6px 6px; }
.sidebar-logo-row{ display:flex; align-items:center; gap:10px; }
.sidebar-logo-img{ width:28px; height:28px; object-fit:contain; border-radius:8px;
    box-shadow: 0 0 18px var(--accent-glow); }
.sidebar-logo-text{ font-size:19px; font-weight:650; color:#fff; letter-spacing:-.01em; }
.sidebar-logo-tagline{ font-size:11px; color: var(--text-4); margin: 1px 0 0 38px; }

/* New chat: accent outline */
div[class*="st-key-newchat_wrap"] button{
    background: linear-gradient(180deg, rgba(79,142,247,.12), rgba(79,142,247,.04)) !important;
    border: 1px solid rgba(79,142,247,.35) !important;
    color: #dfe9ff !important; border-radius: 10px !important; font-weight:600;
    margin-top: 10px;
}
div[class*="st-key-newchat_wrap"] button:hover{
    border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-glow);
}

/* Nav items: one left-aligned icon column. Streamlit centres a button's inner wrappers,
   which made the labels ragged, so the two wrappers are pinned to the left here. */
div[class*="st-key-navitem_"] button{
    background: transparent !important; border: 1px solid transparent !important;
    justify-content: flex-start !important; padding: 7px 10px !important;
    border-radius: 10px !important; min-height: 0 !important;
    transition: background .15s ease, border-color .15s ease;
}
div[class*="st-key-navitem_"] button > div,
div[class*="st-key-histitem_"] button > div, div[class*="st-key-starter_"] button > div{
    justify-content: flex-start !important; width: 100%; text-align: left !important;
}
div[class*="st-key-navitem_"] button > div > span,
div[class*="st-key-histitem_"] button > div > span, div[class*="st-key-starter_"] button > div > span{
    justify-content: flex-start !important; gap: 11px !important; width: 100%; min-width: 0;
}
div[class*="st-key-navitem_"] button p,
div[class*="st-key-navitem_"] button span{
    color: var(--text-3) !important; font-weight:500; font-size:13.5px;
}
div[class*="st-key-navitem_"] button [data-testid="stIconMaterial"]{ color: var(--text-4) !important; font-size: 18px !important; }
div[class*="st-key-navitem_"] button:hover{ background: var(--surface) !important; }
div[class*="st-key-navitem_"] button:hover p,
div[class*="st-key-navitem_"] button:hover span{ color: var(--text) !important; }

/* History: a clean ChatGPT-style list */
div[class*="st-key-histsearch"] input{ font-size:12.5px !important; }
div[class*="st-key-histlist"]{ gap: 0 !important; }
div[class*="st-key-histlist"] > div{ gap: 0 !important; }
.hist-group{ font-size:10.5px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
    color: var(--text-4); margin: 12px 0 4px 10px; }
.hist-empty{ font-size:12px; color: var(--text-4); margin: 2px 0 6px 10px; line-height:1.5; }
div[class*="st-key-histitem_"] button{
    background: transparent !important; border: none !important;
    justify-content: flex-start !important; padding: 6px 10px !important;
    border-radius: 9px !important; min-height: 0 !important; margin: 0 !important;
}
div[class*="st-key-histitem_"] button p{
    color: var(--text-3) !important; font-size:13px !important; font-weight: 450;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left;
}
div[class*="st-key-histitem_"] button:hover{ background: var(--surface) !important; }
div[class*="st-key-histitem_"] button:hover p{ color: var(--text) !important; }
div[class*="st-key-histitem_on_"] button{
    background: linear-gradient(90deg, rgba(79,142,247,.16), rgba(79,142,247,.04)) !important;
    border: 1px solid rgba(79,142,247,.28) !important;
}
div[class*="st-key-histitem_on_"] button p{ color: #fff !important; font-weight: 550 !important; }
/* Streamlit gives text blocks a -16px bottom margin, which slid the first chat over the "Today" label */
div[class*="st-key-histlist"] [data-testid="stMarkdownContainer"]{ margin-bottom: 0 !important; }
.hist-group{ padding-top: 2px; }

/* Account menu (sidebar bottom) */
div[class*="st-key-account"] [data-testid="stPopover"] button,
div[class*="st-key-account"] [data-testid="stPopoverButton"]{
    justify-content: flex-start !important; background: transparent !important;
    border: 1px solid var(--border) !important; border-radius: 12px !important;
    padding: 8px 12px !important; color: var(--text) !important; font-weight: 600 !important;
}
.menu-label{ font-size:10.5px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
    color: var(--text-4); margin: 14px 0 6px 0; }
div[class*="st-key-dangerzone"] button{
    background: transparent !important; border: 1px solid rgba(232,106,106,.35) !important;
    color: var(--danger) !important; border-radius: 10px !important;
}
div[class*="st-key-dangerzone"] button:hover{ background: rgba(232,106,106,.08) !important; }

/* Sidebar inputs */
section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] textarea{
    background: var(--bg) !important; color: var(--text-2) !important;
    border-radius: 8px !important;
}

/* Memory panel */
.mem-item{ font-size:12.5px; color: var(--text-2); line-height:1.45; padding: 2px 0; }
div[class*="st-key-memdel_"] button{
    background: transparent !important; border:none !important; padding:0 !important;
    min-height:0 !important; color: var(--text-4) !important;
}
div[class*="st-key-memdel_"] button:hover{ color: var(--danger) !important; }

/* User chip */
.user-chip{ display:flex; align-items:center; gap:10px; padding: 6px 4px; }
.user-avatar{
    width:32px; height:32px; border-radius:50%; flex-shrink:0;
    background: linear-gradient(135deg, var(--accent), #2a5bd7);
    display:flex; align-items:center; justify-content:center;
    color:#fff; font-weight:700; font-size:13px; box-shadow: 0 0 14px var(--accent-glow);
}
.user-name{ color: var(--text); font-size:13px; font-weight:600; line-height:1.2; }
.user-handle{ color: var(--text-4); font-size:11px; }
div[class*="st-key-signout"] button{
    background: transparent !important; border: 1px solid var(--border) !important;
    border-radius: 9px !important; color: var(--text-3) !important; min-height:0 !important;
    padding: 6px 8px !important;
}
div[class*="st-key-signout"] button:hover{ border-color: var(--danger) !important; color: var(--danger) !important; }
.version-footer{ font-size:10.5px; color: var(--text-4); padding: 8px 6px 4px 6px; }

/* Expanders: trace / sources / citations stay small and quiet */
[data-testid="stExpander"] details{
    background: transparent !important; border: 1px solid var(--border) !important;
    border-radius: 11px !important;
}
[data-testid="stExpander"] summary{ color: var(--text-3) !important; font-size: 12.5px !important; padding: 6px 12px !important; }
[data-testid="stExpander"] summary:hover{ color: var(--text) !important; }
[data-testid="stExpander"]{ margin-bottom: 4px; }

/* ---------- TOPBAR ---------- */
div[class*="st-key-topbar"]{
    background: rgba(18,18,20,.72); backdrop-filter: blur(10px);
    border: 1px solid var(--border); border-radius: var(--radius);
    padding: 8px 10px 8px 16px; margin-bottom: 14px;
}
.topbar-left{ display:flex; align-items:center; gap:10px; min-height: 38px; }
.topbar-icon{
    width:30px; height:30px; border-radius:9px; background: var(--accent-soft);
    display:flex; align-items:center; justify-content:center;
    border: 1px solid rgba(79,142,247,.25);
}
.topbar-icon .material-symbols-outlined{ color: var(--accent); font-size:17px; }
.topbar-title{ color: var(--text); font-weight:600; font-size:14.5px; line-height:1.2; }
.topbar-sub{ color: var(--text-3); font-size:11.5px; }
.chip{
    display:inline-flex; align-items:center; gap:6px; font-size:11.5px; color: var(--text-2);
    background: var(--surface); border:1px solid var(--border-strong); border-radius:999px;
    padding: 3px 10px; margin-left: 6px;
}
.chip .material-symbols-outlined{ font-size:14px; color: var(--accent); }
[data-testid="stPopover"] > div > button, [data-testid="stPopoverButton"]{
    background: var(--surface) !important; border: 1px solid var(--border-strong) !important;
    border-radius: 999px !important; color: var(--text-2) !important; font-size: 12px !important;
}
[data-testid="stPopover"] > div > button:hover, [data-testid="stPopoverButton"]:hover{
    border-color: var(--accent) !important; color: var(--text) !important;
}
[data-testid="stPopoverBody"]{
    background: var(--surface) !important; border: 1px solid var(--border-strong) !important;
    border-radius: 14px !important;
}

/* ---------- WELCOME / HERO ---------- */
.hero{ display:flex; flex-direction:column; align-items:center; text-align:center; padding: 10vh 0 30px 0; }
.hero-badge{
    width:58px; height:58px; border-radius:18px; display:flex; align-items:center; justify-content:center;
    background: radial-gradient(circle at 30% 20%, #1a3a7a, var(--accent-soft));
    border: 1px solid rgba(79,142,247,.35); box-shadow: 0 0 40px rgba(79,142,247,.25);
    margin-bottom: 18px;
}
.hero-badge .material-symbols-outlined{ color: #cfe0ff; font-size:28px; }
.hero-title{
    font-size: 30px; font-weight: 650; letter-spacing: -.02em; margin-bottom: 8px;
    background: linear-gradient(90deg, #ffffff 20%, #9dc0ff 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub{ font-size: 14px; color: var(--text-3); max-width: 560px; line-height: 1.55; }
.hero-hint{ font-size: 12.5px; color: var(--text-3); margin-top: 14px; }
.hero-hint b{ color: var(--accent-2); font-weight:600; }
.hero-badge{ animation: badgeGlow 4.5s ease-in-out infinite; }
@keyframes badgeGlow{ 0%,100%{ box-shadow: 0 0 34px rgba(79,142,247,.22); } 50%{ box-shadow: 0 0 52px rgba(79,142,247,.38); } }
.hero-title .hl{ background: linear-gradient(90deg, #9dc0ff, var(--accent)); -webkit-background-clip:text; background-clip:text; color:transparent; }

/* capability pills under the welcome text */
.caps{ display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin-top: 16px; }
.cap{
    display:inline-flex; align-items:center; gap:6px; font-size:12px; color: var(--text-2);
    padding: 4px 11px 4px 8px; border-radius:999px; background: rgba(18,18,20,.8);
    border: 1px solid var(--border-strong);
}
.cap .material-symbols-outlined{ font-size:15px; color: var(--accent-2); }

/* starter cards: icon tile + arrow that slides in on hover */
div[class*="st-key-starter_"] button{
    background: linear-gradient(180deg, var(--surface), var(--bg-raised)) !important;
    border: 1px solid var(--border) !important; border-radius: 14px !important;
    justify-content: flex-start !important; text-align: left !important;
    padding: 12px 42px 12px 12px !important; min-height: 60px; position: relative;
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
div[class*="st-key-starter_"] button p{ color: var(--text-2) !important; font-size: 13.5px !important; line-height: 1.45 !important; }
div[class*="st-key-starter_"] button [data-testid="stIconMaterial"]{
    color: var(--accent-2) !important; font-size: 18px !important; flex-shrink: 0;
    background: var(--accent-soft); border: 1px solid rgba(79,142,247,.25);
    border-radius: 9px; padding: 7px; line-height: 1;
}
div[class*="st-key-starter_"] button::after{
    content: "arrow_forward"; font-family: 'Material Symbols Outlined'; font-size: 18px;
    position: absolute; right: 14px; top: 50%; transform: translate(-6px, -50%);
    opacity: 0; color: var(--accent-2); transition: opacity .18s ease, transform .18s ease;
}
div[class*="st-key-starter_"] button:hover{
    border-color: rgba(79,142,247,.55) !important; transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(0,0,0,.45), 0 0 0 3px var(--accent-glow);
}
div[class*="st-key-starter_"] button:hover::after{ opacity: 1; transform: translate(0, -50%); }
div[class*="st-key-starter_"] button:hover p{ color: var(--text) !important; }

/* ---------- MESSAGES ---------- */
.msg-user{ display:flex; justify-content:flex-end; margin: 10px 0 12px 0; }
.bubble-user{
    max-width: 78%; padding: 10px 15px; font-size: 14px; line-height: 1.55;
    background: linear-gradient(135deg, #1a4fb3, #12347a);
    border: 1px solid rgba(122,169,255,.35); color: #eef4ff;
    border-radius: 16px 16px 4px 16px; box-shadow: 0 6px 20px rgba(26,79,179,.18);
}
/* Assistant answers: a quiet card with a thin blue edge */
div[class*="st-key-ai_msg_"]{
    background: linear-gradient(180deg, rgba(79,142,247,.035), rgba(255,255,255,.012));
    border: 1px solid var(--border); border-radius: 16px;
    box-shadow: inset 2px 0 0 rgba(79,142,247,.55);
    padding: 14px 20px 8px 20px; margin: 8px 0 4px 0;
    animation: fadeUp .28s ease both;
}
@keyframes fadeUp{ from{ opacity:0; transform: translateY(6px); } to{ opacity:1; transform:none; } }
div[class*="st-key-ai_msg_"] [data-testid="stMarkdownContainer"]{ max-width: 780px; }
div[class*="st-key-ai_msg_"] p{ margin-bottom: .7em !important; }
div[class*="st-key-ai_msg_"] li{ margin-bottom: .3em !important; }
div[class*="st-key-ai_msg_"] strong{ color: #fff; font-weight: 600; }
div[class*="st-key-ai_msg_"] h1, div[class*="st-key-ai_msg_"] h2, div[class*="st-key-ai_msg_"] h3{
    margin-top: .9em !important; margin-bottom: .45em !important; letter-spacing: -.01em; }
div[class*="st-key-ai_msg_"] hr{ border-color: var(--border) !important; margin: 1.1em 0 !important; }
.ai-head{ display:flex; align-items:center; gap:8px; margin-bottom: 2px; }
.ai-avatar{
    width:22px; height:22px; border-radius:7px; background: var(--accent-soft);
    border: 1px solid rgba(79,142,247,.3); display:flex; align-items:center; justify-content:center;
}
.ai-avatar .material-symbols-outlined{ font-size:14px; color: var(--accent); }
.ai-name{ font-size: 12px; font-weight: 600; color: var(--accent-2); letter-spacing:.02em; }
div[class*="st-key-ai_msg_"] p, div[class*="st-key-ai_msg_"] li{
    color: #d6d6da !important; font-size: 14.2px !important; line-height: 1.65 !important;
}
div[class*="st-key-ai_msg_"] h1{ font-size: 20px !important; color:#fff !important; }
div[class*="st-key-ai_msg_"] h2{ font-size: 17px !important; color:#fff !important; }
div[class*="st-key-ai_msg_"] h3{ font-size: 15px !important; color: var(--text) !important; }
div[class*="st-key-ai_msg_"] a{ color: var(--accent-2) !important; text-decoration: none; }
div[class*="st-key-ai_msg_"] a:hover{ text-decoration: underline; }
div[class*="st-key-ai_msg_"] :not(pre) > code{
    background: #1a1a20 !important; color: #cfe0ff !important; border-radius: 6px; padding: 2px 6px;
    font-size: .88em;
}
/* code blocks */
div[class*="st-key-ai_msg_"] pre, div[class*="st-key-ai_msg_"] [data-testid="stCode"] pre{
    background: #0c0c10 !important; border: 1px solid var(--border-strong) !important;
    border-radius: 12px !important; padding: 14px 16px !important;
}
div[class*="st-key-ai_msg_"] pre code{ background: transparent !important; padding: 0 !important; font-size: 12.8px; }
/* tables: rounded, tinted header, soft row lines, scroll sideways on small screens */
div[class*="st-key-ai_msg_"] table{
    display: table; width: 100%;
    border-collapse: separate !important; border-spacing: 0; font-size: 13px;
    border: 1px solid var(--border-strong); border-radius: 12px; margin: 6px 0 14px 0; overflow: hidden;
}
div[class*="st-key-ai_msg_"] th, div[class*="st-key-ai_msg_"] td{
    border: none !important; border-bottom: 1px solid var(--border) !important;
    padding: 9px 14px !important; vertical-align: top; text-align: left;
}
div[class*="st-key-ai_msg_"] th{
    background: rgba(79,142,247,.10) !important; color: #fff !important; font-weight: 600; font-size: 12.5px;
}
div[class*="st-key-ai_msg_"] tbody tr:nth-child(even) td{ background: rgba(255,255,255,.018); }
div[class*="st-key-ai_msg_"] tbody tr:last-child td{ border-bottom: none !important; }
div[class*="st-key-ai_msg_"] tbody tr:hover td{ background: rgba(79,142,247,.05); }
div[class*="st-key-ai_msg_"] td p, div[class*="st-key-ai_msg_"] th p{ margin: 0 !important; font-size: 13px !important; }
div[class*="st-key-ai_msg_"] blockquote{ border-left: 3px solid var(--accent); color: var(--text-3); padding-left: 12px; }

/* reports (Deep Research / AI News): reading layout */
div[class*="st-key-ai_msg_report"] h1{ font-size: 22px !important; }
div[class*="st-key-ai_msg_report"] h2{ border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-top: 1.3em !important; }
.report-head{ border: 1px solid var(--border); background: rgba(12,12,14,.7); border-radius: 12px; padding: 12px 16px; margin: 6px 0 14px 0; }
.report-title{ display:flex; align-items:center; gap:8px; font-weight:600; color:#fff; font-size:13.5px; }
.report-title .material-symbols-outlined{ color: var(--accent-2); font-size:18px; }
.report-meta{ font-size:12px; color: var(--text-4); margin: 2px 0 0 26px; }
.toc{ display:flex; flex-wrap:wrap; gap:6px; margin-top: 10px; }
.toc-chip{ font-size:11.5px; color: var(--text-2); border:1px solid var(--border-strong); border-radius:999px; padding: 2px 10px; background: var(--surface); }

/* sources + PDF citations under an answer */
.src-row, .cite-row{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin: 4px 0 12px 2px; }
.src-label{ font-size:10.5px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color: var(--text-4); margin-right: 4px; }
.src-pill{
    display:inline-flex; align-items:center; gap:6px; padding: 3px 11px 3px 4px; border-radius:999px;
    background: var(--surface); border:1px solid var(--border-strong); color: var(--text-2) !important;
    font-size:12px; text-decoration:none !important; transition: all .15s ease; max-width: 240px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.src-pill:hover{ border-color: rgba(79,142,247,.6); color:#fff !important; background: var(--accent-soft); }
.src-num{
    width:18px; height:18px; border-radius:50%; background: var(--accent-soft); color: var(--accent-2);
    font-size:10.5px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;
}
.cite-chip{ display:inline-block; }
.cite-chip[open]{ flex-basis: 100%; }
.cite-chip summary{
    list-style:none; cursor:pointer; display:inline-flex; align-items:center; gap:5px;
    padding: 3px 11px 3px 8px; border-radius:999px; background: var(--accent-soft);
    border:1px solid rgba(79,142,247,.3); color:#cfe0ff; font-size:12px; font-weight:600; transition: all .15s ease;
}
.cite-chip summary::-webkit-details-marker{ display:none; }
.cite-chip summary .material-symbols-outlined{ font-size:14px; }
.cite-chip summary:hover{ border-color: var(--accent); }
.cite-chip[open] summary{ background: var(--accent); color:#fff; border-color: var(--accent); }
.cite-pop{
    margin-top: 8px; padding: 10px 14px; background: var(--bg-raised); border:1px solid var(--border-strong);
    border-left: 3px solid var(--accent); border-radius: 10px; color: var(--text-2); font-size: 12.8px;
    line-height: 1.6; font-style: italic; max-width: 680px;
}
.cite-src{ font-style: normal; color: var(--text-4); font-size: 11px; margin-top: 6px; }

/* message actions row: quiet until hovered */
div[class*="st-key-msgactions_"]{ margin: -4px 0 18px 4px; opacity: .45; transition: opacity .15s ease; }
div[class*="st-key-msgactions_"]:hover{ opacity: 1; }
div[class*="st-key-msgactions_"] button{
    background: transparent !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text-3) !important; font-size: 12px !important;
    min-height: 0 !important; padding: 3px 10px !important;
}
div[class*="st-key-msgactions_"] button:hover{ border-color: var(--accent) !important; color: var(--text) !important; }

/* thinking: shimmering label + skeleton lines */
.thinking{ padding: 4px 0 12px 0; }
.thinking-label{
    font-size: 13px; font-weight: 600; letter-spacing: .01em;
    background: linear-gradient(90deg, var(--text-4) 0%, #cfe0ff 50%, var(--text-4) 100%);
    background-size: 200% 100%; -webkit-background-clip: text; background-clip: text; color: transparent;
    animation: shimmer 1.6s linear infinite;
}
.sk-line{
    height: 9px; border-radius: 6px; margin-top: 10px;
    background: linear-gradient(90deg, #141418 0%, #1d2334 50%, #141418 100%);
    background-size: 200% 100%; animation: shimmer 1.4s linear infinite;
}
.sk-line.w1{ width: 92%; } .sk-line.w2{ width: 74%; } .sk-line.w3{ width: 56%; }
@keyframes shimmer{ from{ background-position: 200% 0; } to{ background-position: -200% 0; } }

/* agent trace (st.status) as a timeline */
[data-testid="stExpander"] [data-testid="stExpanderDetails"] p{ font-size: 12.5px !important; color: var(--text-2) !important; }
.timeline{ padding: 2px 0 2px 2px; }
.tl-item{ display:flex; align-items:flex-start; gap:10px; position:relative; padding: 5px 0; }
.tl-item:not(:last-child)::before{
    content:""; position:absolute; left:11px; top:29px; bottom:-5px; width:1px; background: var(--border-strong);
}
.tl-dot{
    width:23px; height:23px; flex-shrink:0; border-radius:8px; background: var(--accent-soft);
    border:1px solid rgba(79,142,247,.3); display:flex; align-items:center; justify-content:center;
}
.tl-dot .material-symbols-outlined{ font-size:14px; color: var(--accent-2); }
.tl-text{ font-size:12.5px; color: var(--text-2); line-height:1.5; padding-top:2px; flex:1; min-width:0; overflow-wrap:anywhere; }
.tl-text b{ color:#fff; font-weight:600; }
.tl-text code{ background:#1a1a20; color:#cfe0ff; border-radius:5px; padding:1px 5px; font-size:11.5px; }
.tl-time{ font-size:11px; color: var(--text-4); padding-top:4px; font-variant-numeric: tabular-nums; white-space:nowrap; }

/* Deep Research stage tracker */
.rp{
    background: linear-gradient(180deg, rgba(79,142,247,.07), rgba(79,142,247,.02));
    border: 1px solid rgba(79,142,247,.28); border-radius: 14px; padding: 14px 16px 12px; margin: 4px 0 10px 0;
}
.rp-steps{ display:flex; align-items:center; gap:6px; }
.rp-step{ display:flex; flex-direction:column; align-items:center; gap:6px; min-width:62px; }
.rp-icon.material-symbols-outlined{
    width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:16px; border:1px solid var(--border-strong); color: var(--text-4); background: var(--bg-raised);
}
.rp-label{ font-size:11.5px; color: var(--text-4); white-space:nowrap; }
.rp-step.done .rp-icon{ background: var(--accent); border-color: var(--accent); color:#fff; }
.rp-step.done .rp-label{ color: var(--text-2); }
.rp-step.active .rp-icon{ border-color: var(--accent); color: var(--accent-2); animation: rpPulse 1.6s ease-in-out infinite; }
.rp-step.active .rp-label, .rp-step.wait .rp-label{ color:#fff; font-weight:600; }
.rp-step.wait .rp-icon{ border: 1px dashed var(--accent-2); color: var(--accent-2); }
.rp-bar{ flex:1; height:2px; min-width:10px; background: var(--border-strong); border-radius:2px; margin-bottom:20px; }
.rp-bar.done{ background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
.rp-status{ font-size:12.5px; color: var(--text-3); margin-top: 8px; text-align:center; }
@keyframes rpPulse{ 0%,100%{ box-shadow: 0 0 0 3px var(--accent-glow); } 50%{ box-shadow: 0 0 0 7px rgba(79,142,247,.07); } }

/* ---------- DEEP RESEARCH PLAN REVIEW ---------- */
div[class*="st-key-plan_review"]{
    background: linear-gradient(180deg, rgba(79,142,247,.08), rgba(79,142,247,.02));
    border: 1px solid rgba(79,142,247,.4); border-radius: var(--radius);
    padding: 14px 18px 12px 18px; margin: 6px 0 14px 0;
}
.plan-title{ color: var(--text); font-weight: 600; font-size: 14.5px; }
.plan-sub{ color: var(--text-3); font-size: 12.5px; margin-bottom: 6px; }
div[class*="st-key-plan_review"] textarea{
    background: var(--bg) !important; color: var(--text) !important; font-size: 13.5px !important;
    border-radius: 10px !important;
}

/* ---------- CHAT INPUT ---------- */
[data-testid="stChatInput"]{
    background: var(--bg-raised) !important; border: 1px solid var(--border-strong) !important;
    border-radius: 16px !important; box-shadow: 0 10px 30px rgba(0,0,0,.35);
}
[data-testid="stChatInput"]:focus-within{
    border-color: rgba(79,142,247,.7) !important; box-shadow: 0 0 0 3px var(--accent-glow), 0 10px 30px rgba(0,0,0,.35);
}
[data-testid="stChatInput"] textarea{ color: var(--text) !important; background: transparent !important; }
button[data-testid="stChatInputSubmitButton"]{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important; border-radius: 10px !important;
}
button[data-testid="stChatInputSubmitButton"] svg{ fill:#fff !important; color:#fff !important; }

/* generic primary buttons keep the blue */
button[kind="primary"]{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important;
    border: none !important; border-radius: 10px !important;
}

/* small "Copy" popover in the message actions row */
div[class*="st-key-msgactions_"] [data-testid="stPopover"] button,
div[class*="st-key-msgactions_"] [data-testid="stPopoverButton"]{
    border-radius: 8px !important; padding: 3px 10px !important; font-size: 12px !important; min-height: 0 !important;
}

/* ---------- PHONES ---------- */
@media (max-width: 640px){
    .block-container{ padding-top: 3.4rem !important; padding-left: 14px !important; padding-right: 14px !important; }
    div[class*="st-key-topbar"]{ padding: 6px 8px 6px 10px; }
    /* keep "mode + Settings" on one row (Streamlit stacks columns on small screens) */
    div[class*="st-key-topbar"] [data-testid="stHorizontalBlock"]{ flex-wrap: nowrap !important; gap: 8px !important; align-items: center !important; }
    div[class*="st-key-topbar"] .topbar-left{ min-height: 0; }
    /* Streamlit gives text blocks a -16px bottom margin, which made the label sit 8px low here */
    div[class*="st-key-topbar"] [data-testid="stMarkdownContainer"]{ margin-bottom: 0 !important; }
    div[class*="st-key-topbar"] [data-testid="stColumn"]{ width: auto !important; min-width: 0 !important; flex: 1 1 auto !important; }
    div[class*="st-key-topbar"] [data-testid="stColumn"]:last-child{ flex: 0 0 auto !important; }
    .topbar-sub, .chip{ display:none; }
    .topbar-title{ font-size: 13.5px; }
    .hero{ padding: 5vh 0 16px 0; }
    .hero-title{ font-size: 23px; }
    .hero-sub{ font-size: 13px; }
    .bubble-user{ max-width: 88%; }
    div[class*="st-key-ai_msg_"]{ padding: 12px 14px 6px 14px; }
    /* wide tables scroll sideways instead of squashing on a phone */
    div[class*="st-key-ai_msg_"] table{ display: block; overflow-x: auto; width: max-content; max-width: 100%; }
    .rp-label{ display:none; }
    .rp-step{ min-width: 0; }
}

/* respect "reduce motion" settings */
@media (prefers-reduced-motion: reduce){
    *, *::before, *::after{ animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
</style>
"""
