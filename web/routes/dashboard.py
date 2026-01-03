from flask import Blueprint, render_template, redirect, url_for
from database.user import get_user_by_email
from middlewares import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(user):
    if user['profile'] == 0:
        return redirect(url_for('dashboard.profile'))
    return render_template('dashboard.html', user=user)


@dashboard_bp.route('/profile', methods=['GET'])
@token_required
def profile(user):
    return render_template('profile.html', user=user)
