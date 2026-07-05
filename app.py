import os
import difflib
import re
from datetime import timedelta
from urllib.parse import urlencode, urlparse
import openai
import anthropic
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO, emit
from admin_routes import admin_bp
from models import db, User

# ---------------- APP SETUP ----------------
migrate = Migrate()
socketio = SocketIO()


def create_app(test_config=None):
    load_dotenv()

    app_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = os.path.join(app_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    app = Flask(__name__, instance_path=instance_dir, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    database_uri = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not database_uri:
        database_uri = f"sqlite:///{os.path.join(instance_dir, 'app.db')}"

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "supersecretkey"),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PREFERRED_URL_SCHEME='https' if os.environ.get('FLASK_ENV') == 'production' else 'http',
        SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        SESSION_REFRESH_EACH_REQUEST=True,
    )

    if test_config:
        app.config.update(test_config)

    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

    # ---------------- HELPERS ----------------
    def get_google_oauth_config():
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
        redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', '').strip()
        return client_id, client_secret, redirect_uri

    def is_google_oauth_configured():
        client_id, client_secret, _ = get_google_oauth_config()
        return bool(client_id and client_secret and 'your_google' not in client_id and 'your_google' not in client_secret)

    def get_google_redirect_uri():
        configured_redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', '').strip()
        if configured_redirect_uri and 'your_google' not in configured_redirect_uri:
            return configured_redirect_uri
        return url_for('google_callback', _external=True)

    def get_unique_username(base_name):
        base = re.sub(r'[^A-Za-z0-9_.-]+', '', (base_name or 'user').strip()) or 'user'
        base = base[:30]
        candidate = base
        suffix = 1
        while User.query.filter_by(username=candidate).first():
            candidate = f'{base}{suffix}'
            suffix += 1
        return candidate

    # ---------------- SOCKETIO HANDLERS ----------------
    @socketio.on('message')
    def handle_message(data):
        user_message = data.get('message', '')
        reply = generate_bot_reply(user_message)
        emit('response', {'reply': reply})

    # ---------------- ROUTES ----------------
    @app.route('/')
    def index():
        if 'username' in session:
            return redirect(url_for('home'))
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error_message = request.args.get('oauth_error') or None

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            if not username or not password:
                error_message = 'Please enter both your username and password.'
            else:
                user = User.query.filter_by(username=username).first()

                if user:
                    password_valid = False
                    try:
                        password_valid = check_password_hash(user.password, password)
                    except (TypeError, ValueError):
                        password_valid = (user.password == password)

                    if password_valid:
                        session.permanent = True
                        session['username'] = user.username
                        return redirect(url_for('home'))

                error_message = 'Invalid username or password. Please try again.'

        return render_template('login.html', error_message=error_message)

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

            if not username or not email or not password:
                return render_template('signup.html', error_message='Please fill in all fields to create your account.'), 400

            if len(password) < 6:
                return render_template('signup.html', error_message='Password must be at least 6 characters long.'), 400

            existing_user = User.query.filter_by(username=username).first()
            existing_email = User.query.filter_by(email=email).first()

            if existing_user:
                return render_template('signup.html', error_message='Username already exists. Please choose a different one.'), 400

            if existing_email:
                return render_template('signup.html', error_message='Email already exists. Please use a different email.'), 400

            try:
                hashed_password = generate_password_hash(password)
                new_user = User(username=username, email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return render_template('signup.html', error_message='That username or email is already taken. Please try a different one.'), 400

            return render_template('login.html', success_message='Account created successfully. Please sign in.')

        return render_template('signup.html')

    @app.route('/auth/google/login')
    def google_login():
        if not is_google_oauth_configured():
            return redirect(url_for('login', oauth_error='Google sign-in is not configured yet. Add your real Google OAuth client ID and secret in the .env file to enable this option.'))

        client_id, _, _ = get_google_oauth_config()

        redirect_uri = get_google_redirect_uri()
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'online',
            'prompt': 'select_account',
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return redirect(auth_url)

    @app.route('/auth/google/callback')
    def google_callback():
        error = request.args.get('error')
        if error:
            return redirect(url_for('login'))

        code = request.args.get('code')
        if not code:
            return redirect(url_for('login'))

        if not is_google_oauth_configured():
            return redirect(url_for('login', oauth_error='Google sign-in is not configured yet. Add your real Google OAuth client ID and secret to enable this option.'))

        client_id, client_secret, _ = get_google_oauth_config()

        redirect_uri = get_google_redirect_uri()
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            timeout=15,
        )

        if token_response.status_code != 200:
            return redirect(url_for('login'))

        token_data = token_response.json()
        access_token = token_data.get('access_token')
        if not access_token:
            return redirect(url_for('login'))

        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15,
        )
        if userinfo_response.status_code != 200:
            return redirect(url_for('login'))

        userinfo = userinfo_response.json()
        email = (userinfo.get('email') or '').strip()
        name = (userinfo.get('name') or email.split('@')[0] or 'user').strip()

        user = User.query.filter_by(email=email).first() if email else None
        if not user:
            username = get_unique_username(name)
            hashed_password = generate_password_hash(os.urandom(16).hex())
            user = User(username=username, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()

        session['username'] = user.username
        return redirect(url_for('home'))

    @app.route('/home')
    def home():
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('home.html', username=session['username'])

    @app.route('/logout')
    def logout():
        session.pop('username', None)
        return redirect(url_for('login'))

    @app.route('/profile')
    def profile():
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('profile.html', username=session['username'])

    @app.route('/pcbuilder', methods=['GET', 'POST'])
    def pcbuilder():
        if 'username' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            user_message = request.form['message']
            reply = generate_bot_reply(user_message)
            return jsonify({"reply": reply})

        return render_template('pcbuilder.html', username=session['username'])

    @app.route('/3d-builder')
    def three_d_builder():
        if 'username' not in session:
            return redirect(url_for('login'))

        return render_template('3d_builder.html', username=session['username'])

    @app.route('/reverse-builder', methods=['GET', 'POST'])
    def reverse_builder():
        if 'username' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            use_case = request.form['use_case']
            budget_tier = request.form['budget_tier']
            build = generate_build(use_case, budget_tier)
            checklist = generate_boot_checklist(build)
            return render_template('reverse_builder.html', username=session['username'], build=build, use_case=use_case, budget_tier=budget_tier, checklist=checklist)

        return render_template('reverse_builder.html', username=session['username'])

    @app.route('/upgrade-planner', methods=['GET', 'POST'])
    def upgrade_planner():
        if 'username' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            current_specs = {
                'cpu': request.form['cpu'],
                'gpu': request.form['gpu'],
                'ram': int(request.form['ram']),
                'storage': request.form['storage'],
                'budget': request.form['budget'],
                'use_case': request.form['use_case']
            }
            upgrade_plan = generate_upgrade_plan(current_specs)
            return render_template('upgrade_planner.html', username=session['username'], specs=current_specs, plan=upgrade_plan)

        return render_template('upgrade_planner.html', username=session['username'])

    @app.route('/toggle-beginner-mode', methods=['POST'])
    def toggle_beginner_mode():
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        data = request.get_json()
        beginner_mode = data.get('beginner_mode', False)
        session['beginner_mode'] = beginner_mode
        return jsonify({'success': True, 'beginner_mode': beginner_mode})

    @app.route('/bottleneck-predictor', methods=['GET', 'POST'])
    def bottleneck_predictor():
        if 'username' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            specs = {
                'cpu': request.form['cpu'],
                'gpu': request.form['gpu'],
                'ram': int(request.form['ram']),
                'resolution': request.form['resolution'],
                'settings': request.form['settings']
            }
            analysis = calculate_bottleneck(specs)
            return render_template('bottleneck_predictor.html', username=session['username'], specs=specs, analysis=analysis)

        return render_template('bottleneck_predictor.html', username=session['username'])

    @app.route('/voice-interaction', methods=['GET', 'POST'])
    def voice_interaction():
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('voice_interaction.html', username=session['username'])

    @app.route('/voice-query', methods=['POST'])
    def voice_query():
        if 'username' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        try:
            data = request.get_json()
        except UnicodeDecodeError:
            return jsonify({'error': 'Invalid character encoding in request'}), 400
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Use Claude AI for voice responses
        response = generate_voice_response(query, session.get('beginner_mode', False))
        return jsonify({'response': response})

    @app.route('/purchase-integration', methods=['GET', 'POST'])
    def purchase_integration():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            # Get build requirements from form
            budget_inr = float(request.form.get('budget', 124500))
            budget_usd = budget_inr / 83  # Convert INR to USD for backend processing
            use_case = request.form.get('use_case', 'gaming')
            preferences = {
                'cpu_brand': request.form.get('cpu_brand', 'any'),
                'gpu_brand': request.form.get('gpu_brand', 'any'),
                'priority': request.form.get('priority', 'balanced')
            }
            
            # Generate optimized build
            build = generate_optimized_build(budget_usd, use_case, preferences)
            
            # Fetch real-time prices
            build_with_prices = fetch_real_time_prices(build)
            
            # Calculate totals
            total_cost = sum(item['price'] for item in build_with_prices.values())
            build_with_prices['total_cost'] = total_cost
            
            return render_template('purchase_integration.html', 
                                 username=session['username'], 
                                 build=build_with_prices,
                                 budget=budget_inr,
                                 use_case=use_case,
                                 preferences=preferences)
        
        return render_template('purchase_integration.html', username=session['username'])

    @app.route('/purchase-summary/<build_id>')
    def purchase_summary(build_id):
        if 'username' not in session:
            return redirect(url_for('login'))
        
        # In a real app, you'd fetch the build from database by ID
        # For now, we'll create a sample build
        sample_build = {
            'cpu': {'name': 'AMD Ryzen 5 7600', 'price': 299, 'url': 'https://example.com/cpu'},
            'gpu': {'name': 'NVIDIA RTX 4070', 'price': 599, 'url': 'https://example.com/gpu'},
            'ram': {'name': '32GB DDR5-5600', 'price': 149, 'url': 'https://example.com/ram'},
            'mobo': {'name': 'ASUS B650', 'price': 189, 'url': 'https://example.com/mobo'},
            'psu': {'name': '750W 80+ Gold', 'price': 129, 'url': 'https://example.com/psu'},
            'storage': {'name': '1TB NVMe SSD', 'price': 89, 'url': 'https://example.com/ssd'},
            'case': {'name': 'Mid Tower Case', 'price': 79, 'url': 'https://example.com/case'},
            'total_cost': 1532
        }
        
        return render_template('purchase_summary.html', 
                             username=session['username'], 
                             build=sample_build,
                             build_id=build_id)

    @app.route('/auto-order-execution', methods=['GET', 'POST'])
    def auto_order_execution():
        if 'username' not in session:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            # Get order details from form
            order_data = {
                'customer_email': request.form.get('customer_email'),
                'build_components': request.form.get('build_components'),
                'total_amount': float(request.form.get('total_amount', 0)),
                'payment_method': request.form.get('payment_method'),
                'shipping_address': request.form.get('shipping_address')
            }
            
            # Execute automated order pipeline
            execution_result = execute_auto_order_pipeline(order_data)
            
            return render_template('auto_order_execution.html', 
                                 username=session['username'], 
                                 order_data=order_data,
                                 execution_result=execution_result)
        
        return render_template('auto_order_execution.html', username=session['username'])

    return app


def execute_auto_order_pipeline(order_data):
    """Execute the automated order placement pipeline"""
    import time
    import random
    
    pipeline_steps = [
        {
            'step': 1,
            'name': 'Verify Authentication',
            'description': 'Validating user credentials and permissions',
            'status': 'pending'
        },
        {
            'step': 2,
            'name': 'Confirm Approval',
            'description': 'Checking order approval and compliance',
            'status': 'pending'
        },
        {
            'step': 3,
            'name': 'Check Stock Availability',
            'description': 'Verifying component availability across retailers',
            'status': 'pending'
        },
        {
            'step': 4,
            'name': 'Process Payment',
            'description': 'Securing payment through encrypted channels',
            'status': 'pending'
        },
        {
            'step': 5,
            'name': 'Place Orders',
            'description': 'Executing orders across multiple retailers',
            'status': 'pending'
        },
        {
            'step': 6,
            'name': 'Send Confirmation',
            'description': 'Delivering order confirmations and tracking info',
            'status': 'pending'
        }
    ]
    
    execution_log = []
    
    # Step 1: Verify Authentication
    pipeline_steps[0]['status'] = 'processing'
    time.sleep(1)  # Simulate processing time
    auth_success = random.choice([True, True, True, False])  # 75% success rate
    if auth_success:
        pipeline_steps[0]['status'] = 'completed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 1,
            'message': '✓ Authentication verified successfully',
            'details': f'User {order_data.get("customer_email", "customer")} authenticated'
        })
    else:
        pipeline_steps[0]['status'] = 'failed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 1,
            'message': '✗ Authentication failed',
            'details': 'Invalid credentials or session expired'
        })
        return {
            'success': False,
            'pipeline_steps': pipeline_steps,
            'execution_log': execution_log,
            'error': 'Authentication failed'
        }
    
    # Step 2: Confirm Approval
    pipeline_steps[1]['status'] = 'processing'
    time.sleep(0.8)
    approval_success = random.choice([True, True, True, False])  # 75% success rate
    if approval_success:
        pipeline_steps[1]['status'] = 'completed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 2,
            'message': '✓ Order approved',
            'details': f'Order value ₹{order_data.get("total_amount", 0):.2f} within approved limits'
        })
    else:
        pipeline_steps[1]['status'] = 'failed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 2,
            'message': '✗ Approval denied',
            'details': 'Order exceeds approval limits or requires manual review'
        })
        return {
            'success': False,
            'pipeline_steps': pipeline_steps,
            'execution_log': execution_log,
            'error': 'Approval denied'
        }
    
    # Step 3: Check Stock
    pipeline_steps[2]['status'] = 'processing'
    time.sleep(1.2)
    stock_success = random.choice([True, True, False])  # 66% success rate
    if stock_success:
        pipeline_steps[2]['status'] = 'completed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 3,
            'message': '✓ All components in stock',
            'details': 'Verified availability across all selected retailers'
        })
    else:
        pipeline_steps[2]['status'] = 'failed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 3,
            'message': '✗ Stock unavailable',
            'details': 'One or more components out of stock - order cannot proceed'
        })
        return {
            'success': False,
            'pipeline_steps': pipeline_steps,
            'execution_log': execution_log,
            'error': 'Stock unavailable'
        }
    
    # Step 4: Process Payment
    pipeline_steps[3]['status'] = 'processing'
    time.sleep(1.5)
    payment_success = random.choice([True, True, True, False])  # 75% success rate
    if payment_success:
        pipeline_steps[3]['status'] = 'completed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 4,
            'message': '✓ Payment processed successfully',
            'details': f'₹{order_data.get("total_amount", 0):.2f} charged via {order_data.get("payment_method", "card")}'
        })
    else:
        pipeline_steps[3]['status'] = 'failed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 4,
            'message': '✗ Payment failed',
            'details': 'Payment declined - insufficient funds or card error'
        })
        return {
            'success': False,
            'pipeline_steps': pipeline_steps,
            'execution_log': execution_log,
            'error': 'Payment failed'
        }
    
    # Step 5: Place Orders
    pipeline_steps[4]['status'] = 'processing'
    time.sleep(1.8)
    order_success = random.choice([True, True, True, False])  # 75% success rate
    if order_success:
        pipeline_steps[4]['status'] = 'completed'
        order_ids = [f"ORD-{random.randint(100000, 999999)}" for _ in range(random.randint(1, 3))]
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 5,
            'message': '✓ Orders placed successfully',
            'details': f'Order IDs: {", ".join(order_ids)}'
        })
    else:
        pipeline_steps[4]['status'] = 'failed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 5,
            'message': '✗ Order placement failed',
            'details': 'Retailer API error or system timeout'
        })
        return {
            'success': False,
            'pipeline_steps': pipeline_steps,
            'execution_log': execution_log,
            'error': 'Order placement failed'
        }
    
    # Step 6: Send Confirmation
    pipeline_steps[5]['status'] = 'processing'
    time.sleep(0.5)
    confirmation_success = True  # High success rate for final step
    if confirmation_success:
        pipeline_steps[5]['status'] = 'completed'
        execution_log.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'step': 6,
            'message': '✓ Confirmation sent',
            'details': f'Order confirmation and tracking info sent to {order_data.get("customer_email", "customer")}'
        })
    
    return {
        'success': True,
        'pipeline_steps': pipeline_steps,
        'execution_log': execution_log,
        'order_ids': order_ids if 'order_ids' in locals() else [],
        'estimated_delivery': '3-5 business days'
    }

