from core.extensions import db
from modules.auth.models import User
from core.security import hash_password, verify_password

def create_user(name, email, password, role="CA"):
    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    return user

def authenticate(email, password):
    user = User.query.filter_by(email=email).first()
    if user and verify_password(password, user.password):
        return user
    return None
