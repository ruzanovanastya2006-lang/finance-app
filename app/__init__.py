import os
from flask import Flask
from flask_login import LoginManager
from .models import db, User, Category, DEFAULT_CATEGORIES
from config import Config


login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # редирект на форму входа
login_manager.login_message = 'Пожалуйста, войдите в систему.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth as auth_bp
    from .dashboard import dashboard as dashboard_bp
    from .operations import operations as operations_bp
    from .categories import categories as categories_bp
    from .reports import reports as reports_bp
    from .notifications import notifications as notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    from flask import render_template, redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('index.html')
    app.register_blueprint(operations_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()
        _seed_default_categories()

    _start_scheduler(app)

    return app


def _start_scheduler(app):
    """Запускает APScheduler для еженедельной email-сводки."""
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return  # запускаем только в основном процессе (не в reload-процессе)

    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone='Europe/Moscow')
    scheduler.add_job(
        func=lambda: _send_weekly_summaries(app),
        trigger='cron',
        day_of_week='mon',
        hour=9,
        minute=0,
        id='weekly_summary',
        replace_existing=True,
    )
    scheduler.start()


def _send_weekly_summaries(app):
    """Отправляет еженедельную сводку всем пользователям."""
    from datetime import date, timedelta
    from sqlalchemy import func
    from .models import Transaction, Category
    from .email_service import send_weekly_summary

    with app.app_context():
        users = User.query.all()
        today = date.today()
        week_start = today - timedelta(days=6)

        for user in users:
            try:
                txs = Transaction.query.filter(
                    Transaction.user_id == user.id,
                    Transaction.date >= week_start,
                    Transaction.date <= today,
                ).all()

                income = sum(float(t.amount) for t in txs if t.type == 'income')
                expense = sum(float(t.amount) for t in txs if t.type == 'expense')

                # расходы по категориям
                cat_totals = {}
                for tx in txs:
                    if tx.type == 'expense' and tx.category:
                        cat_totals.setdefault(tx.category.name, 0)
                        cat_totals[tx.category.name] += float(tx.amount)

                by_category = sorted(
                    [{'name': k, 'amount': v} for k, v in cat_totals.items()],
                    key=lambda x: x['amount'], reverse=True
                )

                send_weekly_summary(
                    to_email=user.email,
                    user_name=user.name,
                    summary={'income': income, 'expense': expense,
                             'balance': income - expense, 'by_category': by_category},
                )
            except Exception:
                pass


def _seed_default_categories():
    if Category.query.filter_by(is_default=True).first():
        return
    for cat in DEFAULT_CATEGORIES:
        db.session.add(Category(
            name=cat['name'],
            color=cat['color'],
            icon=cat['icon'],
            is_default=True,
            user_id=None,
        ))
    db.session.commit()