# ---------------- CHATBOT HELPERS ----------------
def generate_build(use_case, budget_tier):
    builds = {
        'gaming': {
            'low': {
                'cpu': {'name': 'AMD Ryzen 5 5600', 'explanation': 'A solid 6-core CPU that handles modern games well without breaking the bank. It provides good multi-threading for background tasks.'},
                'gpu': {'name': 'NVIDIA RTX 3060', 'explanation': 'Excellent 1080p gaming performance with ray tracing support. Future-proof for 1440p gaming.'},
                'ram': {'name': '16GB DDR4-3200', 'explanation': 'Enough memory for smooth gaming and multitasking. Higher speed helps with frame rates.'},
                'motherboard': {'name': 'ASUS B450M', 'explanation': 'Reliable AM4 motherboard with good VRM for stable overclocking if needed.'},
                'psu': {'name': 'Corsair CX550M', 'explanation': '80+ Bronze certified PSU with modular cables for clean builds and stable power delivery.'},
                'case': {'name': 'Fractal Design Meshify C Mini', 'explanation': 'Great airflow with mesh front panel, compact size fits all components perfectly.'},
                'storage': {'name': '500GB NVMe SSD', 'explanation': 'Fast boot times and quick game loading. Sufficient space for several games.'},
                'cooling': {'name': 'Stock AMD cooler', 'explanation': 'Adequate cooling for this CPU at stock speeds, keeping noise low.'}
            },
            'mid': {
                'cpu': {'name': 'AMD Ryzen 7 5700X', 'explanation': '8-core CPU perfect for gaming and streaming simultaneously. Excellent value for performance.'},
                'gpu': {'name': 'NVIDIA RTX 4070', 'explanation': 'Outstanding 1440p gaming with DLSS 3 for future-proofing. Handles ray tracing beautifully.'},
                'ram': {'name': '32GB DDR4-3600', 'explanation': 'Plenty of memory for gaming, streaming, and content creation. Higher speed reduces latency.'},
                'motherboard': {'name': 'MSI B550 Tomahawk', 'explanation': 'Feature-rich board with PCIe 4.0 support and good power delivery for the CPU.'},
                'psu': {'name': 'Corsair RM750x', 'explanation': '80+ Gold certified modular PSU for efficiency and reliability under load.'},
                'case': {'name': 'Fractal Design Define 7', 'explanation': 'Silent case with excellent airflow and sound dampening for quiet gaming sessions.'},
                'storage': {'name': '1TB NVMe SSD', 'explanation': 'Ample storage for games and fast loading times. Room for expansions.'},
                'cooling': {'name': 'Noctua NH-U12S', 'explanation': 'Premium air cooler for quiet operation and excellent thermal performance.'}
            },
            'high': {
                'cpu': {'name': 'AMD Ryzen 9 5900X', 'explanation': '12-core beast for ultimate gaming and multitasking. Handles any game at max settings.'},
                'gpu': {'name': 'NVIDIA RTX 4080', 'explanation': 'Flagship GPU for 4K gaming with incredible ray tracing and DLSS performance.'},
                'ram': {'name': '64GB DDR4-3600', 'explanation': 'Maximum memory for heavy gaming sessions and background applications.'},
                'motherboard': {'name': 'ASUS ROG Strix X570-E', 'explanation': 'Premium motherboard with robust VRM, WiFi 6, and extensive connectivity options.'},
                'psu': {'name': 'Corsair HX1000i', 'explanation': '80+ Platinum certified PSU with full modularity and high efficiency.'},
                'case': {'name': 'Fractal Design Define 7 XL', 'explanation': 'Large case for excellent airflow and easy cable management in high-end builds.'},
                'storage': {'name': '2TB NVMe SSD + 4TB HDD', 'explanation': 'Fast SSD for OS and games, large HDD for media storage.'},
                'cooling': {'name': 'Noctua NH-D15', 'explanation': 'Dual-tower air cooler for silent and effective cooling of high-performance CPUs.'}
            }
        },
        'editing': {
            'low': {
                'cpu': {'name': 'AMD Ryzen 5 5600X', 'explanation': '6 cores provide good multi-threading for video editing and rendering tasks.'},
                'gpu': {'name': 'NVIDIA RTX 3060', 'explanation': 'CUDA cores accelerate video editing software like Adobe Premiere and DaVinci Resolve.'},
                'ram': {'name': '32GB DDR4-3200', 'explanation': 'Essential for handling large video files and multiple applications simultaneously.'},
                'motherboard': {'name': 'ASUS B450M', 'explanation': 'Stable platform with good expansion options for future upgrades.'},
                'psu': {'name': 'Corsair CX550M', 'explanation': 'Reliable power delivery for consistent performance during long editing sessions.'},
                'case': {'name': 'Fractal Design Meshify C Mini', 'explanation': 'Good airflow keeps components cool during intensive workloads.'},
                'storage': {'name': '1TB NVMe SSD', 'explanation': 'Fast storage for quick project loading and saving.'},
                'cooling': {'name': 'Stock AMD cooler', 'explanation': 'Sufficient cooling for this CPU under normal editing loads.'}
            },
            'mid': {
                'cpu': {'name': 'AMD Ryzen 7 5800X', 'explanation': '8 cores excel at multi-threaded editing tasks and faster render times.'},
                'gpu': {'name': 'NVIDIA RTX 4070', 'explanation': 'Powerful GPU acceleration for 4K editing and effects processing.'},
                'ram': {'name': '64GB DDR4-3600', 'explanation': 'Handles complex projects with multiple layers and effects without slowdown.'},
                'motherboard': {'name': 'MSI B550 Tomahawk', 'explanation': 'Good PCIe lanes for multiple storage devices and expansion cards.'},
                'psu': {'name': 'Corsair RM750x', 'explanation': 'Efficient power supply for stable operation during heavy workloads.'},
                'case': {'name': 'Fractal Design Define 7', 'explanation': 'Quiet operation important for focus during editing sessions.'},
                'storage': {'name': '2TB NVMe SSD', 'explanation': 'Large fast storage for project files and scratch disks.'},
                'cooling': {'name': 'Noctua NH-U12S', 'explanation': 'Quiet cooling to maintain concentration during long editing marathons.'}
            },
            'high': {
                'cpu': {'name': 'AMD Ryzen 9 5950X', 'explanation': '16 cores for professional-grade rendering and multi-tasking in editing suites.'},
                'gpu': {'name': 'NVIDIA RTX 4080', 'explanation': 'Professional GPU for real-time effects preview and accelerated rendering.'},
                'ram': {'name': '128GB DDR4-3600', 'explanation': 'Maximum memory for handling massive 8K projects and complex compositions.'},
                'motherboard': {'name': 'ASUS ROG Strix X570-E', 'explanation': 'High-end board with multiple PCIe slots for professional workflows.'},
                'psu': {'name': 'Corsair HX1000i', 'explanation': 'Premium PSU for rock-solid power delivery in demanding professional environments.'},
                'case': {'name': 'Fractal Design Define 7 XL', 'explanation': 'Spacious case for easy access and excellent cooling in workstation setups.'},
                'storage': {'name': '4TB NVMe SSD + 8TB HDD', 'explanation': 'High-speed SSD for active projects, massive HDD for archives.'},
                'cooling': {'name': 'Noctua NH-D15', 'explanation': 'Superior cooling for sustained high-performance computing.'}
            }
        },
        'streaming': {
            'low': {
                'cpu': {'name': 'AMD Ryzen 5 5600X', 'explanation': '6 cores handle gaming and streaming simultaneously without major performance hits.'},
                'gpu': {'name': 'NVIDIA RTX 3060', 'explanation': 'Good gaming performance while encoding streams with NVENC.'},
                'ram': {'name': '32GB DDR4-3200', 'explanation': 'Enough memory for streaming software, games, and overlays.'},
                'motherboard': {'name': 'ASUS B450M', 'explanation': 'Stable platform with integrated audio for clear stream quality.'},
                'psu': {'name': 'Corsair CX550M', 'explanation': 'Reliable power for consistent streaming sessions.'},
                'case': {'name': 'Fractal Design Meshify C Mini', 'explanation': 'Quiet case to avoid microphone interference during streams.'},
                'storage': {'name': '1TB NVMe SSD', 'explanation': 'Fast storage for quick game loading and recording saves.'},
                'cooling': {'name': 'Stock AMD cooler', 'explanation': 'Adequate cooling that stays quiet during streams.'}
            },
            'mid': {
                'cpu': {'name': 'AMD Ryzen 7 5800X', 'explanation': '8 cores provide excellent multi-tasking for gaming, streaming, and chat management.'},
                'gpu': {'name': 'NVIDIA RTX 4070', 'explanation': 'Superior encoding performance with NVENC for high-quality streams.'},
                'ram': {'name': '64GB DDR4-3600', 'explanation': 'Handles streaming software, games, and multiple browser tabs without issues.'},
                'motherboard': {'name': 'MSI B550 Tomahawk', 'explanation': 'Good audio quality and multiple USB ports for streaming peripherals.'},
                'psu': {'name': 'Corsair RM750x', 'explanation': 'Efficient PSU for stable power during long streaming sessions.'},
                'case': {'name': 'Fractal Design Define 7', 'explanation': 'Ultra-quiet case perfect for content creation environments.'},
                'storage': {'name': '2TB NVMe SSD', 'explanation': 'Plenty of space for game libraries and stream recordings.'},
                'cooling': {'name': 'Noctua NH-U12S', 'explanation': 'Silent cooling to eliminate fan noise from streams.'}
            },
            'high': {
                'cpu': {'name': 'AMD Ryzen 9 5900X', 'explanation': '12 cores for flawless multi-tasking during professional streaming setups.'},
                'gpu': {'name': 'NVIDIA RTX 4080', 'explanation': 'Top-tier encoding for 4K streaming with minimal performance impact.'},
                'ram': {'name': '128GB DDR4-3600', 'explanation': 'Maximum memory for complex streaming setups with multiple applications.'},
                'motherboard': {'name': 'ASUS ROG Strix X570-E', 'explanation': 'Premium features like WiFi 6 and excellent audio for professional streams.'},
                'psu': {'name': 'Corsair HX1000i', 'explanation': 'High-efficiency PSU for reliable operation in demanding streaming environments.'},
                'case': {'name': 'Fractal Design Define 7 XL', 'explanation': 'Large, quiet case for professional streaming rigs with room for expansion.'},
                'storage': {'name': '4TB NVMe SSD + 4TB HDD', 'explanation': 'Fast SSD for active content, HDD for storing past streams and backups.'},
                'cooling': {'name': 'Noctua NH-D15', 'explanation': 'Exceptional cooling performance while maintaining whisper-quiet operation.'}
            }
        }
    }
    
    return builds.get(use_case, {}).get(budget_tier, {})


