from flask import Flask, request, jsonify, Response
import urllib.request
import urllib.parse
import urllib.error
import json
import time

app = Flask(__name__)

GUILD_BASE = "https://flash-guild-management.vercel.app"
PLAYER_BASE = "https://flash-player-info-v1.vercel.app"
BRAND = "XORE"
API_BY = "@FL4SH_FF"
VERSION = "2.0.0"

# ============================================================
#  HELPERS
# ============================================================
def fetch_json(url, timeout=20):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (XORE-FLASH-HUB)",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw), r.status
            except Exception:
                return {"raw": raw}, r.status
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body), e.code
            except Exception:
                return {"error": f"HTTP {e.code}", "details": body[:500]}, e.code
        except Exception:
            return {"error": f"HTTP {e.code}", "details": e.reason}, e.code
    except urllib.error.URLError as e:
        return {"error": "Connection failed", "details": str(e.reason)}, 502
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}, 500


def build_url(base, path, params):
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def wrap(data, status, endpoint, elapsed):
    return {
        "brand": BRAND,
        "api_by": API_BY,
        "version": VERSION,
        "endpoint": endpoint,
        "response_time_ms": round(elapsed * 1000, 2),
        "status_code": status,
        "data": data
    }, status


# ============================================================
#  HOME PAGE
# ============================================================
@app.route("/", methods=["GET"])
def home():
    return Response(HTML_PAGE, mimetype="text/html")


# ============================================================
#  HEALTH
# ============================================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "brand": BRAND,
        "api_by": API_BY,
        "version": VERSION,
        "uptime": "running",
        "endpoints": ENDPOINTS_LIST,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    })


@app.route("/endpoints", methods=["GET"])
def endpoints():
    return jsonify({
        "brand": BRAND,
        "api_by": API_BY,
        "total": len(ENDPOINTS_LIST),
        "endpoints": ENDPOINTS_LIST
    })


# ============================================================
#  GUILD MANAGEMENT PROXY
# ============================================================
def guild_proxy(path):
    t0 = time.time()
    params = request.args.to_dict()
    if not params:
        return jsonify({"error": "لا توجد باراميترات", "brand": BRAND}), 400
    url = build_url(GUILD_BASE, path, params)
    data, status = fetch_json(url)
    return wrap(data, status, path, time.time() - t0)


@app.route("/token", methods=["GET"])
def ep_token(): return guild_proxy("/token")

@app.route("/clan_info", methods=["GET"])
def ep_clan_info(): return guild_proxy("/clan_info")

@app.route("/request_clan", methods=["GET"])
def ep_request_clan(): return guild_proxy("/request_clan")

@app.route("/quit_clan", methods=["GET"])
def ep_quit_clan(): return guild_proxy("/quit_clan")


# ============================================================
#  PLAYER PROXY (needs uid+pwd in path, target in query)
# ============================================================
def player_proxy(endpoint):
    t0 = time.time()
    uid = request.args.get("uid")
    pwd = request.args.get("pwd") or request.args.get("password")
    if not uid or not pwd:
        return jsonify({"error": "uid و pwd مطلوبان", "brand": BRAND}), 400

    query = {}
    if "target_uid" in request.args:
        query["uid"] = request.args.get("target_uid")
    elif "name" in request.args:
        query["name"] = request.args.get("name")
    else:
        return jsonify({"error": "target_uid أو name مطلوب", "brand": BRAND}), 400

    url = f"{PLAYER_BASE}/{uid}/{pwd}/{endpoint}?" + urllib.parse.urlencode(query)
    data, status = fetch_json(url)
    return wrap(data, status, endpoint, time.time() - t0)


@app.route("/player-info", methods=["GET"])
def ep_player_info(): return player_proxy("player-info")

@app.route("/bancheck", methods=["GET"])
def ep_bancheck(): return player_proxy("bancheck")

@app.route("/stats-info", methods=["GET"])
def ep_stats_info(): return player_proxy("stats-info")

@app.route("/level", methods=["GET"])
def ep_level(): return player_proxy("level")

@app.route("/region", methods=["GET"])
def ep_region(): return player_proxy("region")

@app.route("/wishlist", methods=["GET"])
def ep_wishlist(): return player_proxy("wishlist")

