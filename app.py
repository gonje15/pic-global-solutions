import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()  # reads variables from .env into the environment

app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

db = SQLAlchemy(app)
mail = Mail(app)
gemini_client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))


# --- Database Model ---
class ContactSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


# --- Gemini Helper ---
def ask_gemini(prompt, retries=3):
    for attempt in range(retries):
        try:
            response = gemini_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            return response.text
        except errors.ServerError:
            time.sleep(2 * (attempt + 1))
    return None


@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}


# --- Page Routes ---
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        # Save to database
        submission = ContactSubmission(name=name, email=email, phone=phone, message=message)
        db.session.add(submission)
        db.session.commit()

        # Send email notification
        msg = Message(
            subject=f'New Contact Form Submission from {name}',
            recipients=[app.config['MAIL_USERNAME']],
            body=f'Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}'
        )
        mail.send(msg)

        flash('Thanks for reaching out! We\'ll be in touch soon.', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


@app.route('/why_us')
def why_us():
    return render_template('why_us.html')


@app.route('/services')
def services():
    return render_template('services/index.html')


@app.route('/services/consultancy')
def consultancy():
    return render_template('services/consultancy.html')


@app.route('/services/marketing')
def marketing():
    return render_template('services/marketing.html')


@app.route('/services/supply')
def supply():
    return render_template('services/supply.html')


# --- API Routes ---
@app.route('/api/service-fit', methods=['POST'])
def service_fit():
    data = request.get_json()
    description = (data.get('description') or '').strip()

    if not description:
        return jsonify({'error': 'Please describe your business situation first.'}), 400

    if len(description) > 500:
        return jsonify({'error': 'Please keep your description under 500 characters.'}), 400

    prompt = f"""You are a service-recommendation assistant for P.I.C Global Solutions, a consultancy offering exactly three services:
1. Supply of Goods — sourcing and procurement of goods
2. Business Consultancy & Advisory — accounting, tax, audit, business strategy
3. Marketing & Business Development — visibility, lead generation, growth strategy

Based on the business situation below, recommend ONE of these three services (or note if it's a mix of two, but never all three). Keep your response to 2-3 friendly, specific sentences. Do not recommend anything outside this list of three services, and do not make claims about pricing or timelines.

Business situation: {description}"""

    result = ask_gemini(prompt)

    if result is None:
        return jsonify({'error': 'Our assistant is temporarily busy. Please try again in a moment.'}), 503

    return jsonify({'recommendation': result})


if __name__ == '__main__':
    app.run(debug=True)