from flask import Blueprint, request, jsonify, url_for, make_response, redirect
from database.user import create_user, verify_user
from services.jwt import create_token
from middlewares import guest

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signin', methods=['GET', 'POST'])
@guest
def signin():
    if request.method == 'GET':
        return redirect(url_for('index'))

    # 1. Parse JSON data from the Alpine fetch request
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    email = data.get('email')
    password = data.get('password')

    # 2. Verify with hashed password logic
    if verify_user(email, password):
        token = create_token(email)

        response = make_response(jsonify({
            "success": True,
            "message": "Login successful",
            "redirect": url_for('dashboard.dashboard')
        }))

        # Set the JWT in a secure cookie
        response.set_cookie(
            'auth_token',
            token,
            httponly=True,   # Prevents JS access
            samesite='Lax',  # CSRF protection
            max_age=86400    # 1 day in seconds
        )

        return response, 200

    return jsonify({"success": False, "message": "Invalid email or password"}), 401


@auth_bp.route('/signup', methods=['GET', 'POST'])
@guest
def signup():
    if request.method == 'GET':
        return redirect(url_for('index'))

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    # 3. Validation
    if not all([name, email, password]):
        return jsonify({"success": False, "message": "All fields are required"}), 400

    try:
        # This calls your function that hashes the PW and saves it
        create_user(name, email, password)
        return jsonify({
            "success": True,
            "message": "Account created! You can now sign in.",
            "redirect": url_for('auth.signin')
        }), 201
    except Exception as e:
        return jsonify({"success": False, "message": "User already exists or database error"}), 409


@auth_bp.route('/signout', methods=['POST'])
def signout():
    response = make_response(redirect(url_for('auth.signin')))
    response.set_cookie('auth_token', '', expires=0)
    return response
