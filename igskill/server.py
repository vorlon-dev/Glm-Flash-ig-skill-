"""FastAPI server + dashboard — the user's mission control.

Run:  python scripts/ig_server.py   ->  http://127.0.0.1:8790
Endpoints: /api/status /api/queue /api/slots /api/autopilot /api/analytics /api/consent
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .analytics import report, snapshot
from .autopilot import build_plan, execute_plan
from .config import load_config
from .privacy import VALID_SCOPES, consent_report, grant_consent, revoke_consent
from .scheduler import add_to_queue, best_slots, cancel_queued, list_queue, run_due

app = FastAPI(title="Glm-Flash IG Viral Manager", version="1.0.0")
cfg = load_config()  # zero-config: always loadable, no .env required


class QueueIn(BaseModel):
    media_path: str
    caption: str = ""
    hashtags: list[str] = []
    post_type: str = "reel"
    scheduled_at: str | None = None


class AutopilotIn(BaseModel):
    niche: str
    count: int = 7
    media_dir: str | None = None


class ConsentIn(BaseModel):
    scope: str
    note: str = ""
    grant: bool = True


@app.get("/api/status")
def status():
    q = list_queue(cfg)
    info = {"mode": cfg.resolved_mode, "timezone": cfg.timezone,
            "niche": cfg.niche, "state_dir": ".state/ (local only)",
            "connection": cfg.connected_hint(),
            "queued": sum(1 for i in q if i["status"] == "queued"),
            "posted": sum(1 for i in q if i["status"] == "posted"),
            "max_posts_per_day": cfg.max_posts_per_day,
            "consent": consent_report(cfg)}
    try:
        from .ig_client import get_client
        info["profile"] = get_client(cfg).profile()
        info["connected"] = True
    except Exception as e:
        info["connected"] = False
        info["connect_hint"] = str(e)[:200]
    return info


@app.get("/api/queue")
def get_queue():
    return list_queue(cfg)


@app.post("/api/queue")
def post_queue(item: QueueIn):
    if not Path(item.media_path).exists():
        raise HTTPException(400, f"media not found: {item.media_path}")
    qid = add_to_queue(cfg, item.media_path,
                       {"caption": item.caption, "hashtags": item.hashtags,
                        "post_type": item.post_type},
                       item.post_type, item.scheduled_at)
    return {"ok": True, "queue_id": qid}


@app.delete("/api/queue/{qid}")
def delete_queue(qid: int):
    if not cancel_queued(cfg, qid):
        raise HTTPException(404, f"queue #{qid} not cancelable (not queued?)")
    return {"ok": True}


@app.post("/api/queue/run-due")
def run_now():
    return {"results": run_due(cfg)}


@app.get("/api/slots")
def slots(post_type: str = "reel", days: int = 7):
    return best_slots(cfg, post_type, days)


@app.post("/api/autopilot/plan")
def autopilot_plan(body: AutopilotIn):
    plan = build_plan(cfg, body.niche, body.count, media_dir=body.media_dir)
    return {"ok": True, "plan_file": str(plan),
            "preview": json.loads(plan.read_text(encoding="utf-8"))}


@app.post("/api/autopilot/run")
def autopilot_run():
    return {"results": execute_plan(cfg)}


@app.get("/api/analytics")
def analytics():
    return {"report": report(cfg)}


@app.post("/api/analytics/snapshot")
def analytics_snapshot():
    try:
        return {"ok": True, "saved": snapshot(cfg)}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/consent")
def consent(body: ConsentIn):
    if body.scope not in VALID_SCOPES:
        raise HTTPException(400, f"scope must be one of {sorted(VALID_SCOPES)}")
    if body.grant:
        grant_consent(body.scope, body.note, cfg)
    else:
        revoke_consent(body.scope, cfg)
    return {"ok": True, "status": consent_report(cfg)}


# ------------------------------------------------------------------ UI ----

DASH = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>IG Viral Manager</title><style>
*{box-sizing:border-box;margin:0}
body{background:#0b0b16;color:#e8e8f2;font-family:'Segoe UI',system-ui,sans-serif;padding:24px}
h1{font-size:26px;background:linear-gradient(90deg,#f06,#fa0,#f6c);-webkit-background-clip:text;color:transparent;margin-bottom:4px}
.sub{color:#8888a8;font-size:13px;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:22px}
.card{background:#14142588;border:1px solid #2a2a4a;border-radius:16px;padding:18px}
.card h3{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:#8f8fb8;margin-bottom:10px}
.big{font-size:30px;font-weight:700}
.ok{color:#4ade80}.warn{color:#fbbf24}
button{background:linear-gradient(90deg,#e11d6f,#f59e0b);border:0;color:#fff;padding:9px 16px;border-radius:10px;font-weight:600;cursor:pointer;font-size:13px}
button.ghost{background:#23233d}input,select{background:#1b1b30;border:1px solid #33335a;color:#e8e8f2;padding:8px 10px;border-radius:8px;font-size:13px;width:100%}
.row{display:flex;gap:8px;margin:8px 0;flex-wrap:wrap}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:#8f8fb8;text-align:left;padding:6px;font-weight:600}td{padding:7px 6px;border-top:1px solid #232344}
pre{background:#10101f;border-radius:12px;padding:14px;font-size:12px;overflow:auto;white-space:pre-wrap;color:#c9c9e6;max-height:340px}
.x{color:#f66;cursor:pointer;font-weight:700}.pill{padding:2px 9px;border-radius:99px;font-size:11px;background:#23234a}
.tag{font-size:11px;color:#f0abfc}.sec{margin-bottom:26px}
label{font-size:11px;color:#8f8fb8;display:block;margin-bottom:3px}
</style></head><body>
<h1>⚡ IG Viral Manager</h1><div class=sub>Glm-Flash-ig-skill · mission control — the AI plans, edits & posts, you stay in control</div>

<div class=grid id=stats></div>

<div class="card sec"><h3>Content queue</h3>
<table id=queue><tr><th>#</th><th>when</th><th>type</th><th>caption</th><th>status</th><th></th></tr></table>
<div class=row><button class=ghost onclick=runDue()>▶ Run due now</button>
<button class=ghost onclick=snap()>📸 Analytics snapshot</button></div></div>

<div class=grid>
<div class=card><h3>🚀 Autopilot</h3>
<label>Niche</label><input id=niche placeholder="street food">
<label>Posts this week</label><input id=count type=number value=7 style=width:80px>
<div class=row><button onclick=plan()>1. Generate plan</button><button class=ghost onclick=runPlan()>2. Execute plan</button></div>
<div class=tag id=planmsg>Plan shows to user first — full-auto needs consent (right).</div></div>

<div class=card><h3>🛡 Privacy consent</h3><div id=consent></div></div>

<div class=card><h3>📈 What worked</h3><pre id=report>press snapshot / open /api/analytics</pre></div>
</div>

<script>
async function j(u,o){const r=await fetch(u,o);if(!r.ok){const e=await r.json().catch(()=>({detail:r.statusText}));throw new Error(e.detail||'error')}return r.json()}
async function status(){const s=await j('/api/status');
document.getElementById('stats').innerHTML=
 card('Engine',s.mode+(s.connected?' <span class=ok>●</span>':' <span class=warn>○ not connected</span>'))+
 card('Queued / posted',s.queued+' / '+s.posted)+
 card('Daily cap',s.max_posts_per_day+' posts')+
 card('Niche',s.niche||'—')+(s.profile?card('Followers',(s.profile.followers_count??'—')):'');
document.getElementById('consent').innerHTML=s.consent.split('\\n').slice(1).map(l=>{const[n,st]=l.trim().split(/\\s+/);const on=st==='GRANTED';
return `<div class=row><span style="flex:1">${n}</span><button class=ghost style="padding:3px 10px" onclick="toggleConsent('${n}',${on})">${on?'on':'off'}</button></div>`}).join('')}
const card=(k,v)=>`<div class=card><h3>${k}</h3><div class=big>${v}</div></div>`;
async function queue(){const q=await j('/api/queue');const t=document.getElementById('queue');
t.innerHTML='<tr><th>#</th><th>when</th><th>type</th><th>caption</th><th>status</th><th></th></tr>'+
q.map(i=>`<tr><td>${i.id}</td><td>${i.scheduled_at}</td><td><span class=pill>${i.post_type}</span></td><td>${(JSON.parse(i.content_json).caption||'').slice(0,42)}…</td><td>${i.status}</td><td>${i.status==='queued'?`<span class=x onclick="cancel(${i.id})">✕</span>`:''}</td></tr>`).join('')}
async function plan(){try{const n=niche.value||'general';const r=await j('/api/autopilot/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({niche:n,count:+count.value})});document.getElementById('planmsg').textContent=r.plan_file+' — review then execute'}catch(e){alert(e.message)}}
async function runPlan(){try{const r=await j('/api/autopilot/run',{method:'POST'});alert(r.results.length+' items queued')}catch(e){alert(e.message)}}
async function runDue(){await j('/api/queue/run-due',{method:'POST'});queue();status()}
async function snap(){try{await j('/api/analytics/snapshot',{method:'POST'})}catch(e){}const a=await j('/api/analytics');document.getElementById('report').textContent=a.report}
async function cancel(id){await fetch('/api/queue/'+id,{method:'DELETE'});queue();status()}
async function toggleConsent(scope,on){await j('/api/consent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scope,grant:!on,note:'dashboard toggle by user'})});status()}
status();queue();setInterval(status,15000)
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASH


if __name__ == "__main__":
    import uvicorn
    print(f"dashboard -> http://{cfg.host}:{cfg.port}")
    uvicorn.run(app, host=cfg.host, port=cfg.port)
