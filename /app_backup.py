import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for session handling

# Keep sessions alive for 7 days
app.permanent_session_lifetime = timedelta(days=7)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.password and check_password_hash(user.password, password):
            session['username'] = username
            session.permanent = True
            return redirect(url_for('home'))
        else:
            return "❌ Invalid username or password. Try again."

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()

        if existing_user:
            return "⚠️ Username already exists. Try another."
        elif existing_email:
            return "⚠️ Email already registered. Try another."
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        return render_template('profile.html', username=user.username, email=user.email)
    else:
        return redirect(url_for('login'))

@app.route('/pcbuilder', methods=['GET', 'POST'])
def pcbuilder():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_message = request.form['message'].lower()

        # Simple rules-based responses
        if "psu" in user_message or "power supply" in user_message:
            bot_reply = "For most mid-range builds, a 650W PSU is sufficient. High-end GPUs may need 750W or more."
        elif "ram" in user_message:
            bot_reply = "Check your motherboard’s QVL list. DDR4 and DDR5 are not interchangeable."
        elif "gpu" in user_message or "graphics card" in user_message:
            bot_reply = "Ensure your case has clearance and your PSU can handle the GPU’s power draw."
        elif "cpu" in user_message:
            bot_reply = "Match your CPU with the correct motherboard socket (Intel LGA1700, AMD AM5, etc.)."
        elif "airflow" in user_message or "cooling" in user_message:
            bot_reply = "Good airflow means at least one intake and one exhaust fan. Positive pressure helps reduce dust."
        else:
            bot_reply = "I’ll need more details. Try asking about PSU, RAM, GPU, CPU, or airflow!"

        return jsonify({'reply': bot_reply})

    return render_template('pcbuilder.html', page_class="pcbuilder-page", username=session['username'])

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['new_password']

        user = User.query.filter_by(email=email).first()
        if user:
            # ✅ Store hashed password instead of plain text
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return "✅ Password updated successfully. Please log in."
        else:
            return "❌ Email not found."

    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)