from flask import Blueprint, render_template, redirect, url_for, session
from models import db, User   # ✅ import from models, not app

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    if session.get('username') != 'admin':
        return redirect('/login')

    users = User.query.all()
    return render_template('admin/dashboard.html', users=users)