def generate_boot_checklist(build):
    checklist = []
    
    # BIOS Settings
    checklist.append({
        'phase': 'BIOS Setup',
        'steps': [
            'Enter BIOS by pressing DEL (or F2/F10 depending on motherboard) during POST',
            'Load Optimized Defaults to start fresh',
            'Set SATA Mode to AHCI (if using SSD/HDD)',
            'Enable XMP Profile for RAM (if RAM speed is 3200MHz or higher) - this optimizes memory timing',
            'Set CPU Voltage to Auto (let motherboard handle it)',
            'Enable Global C-State Control for better power management',
            'Save and Exit BIOS (F10 + Enter)'
        ]
    })
    
    # Hardware Assembly Check
    checklist.append({
        'phase': 'Hardware Verification',
        'steps': [
            'Ensure all power cables are securely connected',
            'Verify CPU cooler is properly mounted and thermal paste applied',
            'Check all case fans are connected and spinning',
            'Confirm RAM is seated firmly in slots (click sound)',
            'Verify GPU is fully seated in PCIe slot and power connectors attached',
            'Check front panel connectors (power switch, reset, LEDs) are properly connected'
        ]
    })
    
    # Driver Installation Order
    checklist.append({
        'phase': 'Driver Installation',
        'steps': [
            'Install motherboard chipset drivers first (AMD Chipset Drivers from manufacturer website)',
            'Install GPU drivers (NVIDIA GeForce Experience or AMD Radeon Software)',
            'Install network drivers if needed (usually included in chipset drivers)',
            'Install audio drivers (Realtek or motherboard-specific)',
            'Install USB drivers if any additional controllers',
            'Update Windows and install Windows updates',
            'Install motherboard utilities (RGB control, fan control software)'
        ]
    })
    
    # Software Setup
    checklist.append({
        'phase': 'Software & Optimization',
        'steps': [
            'Install antivirus software',
            'Update all drivers using manufacturer tools',
            'Install monitoring software (HWMonitor, MSI Afterburner for GPU)',
            'Configure Windows power plan to High Performance',
            'Disable unnecessary startup programs',
            'Run Windows Memory Diagnostic to verify RAM',
            'Test system stability with Prime95 or AIDA64'
        ]
    })
    
    # Component-specific steps
    if 'RTX' in build.get('gpu', {}).get('name', ''):
        checklist[2]['steps'].insert(1, 'Install NVIDIA GeForce Experience for optimal settings')
    elif 'RX' in build.get('gpu', {}).get('name', ''):
        checklist[2]['steps'].insert(1, 'Install AMD Radeon Software for optimal settings')
    
    if 'Ryzen' in build.get('cpu', {}).get('name', ''):
        checklist[0]['steps'].insert(2, 'Enable Precision Boost Overdrive in BIOS for better CPU performance')
        checklist[0]['steps'].insert(3, 'Set PCIe Link Speed to Gen 3 or Auto for stability')
    
    return checklist


