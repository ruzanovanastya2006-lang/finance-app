import base64
import requests
from datetime import date, timedelta
from flask import current_app


def _brevo_send(to_email: str, to_name: str, subject: str,
                html: str = None, text: str = None, attachments: list = None):
    api_key = current_app.config.get('BREVO_API_KEY') or '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'
    from_email = 'ruzanova.nastya2006@gmail.com'

    payload = {
        "sender": {"name": "finance-course", "email": from_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
    }
    if html:
        payload["htmlContent"] = html
    elif text:
        payload["textContent"] = text

    if attachments:
        payload["attachment"] = attachments

    resp = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
        proxies={"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"},
    )
    if not resp.ok:
        raise Exception(f"{resp.status_code}: {resp.text}")
    return resp


def send_pdf_report(to_email: str, pdf_bytes: bytes, date_from: str, date_to: str, user_name: str):
    html = (
        f"<p>Добрый день, <b>{user_name}</b>!</p>"
        f"<p>Во вложении — ваш финансовый отчёт за период {date_from} — {date_to}.</p>"
        f"<p>С уважением,<br>Финансовый дашборд</p>"
    )
    attachment = [{
        "content": base64.b64encode(pdf_bytes).decode(),
        "name": f"report_{date_from}_{date_to}.pdf",
    }]
    _brevo_send(
        to_email=to_email,
        to_name=user_name,
        subject=f"Финансовый отчёт за {date_from} — {date_to}",
        html=html,
        attachments=attachment,
    )


def send_limit_notification(to_email: str, user_name: str, category_name: str,
                            spent: float, limit: float, percent: float):
    if percent >= 100:
        subject = f"Лимит превышен: {category_name}"
        color = "#dc2626"
        headline = f"Лимит по категории «{category_name}» превышен!"
        detail = f"Потрачено {spent:.0f} ₽ из {limit:.0f} ₽ ({percent:.0f}%)."
    elif percent >= 90:
        subject = f"Лимит почти исчерпан: {category_name}"
        color = "#ea580c"
        headline = f"Использовано {percent:.0f}% лимита по «{category_name}»"
        detail = f"Потрачено {spent:.0f} ₽ из {limit:.0f} ₽. Осталось {limit - spent:.0f} ₽."
    else:
        subject = f"Приближение к лимиту: {category_name}"
        color = "#d97706"
        headline = f"Использовано {percent:.0f}% лимита по «{category_name}»"
        detail = f"Потрачено {spent:.0f} ₽ из {limit:.0f} ₽. Осталось {limit - spent:.0f} ₽."

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto">
      <div style="background:{color};color:white;padding:16px 20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">{headline}</h2>
      </div>
      <div style="background:#f9f9f9;padding:20px;border-radius:0 0 8px 8px;border:1px solid #eee">
        <p>Добрый день, <b>{user_name}</b>!</p>
        <p>{detail}</p>
        <p style="color:#888;font-size:13px">Это автоматическое уведомление от Финансового дашборда.</p>
      </div>
    </body></html>
    """
    _brevo_send(to_email=to_email, to_name=user_name, subject=subject, html=html)


def send_weekly_summary(to_email: str, user_name: str, summary: dict):
    week_end = date.today()
    week_start = week_end - timedelta(days=6)

    rows_html = "".join(
        f'<tr><td style="padding:6px 10px">{r["name"]}</td>'
        f'<td style="padding:6px 10px;text-align:right"><b>{r["amount"]:.0f} ₽</b></td></tr>'
        for r in summary.get("by_category", [])
    )

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:540px;margin:0 auto">
      <div style="background:#4f46e5;color:white;padding:16px 20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">Еженедельная сводка трат</h2>
        <p style="margin:6px 0 0;opacity:.85">{week_start.strftime('%d.%m')} — {week_end.strftime('%d.%m.%Y')}</p>
      </div>
      <div style="background:#f9f9f9;padding:20px;border-radius:0 0 8px 8px;border:1px solid #eee">
        <p>Добрый день, <b>{user_name}</b>!</p>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:6px">
          <tr style="background:#eee">
            <th style="padding:8px 10px;text-align:left">Доходы</th>
            <td style="padding:8px 10px;text-align:right;color:#10b981"><b>{summary.get('income', 0):.0f} ₽</b></td>
          </tr>
          <tr>
            <th style="padding:8px 10px;text-align:left">Расходы</th>
            <td style="padding:8px 10px;text-align:right;color:#ef4444"><b>{summary.get('expense', 0):.0f} ₽</b></td>
          </tr>
          <tr style="background:#eee">
            <th style="padding:8px 10px;text-align:left">Баланс</th>
            <td style="padding:8px 10px;text-align:right"><b>{summary.get('balance', 0):.0f} ₽</b></td>
          </tr>
        </table>
        {'<h4 style="margin:16px 0 8px">По категориям:</h4><table style="width:100%;border-collapse:collapse">' + rows_html + '</table>' if rows_html else ''}
        <p style="color:#888;font-size:13px;margin-top:16px">Это автоматическое письмо от Финансового дашборда.</p>
      </div>
    </body></html>
    """
    _brevo_send(
        to_email=to_email,
        to_name=user_name,
        subject=f"Сводка трат за неделю ({week_start.strftime('%d.%m')}–{week_end.strftime('%d.%m.%Y')})",
        html=html,
    )