@app.route("/workshop-info", methods=["GET"])
def ep_workshop(): return player_proxy("workshop-info")

@app.route("/duo-info", methods=["GET"])
def ep_duo(): return player_proxy("duo-info")


# ============================================================
#  STATS MODE-WISE
# ============================================================
@app.route("/stats", methods=["GET"])
def ep_stats():
    t0 = time.time()
    uid = request.args.get("uid")
    pwd = request.args.get("pwd") or request.args.get("password")
    mm = request.args.get("matchmode", "CAREER").upper()
    gm = request.args.get("gamemode", "BR").upper()
    target_uid = request.args.get("target_uid")
    name = request.args.get("name")

    if not uid or not pwd:
        return jsonify({"error": "uid و pwd مطلوبان", "brand": BRAND}), 400
    if not target_uid and not name:
        return jsonify({"error": "target_uid أو name مطلوب", "brand": BRAND}), 400
    if mm not in ("CAREER", "RANKED", "NORMAL"):
        return jsonify({"error": "matchmode يجب أن يكون CAREER/RANKED/NORMAL"}), 400
    if gm not in ("BR", "CS"):
        return jsonify({"error": "gamemode يجب أن يكون BR/CS"}), 400

    query = {"uid": target_uid} if target_uid else {"name": name}
    url = f"{PLAYER_BASE}/{uid}/{pwd}/STATS/{mm}/{gm}?" + urllib.parse.urlencode(query)
    data, status = fetch_json(url)
    return wrap(data, status, f"/STATS/{mm}/{gm}", time.time() - t0)


# ============================================================
#  ERROR HANDLERS
# ============================================================
@app.errorhandler(404)
def e404(e):
    return jsonify({"error": "Endpoint not found", "brand": BRAND,
                    "available": ENDPOINTS_LIST}), 404

@app.errorhandler(405)
def e405(e):
    return jsonify({"error": "Method not allowed", "brand": BRAND}), 405

@app.errorhandler(500)
def e500(e):
    return jsonify({"error": "Internal server error", "brand": BRAND}), 500


# ============================================================
#  ENDPOINTS LIST
# ============================================================
ENDPOINTS_LIST = [
    {"method": "GET", "path": "/", "desc": "الصفحة الرئيسية"},
    {"method": "GET", "path": "/health", "desc": "فحص حالة السيرفر"},
    {"method": "GET", "path": "/endpoints", "desc": "قائمة كل الـ endpoints"},

    {"method": "GET", "path": "/token", "desc": "الحصول على التوكن",
     "params": "uid+password | access_token | eat"},

    {"method": "GET", "path": "/clan_info", "desc": "معلومات السيرفر",
     "params": "clan_id + (jwt|uid+password|access_token|eat)"},

    {"method": "GET", "path": "/request_clan", "desc": "طلب انضمام للسيرفر",
     "params": "clan_id + (jwt|uid+password|access_token|eat)"},

    {"method": "GET", "path": "/quit_clan", "desc": "مغادرة السيرفر",
     "params": "clan_id + (jwt|uid+password|access_token|eat)"},

    {"method": "GET", "path": "/player-info", "desc": "معلومات اللاعب",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/bancheck", "desc": "فحص الحظر",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/stats-info", "desc": "ملخص الإحصائيات",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/stats", "desc": "إحصائيات حسب الوضع",
     "params": "uid+pwd+matchmode+gamemode + (target_uid|name)"},

    {"method": "GET", "path": "/level", "desc": "مستوى اللاعب",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/region", "desc": "منطقة اللاعب",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/wishlist", "desc": "قائمة المفضلة",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/workshop-info", "desc": "الورشة",
     "params": "uid+pwd + (target_uid|name)"},

    {"method": "GET", "path": "/duo-info", "desc": "معلومات الثنائي",
     "params": "uid+pwd + (target_uid|name)"},
]


