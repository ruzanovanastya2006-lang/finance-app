from datetime import date, timedelta
from calendar import monthrange
from flask import render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from ..models import db, Transaction, Category, Notification
from ..notifications.service import get_unread_count
from . import dashboard


def _get_month_range(year: int, month: int):
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def _get_analytics(user_id: int, year: int, month: int) -> dict:
    first, last = _get_month_range(year, month)

    def sum_by_type(t):
        return float(db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == t,
            Transaction.date >= first,
            Transaction.date <= last,
        ).scalar() or 0)

    income = sum_by_type('income')
    expense = sum_by_type('expense')
    balance = income - expense

    # сравнение с предыдущим месяцем
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    prev_first, prev_last = _get_month_range(prev_year, prev_month)
    prev_expense = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= prev_first,
        Transaction.date <= prev_last,
    ).scalar() or 0)

    expense_diff_pct = None
    if prev_expense > 0:
        expense_diff_pct = round((expense - prev_expense) / prev_expense * 100, 1)

    # расходы по категориям
    cats = (db.session.query(
        Category.id, Category.name, Category.color, Category.icon,
        Category.monthly_limit,
        func.sum(Transaction.amount).label('spent')
    ).join(Transaction, (Transaction.category_id == Category.id) &
                        (Transaction.user_id == user_id) &
                        (Transaction.type == 'expense') &
                        (Transaction.date >= first) &
                        (Transaction.date <= last))
    .group_by(Category.id)
    .all())

    # все видимые категории пользователя (для прогресс-баров)
    all_cats = Category.query.filter(
        ((Category.user_id == user_id) | (Category.is_default == True)),
        Category.is_hidden == False,
    ).all()

    cat_stats = []
    spent_map = {c.id: float(c.spent) for c in cats}
    for c in all_cats:
        spent = spent_map.get(c.id, 0)
        limit = float(c.monthly_limit) if c.monthly_limit else 0
        pct = round(spent / limit * 100, 1) if limit > 0 else None
        cat_stats.append({
            'id': c.id, 'name': c.name, 'color': c.color, 'icon': c.icon,
            'spent': spent, 'limit': limit, 'pct': pct,
        })

    # динамика расходов по дням
    daily = (db.session.query(
        Transaction.date, func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= first,
        Transaction.date <= last,
    ).group_by(Transaction.date).order_by(Transaction.date).all())

    daily_labels = [str(r.date) for r in daily]
    daily_values = [float(r.total) for r in daily]

    # данные для круговой диаграммы
    pie_labels = [c.name for c in cats if float(c.spent) > 0]
    pie_values = [float(c.spent) for c in cats if float(c.spent) > 0]
    pie_colors = [c.color for c in cats if float(c.spent) > 0]

    return {
        'income': income,
        'expense': expense,
        'balance': balance,
        'expense_diff_pct': expense_diff_pct,
        'cat_stats': cat_stats,
        'daily_labels': daily_labels,
        'daily_values': daily_values,
        'pie_labels': pie_labels,
        'pie_values': pie_values,
        'pie_colors': pie_colors,
    }


@dashboard.route('/')
@login_required
def index():
    today = date.today()
    try:
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))
        if not (1 <= month <= 12) or year < 2000:
            raise ValueError
    except ValueError:
        year, month = today.year, today.month

    analytics = _get_analytics(current_user.id, year, month)

    # последние 20 операций
    first, last = _get_month_range(year, month)
    page = request.args.get('page', 1, type=int)
    filter_cat = request.args.get('cat', type=int)
    filter_type = request.args.get('type', '')
    date_from = request.args.get('date_from', str(first))
    date_to = request.args.get('date_to', str(last))

    q = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    )
    if filter_cat:
        q = q.filter(Transaction.category_id == filter_cat)
    if filter_type in ('income', 'expense'):
        q = q.filter(Transaction.type == filter_type)
    transactions = q.order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(50).all()

    # категории для фильтра
    user_cats = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.is_default == True),
        Category.is_hidden == False,
    ).order_by(Category.name).all()

    # уведомления
    unread = get_unread_count(current_user.id)
    notifications = (Notification.query
                     .filter_by(user_id=current_user.id, is_read=False)
                     .order_by(Notification.created_at.desc())
                     .limit(10).all())

    # навигация по месяцам
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    MONTHS_RU = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                 'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

    return render_template(
        'dashboard/index.html',
        analytics=analytics,
        transactions=transactions,
        user_cats=user_cats,
        unread=unread,
        notifications=notifications,
        year=year, month=month,
        month_name=MONTHS_RU[month - 1],
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        filter_cat=filter_cat, filter_type=filter_type,
        date_from=date_from, date_to=date_to,
        today=today,
    )


@dashboard.route('/analytics-data')
@login_required
def analytics_data():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    return jsonify(_get_analytics(current_user.id, year, month))
