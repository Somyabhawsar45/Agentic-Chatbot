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
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<!-- display=block: icons stay blank for a moment instead of showing their names ("travel_explore") while the font loads -->
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,400,0,0&display=block" />
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
/* the bar behind the chat box fades out upwards, so the aurora has no hard edge */
[data-testid="stBottom"]{ background: linear-gradient(to top, var(--bg) 62%, rgba(10,10,10,0)) !important; }
[data-testid="stBottomBlockContainer"]{ background: transparent !important; }
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
.guest-hint{ font-size:12px; color: var(--text-2); line-height:1.5; margin: 6px 0 2px 0;
    padding: 8px 10px; border-radius: 10px; background: var(--accent-soft); border: 1px solid rgba(79,142,247,.25); }
.guest-hint b{ color:#fff; }
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
    color:#fff; font-weight:700; font-size:13px; box-shadow: 0 0 8px rgba(79,142,247,.12);
}
.user-name{ color: var(--text); font-size:13px; font-weight:600; line-height:1.2; }
.user-handle{ color: var(--text-4); font-size:11px; }
div[class*="st-key-signout"] button{
    background: transparent !important; border: 1px solid var(--border) !important;
    border-radius: 9px !important; color: var(--text-3) !important; min-height:0 !important;
    padding: 6px 8px !important;
}
div[class*="st-key-signout"] button:hover{ border-color: var(--danger) !important; color: var(--danger) !important; }

/* Expanders: trace / sources / citations stay small and quiet */
[data-testid="stExpander"] details{
    background: transparent !important; border: 1px solid var(--border) !important;
    border-radius: 11px !important;
}
[data-testid="stExpander"] summary{ color: var(--text-3) !important; font-size: 12.5px !important; padding: 6px 12px !important; }
[data-testid="stExpander"] summary:hover{ color: var(--text) !important; }
[data-testid="stExpander"]{ margin-bottom: 4px; }

/* ---------- TOPBAR ---------- */
/* No box: a small mode label on the left (only inside a chat) and two floating buttons on the right,
   a model chip and a round gear. */
div[class*="st-key-topbar"]{ flex-wrap: nowrap !important; align-items: center; gap: 8px !important;
    margin: -8px 0 6px 0; min-height: 36px; }
div[class*="st-key-topbar"] > div:first-child{ flex: 1 1 auto !important; min-width: 0; }
div[class*="st-key-topbar"] [data-testid="stMarkdownContainer"]{ margin-bottom: 0 !important; }
.topbar-mode{ display: flex; align-items: center; gap: 7px; color: var(--text-3); font-size: 13px; font-weight: 600;
    white-space: nowrap; overflow: hidden; }