# ============================================================
#  HTML PAGE
# ============================================================
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ FLASH API HUB | XORE</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{
  --red:#ff1e1e;--red2:#ff3b3b;--red-dark:#8b0000;--red-soft:rgba(255,30,30,.12);
  --black:#050505;--dark:#0f0f0f;--dark2:#161616;--dark3:#1e1e1e;
  --gray:#888;--text:#eaeaea;
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
html{scroll-behavior:smooth;}
body{
  font-family:'Cairo',sans-serif;color:var(--text);overflow-x:hidden;
  background:
    radial-gradient(ellipse at top left, rgba(255,30,30,.18), transparent 45%),
    radial-gradient(ellipse at bottom right, rgba(255,30,30,.14), transparent 50%),
    var(--black);
  min-height:100vh;
}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    linear-gradient(rgba(255,30,30,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,30,30,.035) 1px, transparent 1px);
  background-size:44px 44px;
  mask-image:radial-gradient(ellipse at center, #000 20%, transparent 80%);
}

/* TOP BAR */
.top{
  position:fixed;top:0;left:0;right:0;z-index:100;
  background:rgba(5,5,5,.88);backdrop-filter:blur(14px);
  border-bottom:2px solid var(--red);
  padding:13px 22px;display:flex;align-items:center;justify-content:space-between;
}
.top .logo{
  font-family:'Orbitron',sans-serif;font-weight:900;font-size:1.35rem;
  color:#fff;letter-spacing:3px;display:flex;align-items:center;gap:10px;
}
.top .logo .zap{color:var(--red);animation:zap 2s infinite;font-size:1.5rem;}
@keyframes zap{0%,100%{text-shadow:0 0 10px var(--red);}50%{text-shadow:0 0 25px var(--red2),0 0 40px var(--red);}}
.top .logo span{color:var(--red);text-shadow:0 0 15px var(--red);}
.top .right{display:flex;gap:10px;align-items:center;}
.pill{
  padding:6px 14px;border-radius:20px;font-size:.75rem;font-weight:700;
  border:1px solid rgba(255,30,30,.4);
}
.pill.live{
  background:linear-gradient(135deg,var(--red),var(--red-dark));
  box-shadow:0 0 15px rgba(255,30,30,.5);
  display:flex;align-items:center;gap:6px;
}
.pill.live::before{content:'';width:7px;height:7px;border-radius:50%;background:#0f0;box-shadow:0 0 8px #0f0;animation:pulse 1.5s infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.3;}}
.pill.brand-xore{background:transparent;color:var(--red);letter-spacing:2px;font-family:'Orbitron',sans-serif;}

/* HERO */
.hero{padding:130px 20px 40px;text-align:center;position:relative;z-index:1;}
.hero .tag{
  display:inline-block;padding:6px 18px;border-radius:30px;
  border:1px solid rgba(255,30,30,.35);background:rgba(255,30,30,.06);
  font-size:.8rem;font-weight:700;color:var(--red);margin-bottom:22px;
  letter-spacing:2px;
}
.hero h1{
  font-family:'Orbitron',sans-serif;font-size:clamp(2.2rem,6.5vw,4.5rem);
  font-weight:900;line-height:1.1;margin-bottom:16px;
  background:linear-gradient(135deg,#fff 10%,var(--red2) 55%,var(--red-dark) 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  animation:glow 3s ease-in-out infinite alternate;
}
@keyframes glow{from{filter:drop-shadow(0 0 12px rgba(255,30,30,.4));}to{filter:drop-shadow(0 0 28px rgba(255,30,30,.9));}}
.hero p{color:#aaa;font-size:1.02rem;max-width:680px;margin:0 auto;line-height:1.7;}
.divider{width:100px;height:3px;margin:24px auto;background:linear-gradient(90deg,transparent,var(--red),transparent);border-radius:3px;}

/* STATS BAR */
.stats{
  display:grid;grid-template-columns:repeat(2,1fr);gap:12px;
  max-width:700px;margin:30px auto 0;padding:0 20px;position:relative;z-index:1;
}
@media(min-width:600px){.stats{grid-template-columns:repeat(4,1fr);}}
.stat{
  background:linear-gradient(145deg,var(--dark2),var(--dark));
  border:1px solid rgba(255,30,30,.2);border-radius:12px;
  padding:14px;text-align:center;
}
.stat .num{font-family:'Orbitron',sans-serif;font-size:1.5rem;font-weight:900;color:var(--red);text-shadow:0 0 12px rgba(255,30,30,.5);}
.stat .lbl{font-size:.72rem;color:var(--gray);margin-top:4px;font-weight:600;}

/* TABS */
.tabs{
  display:flex;flex-wrap:wrap;justify-content:center;gap:8px;
  padding:16px;position:sticky;top:62px;z-index:50;
  background:rgba(5,5,5,.75);backdrop-filter:blur(12px);
  border-bottom:1px solid rgba(255,30,30,.15);margin-top:20px;
}
.tab{
  padding:9px 18px;border-radius:30px;border:1px solid rgba(255,30,30,.3);
  background:rgba(255,30,30,.05);color:#bbb;font-weight:700;cursor:pointer;
  transition:.25s;font-family:'Cairo',sans-serif;font-size:.85rem;
  display:flex;align-items:center;gap:6px;
}
.tab:hover{background:rgba(255,30,30,.15);color:#fff;transform:translateY(-1px);}
.tab.active{
  background:linear-gradient(135deg,var(--red),var(--red-dark));
  color:#fff;border-color:var(--red);
  box-shadow:0 0 20px rgba(255,30,30,.55);
}

/* CONTAINER */
.container{max-width:1200px;margin:0 auto;padding:32px 20px 80px;position:relative;z-index:1;}
.section{display:none;animation:fadeUp .5s ease;}
.section.active{display:block;}
@keyframes fadeUp{from{opacity:0;transform:translateY(18px);}to{opacity:1;transform:translateY(0);}}
.section-title{
  font-family:'Orbitron',sans-serif;font-size:1.5rem;font-weight:900;
  color:#fff;margin-bottom:6px;display:flex;align-items:center;gap:12px;
}
.section-title .icon{
  width:46px;height:46px;border-radius:12px;display:grid;place-items:center;font-size:1.35rem;
  background:linear-gradient(135deg,var(--red),var(--red-dark));
  box-shadow:0 0 22px rgba(255,30,30,.5);flex-shrink:0;
}
.section-desc{color:var(--gray);margin-bottom:24px;font-size:.92rem;}

/* GRID & CARDS */
.grid{display:grid;gap:18px;grid-template-columns:1fr;}
@media(min-width:768px){.grid{grid-template-columns:1fr 1fr;}}
@media(min-width:1100px){.grid.cols-3{grid-template-columns:repeat(3,1fr);}}
.card{
  background:linear-gradient(145deg,var(--dark2),var(--dark));
  border:1px solid rgba(255,30,30,.18);border-radius:16px;padding:20px;
  position:relative;overflow:hidden;transition:.3s;
}
.card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,transparent,var(--red),transparent);opacity:.8;
}
.card:hover{
  border-color:rgba(255,30,30,.55);transform:translateY(-4px);
  box-shadow:0 14px 45px rgba(255,30,30,.15);
}
.card-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;}
.emoji{
  width:42px;height:42px;border-radius:11px;display:grid;place-items:center;font-size:1.25rem;
  background:rgba(255,30,30,.12);border:1px solid rgba(255,30,30,.3);flex-shrink:0;
}
.card h3{font-size:1rem;font-weight:900;color:#fff;font-family:'Orbitron',sans-serif;letter-spacing:.5px;}
.card h3 small{display:block;color:var(--red);font-size:.68rem;letter-spacing:1.5px;margin-top:3px;font-family:'Cairo',sans-serif;}
.ep{
  display:block;background:#000;border:1px solid rgba(255,30,30,.22);
  border-radius:8px;padding:10px 12px;font-family:'JetBrains Mono',monospace;
  font-size:.75rem;color:#ffb3b3;margin-bottom:8px;
  position:relative;transition:.2s;word-break:break-all;
}
.ep:hover{border-color:var(--red);background:#0d0000;color:#fff;}
.ep .method{
  display:inline-block;padding:1px 6px;border-radius:4px;margin-left:6px;
  background:rgba(0,255,0,.15);color:#0f0;font-size:.6rem;font-weight:700;
  font-family:'Cairo',sans-serif;
}
.ep .copy{
  position:absolute;top:6px;left:6px;background:var(--red);border:none;
  color:#fff;padding:2px 7px;border-radius:4px;font-size:.6rem;cursor:pointer;
  font-weight:700;opacity:0;transition:.2s;font-family:'Cairo',sans-serif;
}
.ep:hover .copy{opacity:1;}
.ep .copy:hover{background:var(--red2);}
.note{font-size:.78rem;color:#999;margin-top:6px;display:flex;gap:6px;align-items:flex-start;}
.note strong{color:var(--red);}
.example{
  margin-top:10px;padding:9px 11px;border-right:3px solid var(--red);
  background:rgba(255,30,30,.05);border-radius:6px;
  font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#ddd;
  word-break:break-all;line-height:1.6;
}
.example::before{content:'مثال ⟶ ';color:var(--red);font-weight:700;font-family:'Cairo',sans-serif;}

/* TESTER */
.tester{
  background:linear-gradient(145deg,var(--dark2),var(--dark));
  border:1px solid rgba(255,30,30,.3);border-radius:18px;padding:24px;
  max-width:900px;margin:0 auto;
}
.tester h2{
  font-family:'Orbitron',sans-serif;font-size:1.3rem;color:#fff;
  margin-bottom:6px;display:flex;align-items:center;gap:10px;
}
.tester p.sub{color:var(--gray);font-size:.85rem;margin-bottom:20px;}
.tester .row{display:grid;gap:12px;margin-bottom:14px;}
@media(min-width:600px){.tester .row{grid-template-columns:1fr 1fr;}}
.tester label{font-size:.8rem;color:var(--red);font-weight:700;display:block;margin-bottom:5px;}
.tester input, .tester select{
  width:100%;background:#000;border:1px solid rgba(255,30,30,.3);
  border-radius:8px;padding:11px 13px;color:#fff;font-family:'JetBrains Mono',monospace;
  font-size:.82rem;transition:.2s;
}
.tester input:focus, .tester select:focus{
  outline:none;border-color:var(--red);box-shadow:0 0 12px rgba(255,30,30,.3);
}
.tester input::placeholder{color:#555;}
.btn{
  background:linear-gradient(135deg,var(--red),var(--red-dark));
  color:#fff;border:none;padding:12px 28px;border-radius:10px;
  font-weight:900;font-size:.9rem;cursor:pointer;letter-spacing:1px;
  font-family:'Cairo',sans-serif;transition:.25s;
  box-shadow:0 0 20px rgba(255,30,30,.4);width:100%;
}
.btn:hover{transform:translateY(-2px);box-shadow:0 0 30px rgba(255,30,30,.7);}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none;}
.result{
  margin-top:20px;background:#000;border:1px solid rgba(255,30,30,.3);
  border-radius:10px;padding:16px;font-family:'JetBrains Mono',monospace;
  font-size:.78rem;color:#ffb3b3;max-height:450px;overflow:auto;
  white-space:pre-wrap;word-break:break-all;line-height:1.6;display:none;
}
.result.show{display:block;}
.result.ok{border-color:rgba(0,255,0,.4);}
.result.err{border-color:rgba(255,30,30,.6);}

/* FOOTER */
footer{
  text-align:center;padding:45px 20px 30px;
  border-top:1px solid rgba(255,30,30,.2);
  background:rgba(5,5,5,.6);position:relative;z-index:1;
}
footer .brand{
  font-family:'Orbitron',sans-serif;font-weight:900;font-size:1.6rem;
  color:var(--red);text-shadow:0 0 20px rgba(255,30,30,.7);
  letter-spacing:6px;margin-bottom:10px;
}
footer p{color:#666;font-size:.85rem;margin-top:6px;}
footer a{color:var(--red);text-decoration:none;font-weight:700;}
footer .links{display:flex;gap:14px;justify-content:center;margin-top:16px;flex-wrap:wrap;}
footer .links a{
  padding:6px 14px;border:1px solid rgba(255,30,30,.3);border-radius:20px;
  font-size:.78rem;transition:.2s;
}
footer .links a:hover{background:rgba(255,30,30,.15);}

/* TOAST */
.toast{
  position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(120px);
  background:linear-gradient(135deg,var(--red),var(--red-dark));color:#fff;
  padding:12px 26px;border-radius:30px;font-weight:700;font-size:.88rem;
  box-shadow:0 0 30px rgba(255,30,30,.7);transition:.35s;opacity:0;z-index:999;
  pointer-events:none;
}
.toast.show{transform:translateX(-50%) translateY(0);opacity:1;}

/* SCROLLBAR */
::-webkit-scrollbar{width:9px;height:9px;}
::-webkit-scrollbar-track{background:var(--black);}
::-webkit-scrollbar-thumb{background:linear-gradient(var(--red),var(--red-dark));border-radius:10px;}

@media(max-width:600px){
  .hero{padding-top:110px;}
  .hero h1{font-size:1.9rem;}
  .tabs{top:56px;padding:12px 8px;}
  .tab{padding:7px 12px;font-size:.75rem;}
  .top{padding:10px 12px;}
  .top .logo{font-size:1rem;letter-spacing:2px;}
  .pill{padding:5px 10px;font-size:.65rem;}
  .section-title{font-size:1.15rem;}
}
</style>
</head>
<body>

<div class="top">
  <div class="logo"><span class="zap">⚡</span>FLASH<span>API</span></div>
  <div class="right">
    <div class="pill live">ONLINE</div>
    <div class="pill brand-xore">XORE</div>
  </div>
</div>

<header class="hero">
  <div class="tag">🔥 POWERED BY XORE × FL4SH</div>
  <h1>FREE FIRE API HUB</h1>
  <div class="divider"></div>
  <p>بوابة موحدة لكل APIs فريب فاير — إدارة السيرفرات، معلومات اللاعبين، الإحصائيات، الورشة والمزيد — بتصميم احترافي وتجربة سريعة.</p>
</header>

<div class="stats">
  <div class="stat"><div class="num">15+</div><div class="lbl">ENDPOINTS</div></div>
  <div class="stat"><div class="num">2</div><div class="lbl">API SOURCES</div></div>
  <div class="stat"><div class="num">24/7</div><div class="lbl">UPTIME</div></div>
  <div class="stat"><div class="num">v2.0</div><div class="lbl">VERSION</div></div>
</div>

<div class="tabs">
  <div class="tab active" data-tab="guild">🛡️ إدارة السيرفر</div>
  <div class="tab" data-tab="player">👤 اللاعب</div>
  <div class="tab" data-tab="stats">📊 الإحصائيات</div>
  <div class="tab" data-tab="extras">🎁 إضافات</div>
  <div class="tab" data-tab="tester">⚡ اختبار مباشر</div>
</div>

<div class="container">

  <!-- GUILD -->
  <section class="section active" id="guild">
    <div class="section-title"><div class="icon">🛡️</div>GUILD MANAGEMENT</div>
    <div class="section-desc">🌐 flash-guild-management.vercel.app — إدارة كاملة للسيرفرات (4 طرق مصادقة)</div>
    <div class="grid">

      <div class="card">
        <div class="card-head"><div class="emoji">🔑</div><h3>TOKEN<small>الحصول على التوكن</small></h3></div>
        <div class="ep"><span class="method">GET</span>/token?uid={uid}&password={pwd}<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/token?access_token={token}<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/token?eat={eat}<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="note"><strong>ℹ️</strong> 3 طرق مختلفة للحصول على JWT.</div>
      </div>

      <div class="card">
        <div class="card-head"><div class="emoji">🛡️</div><h3>CLAN INFO<small>معلومات السيرفر</small></h3></div>
        <div class="ep"><span class="method">GET</span>/clan_info?clan_id=X&jwt=Y<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/clan_info?clan_id=X&uid=Y&password=Z<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/clan_info?clan_id=X&access_token=Y<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/clan_info?clan_id=X&eat=Y<button class="copy" onclick="copyText(this)">نسخ</button></div>
      </div>

      <div class="card">
        <div class="card-head"><div class="emoji">➕</div><h3>REQUEST CLAN<small>طلب انضمام</small></h3></div>
        <div class="ep"><span class="method">GET</span>/request_clan?clan_id=X&jwt=Y<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/request_clan?clan_id=X&uid=Y&password=Z<button class="copy" onclick="copyText(this)">نسخ</button></div>
        <div class="ep"><span class="method">GET</span>/request_clan?clan_id=X&access