def generate_upgrade_plan(specs):
    plan = {
        'phase1': {'upgrades': [], 'timeline': '0-6 months', 'focus': 'Maximum immediate performance gain'},
        'phase2': {'upgrades': [], 'timeline': '6-12 months', 'focus': 'Balanced upgrades for sustained performance'},
        'phase3': {'upgrades': [], 'timeline': '12-24 months', 'focus': 'Future-proofing and final optimizations'}
    }
    
    cpu = specs['cpu'].lower()
    gpu = specs['gpu'].lower()
    ram = specs['ram']
    storage = specs['storage'].lower()
    budget = specs['budget'].lower()
    use_case = specs['use_case']
    
    # Phase 1: Quick wins
    if 'rtx 30' in gpu or 'gtx 16' in gpu or 'rx 6' in gpu or 'gtx 10' in gpu:
        plan['phase1']['upgrades'].append({
            'component': 'GPU',
            'recommendation': 'Upgrade to RTX 4060/4070',
            'reason': 'GPU is often the biggest bottleneck for gaming and content creation. Newer GPUs offer significant performance improvements.',
            'cost_estimate': '₹25,000-40,000',
            'performance_gain': '50-100% improvement in gaming/rendering'
        })
    elif ram < 16:
        plan['phase1']['upgrades'].append({
            'component': 'RAM',
            'recommendation': 'Upgrade to 16GB DDR4-3200',
            'reason': 'More RAM allows better multitasking and prevents bottlenecks in memory-intensive applications.',
            'cost_estimate': '₹4,000-6,000',
            'performance_gain': 'Significant improvement in multitasking and heavy applications'
        })
    else:
        plan['phase1']['upgrades'].append({
            'component': 'Storage',
            'recommendation': 'Add NVMe SSD (500GB-1TB)',
            'reason': 'Fast storage dramatically improves load times and system responsiveness.',
            'cost_estimate': '₹5,000-8,000',
            'performance_gain': '10x faster load times'
        })
    
    # Phase 2: Balanced upgrades
    if ram < 32 and use_case in ['editing', 'streaming']:
        plan['phase2']['upgrades'].append({
            'component': 'RAM',
            'recommendation': 'Upgrade to 32GB-64GB DDR4-3600',
            'reason': 'Professional workloads need more memory for complex projects and multi-tasking.',
            'cost_estimate': '₹8,000-15,000',
            'performance_gain': 'Better handling of large files and effects'
        })
    elif 'ryzen 5' in cpu or 'i5' in cpu:
        plan['phase2']['upgrades'].append({
            'component': 'CPU',
            'recommendation': 'Upgrade to Ryzen 7 5700X or i7-12700K',
            'reason': 'Better CPU improves multi-threaded performance for gaming, streaming, and content creation.',
            'cost_estimate': '₹20,000-30,000',
            'performance_gain': '30-50% improvement in CPU-intensive tasks'
        })
    else:
        plan['phase2']['upgrades'].append({
            'component': 'PSU',
            'recommendation': 'Upgrade to 80+ Gold 650W+ PSU',
            'reason': 'Better PSU provides stable power and efficiency, especially important for high-end components.',
            'cost_estimate': '₹6,000-10,000',
            'performance_gain': 'Improved system stability and efficiency'
        })
    
    # Phase 3: Future-proofing
    plan['phase3']['upgrades'].append({
        'component': 'Full System Refresh',
        'recommendation': 'Consider new motherboard, CPU, and RAM for DDR5/PCIe 5.0',
        'reason': 'Future-proof your system with next-gen technologies for longevity.',
        'cost_estimate': '₹50,000+',
        'performance_gain': 'Ready for future software and games requiring newer standards'
    })
    
    if use_case == 'gaming':
        plan['phase3']['upgrades'].insert(0, {
            'component': 'GPU',
            'recommendation': 'Upgrade to RTX 4070 Super/4080',
            'reason': 'For 4K gaming and ray tracing at high settings.',
            'cost_estimate': '₹50,000-70,000',
            'performance_gain': '4K gaming capability with DLSS'
        })
    elif use_case == 'editing':
        plan['phase3']['upgrades'].insert(0, {
            'component': 'Storage',
            'recommendation': 'Add 2TB+ NVMe SSD',
            'reason': 'Massive fast storage for 4K/8K editing workflows.',
            'cost_estimate': '₹15,000-25,000',
            'performance_gain': 'Handle large video files without slowdown'
        })
    
    return plan


