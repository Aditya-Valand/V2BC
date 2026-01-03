from flask import Flask, render_template, request, redirect, url_for
import database

app = Flask(__name__)

# Setup the database table when we start the app
database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
