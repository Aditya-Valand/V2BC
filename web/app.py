import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
import database.config as db_config
from routes.transactions import transactions_bp
from middlewares import guest
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')


# Routes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/')
app.register_blueprint(transactions_bp, url_prefix='/')

# Setup the database table when we start the app
db_config.init_db()

@app.route('/')
@guest
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
