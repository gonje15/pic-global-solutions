from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
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

