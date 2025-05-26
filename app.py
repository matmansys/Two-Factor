from flask import Flask, render_template, request, jsonify, render_template_string
from flask_mail import Mail, Message
import pandas as pd
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

USERS_CSV = 'users.csv'
OTP_STORE = {}

# Ensure users.csv exists
def load_users():
    try:
        return pd.read_csv(USERS_CSV)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['name', 'email', 'password'])
        df.to_csv(USERS_CSV, index=False)
        return df

def save_user(name, email, password):
    df = load_users()
    email = email.lower()
    if email in df['email'].str.lower().values:
        return False
    df = pd.concat([df, pd.DataFrame([{'name': name, 'email': email, 'password': password}])], ignore_index=True)
    df.to_csv(USERS_CSV, index=False)
    return True

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not (name and email and password):
        return jsonify({'status': 'fail', 'message': 'Please fill all fields'})

    if save_user(name, email, password):
        return jsonify({'status': 'success', 'message': 'Registered successfully'})
    else:
        return jsonify({'status': 'fail', 'message': 'Email already registered'})

@app.route('/signin', methods=['POST'])
def signin():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    df = load_users()
    user = df[(df['email'].str.lower() == email) & (df['password'] == password)]

    if user.empty:
        return jsonify({'status': 'fail', 'message': "You aren't registered, please sign up."})

    otp = random.randint(100000, 999999)
    OTP_STORE[email] = {'otp': otp, 'expires': datetime.now() + timedelta(minutes=5)}

    try:
        html_body = render_template('otp_email.html', otp=otp)
        msg = Message('🔐 Your OTP Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.html = html_body
        mail.send(msg)
    except Exception as e:
        print('Mail error:', e)
        return jsonify({'status': 'fail', 'message': 'Failed to send OTP.'})

    return jsonify({'status': 'otp_sent', 'message': 'OTP sent to your email.'})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email', '').strip().lower()
    otp = str(data.get('otp', '')).strip()

    entry = OTP_STORE.get(email)
    if not entry:
        return jsonify({'status': 'fail', 'message': 'No OTP sent. Please login again.'})

    if datetime.now() > entry['expires']:
        OTP_STORE.pop(email)
        return jsonify({'status': 'fail', 'message': 'OTP expired. Login again.'})

    if str(entry['otp']) == otp:
        OTP_STORE.pop(email)
        return jsonify({'status': 'success', 'message': 'OTP verified!'})
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid OTP.'})

if __name__ == '__main__':
    app.run(debug=True)