.topbar-mode .material-symbols-outlined{ color: var(--accent-2); font-size: 17px; }
div[class*="st-key-topbar"] [data-testid="stPopover"]{ flex: 0 0 auto; }
div[class*="st-key-topbar"] [data-testid="stPopoverButton"]{
    background: rgba(18,18,22,.7) !important; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    border: 1px solid var(--border-strong) !important; border-radius: 999px !important;
    padding: 5px 12px !important; min-height: 0 !important; transition: border-color .15s ease, background .15s ease;
}
div[class*="st-key-topbar"] [data-testid="stPopoverButton"] p{ font-size: 12.5px !important; color: var(--text-2) !important; }
div[class*="st-key-topbar"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"]{ color: var(--accent-2) !important; font-size: 17px !important; }
div[class*="st-key-topbar"] [data-testid="stPopoverButton"]:hover{ border-color: rgba(79,142,247,.55) !important; background: var(--accent-soft) !important; }
/* the gear is a plain round button, without the dropdown arrow */
div[class*="st-key-topbar"] div[class*="st-key-gear"] [data-testid="stPopoverButton"]{ width: 36px; height: 36px; padding: 0 !important; justify-content: center; }
div[class*="st-key-topbar"] div[class*="st-key-gear"] [data-testid="stPopoverButton"] > div > div[aria-hidden="true"]{ display: none; }
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
    border: 1px solid rgba(79,142,247,.28); box-shadow: 0 0 24px rgba(79,142,247,.13);
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
@keyframes badgeGlow{ 0%,100%{ box-shadow: 0 0 20px rgba(79,142,247,.11); } 50%{ box-shadow: 0 0 30px rgba(79,142,247,.19); } }
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

/* thinking: the scanning Netra eye + a shimmering label (eye styles: see LIVING NETRA EYE) */
.thinking{ padding: 6px 0 12px 0; }
.thinking-label{
    font-size: 13px; font-weight: 600; letter-spacing: .01em;
    background: linear-gradient(90deg, var(--text-4) 0%, #cfe0ff 50%, var(--text-4) 100%);
    background-size: 200% 100%; -webkit-background-clip: text; background-clip: text; color: transparent;
    animation: shimmer 1.6s linear infinite;
}
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

/* "Try it with a sample PDF" under the welcome text */
div[class*="st-key-sample_pdf"] button{
    border: 1px dashed rgba(79,142,247,.5) !important; background: var(--accent-soft) !important;
    border-radius: 999px !important; min-height: 38px !important; margin: -4px 0 14px 0;
}
div[class*="st-key-sample_pdf"] button p{ color: #cfe0ff !important; font-weight: 600 !important; font-size: 13px !important; }
div[class*="st-key-sample_pdf"] button [data-testid="stIconMaterial"]{ color: var(--accent-2) !important; }
div[class*="st-key-sample_pdf"] button:hover{ border-style: solid !important; border-color: var(--accent) !important; }

/* a background run waiting for a free slot */
.queue-card{ display:flex; gap:12px; align-items:flex-start; padding: 14px 16px; margin: 4px 0 12px 0;
    border: 1px dashed rgba(79,142,247,.45); border-radius: 14px; background: var(--accent-soft);
    color: var(--text-2); font-size: 13px; line-height: 1.55; }
.queue-card b{ color:#fff; }
.queue-card .material-symbols-outlined{ color: var(--accent-2); font-size: 22px; animation: amSpin 2.4s linear infinite; }

/* live agent map (Deep Research): Planner -> Researchers (parallel) -> Writer <-> Critic -> Report */
.amap{ display:flex; align-items:center; overflow-x:auto; padding: 2px 2px 4px 2px; }
.am-col{ display:flex; flex-direction:column; gap:6px; flex: 0 0 auto; }
.am-fan{ flex: 1 1 auto; min-width: 170px; max-width: 300px; }
.am-node{
    display:flex; align-items:center; gap:8px; padding: 6px 10px 6px 6px; border-radius: 11px; min-width: 0;
    border: 1px solid var(--border-strong); background: rgba(12,12,15,.8);
    transition: border-color .3s ease, background .3s ease;
}
.am-ic.material-symbols-outlined{
    width:26px; height:26px; flex-shrink:0; border-radius:8px; display:flex; align-items:center; justify-content:center;
    font-size:15px; color: var(--text-4); background: rgba(255,255,255,.04);
}
.am-text{ min-width:0; }
.am-title{ font-size:12px; font-weight:600; color: var(--text-3); white-space:nowrap; line-height:1.25; }
.am-sub{ font-size:10.5px; color: var(--text-4); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width: 200px; line-height:1.3; }
.am-col:not(.am-fan) .am-sub{ max-width: 96px; }
.am-node.active{ border-color: var(--accent); background: rgba(79,142,247,.09); animation: amPulse 1.6s ease-in-out infinite; }
.am-node.active .am-ic{ background: var(--accent-soft); color: var(--accent-2); animation: amSpin 2.4s linear infinite; }
.am-node.active .am-title{ color:#fff; }
.am-node.done{ border-color: rgba(79,142,247,.30); }
.am-node.done .am-ic{ background: var(--accent); color:#fff; }
.am-node.done .am-title{ color: var(--text-2); }
.am-node.wait{ border-style: dashed; border-color: var(--accent-2); }
.am-node.wait .am-ic{ color: var(--accent-2); }
.am-node.todo{ opacity: .6; }
@keyframes amPulse{ 0%,100%{ box-shadow: 0 0 0 0 rgba(79,142,247,0); } 50%{ box-shadow: 0 0 0 4px rgba(79,142,247,.12); } }
@keyframes amSpin{ 0%,100%{ transform: rotate(0deg); } 50%{ transform: rotate(-12deg); } }
.am-edge{ flex: 0 0 20px; height: 2px; border-radius: 2px; background: var(--border-strong); position: relative; overflow: hidden; }
.am-edge.on{ background: rgba(79,142,247,.45); }
.am-edge.flow{ background: rgba(79,142,247,.25); }
.am-edge.flow::after{
    content:""; position:absolute; top:0; bottom:0; left:0; width: 60%;
    background: linear-gradient(90deg, transparent, #cfe0ff, transparent); animation: amFlow 1s linear infinite;
}
@keyframes amFlow{ from{ transform: translateX(-100%); } to{ transform: translateX(180%); } }
/* narrow chat column (small laptop with the sidebar open, tablet, phone): the map runs top to bottom */
.rp:has(.amap){ container: amap / inline-size; }
@container amap (max-width: 700px){
    .amap{ flex-direction: column; align-items: stretch; }
    .am-col, .am-fan{ max-width: none; }
    .am-sub, .am-col:not(.am-fan) .am-sub{ max-width: none; }
    .am-edge{ flex: 0 0 14px; width: 2px; height: 14px; align-self: center; }
    .am-edge.flow::after{ width: auto; height: 60%; left: 0; right: 0; top: 0; bottom: auto;
        background: linear-gradient(180deg, transparent, #cfe0ff, transparent); animation-name: amFlowDown; }
}
@keyframes amFlowDown{ from{ transform: translateY(-100%); } to{ transform: translateY(180%); } }

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

/* ---------- LIVING NETRA EYE ---------- */
/* The logo is a blue eye on pure black: two black "eyelids" close toward the middle for a
   moment every few seconds (a thin blue line remains, like a closed eye), then open again. */
.netra-eye{
    position: relative; display: inline-flex; flex-shrink: 0; vertical-align: middle;
    width: var(--eye); height: var(--eye); border-radius: calc(var(--eye) * .28); overflow: hidden;
    background: #000; box-shadow: 0 0 10px rgba(79,142,247,.10);
}
.netra-eye img{ width: 100% !important; height: 100% !important; display: block;
    border-radius: 0 !important; box-shadow: none !important; }
.netra-eye::before, .netra-eye::after{
    content: ""; position: absolute; left: 0; right: 0; height: 27%; background: #000;
    transform: scaleY(0); pointer-events: none; animation: eyeBlink 4.2s ease-in-out infinite;
}
.netra-eye::before{ top: 23%; transform-origin: top; box-shadow: inset 0 -1.5px 0 var(--accent); }
.netra-eye::after{ bottom: 23%; transform-origin: bottom; }
@keyframes eyeBlink{ 0%, 90%, 96%, 100%{ transform: scaleY(0); } 93%{ transform: scaleY(1); } }
.hero-badge.hero-eye{ background: #000; padding: 0; overflow: visible; border-color: rgba(79,142,247,.45); }
.hero-badge.hero-eye .netra-eye::before, .hero-badge.hero-eye .netra-eye::after{ animation-duration: 3.6s; }

/* while thinking: the eye sits in a spinning "scanning" ring */
@property --ring-a{ syntax: '<angle>'; inherits: false; initial-value: 0deg; }
.thinking-row{ display: flex; align-items: center; gap: 12px; }
.eye-ring{
    position: relative; display: inline-flex; padding: 2.5px; border-radius: 50%;
    background: conic-gradient(from var(--ring-a), rgba(79,142,247,.08) 0deg, rgba(79,142,247,.08) 150deg,
                var(--accent) 290deg, #cfe0ff 350deg, rgba(79,142,247,.08) 360deg);
    box-shadow: 0 0 22px rgba(79,142,247,.30); animation: ringSpin 1.1s linear infinite;
}
.eye-ring .netra-eye{ border-radius: 50%; box-shadow: none; }
.eye-ring .netra-eye::before, .eye-ring .netra-eye::after{ animation-duration: 2.6s; }
@keyframes ringSpin{ to{ --ring-a: 360deg; } }

/* ---------- GLOWING CHAT BOX WHILE NETRA WORKS ---------- */
/* A hidden .netra-busy marker is on the page only while an answer or background run is in progress. */
div[data-testid="stElementContainer"]:has(.netra-busy){ display: none; }
/* the tiny script that saves / clears the "stay signed in" cookie takes no space */
div[data-testid="stElementContainer"]:has(.netra-cookie){ display: none; }
div[data-testid="stElementContainer"]:has(.pop-mark){ display: none; }

/* compact account + settings menus (they otherwise grow up to 700px wide with their text) */
[data-testid="stPopoverBody"]:has(.user-chip), [data-testid="stPopoverBody"]:has(.pop-settings){
    min-width: 0 !important; width: 290px !important; max-width: calc(100vw - 24px) !important;
    padding: 14px 16px !important;
}
[data-testid="stPopoverBody"]:has(.pop-settings){ width: 300px !important; }
[data-testid="stPopoverBody"]:has(.user-chip) [data-testid="stVerticalBlock"],
[data-testid="stPopoverBody"]:has(.pop-settings) [data-testid="stVerticalBlock"]{ gap: .55rem; }
[data-testid="stPopoverBody"]:has(.user-chip) .user-chip{ padding: 0 0 2px 0; }
[data-testid="stPopoverBody"]:has(.user-chip) .user-avatar{ width: 34px; height: 34px; font-size: 12.5px; }
[data-testid="stPopoverBody"]:has(.user-chip) .menu-label{ margin: 6px 0 2px 0; font-size: 10px; }
[data-testid="stPopoverBody"]:has(.user-chip) [data-testid="stCaptionContainer"],
[data-testid="stPopoverBody"]:has(.pop-settings) [data-testid="stCaptionContainer"]{ font-size: 12px !important; }
[data-testid="stPopoverBody"]:has(.user-chip) hr{ margin: 4px 0 !important; }
[data-testid="stPopoverBody"]:has(.user-chip) button,
[data-testid="stPopoverBody"]:has(.pop-settings) button[kind]{ min-height: 34px !important; padding-top: 4px !important; padding-bottom: 4px !important; }
[data-testid="stPopoverBody"]:has(.user-chip) button p{ font-size: 13px !important; }
[data-testid="stPopoverBody"]:has(.pop-settings) label p{ font-size: 12.5px !important; }
[data-testid="stPopoverBody"]:has(.pop-settings) input{ font-size: 13px !important; min-height: 36px; }
.guest-hint{ font-size: 11.5px; padding: 7px 9px; }
@property --glow-a{ syntax: '<angle>'; inherits: false; initial-value: 0deg; }
.stApp:has(.netra-busy) [data-testid="stChatInput"]{
    position: relative; border-color: rgba(79,142,247,.25) !important;
    box-shadow: 0 0 0 3px rgba(79,142,247,.07), 0 0 30px rgba(79,142,247,.20), 0 10px 30px rgba(0,0,0,.35) !important;
}
.stApp:has(.netra-busy) [data-testid="stChatInput"]::before{
    content: ""; position: absolute; inset: -1px; border-radius: 17px; padding: 1.5px; pointer-events: none; z-index: 2;
    background: conic-gradient(from var(--glow-a), transparent 0deg, transparent 190deg,
                rgba(79,142,247,.6) 260deg, #cfe0ff 320deg, transparent 360deg);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude;
    animation: glowSpin 2.4s linear infinite;
}
@keyframes glowSpin{ to{ --glow-a: 360deg; } }

/* ---------- AURORA BACKGROUND ---------- */
/* A faint, slowly drifting blue glow behind everything. It is one fixed layer that only moves
   (cheap for the GPU) and sits under all content; "reduce motion" users get it still. */
[data-testid="stAppViewContainer"]{ isolation: isolate; }
[data-testid="stAppViewContainer"]::before{
    content: ""; position: fixed; inset: -25%; z-index: -1; pointer-events: none;
    background:
        radial-gradient(36% 28% at 32% 34%, rgba(79,142,247,.10), transparent 70%),
        radial-gradient(30% 24% at 70% 62%, rgba(99,102,241,.07), transparent 70%),
        radial-gradient(28% 22% at 56% 18%, rgba(56,189,248,.06), transparent 70%);
    filter: blur(28px); will-change: transform;
    animation: aurora 48s ease-in-out infinite alternate;
}
@keyframes aurora{
    0%{ transform: translate3d(-4%, -2%, 0) rotate(0deg) scale(1); }
    50%{ transform: translate3d(3%, 3%, 0) rotate(7deg) scale(1.08); }
    100%{ transform: translate3d(-2%, 4%, 0) rotate(-5deg) scale(1.03); }
}

/* ---------- FLOATING SIDEBAR ---------- */
/* The sidebar is a rounded glass panel floating over the aurora, with a quiet hairline border. */
section[data-testid="stSidebar"]{ background: transparent !important; border-right: none !important; }
section[data-testid="stSidebar"][data-collapsed="false"]{ width: 284px !important; min-width: 284px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{
    margin: 10px 0 10px 10px; width: calc(100% - 10px) !important; height: calc(100% - 20px) !important;
    border-radius: 18px; background: rgba(15,17,25,.88) !important; border: 1px solid rgba(255,255,255,.06);
    box-shadow: 0 24px 60px rgba(0,0,0,.5); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    padding-top: 0 !important; position: relative;
}
/* no tall empty strip at the top: the collapse arrow floats in the panel's corner instead */
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"]{
    position: absolute; top: 16px; right: 12px; z-index: 6; padding: 0 !important; height: auto !important;
}
section[data-testid="stSidebar"] [data-testid="stLogoSpacer"]{ display: none; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{
    padding: 16px 12px 12px 12px !important; min-height: 100%; display: flex; flex-direction: column;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div{ flex: 1; display: flex; flex-direction: column; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"]{ flex: 1; gap: 3px; }
/* Streamlit gives text blocks a -16px bottom margin; with the tighter spacing here it made labels overlap */
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]{ margin-bottom: 0 !important; }
.sidebar-logo-wrap{ padding: 0 4px 2px 4px; }
.sidebar-logo-tagline{ margin-left: 38px; }
.sidebar-label{ margin: 16px 0 6px 8px; }

/* New chat: a solid blue pill */
div[class*="st-key-newchat_wrap"] button{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important; border: none !important;
    border-radius: 999px !important; margin-top: 12px; box-shadow: 0 4px 12px rgba(42,91,215,.18);
    transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
div[class*="st-key-newchat_wrap"] button p, div[class*="st-key-newchat_wrap"] button span{ color: #fff !important; }
div[class*="st-key-newchat_wrap"] button:hover{ transform: translateY(-1px); filter: brightness(1.06); box-shadow: 0 6px 16px rgba(42,91,215,.26); }

/* Modes: compact pills (the active one is solid blue, see loadui) */
div[class*="st-key-navitem_"] button{ border-radius: 999px !important; padding: 6px 12px !important; }

/* History rows: title + a ⋯ menu that appears on hover */
div[class*="st-key-histitem_"]{ flex-wrap: nowrap !important; gap: 0 !important; align-items: center; border-radius: 10px; }
div[class*="st-key-histitem_"] > div:first-child{ flex: 1 1 auto !important; min-width: 0; }
div[class*="st-key-histitem_"] button{ border-radius: 10px !important; }
div[class*="st-key-histitem_on_"] button{ box-shadow: inset 2px 0 0 var(--accent); }
div[class*="st-key-histitem_"] [data-testid="stIconMaterial"]{ color: var(--accent-2) !important; font-size: 15px !important; }
div[class*="st-key-histitem_"] [data-testid="stPopover"]{ opacity: 0; transition: opacity .15s ease; flex: 0 0 auto; }
div[class*="st-key-histitem_"]:hover [data-testid="stPopover"],
div[class*="st-key-histitem_on_"] [data-testid="stPopover"],
div[class*="st-key-histitem_"] [data-testid="stPopover"]:focus-within{ opacity: 1; }
div[class*="st-key-histitem_"] [data-testid="stPopover"] button{
    background: transparent !important; border: none !important; box-shadow: none !important;
    padding: 4px 6px !important; min-height: 0 !important; color: var(--text-4) !important;
}
/* the ⋯ buttons don't need Streamlit's dropdown arrow next to them */
div[class*="st-key-histitem_"] [data-testid="stPopoverButton"] > div > div[aria-hidden="true"]{ display: none; }
div[class*="st-key-histitem_"] [data-testid="stPopover"] button:hover{ color: #fff !important; background: var(--surface) !important; }
.hist-empty{
    margin: 4px 2px 8px 2px; border: 1px dashed rgba(79,142,247,.35); border-radius: 12px; padding: 12px 10px;
    text-align: center; color: var(--text-4); font-size: 12px; line-height: 1.5;
}
.hist-empty .material-symbols-outlined{ display: block; color: var(--accent-2); font-size: 20px; margin-bottom: 4px; }
div[class*="st-key-dangerzone_h"] button{ color: var(--danger) !important; border-color: rgba(232,106,106,.35) !important; background: transparent !important; }
div[class*="st-key-dangerzone_h"] button p{ color: var(--danger) !important; }

/* Account row at the bottom (stays put while the history scrolls):
   [avatar  name  v]  ...  [gear]. The avatar is a ::before on the menu button (initials set in loadui). */
section[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> div[class*="st-key-acctcard"]){
    margin-top: auto; position: sticky; bottom: 0; z-index: 4; padding-top: 8px;
    background: linear-gradient(to top, rgba(15,17,25,1) 75%, rgba(15,17,25,0));
}
div[class*="st-key-acctcard"]{
    flex-wrap: nowrap !important; gap: 4px !important; align-items: center; justify-content: space-between;
    border-top: 1px solid rgba(255,255,255,.06); padding: 8px 0 2px 0;
}
div[class*="st-key-acctmenu"]{ min-width: 0; flex: 0 1 auto !important; }
div[class*="st-key-acctmenu"] [data-testid="stPopover"]{ min-width: 0; }
div[class*="st-key-acctmenu"] [data-testid="stPopoverButton"]{
    background: transparent !important; border: none !important; box-shadow: none !important;
    padding: 4px 8px 4px 4px !important; min-height: 0 !important; border-radius: 12px !important;
    gap: 9px; max-width: 100%; transition: background .15s ease;
}
div[class*="st-key-acctmenu"] [data-testid="stPopoverButton"]::before{
    width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
    display: inline-flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #7a6cf2, #5662e6); color: #fff; font-size: 12px; font-weight: 600;
}
div[class*="st-key-acctmenu"] [data-testid="stPopoverButton"] p{
    color: var(--text) !important; font-size: 14px !important; font-weight: 600 !important;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
div[class*="st-key-acctmenu"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"]{ color: var(--text-4) !important; }
div[class*="st-key-acctmenu"] [data-testid="stPopoverButton"]:hover,
div[class*="st-key-acctgear"] [data-testid="stPopoverButton"]:hover{ background: var(--surface) !important; }
div[class*="st-key-acctgear"] [data-testid="stPopoverButton"]{
    background: transparent !important; border: none !important; box-shadow: none !important;
    width: 36px; height: 36px; padding: 0 !important; min-height: 0 !important; border-radius: 50% !important;
    justify-content: center;
}
div[class*="st-key-acctgear"] [data-testid="stPopoverButton"] > div > div[aria-hidden="true"]{ display: none; }
div[class*="st-key-acctgear"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"]{
    color: var(--text-3) !important; font-size: 21px !important;
}
div[class*="st-key-acctgear"] [data-testid="stPopoverButton"]:hover [data-testid="stIconMaterial"]{ color: #fff !important; }

/* ---------- ANSWERS: SOURCE ICONS + HOVER TOOLBAR ---------- */
.fav{
    position: relative; width: 18px; height: 18px; border-radius: 50%; flex-shrink: 0; overflow: hidden;
    display: inline-flex; align-items: center; justify-content: center;
    background: #e9edf5; color: hsl(var(--fav-h) 55% 34%); font-size: 10px; font-weight: 700; line-height: 1;
}
.fav img{ position: absolute; inset: 2px; width: calc(100% - 4px); height: calc(100% - 4px); object-fit: contain; }
.src-stack{ display: inline-flex; align-items: center; padding-left: 6px; }
.src-stack .fav{ width: 24px; height: 24px; margin-left: -7px; border: 2px solid var(--bg); box-sizing: content-box; }
.src-count{ font-size: 12px; font-weight: 600; color: var(--accent-2); margin: 0 6px 0 4px; }
/* older answers show their 👍 / Copy / Share row only while you hover them; the newest always does */
div[class*="st-key-turn_"]:not([class*="st-key-turn_last"]) div[class*="st-key-msgactions_"]{ opacity: 0; }
div[class*="st-key-turn_"]:hover div[class*="st-key-msgactions_"],
div[class*="st-key-msgactions_"]:focus-within{ opacity: 1 !important; }

/* ---------- TYPING EFFECTS ---------- */
.typed .tw{ display: inline-block; white-space: nowrap; }
.typed .ch{ opacity: 0; animation: chIn .22s ease forwards; animation-delay: var(--d); }
@keyframes chIn{ from{ opacity: 0; filter: blur(3px); } to{ opacity: 1; filter: none; } }
.type-cur{
    display: inline-block; width: 3px; height: .9em; margin-left: 5px; vertical-align: -.06em; border-radius: 2px;
    background: var(--accent);
    animation: curBlink 1s step-end infinite, curOff .3s ease calc(var(--d) + 2.6s) forwards;
}
@keyframes curBlink{ 50%{ opacity: 0; } }
@keyframes curOff{ to{ opacity: 0; } }
/* example questions typed into the empty message box (keyframes come from loadui, per mode) */
[data-testid="stChatInput"] div:has(> textarea){ position: relative; }
[data-testid="stChatInput"] div:has(> textarea:placeholder-shown)::after{
    position: absolute; left: 0; right: 6px; top: 50%; transform: translateY(-50%); pointer-events: none;
    color: var(--text-4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ---------- POLISH: calmer sidebar, chat and menus ---------- */
/* Sidebar: a soft floating panel (inset, rounded, faint border; no glow) */
section[data-testid="stSidebar"]{ background: transparent !important; border-right: none !important; }
section[data-testid="stSidebar"][data-collapsed="false"]{ width: 280px !important; min-width: 280px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{
    margin: 8px 0 8px 8px !important; width: calc(100% - 8px) !important; height: calc(100% - 16px) !important;
    border-radius: 16px !important; background: #111116 !important; border: 1px solid #22222b !important;
    box-shadow: 0 10px 30px rgba(0,0,0,.35) !important;
    backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
}
section[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> div[class*="st-key-acctcard"]){
    background: linear-gradient(to top, #111116 75%, rgba(17,17,22,0)) !important;
}
/* New chat: an outlined button, so it doesn't look like the selected mode */
div[class*="st-key-newchat_wrap"] button{
    background: transparent !important; border: 1px solid var(--border-strong) !important;
    border-radius: 12px !important; box-shadow: none !important;
}
div[class*="st-key-newchat_wrap"] button p{ color: var(--text) !important; font-weight: 600 !important; }
div[class*="st-key-newchat_wrap"] button [data-testid="stIconMaterial"]{ color: var(--accent-2) !important; }
div[class*="st-key-newchat_wrap"] button:hover{
    background: var(--surface) !important; border-color: rgba(79,142,247,.55) !important;
    transform: none !important; filter: none !important; box-shadow: none !important;
}

/* Messages: your message is a quiet grey bubble; answers have no card, just a small Netra eye on the
   left, and the trace, answer, sources and actions all line up in one column next to it. */
.bubble-user{
    background: #1c1e25 !important; border: 1px solid #2a2d38 !important; color: var(--text) !important;
    box-shadow: none !important; border-radius: 18px 18px 6px 18px !important; padding: 9px 14px !important;
    max-width: 72% !important;
}
div[class*="st-key-ai_msg_"]{
    background: none !important; border: none !important; box-shadow: none !important;
    padding: 0 0 0 38px !important; margin: 6px 0 2px 0 !important; position: relative;
}
.ai-head{ position: absolute; left: 0; top: 1px; margin: 0; }
/* the avatar's own box takes no room, so the answer text starts right beside it */
div[class*="st-key-ai_msg_"] [data-testid="stElementContainer"]:has(.ai-head){ display: contents; }
.ai-head .netra-eye{ box-shadow: none; }
.netra-eye.still::before, .netra-eye.still::after{ animation: none !important; }
div[class*="st-key-ai_msg_"]:has(.thinking) .ai-head{ display: none; }        /* the thinking eye takes its place */
div[class*="st-key-ai_msg_"]:has(.thinking) .thinking{ margin-left: -38px; }
.stMain [data-testid="stExpander"]{ margin-left: 38px; width: calc(100% - 38px) !important; }
.stMain [data-testid="stExpander"] details{ border: none !important; }
.stMain [data-testid="stExpander"] summary{ padding: 2px 0 !important; }
.src-row, .cite-row{ margin-left: 38px !important; }

/* answer actions: small and quiet */
div[class*="st-key-msgactions_"]{ margin: -2px 0 14px 38px !important; gap: 6px !important; width: calc(100% - 38px) !important; }
.copy-btn{
    display: inline-flex; align-items: center; gap: 5px; cursor: pointer; font-family: inherit;
    background: transparent; border: 1px solid var(--border); border-radius: 8px;
    color: var(--text-3); font-size: 12px; line-height: 1.4; padding: 3px 9px;
    transition: border-color .15s ease, color .15s ease;
}
.copy-btn .material-symbols-outlined{ font-size: 15px; }
.copy-btn:hover{ border-color: var(--accent); color: var(--text); }
.copy-btn.done{ border-color: rgba(47,191,113,.6); color: #7ee2a8; }
div[class*="st-key-msgactions_"] [data-testid="stPopoverButton"],
div[class*="st-key-msgactions_"] [data-testid="stDownloadButton"] button{
    background: transparent !important; border: 1px solid var(--border) !important; border-radius: 8px !important;
    padding: 3px 9px !important; min-height: 0 !important; box-shadow: none !important;
}
div[class*="st-key-msgactions_"] [data-testid="stPopoverButton"] p,
div[class*="st-key-msgactions_"] [data-testid="stDownloadButton"] button p{ font-size: 12px !important; color: var(--text-3) !important; }
div[class*="st-key-msgactions_"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"],
div[class*="st-key-msgactions_"] [data-testid="stDownloadButton"] [data-testid="stIconMaterial"]{ font-size: 15px !important; }
div[class*="st-key-msgactions_"] [data-testid="stPopoverButton"] > div > div[aria-hidden="true"]{ display: none; }

/* compact menus: share, model, chat options */
[data-testid="stPopoverBody"]:has(.pop-share){ min-width: 0 !important; width: 300px !important; padding: 12px 14px !important; }
[data-testid="stPopoverBody"]:has(.pop-model){ min-width: 0 !important; width: 210px !important; padding: 12px 14px !important; }
[data-testid="stPopoverBody"]:has(.pop-hist){ min-width: 0 !important; width: 220px !important; padding: 8px !important; }
[data-testid="stPopoverBody"]:has(.pop-share) [data-testid="stVerticalBlock"],
[data-testid="stPopoverBody"]:has(.pop-model) [data-testid="stVerticalBlock"],
[data-testid="stPopoverBody"]:has(.pop-hist) [data-testid="stVerticalBlock"]{ gap: .35rem; }
[data-testid="stPopoverBody"]:has(.pop-model) label p{ font-size: 13px !important; }
[data-testid="stPopoverBody"]:has(.pop-share) button[kind]{ min-height: 32px !important; padding: 3px 12px !important; }
.share-link{ font-size: 12px; color: var(--accent-2); background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 6px 8px; word-break: break-all; }
[data-testid="stPopoverBody"]:has(.pop-hist) button{
    background: transparent !important; border: none !important; box-shadow: none !important;
    justify-content: flex-start !important; padding: 6px 8px !important; min-height: 0 !important; border-radius: 8px !important;
}
[data-testid="stPopoverBody"]:has(.pop-hist) button > div{ justify-content: flex-start !important; }
[data-testid="stPopoverBody"]:has(.pop-hist) button p{ font-size: 13px !important; color: var(--text-2) !important; }
[data-testid="stPopoverBody"]:has(.pop-hist) button:hover{ background: var(--bg-raised) !important; }
[data-testid="stPopoverBody"]:has(.pop-hist) div[class*="st-key-dangerzone_h"] button p,
[data-testid="stPopoverBody"]:has(.pop-hist) div[class*="st-key-dangerzone_h"] button [data-testid="stIconMaterial"]{ color: var(--danger) !important; }
[data-testid="stPopoverBody"]:has(.pop-hist) input{ font-size: 12.5px !important; min-height: 32px; padding: 4px 8px !important; }

/* Deep Research map: smaller cards */
.rp{ padding: 10px 12px 8px 12px !important; }
.am-col{ gap: 4px; }
.am-node{ padding: 4px 8px 4px 4px; border-radius: 9px; gap: 6px; }
.am-ic.material-symbols-outlined{ width: 22px; height: 22px; font-size: 13px; border-radius: 7px; }
.am-title{ font-size: 11.5px; }
.am-sub{ font-size: 10px; max-width: 170px; }
.am-fan{ min-width: 150px; max-width: 250px; }
.am-edge{ flex-basis: 16px; }
.rp-status{ margin-top: 6px !important; font-size: 12px !important; }
@container amap (max-width: 700px){
    .am-fan{ max-width: none; }
    .am-sub, .am-col:not(.am-fan) .am-sub{ max-width: none; }
}

/* ---------- ROUND 3: centred welcome, account card, answer alignment ---------- */
/* W1: the welcome sits in the middle of the space above the message box on any screen height */
.hero{ padding-top: max(1vh, calc(36vh - 260px)) !important; }

/* A2: account menu = soft blue header card, then memory, then two even buttons */
[data-testid="stPopoverBody"]:has(.acct-head){ padding: 0 0 12px 0 !important; overflow: hidden; }
[data-testid="stPopoverBody"]:has(.acct-head) [data-testid="stVerticalBlock"]{ gap: .5rem; }
.acct-head{ background: linear-gradient(135deg, #16264a, #121a2e); padding: 14px 16px !important;
    border-bottom: 1px solid #22304d; }
.acct-head .user-name{ font-size: 14px; }
.acct-head .user-handle{ color: #9dc0ff; font-size: 11.5px; }
.acct-mem{ font-size: 12px; color: var(--text-4); padding: 2px 16px; }
[data-testid="stPopoverBody"]:has(.acct-head) .menu-label,
[data-testid="stPopoverBody"]:has(.acct-head) .mem-item{ padding-left: 16px; padding-right: 16px; }
div[class*="st-key-acct_btns"]{ padding: 0 12px; }
div[class*="st-key-acct_btns"] > div{ flex: 1 1 0 !important; min-width: 0; }   /* two equal buttons */
div[class*="st-key-acct_btns"] button{
    min-height: 34px !important; padding: 4px 10px !important; border-radius: 10px !important;
    background: transparent !important; border: 1px solid var(--border-strong) !important; box-shadow: none !important;
}
div[class*="st-key-acct_btns"] button p{ font-size: 12.5px !important; color: var(--text-2) !important; }
div[class*="st-key-acct_btns"] div[class*="st-key-guest_signup"] button{ border-color: rgba(79,142,247,.5) !important; background: var(--accent-soft) !important; }
div[class*="st-key-acct_btns"] div[class*="st-key-guest_signup"] button p,
div[class*="st-key-acct_btns"] div[class*="st-key-guest_signup"] button [data-testid="stIconMaterial"]{ color: #cfe0ff !important; }
div[class*="st-key-acct_btns"] button:hover{ border-color: var(--accent) !important; }

/* R2: the eye lines up with the first line of the answer (its box takes no room), and the trace
   is a small line under the answer, just above Copy / Share */
div[class*="st-key-ai_msg_"] [data-testid="stElementContainer"]:has(.ai-head){
    display: block !important; position: absolute !important; left: 0; top: -1px; width: auto !important; margin: 0 !important;
}
.ai-head{ position: static !important; }
.stMain [data-testid="stExpander"]:has([data-testid="stExpanderIconCheck"], [data-testid="stExpanderIconSpinner"]){ margin-top: -10px; }

/* phone-only mode chips on the welcome screen */
.stMain [data-testid="stLayoutWrapper"]:has(> div[class*="st-key-mode_chips"]){ display: none; }
div[class*="st-key-mode_chips"] button{
    background: transparent !important; border: 1px solid var(--border-strong) !important; border-radius: 999px !important;
    padding: 3px 11px !important; min-height: 0 !important; box-shadow: none !important;
}
div[class*="st-key-mode_chips"] button p{ font-size: 12px !important; color: var(--text-2) !important; }
div[class*="st-key-mode_chips"] button [data-testid="stIconMaterial"]{ font-size: 15px !important; color: var(--accent-2) !important; }
@media (max-width: 640px){
    .stMain [data-testid="stLayoutWrapper"]:has(> div[class*="st-key-mode_chips"]){ display: block; margin: -6px 0 6px 0; }
    div[class*="st-key-mode_chips"]{ flex-wrap: wrap !important; justify-content: center; }
    .hero .caps{ display: none; }      /* on phones the tappable mode chips replace the info-only tags */
}

/* "Get another digest" pills under a news report */
div[class*="st-key-newsagain_row"]{ flex-wrap: wrap !important; margin-left: 38px; width: calc(100% - 38px) !important; }
div[class*="st-key-newsagain_row"] button{
    background: transparent !important; border: 1px solid var(--border-strong) !important; border-radius: 999px !important;
    padding: 4px 12px !important; min-height: 0 !important; box-shadow: none !important;
}
div[class*="st-key-newsagain_row"] button p{ font-size: 12.5px !important; color: var(--text-2) !important; }
div[class*="st-key-newsagain_row"] button [data-testid="stIconMaterial"]{ font-size: 16px !important; color: var(--accent-2) !important; }
div[class*="st-key-newsagain_row"] button:hover{ border-color: var(--accent) !important; }

/* PDF page chips: the pages the answer cites first; the others it looked at are quieter */
.cite-also-label{ margin-left: 8px; }
.cite-chip.also summary{ background: transparent; border-color: var(--border-strong); color: var(--text-3); font-weight: 500; }
.cite-chip.also summary .material-symbols-outlined{ color: var(--text-4); }

/* ---------- EVERY SCREEN SIZE ---------- */
/* touch screens can't hover: keep the hover-only controls visible */
@media (hover: none){
    div[class*="st-key-histitem_"] [data-testid="stPopover"]{ opacity: .75; }
    div[class*="st-key-msgactions_"], div[class*="st-key-turn_"] div[class*="st-key-msgactions_"]{ opacity: .85 !important; }
}
/* big monitors: a little more reading width */
@media (min-width: 1600px){ .block-container{ max-width: 1080px; } }
/* tablets and small laptops: a little less side padding so the chat keeps its room */
@media (min-width: 641px) and (max-width: 1100px){
    .block-container{ padding-left: 2rem !important; padding-right: 2rem !important; }
}

/* ---------- PHONES ---------- */
@media (max-width: 640px){
    section[data-testid="stSidebar"][data-collapsed="false"]{ width: min(86vw, 320px) !important; min-width: min(86vw, 320px) !important; }
    div[class*="st-key-ai_msg_"]{ padding-left: 32px !important; }
    div[class*="st-key-ai_msg_"]:has(.thinking) .thinking{ margin-left: -32px; }
    .stMain [data-testid="stExpander"], .src-row, .cite-row{ margin-left: 32px !important; }
    .stMain [data-testid="stExpander"], div[class*="st-key-msgactions_"]{ width: calc(100% - 32px) !important; }
    div[class*="st-key-msgactions_"]{ margin-left: 32px !important; }
    .bubble-user{ max-width: 85% !important; }
    .src-row .src-pill{ max-width: 170px; }
    .block-container{ padding-top: 3.4rem !important; padding-left: 14px !important; padding-right: 14px !important; }
    div[class*="st-key-topbar"]{ margin-top: -2.4rem; }        /* level with the sidebar arrow */
    .topbar-mode{ font-size: 12.5px; padding-left: 40px; }      /* clear of the sidebar arrow */
    .topbar-mode .chip{ display: none; }
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