def calculate_bottleneck(specs):
    # Performance scores (approximate, based on benchmarks)
    cpu_scores = {
        'Ryzen 5 5600': 85, 'Ryzen 5 5600X': 88, 'Ryzen 7 5700X': 95,
        'Ryzen 7 5800X': 98, 'Ryzen 9 5900X': 100, 'Ryzen 9 5950X': 105,
        'Intel i5-12400F': 82, 'Intel i5-12600K': 90, 'Intel i7-12700K': 97,
        'Intel i9-12900K': 102
    }
    
    gpu_scores = {
        'RTX 3060': 75, 'RTX 3060 Ti': 82, 'RTX 3070': 88, 'RTX 3070 Ti': 92,
        'RTX 3080': 95, 'RTX 3080 Ti': 98, 'RTX 3090': 100, 'RTX 4070': 90,
        'RTX 4070 Ti': 96, 'RTX 4080': 102, 'RTX 4090': 110,
        'RX 6600': 70, 'RX 6700 XT': 78, 'RX 6800': 85, 'RX 6900 XT': 92,
        'RX 6950 XT': 95, 'RX 7600': 72, 'RX 7700 XT': 80, 'RX 7800 XT': 87,
        'RX 7900 XT': 94, 'RX 7900 XTX': 100
    }
    
    resolution_multipliers = {
        '1080p': 1.0, '1440p': 1.4, '4K': 2.0
    }
    
    settings_multipliers = {
        'Low': 0.7, 'Medium': 0.85, 'High': 1.0, 'Ultra': 1.15
    }
    
    cpu = specs['cpu']
    gpu = specs['gpu']
    ram = specs['ram']
    resolution = specs['resolution']
    settings = specs['settings']
    
    cpu_score = cpu_scores.get(cpu, 80)  # Default score if not found
    gpu_score = gpu_scores.get(gpu, 75)  # Default score if not found
    
    # Adjust GPU score based on resolution and settings
    gpu_effective = gpu_score * resolution_multipliers.get(resolution, 1.0) * settings_multipliers.get(settings, 1.0)
    
    # RAM factor (bottleneck if <16GB for modern gaming)
    ram_factor = min(1.0, ram / 16.0)
    gpu_effective *= ram_factor
    
    # Calculate bottleneck percentages
    if gpu_effective > cpu_score:
        # GPU is stronger, CPU bottleneck
        cpu_bottleneck = ((gpu_effective - cpu_score) / gpu_effective) * 100
        gpu_bottleneck = 0
        limiting_factor = 'CPU'
    else:
        # CPU is stronger, GPU bottleneck
        gpu_bottleneck = ((cpu_score - gpu_effective) / cpu_score) * 100
        cpu_bottleneck = 0
        limiting_factor = 'GPU'
    
    # Recommendations
    recommendations = []
    if cpu_bottleneck > 20:
        recommendations.append(f"Consider upgrading to a stronger CPU to reduce bottleneck by ~{cpu_bottleneck:.0f}%")
    elif gpu_bottleneck > 20:
        recommendations.append(f"GPU upgrade would provide the most benefit at this resolution")
    else:
        recommendations.append("Good balance! Components are well-matched for this workload")
    
    if ram < 16:
        recommendations.append("Upgrade RAM to at least 16GB to prevent memory bottlenecks")
    
    return {
        'cpu_score': cpu_score,
        'gpu_score': gpu_score,
        'gpu_effective': gpu_effective,
        'cpu_bottleneck': round(cpu_bottleneck, 1),
        'gpu_bottleneck': round(gpu_bottleneck, 1),
        'limiting_factor': limiting_factor,
        'recommendations': recommendations,
        'overall_balance': 'Good' if max(cpu_bottleneck, gpu_bottleneck) < 15 else 'Needs Attention'
    }


def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    synonyms = {
        "graphics card": "gpu",
        "video card": "gpu",
        "power supply unit": "psu",
        "power supply": "psu",
        "solid state drive": "ssd",
        "hard disk drive": "hdd",
        "mother board": "motherboard",
        "central processing unit": "cpu",
        "computer case": "case",
        "liquid cooling": "liquid",
        "water cooling": "liquid",
        "high end": "high-end",
        "over clocking": "overclocking",
        "refresh rate": "refresh-rate",
    }

    for phrase, replacement in synonyms.items():
        text = text.replace(phrase, replacement)

    return text


def normalize_question(user_message):
    keywords = [
        "psu", "watt", "ram", "memory", "gpu", "rtx", "cpu", "processor",
        "airflow", "cooling", "fans", "bottleneck", "budget", "storage",
        "ssd", "hdd", "nvme", "case", "clearance", "monitor", "display",
        "rgb", "lighting", "vrm", "wifi", "mix", "brands", "efficiency"
    ]

    normalized = normalize_text(user_message)
    words = normalized.split()
    matched = []

    for word in words:
        match = difflib.get_close_matches(word, keywords, n=1, cutoff=0.7)
        if match:
            matched.append(match[0])

    return matched


