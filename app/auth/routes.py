from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User
from . import auth


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        surname = request.form.get('surname', '').strip()
        birth_date_str = request.form.get('birth_date', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not email or not name or not password:
            flash('Заполните все обязательные поля.', 'danger')
            return render_template('auth/register.html')

        if password != confirm:
            flash('Пароли не совпадают.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Пароль должен содержать не менее 6 символов.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже зарегистрирован.', 'danger')
            return render_template('auth/register.html')

        user = User(email=email, name=name, surname=surname or None)
        if birth_date_str:
            from datetime import date
            try:
                year, month, day = map(int, birth_date_str.split('-'))
                user.birth_date = date(year, month, day)
            except ValueError:
                flash('Некорректная дата рождения.', 'danger')
                return render_template('auth/register.html')
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Добро пожаловать, {user.name}!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Неверный email или пароль.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.index'))

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
