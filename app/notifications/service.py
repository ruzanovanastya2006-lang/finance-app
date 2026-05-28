from datetime import date
from sqlalchemy import func
from ..models import db, Transaction, Category, Notification

THRESHOLDS = [80, 90, 100]


def check_limits_after_transaction(user_id: int, category_id: int):
    """Проверяет лимиты после добавления/редактирования транзакции и создаёт уведомления."""
    category = Category.query.get(category_id)
    if not category or not category.monthly_limit or float(category.monthly_limit) <= 0:
        return []

    today = date.today()
    month_start = today.replace(day=1)

    spent = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.category_id == category_id,
        Transaction.type == 'expense',
        Transaction.date >= month_start,
        Transaction.date <= today,
    ).scalar() or 0

    limit = float(category.monthly_limit)
    percent = (float(spent) / limit) * 100

    new_notifications = []
    for threshold in THRESHOLDS:
        if percent >= threshold:
            exists = Notification.query.filter_by(
                user_id=user_id,
                category_id=category_id,
                threshold=threshold,
            ).filter(
                func.date_trunc('month', Notification.created_at) ==
                func.date_trunc('month', func.now())
            ).first()

            if not exists:
                if threshold == 100:
                    msg = (f'Превышение лимита по категории «{category.name}»: '
                           f'потрачено {float(spent):.0f} ₽ из {limit:.0f} ₽ '
                           f'({percent:.0f}%).')
                else:
                    msg = (f'Внимание: использовано {percent:.0f}% лимита '
                           f'по категории «{category.name}» '
                           f'({float(spent):.0f} ₽ из {limit:.0f} ₽).')

                notif = Notification(
                    user_id=user_id,
                    category_id=category_id,
                    message=msg,
                    threshold=threshold,
                )
                db.session.add(notif)
                new_notifications.append((notif, threshold, float(spent), limit, percent))

    if new_notifications:
        db.session.commit()
        _send_limit_emails(user_id, new_notifications)

    return [n for n, *_ in new_notifications]


def _send_limit_emails(user_id, notifications_data):
    """Отправляет email-уведомления о превышении лимитов."""
    from ..models import User
    from ..email_service import send_limit_notification

    user = User.query.get(user_id)
    if not user:
        return

    for notif, threshold, spent, limit, percent in notifications_data:
        category = Category.query.get(notif.category_id)
        if not category:
            continue
        try:
            send_limit_notification(
                to_email=user.email,
                user_name=user.name,
                category_name=category.name,
                spent=spent,
                limit=limit,
                percent=percent,
            )
        except Exception:
            pass  # не прерываем основной поток при ошибке email


def get_unread_count(user_id: int) -> int:
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_all_read(user_id: int):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
