from datetime import date
from flask import render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from ..models import db, Transaction, Category
from ..notifications.service import check_limits_after_transaction
from . import operations


def _get_user_categories():
    return Category.query.filter(
        (Category.user_id == current_user.id) | (Category.is_default == True),
        Category.is_hidden == False,
    ).order_by(Category.name).all()


@operations.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        return _save_transaction()
    cats = _get_user_categories()
    return render_template('operations/form.html', cats=cats, tx=None,
                           today=str(date.today()))


@operations.route('/<int:tx_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        return _save_transaction(tx)
    cats = _get_user_categories()
    return render_template('operations/form.html', cats=cats, tx=tx,
                           today=str(date.today()))


@operations.route('/<int:tx_id>/delete', methods=['POST'])
@login_required
def delete(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    db.session.delete(tx)
    db.session.commit()
    if request.is_json:
        return jsonify({'ok': True})
    flash('Операция удалена.', 'success')
    return redirect(url_for('dashboard.index'))


def _save_transaction(tx=None):
    amount_str = request.form.get('amount', '').strip()
    category_id = request.form.get('category_id', type=int)
    tx_type = request.form.get('type', 'expense')
    date_str = request.form.get('date', str(date.today())).strip()
    comment = request.form.get('comment', '').strip()

    errors = []
    if not amount_str:
        errors.append('Введите сумму.')
    else:
        try:
            amount = float(amount_str.replace(',', '.'))
            if amount <= 0:
                errors.append('Сумма должна быть положительным числом.')
        except ValueError:
            errors.append('Введите числовое значение для суммы.')

    if not category_id:
        errors.append('Выберите категорию.')

    try:
        tx_date = date.fromisoformat(date_str)
        if tx_date > date.today():
            errors.append('Дата операции не может быть позже текущей.')
    except ValueError:
        errors.append('Некорректный формат даты. Используйте YYYY-MM-DD.')
        tx_date = date.today()

    if tx_type not in ('income', 'expense'):
        tx_type = 'expense'

    if errors:
        for e in errors:
            flash(e, 'danger')
        cats = _get_user_categories()
        return render_template('operations/form.html', cats=cats, tx=tx,
                               today=str(date.today()))

    if tx is None:
        tx = Transaction(user_id=current_user.id)
        db.session.add(tx)

    tx.amount = amount
    tx.category_id = category_id
    tx.type = tx_type
    tx.date = tx_date
    tx.comment = comment or None
    db.session.commit()

    if tx_type == 'expense':
        check_limits_after_transaction(current_user.id, category_id)

    flash('Операция сохранена.', 'success')
    return redirect(url_for('dashboard.index'))
