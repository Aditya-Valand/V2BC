from flask import Flask, render_template, request, redirect, url_for
import database.config as db_config
from middlewares import guest
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'


# Routes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/')

# Setup the database table when we start the app
db_config.init_db()

@app.route('/')
@guest
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
