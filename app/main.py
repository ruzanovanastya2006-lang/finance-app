from flask import render_template, redirect, url_for
from flask_login import current_user
from . import db


def register_main(app):
    @app.route('/home')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('index.html')
