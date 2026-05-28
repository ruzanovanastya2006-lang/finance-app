from flask import render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from ..models import db, Category, Transaction
from . import categories


def _user_category_or_404(cat_id):
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first()
    if not cat:
        from flask import abort
        abort(404)
    return cat


@categories.route('/')
@login_required
def index():
    default_cats = Category.query.filter_by(is_default=True).order_by(Category.name).all()
    user_cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    hidden_ids = {c.id for c in user_cats if c.is_hidden}
    return render_template('categories/index.html',
                           default_cats=default_cats,
                           user_cats=[c for c in user_cats if not c.is_default],
                           hidden_ids=hidden_ids)


@categories.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form.get('name', '').strip()
    limit_str = request.form.get('monthly_limit', '0').strip()
    color = request.form.get('color', '#9E9E9E').strip()
    icon = request.form.get('icon', '📦').strip()

    if not name:
        flash('Название категории не может быть пустым.', 'danger')
        return redirect(url_for('categories.index'))

    exists = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.is_default == True),
        Category.name == name
    ).first()
    if exists:
        flash('Категория с таким названием уже существует.', 'danger')
        return redirect(url_for('categories.index'))

    try:
        limit = float(limit_str.replace(',', '.')) if limit_str else 0
        if limit < 0:
            limit = 0
    except ValueError:
        limit = 0

    cat = Category(user_id=current_user.id, name=name,
                   monthly_limit=limit, color=color, icon=icon)
    db.session.add(cat)
    db.session.commit()
    flash(f'Категория «{name}» создана.', 'success')
    return redirect(url_for('categories.index'))


@categories.route('/<int:cat_id>/edit', methods=['POST'])
@login_required
def edit(cat_id):
    cat = _user_category_or_404(cat_id)
    name = request.form.get('name', '').strip()
    limit_str = request.form.get('monthly_limit', '0').strip()
    color = request.form.get('color', cat.color).strip()
    icon = request.form.get('icon', cat.icon).strip()

    if not name:
        flash('Название категории не может быть пустым.', 'danger')
        return redirect(url_for('categories.index'))

    try:
        limit = float(limit_str.replace(',', '.')) if limit_str else 0
    except ValueError:
        limit = 0

    cat.name = name
    cat.monthly_limit = limit
    cat.color = color
    cat.icon = icon
    db.session.commit()
    flash(f'Категория «{name}» обновлена.', 'success')
    return redirect(url_for('categories.index'))


@categories.route('/<int:cat_id>/delete', methods=['POST'])
@login_required
def delete(cat_id):
    cat = _user_category_or_404(cat_id)
    # переносим транзакции в "Прочее"
    other = Category.query.filter_by(name='Прочее', is_default=True).first()
    if other:
        Transaction.query.filter_by(
            user_id=current_user.id, category_id=cat.id
        ).update({'category_id': other.id})
    db.session.delete(cat)
    db.session.commit()
    flash('Категория удалена. Операции перенесены в «Прочее».', 'success')
    return redirect(url_for('categories.index'))


@categories.route('/<int:cat_id>/toggle-hide', methods=['POST'])
@login_required
def toggle_hide(cat_id):
    """Скрыть/показать стандартную категорию."""
    cat = Category.query.filter_by(id=cat_id, is_default=True).first_or_404()
    # создаём пользовательский override если его нет
    user_override = Category.query.filter_by(
        user_id=current_user.id, name=cat.name
    ).first()
    if user_override:
        user_override.is_hidden = not user_override.is_hidden
    else:
        override = Category(
            user_id=current_user.id, name=cat.name,
            color=cat.color, icon=cat.icon,
            is_hidden=True, is_default=False
        )
        db.session.add(override)
    db.session.commit()
    return redirect(url_for('categories.index'))


@categories.route('/set-limit', methods=['POST'])
@login_required
def set_limit():
    """Установить лимит на стандартную или пользовательскую категорию через JSON."""
    data = request.get_json()
    cat_id = data.get('cat_id')
    limit = data.get('limit', 0)
    cat = Category.query.get_or_404(cat_id)
    if cat.user_id and cat.user_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403
    cat.monthly_limit = limit
    db.session.commit()
    return jsonify({'ok': True})
