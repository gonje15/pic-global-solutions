import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv

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


# --- Database Model ---
class ContactSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}


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


if __name__ == '__main__':
    app.run(debug=True)