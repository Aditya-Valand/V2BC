from flask import Blueprint, render_template
from database.user import get_user_by_email
from middlewares import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(user):
    return render_template('dashboard.html', user=user)