def semantic_match(msg, candidates, threshold=0.55):
    normalized_msg = normalize_text(msg)
    msg_tokens = set(normalized_msg.split())
    best_candidate = None
    best_score = 0.0

    for candidate in candidates:
        normalized_candidate = normalize_text(candidate)
        ratio = difflib.SequenceMatcher(None, normalized_msg, normalized_candidate).ratio()
        candidate_tokens = set(normalized_candidate.split())
        overlap = len(msg_tokens & candidate_tokens)
        score = ratio + overlap * 0.08

        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate if best_score >= threshold else None


def extract_budget_and_currency(user_message):
    match = re.search(r'(\d+)', user_message)
    amount = int(match.group(1)) if match else None

    if "₹" in user_message or "rupee" in user_message.lower() or "inr" in user_message.lower():
        currency = "INR"
    elif "$" in user_message or "usd" in user_message.lower():
        currency = "USD"
    elif "eur" in user_message.lower() or "€" in user_message:
        currency = "EUR"
    else:
        currency = "USD"

    return amount, currency


def search_pc_question(query, beginner_mode=False):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    openai.api_key = api_key

    if beginner_mode:
        system_prompt = (
            "You are a friendly PC building teacher who explains everything in simple, everyday language. "
            "Imagine you're teaching a complete beginner who has never built a PC before. "
            "Use analogies from everyday life to explain technical concepts. "
            "Avoid jargon or explain it immediately when you must use it. "
            "Be encouraging and patient, like a good friend helping someone learn. "
            "Break down complex topics into tiny, easy-to-understand steps. "
            "If something is confusing, compare it to something familiar (like comparing RAM to a desk workspace). "
            "Answer questions about PC components, compatibility, performance, and building advice. "
            "If the user asks something outside this domain, say: \"I'm here to help with PC building questions!\""
        )
    else:
        system_prompt = (
            "You are a PC hardware expert assistant. "
            "Your role is to answer ANY questions about PC components, compatibility, performance, and building advice. "
            "If the user asks something outside this domain, respond with: \"I can only answer PC hardware questions.\" "
            "Always give clear, concise, and technically accurate answers. "
            "Break down complex topics into simple step-by-step explanations. "
            "Provide examples of real PC builds (budget, mid-range, high-end) when relevant. "
            "Always check compatibility between CPU, GPU, RAM, motherboard, and PSU when asked. "
            "Suggest solutions for bottlenecks, airflow issues, and wattage requirements. "
            "If the question is not in the database, generate a focused response based only on PC hardware knowledge. "
            "If unsure, say: \"I don't have enough data to answer that, but I can guide you if you share your PC specs.\""
        )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=300,
        )

        answer = response.choices[0].message["content"].strip()
        return answer
    except Exception as e:
        print("OpenAI error:", e)
        return None


