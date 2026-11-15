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
    width: 264px !important; min-width: 264px !important;
}
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

/* Nav items */
div[class*="st-key-navitem_"] button{
    background: transparent !important; border: none !important;
    justify-content: flex-start !important; padding: 7px 10px !important;
    border-radius: 10px !important; min-height: 0 !important;
}
div[class*="st-key-navitem_"] button p,
div[class*="st-key-navitem_"] button span{ color: var(--text-3) !important; font-weight:500; font-size:13.5px; }
div[class*="st-key-navitem_"] button [data-testid="stIconMaterial"]{ color: var(--text-4) !important; }
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
div[class*="st-key-histitem_on_"] button{ background: var(--surface-2) !important; box-shadow: inset 2px 0 0 var(--accent); }
div[class*="st-key-histitem_on_"] button p{ color: #fff !important; }

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

div[class*="st-key-starter_"] button{
    background: linear-gradient(180deg, var(--surface), var(--bg-raised)) !important;
    border: 1px solid var(--border) !important; border-radius: 14px !important;
    justify-content: flex-start !important; text-align: left !important;
    padding: 12px 16px !important; min-height: 52px; transition: all .18s ease;
}
div[class*="st-key-starter_"] button p{ color: var(--text-2) !important; font-size: 13.5px !important; }
div[class*="st-key-starter_"] button [data-testid="stIconMaterial"]{ color: var(--accent) !important; }
div[class*="st-key-starter_"] button:hover{
    border-color: rgba(79,142,247,.55) !important; transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(0,0,0,.45), 0 0 0 3px var(--accent-glow);
}
div[class*="st-key-starter_"] button:hover p{ color: var(--text) !important; }

/* ---------- MESSAGES ---------- */
.msg-user{ display:flex; justify-content:flex-end; margin: 10px 0 12px 0; }
.bubble-user{
    max-width: 78%; padding: 10px 15px; font-size: 14px; line-height: 1.55;
    background: linear-gradient(135deg, #1a4fb3, #12347a);
    border: 1px solid rgba(122,169,255,.35); color: #eef4ff;
    border-radius: 16px 16px 4px 16px; box-shadow: 0 6px 20px rgba(26,79,179,.18);
}
/* Assistant answers: clean text on the page (no heavy box), like modern AI chat apps */
div[class*="st-key-ai_msg_"]{
    background: transparent; border: none;
    padding: 2px 4px 0 4px; margin: 8px 0 0 0;
}
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
div[class*="st-key-ai_msg_"] code{
    background: #1a1a20 !important; color: #cfe0ff !important; border-radius: 6px; padding: 2px 6px;
}
div[class*="st-key-ai_msg_"] table{ border-collapse: collapse; width:100%; font-size:13px; }
div[class*="st-key-ai_msg_"] th, div[class*="st-key-ai_msg_"] td{ border: 1px solid var(--border-strong) !important; padding: 6px 10px; }
div[class*="st-key-ai_msg_"] th{ background: var(--surface-2); color: var(--text); }
div[class*="st-key-ai_msg_"] blockquote{ border-left: 3px solid var(--accent); color: var(--text-3); padding-left: 12px; }

/* message actions row: quiet until hovered */
div[class*="st-key-msgactions_"]{ margin: -4px 0 18px 4px; opacity: .45; transition: opacity .15s ease; }
div[class*="st-key-msgactions_"]:hover{ opacity: 1; }
div[class*="st-key-msgactions_"] button{
    background: transparent !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text-3) !important; font-size: 12px !important;
    min-height: 0 !important; padding: 3px 10px !important;
}
div[class*="st-key-msgactions_"] button:hover{ border-color: var(--accent) !important; color: var(--text) !important; }

/* thinking dots */
.thinking-dots{ display:flex; gap:6px; padding: 8px 0 10px 2px; }
.thinking-dots span{
    width:7px; height:7px; border-radius:50%; background: var(--accent);
    animation: tdBounce 1.2s infinite ease-in-out;
}
.thinking-dots span:nth-child(2){ animation-delay:.15s; }
.thinking-dots span:nth-child(3){ animation-delay:.3s; }
@keyframes tdBounce{ 0%,80%,100%{ transform:scale(.6); opacity:.4; } 40%{ transform:scale(1); opacity:1; } }

/* agent trace (st.status) */
[data-testid="stExpander"] [data-testid="stExpanderDetails"] p{ font-size: 12.5px !important; color: var(--text-2) !important; }

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
</style>
"""