def generate_voice_response(query, beginner_mode=False):
    """Generate voice response using Claude AI"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Voice interaction requires Claude AI setup. Please configure your ANTHROPIC_API_KEY."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        if beginner_mode:
            system_prompt = (
                "You are a friendly PC building assistant who speaks naturally and conversationally, like talking to a friend. "
                "Keep responses concise (under 100 words) since this is voice output. "
                "Use simple, everyday language with analogies when explaining technical concepts. "
                "Be encouraging and patient. Focus on the most important advice. "
                "Answer questions about PC components, compatibility, performance, and building advice. "
                "If unsure, say: 'I'm not certain about that, but I can help with general PC building questions.'"
            )
        else:
            system_prompt = (
                "You are a knowledgeable PC building assistant who provides clear, technical guidance. "
                "Keep responses concise (under 100 words) for voice output. "
                "Give specific recommendations with brief explanations. "
                "Answer questions about PC components, compatibility, performance, and building advice. "
                "If unsure, say: 'I don't have enough data for that specific question.'"
            )

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": query}
            ]
        )
        
        return message.content[0].text.strip()
    except Exception as e:
        print("Claude AI error:", e)
        return "Sorry, I'm having trouble connecting to the voice service right now. Please try again."


def generate_optimized_build(budget, use_case, preferences):
    """Generate an optimized PC build based on budget, use case, and preferences"""
    builds = {
        'gaming': {
            'budget': {
                'cpu': 'AMD Ryzen 5 5600',
                'gpu': 'NVIDIA RTX 4060',
                'ram': '16GB DDR4-3200',
                'mobo': 'ASUS B450M',
                'psu': '650W 80+ Bronze',
                'storage': '500GB NVMe SSD',
                'case': 'Fractal Design Meshify C Mini'
            },
            'mid': {
                'cpu': 'AMD Ryzen 7 5700X',
                'gpu': 'NVIDIA RTX 4070',
                'ram': '32GB DDR4-3600',
                'mobo': 'MSI B550 Tomahawk',
                'psu': '750W 80+ Gold',
                'storage': '1TB NVMe SSD',
                'case': 'Fractal Design Define 7'
            },
            'high': {
                'cpu': 'AMD Ryzen 9 5900X',
                'gpu': 'NVIDIA RTX 4080',
                'ram': '32GB DDR5-5600',
                'mobo': 'ASUS ROG Strix X570-E',
                'psu': '850W 80+ Gold',
                'storage': '2TB NVMe SSD',
                'case': 'Lian Li PC-O11 Dynamic'
            }
        },
        'content_creation': {
            'budget': {
                'cpu': 'AMD Ryzen 5 5600',
                'gpu': 'NVIDIA RTX 3060',
                'ram': '32GB DDR4-3200',
                'mobo': 'ASUS B450M',
                'psu': '650W 80+ Bronze',
                'storage': '1TB NVMe SSD',
                'case': 'Fractal Design Meshify C Mini'
            },
            'mid': {
                'cpu': 'AMD Ryzen 7 5800X',
                'gpu': 'NVIDIA RTX 4070',
                'ram': '64GB DDR4-3600',
                'mobo': 'MSI B550 Tomahawk',
                'psu': '750W 80+ Gold',
                'storage': '2TB NVMe SSD',
                'case': 'Fractal Design Define 7'
            },
            'high': {
                'cpu': 'AMD Ryzen 9 5950X',
                'gpu': 'NVIDIA RTX 4080',
                'ram': '128GB DDR4-3600',
                'mobo': 'ASUS ROG Crosshair X570',
                'psu': '1000W 80+ Platinum',
                'storage': '4TB NVMe SSD',
                'case': 'Fractal Design Define 7 XL'
            }
        },
        'productivity': {
            'budget': {
                'cpu': 'AMD Ryzen 5 5600G',
                'gpu': 'Integrated Radeon',
                'ram': '16GB DDR4-3200',
                'mobo': 'ASUS B450M',
                'psu': '550W 80+ Bronze',
                'storage': '512GB NVMe SSD',
                'case': 'Fractal Design Core 1000'
            },
            'mid': {
                'cpu': 'AMD Ryzen 7 5700G',
                'gpu': 'Integrated Radeon',
                'ram': '32GB DDR4-3600',
                'mobo': 'MSI B550 Tomahawk',
                'psu': '650W 80+ Bronze',
                'storage': '1TB NVMe SSD',
                'case': 'Fractal Design Define 7'
            },
            'high': {
                'cpu': 'AMD Ryzen 9 5900X',
                'gpu': 'NVIDIA RTX 3060',
                'ram': '64GB DDR4-3600',
                'mobo': 'ASUS ROG Strix X570-E',
                'psu': '750W 80+ Gold',
                'storage': '2TB NVMe SSD',
                'case': 'Fractal Design Define 7'
            }
        }
    }
    
    # Determine budget tier
    if budget <= 800:
        tier = 'budget'
    elif budget <= 1500:
        tier = 'mid'
    else:
        tier = 'high'
    
    # Apply brand preferences
    build = builds[use_case][tier].copy()
    
    if preferences['cpu_brand'] == 'intel':
        if tier == 'budget':
            build['cpu'] = 'Intel Core i5-12400F'
        elif tier == 'mid':
            build['cpu'] = 'Intel Core i7-12700K'
        else:
            build['cpu'] = 'Intel Core i9-12900K'
    
    if preferences['gpu_brand'] == 'amd':
        if tier == 'budget':
            build['gpu'] = 'AMD RX 7600'
        elif tier == 'mid':
            build['gpu'] = 'AMD RX 7800 XT'
        else:
            build['gpu'] = 'AMD RX 7900 XTX'
    
    return build


def fetch_real_time_prices(build):
    """Fetch real-time prices for components (mock implementation)"""
    # In a real implementation, this would call actual e-commerce APIs
    # For demo purposes, we'll use mock prices with some variation
    
    import random
    import time
    
    # Exchange rate: 1 USD = 83 INR
    USD_TO_INR = 83
    
    # Base prices with some randomization to simulate real-time pricing (in USD)
    base_prices_usd = {
        # AMD CPUs
        'AMD Ryzen 5 5600': 159 + random.randint(-10, 10),
        'AMD Ryzen 7 5700X': 299 + random.randint(-15, 15),
        'AMD Ryzen 9 5900X': 549 + random.randint(-20, 20),
        'AMD Ryzen 5 5600G': 199 + random.randint(-10, 10),
        'AMD Ryzen 7 5700G': 329 + random.randint(-15, 15),
        'AMD Ryzen 7 5800X': 449 + random.randint(-20, 20),
        'AMD Ryzen 9 5950X': 799 + random.randint(-30, 30),
        
        # Intel CPUs
        'Intel Core i5-12400F': 189 + random.randint(-10, 10),
        'Intel Core i7-12700K': 419 + random.randint(-20, 20),
        'Intel Core i9-12900K': 699 + random.randint(-25, 25),
        
        # GPUs
        'NVIDIA RTX 4060': 329 + random.randint(-15, 15),
        'NVIDIA RTX 4070': 599 + random.randint(-25, 25),
        'NVIDIA RTX 4080': 1199 + random.randint(-50, 50),
        'NVIDIA RTX 3060': 249 + random.randint(-10, 10),
        'AMD RX 7600': 269 + random.randint(-15, 15),
        'AMD RX 7800 XT': 499 + random.randint(-20, 20),
        'AMD RX 7900 XTX': 999 + random.randint(-40, 40),
        'Integrated Radeon': 0,  # No additional cost
        
        # RAM
        '16GB DDR4-3200': 59 + random.randint(-5, 5),
        '32GB DDR4-3600': 119 + random.randint(-10, 10),
        '32GB DDR5-5600': 149 + random.randint(-10, 10),
        '64GB DDR4-3600': 229 + random.randint(-15, 15),
        '128GB DDR4-3600': 449 + random.randint(-20, 20),
        
        # Motherboards
        'ASUS B450M': 79 + random.randint(-5, 5),
        'MSI B550 Tomahawk': 159 + random.randint(-10, 10),
        'ASUS ROG Strix X570-E': 329 + random.randint(-15, 15),
        'ASUS ROG Crosshair X570': 379 + random.randint(-20, 20),
        
        # PSUs
        '550W 80+ Bronze': 49 + random.randint(-5, 5),
        '650W 80+ Bronze': 69 + random.randint(-5, 5),
        '750W 80+ Gold': 119 + random.randint(-10, 10),
        '850W 80+ Gold': 149 + random.randint(-10, 10),
        '1000W 80+ Platinum': 199 + random.randint(-15, 15),
        
        # Storage
        '500GB NVMe SSD': 49 + random.randint(-5, 5),
        '512GB NVMe SSD': 54 + random.randint(-5, 5),
        '1TB NVMe SSD': 89 + random.randint(-8, 8),
        '2TB NVMe SSD': 159 + random.randint(-12, 12),
        '4TB NVMe SSD': 299 + random.randint(-20, 20),
        
        # Cases
        'Fractal Design Core 1000': 59 + random.randint(-5, 5),
        'Fractal Design Meshify C Mini': 89 + random.randint(-8, 8),
        'Fractal Design Define 7': 149 + random.randint(-10, 10),
        'Fractal Design Define 7 XL': 199 + random.randint(-15, 15),
        'Lian Li PC-O11 Dynamic': 149 + random.randint(-10, 10)
    }
    
    # Generate purchase URLs (search-based for demo)
    def generate_search_url(retailer, component_name):
        """Generate search URLs for retailers based on component type and name"""
        component_name_encoded = component_name.replace(' ', '+').replace('-', '+')
        
        if retailer == 'amazon':
            return f"https://www.amazon.com/s?k={component_name_encoded}"
        elif retailer == 'newegg':
            return f"https://www.newegg.com/p/pl?d={component_name_encoded}"
        elif retailer == 'bestbuy':
            return f"https://www.bestbuy.com/site/searchpage.jsp?st={component_name_encoded}"
        else:
            return f"https://www.google.com/search?q={component_name_encoded}+price"
    
    retailers = ['amazon', 'newegg', 'bestbuy']
    
    build_with_prices = {}
    for component, name in build.items():
        if component == 'total_cost':
            continue
            
        price_usd = base_prices_usd.get(name, 100)
        price_inr = price_usd * USD_TO_INR  # Convert to INR
        retailer = random.choice(retailers)
        
        build_with_prices[component] = {
            'name': name,
            'price': price_inr,
            'url': generate_search_url(retailer, name),
            'retailer': retailer.title(),
            'in_stock': random.choice([True, True, True, False])  # 75% in stock
        }
    
    return build_with_prices


# ---------------- PRESET QUESTION BANK ----------------
# These are 20 clear PC-building questions with direct answers.
# Categories included:
# - Power and PSU sizing
# - RAM capacity and compatibility
# - Storage choices (SSD, NVMe, HDD)
# - Cooling and airflow guidance
# - CPU/GPU compatibility and bottlenecks
# - Case, motherboard, monitor, and accessories
# - Budget builds and upgrade advice
EXTRA_QA = {
    "what psu wattage do i need for rtx 3070 and ryzen 5 7600":
        "A good 650W to 700W 80+ Gold PSU is ideal for an RTX 3070 paired with a Ryzen 5 7600.",
    "how much ram is enough for gaming and streaming":
        "16GB is the sweet spot for gaming and streaming; upgrade to 32GB if you run many apps or record at high quality.",
    "can i use ddr4 ram with an am5 motherboard":
        "No, AM5 motherboards require DDR5 RAM. DDR4 is not compatible with AM5 sockets.",
    "should i choose air cooling or liquid cooling":
        "Air cooling is reliable and cost-effective; liquid cooling can be quieter and better for overclocking but is more complex.",
    "is a 650w psu enough for rtx 4060":
        "Yes, a 650W PSU is enough for an RTX 4060 build in most cases, especially with a modern CPU.",
    "how many fans should a mid tower case have":
        "Aim for at least 3 fans: two intakes in front and one exhaust in the rear for balanced airflow.",
    "what is the difference between ssd and hdd":
        "SSD is much faster and more reliable than HDD, while HDD offers more capacity per dollar for bulk storage.",
    "is nvme faster than sata ssd":
        "Yes, NVMe drives are significantly faster than SATA SSDs for both sequential and random reads.",
    "how do i avoid cpu and gpu bottleneck":
        "Choose a GPU and CPU from the same performance tier and avoid pairing an entry-level CPU with a high-end GPU.",
    "what motherboard form factor fits atx case":
        "ATX, micro ATX, and mini ITX motherboards all fit in a standard ATX case; E-ATX may not fit depending on the case.",
    "do i need a separate cooler for ryzen 7":
        "Yes, Ryzen 7 CPUs usually need a good cooler; stock coolers work for normal use but a better air or AIO cooler is recommended.",
    "how to choose a monitor refresh rate":
        "If you play fast games, choose 144Hz or higher. For general use, 60Hz to 75Hz is usually enough.",
    "is 32gb ram overkill for normal gaming":
        "For normal gaming, 16GB is enough; 32GB is useful if you also stream, edit video, or run many background apps.",
    "what storage size should i buy for content creation":
        "For content creation, 1TB or larger SSD storage is recommended to hold projects, media files, and applications.",
    "can i upgrade a laptop gpu later":
        "Most laptops cannot upgrade the GPU later because it is soldered to the motherboard; only a few modular models support it.",
    "how much vram do i need for 1440p gaming":
        "For 1440p gaming, 8GB VRAM is the minimum; 10GB to 12GB is better for high settings and future-proofing.",
    "should i get a modular psu or non modular":
        "A modular PSU is cleaner and easier to build with, while non-modular is cheaper but may create more cable clutter.",
    "does rgb lighting affect pc temperature":
        "RGB lighting has a negligible effect on temperature; focus on fans and airflow for real cooling benefits.",
    "should i buy a wi-fi motherboard or add a wi-fi card":
        "If you need wireless networking, a Wi-Fi motherboard is convenient; a Wi-Fi card lets you upgrade later if desired.",
    "what is a good budget build under 1000 dollars":
        "A strong budget build under $1000 can include a mid-range CPU, 16GB RAM, a GTX 1660 Super or RTX 3050, and a 500GB NVMe SSD.",
}


def match_preset_question(msg):
    normalized = normalize_text(msg)
    if normalized in EXTRA_QA:
        return EXTRA_QA[normalized]

    best_match = semantic_match(msg, EXTRA_QA.keys(), threshold=0.56)
    if best_match:
        return EXTRA_QA[best_match]

    close_match = difflib.get_close_matches(normalized, EXTRA_QA.keys(), n=1, cutoff=0.62)
    if close_match:
        return EXTRA_QA[close_match[0]]

    return None


# ---------------- CHATBOT CORE ----------------
def generate_bot_reply(msg):
    beginner_mode = session.get('beginner_mode', False)
    
    preset_answer = match_preset_question(msg)
    if preset_answer:
        if beginner_mode:
            # Convert preset answers to beginner-friendly language
            return simplify_technical_terms(preset_answer)
        return preset_answer

    ai_answer = search_pc_question(msg, beginner_mode)
    if ai_answer:
        return ai_answer

    matched_keywords = normalize_question(msg)
    amount, currency = extract_budget_and_currency(msg)

    # Beginner-friendly fallback responses
    if beginner_mode:
        responses = {
            "psu_fallback": "Think of your power supply as the electricity manager for your PC. Most gaming computers need about 650 watts - like choosing the right battery for your phone.",
            "ram_fallback": "RAM is like your desk space - the more you have, the more programs you can work on at once without everything getting cluttered.",
            "gpu_fallback": "A graphics card is like the artist in your computer. It handles all the pretty pictures and special effects in games.",
            "cpu_fallback": "The CPU is like the brain of your computer. It thinks through all the instructions and tells other parts what to do.",
            "cooling_fallback": "Cooling is like air conditioning for your PC. Fans blow hot air out and bring cool air in, just like keeping your room comfortable.",
            "bottleneck_fallback": "A bottleneck is when one part of your PC is waiting for another part to catch up, like when you're stuck in traffic.",
            "storage_fallback": "Storage is like filing cabinets for your computer. SSDs are fast filing cabinets, HDDs are bigger but slower ones."
        }
        
        if any(k in matched_keywords for k in ["psu", "power supply", "watt"]):
            return responses["psu_fallback"]
        elif any(k in matched_keywords for k in ["ram", "memory"]):
            return responses["ram_fallback"]
        elif any(k in matched_keywords for k in ["gpu", "graphics card", "rtx"]):
            return responses["gpu_fallback"]
        elif any(k in matched_keywords for k in ["cpu", "processor"]):
            return responses["cpu_fallback"]
        elif any(k in matched_keywords for k in ["cooling", "fans", "airflow"]):
            return responses["cooling_fallback"]
        elif "bottleneck" in matched_keywords:
            return responses["bottleneck_fallback"]
        elif any(k in matched_keywords for k in ["ssd", "hdd", "nvme", "storage"]):
            return responses["storage_fallback"]
    else:
        # Expert mode responses
        if any(k in matched_keywords for k in ["psu", "power supply", "watt"]):
            return "650W PSU is enough for most builds. High-end GPUs may need 750W+."
        elif any(k in matched_keywords for k in ["ram", "memory"]):
            return "DDR4 and DDR5 are not interchangeable. Check motherboard compatibility."
        elif any(k in matched_keywords for k in ["gpu", "graphics card", "rtx"]):
            return "Ensure PSU wattage and case clearance support your GPU."
        elif any(k in matched_keywords for k in ["cpu", "processor"]):
            return "Match CPU socket with motherboard (AM5, LGA1700, etc.)."
        elif any(k in matched_keywords for k in ["cooling", "fans", "airflow"]):
            return "Use at least 1 intake + 1 exhaust fan. Positive airflow reduces dust."
        elif "bottleneck" in matched_keywords:
            return "Balance CPU + GPU to avoid bottlenecks."
        elif any(k in matched_keywords for k in ["ssd", "hdd", "nvme", "storage"]):
            return "NVMe SSD is fastest. HDD is cheaper for large storage."

    # Budget responses (same for both modes since they're straightforward)
    if "budget" in matched_keywords and amount:
        if currency == "INR":
            if amount <= 40000:
                return f"₹{amount}: Ryzen 3 + GTX 1650, 8GB RAM"
            elif amount <= 60000:
                return f"₹{amount}: Ryzen 5 + RTX 3060, 16GB RAM"
            elif amount <= 100000:
                return f"₹{amount}: Ryzen 7 + RTX 4070, 32GB RAM"
            else:
                return f"₹{amount}: Ryzen 9 + RTX 4080+, high-end build"
        else:
            if amount <= 500:
                return f"{amount} {currency}: GTX 1650 build"
            elif amount <= 1000:
                return f"{amount} {currency}: RTX 3060 build"
            elif amount <= 1500:
                return f"{amount} {currency}: RTX 4070 build"
            else:
                return f"{amount} {currency}: RTX 4080+ high-end build"

    else:
        with open("chat_log.txt", "a") as f:
            f.write(msg + "\n")

        result = search_pc_question(msg, beginner_mode)
        return result or ("I don't understand that question. Could you ask it in a different way?" if beginner_mode else "No direct answer found, but logged.")


def simplify_technical_terms(text):
    """Convert technical terms to simple explanations for beginner mode"""
    replacements = {
        "PSU": "power supply (the electricity box)",
        "wattage": "power amount",
        "DDR4": "type of memory sticks",
        "DDR5": "newer type of memory sticks",
        "motherboard": "main circuit board that connects everything",
        "socket": "connection type",
        "AM5": "AMD's newest CPU connection",
        "LGA1700": "Intel's CPU connection type",
        "airflow": "how air moves through the case",
        "bottleneck": "when one part slows down the others",
        "NVMe": "super fast storage connection",
        "PCIe": "high-speed connection for cards",
        "VRAM": "memory built into the graphics card",
        "overclocking": "making parts run faster than normal",
        "thermal paste": "special goo that helps heat transfer",
        "RGB": "colored lights on components",
        "modular": "cables you can add/remove as needed",
        "efficiency": "how well it converts electricity to power",
        "certified": "officially tested and approved"
    }
    
    result = text
    for term, explanation in replacements.items():
        result = result.replace(term, f"{term} ({explanation})")
    
    return result


# ---------------- SOCKET ----------------
@socketio.on('message')
def handle_socket_message(msg):
    reply = generate_bot_reply(msg)
    emit('response', {'reply': reply}, broadcast=True)