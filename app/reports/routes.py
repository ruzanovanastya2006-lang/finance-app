import csv
import io
from datetime import date
from calendar import monthrange
from flask import render_template, request, Response, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ..models import Transaction, Category
from . import reports


def _get_transactions(user_id, date_from, date_to, tx_type=None):
    q = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    )
    if tx_type in ('income', 'expense'):
        q = q.filter(Transaction.type == tx_type)
    return q.order_by(Transaction.date).all()


@reports.route('/')
@login_required
def index():
    today = date.today()
    return render_template('reports/index.html', today=today)


@reports.route('/export-csv')
@login_required
def export_csv():
    date_from = request.args.get('date_from', str(date.today().replace(day=1)))
    date_to = request.args.get('date_to', str(date.today()))
    tx_type = request.args.get('type', '')

    txs = _get_transactions(current_user.id, date_from, date_to, tx_type or None)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Дата', 'Тип', 'Категория', 'Сумма', 'Комментарий'])
    for tx in txs:
        writer.writerow([
            tx.date.strftime('%d.%m.%Y'),
            'Доход' if tx.type == 'income' else 'Расход',
            tx.category.name if tx.category else '—',
            f'{float(tx.amount):.2f}',
            tx.comment or '',
        ])

    output.seek(0)
    return Response(
        '﻿' + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=finance_{date_from}_{date_to}.csv'}
    )


@reports.route('/generate-pdf', methods=['POST'])
@login_required
def generate_pdf():
    """Генерация PDF-отчёта с ReportLab."""
    date_from = request.form.get('date_from', str(date.today().replace(day=1)))
    date_to = request.form.get('date_to', str(date.today()))
    txs = _get_transactions(current_user.id, date_from, date_to)
    pdf_bytes = _build_pdf(txs, date_from, date_to)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=report_{date_from}_{date_to}.pdf'}
    )


@reports.route('/send-email', methods=['POST'])
@login_required
def send_email():
    """Генерирует PDF и отправляет на указанный email."""
    from ..email_service import send_pdf_report

    to_email = request.form.get('email', current_user.email).strip()
    date_from = request.form.get('date_from', str(date.today().replace(day=1)))
    date_to = request.form.get('date_to', str(date.today()))

    txs = _get_transactions(current_user.id, date_from, date_to)
    pdf_bytes = _build_pdf(txs, date_from, date_to)

    try:
        send_pdf_report(to_email, pdf_bytes, date_from, date_to, current_user.name)
        flash(f'Отчёт успешно отправлен на {to_email} 📧', 'success')
    except Exception as e:
        flash(f'Ошибка отправки: {e}', 'danger')

    return redirect(url_for('reports.index'))


def _build_pdf(txs, date_from, date_to):
    """Вспомогательная функция — собирает PDF и возвращает bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    font_name, font_bold = 'Arial', 'Arial-Bold'
    try:
        pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', r'C:\Windows\Fonts\arialbd.ttf'))
        registerFontFamily('Arial', normal='Arial', bold='Arial-Bold')
    except Exception:
        font_name, font_bold = 'Helvetica', 'Helvetica-Bold'

    total_income = sum(float(t.amount) for t in txs if t.type == 'income')
    total_expense = sum(float(t.amount) for t in txs if t.type == 'expense')

    buf = __import__('io').BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    style_n = ParagraphStyle('n', fontName=font_name, fontSize=10, leading=14)
    style_t = ParagraphStyle('t', fontName=font_bold, fontSize=16, spaceAfter=12, leading=20)

    story = [
        Paragraph('Финансовый отчёт', style_t),
        Paragraph(f'Период: {date_from} — {date_to}', style_n),
        Spacer(1, 0.4*cm),
        Paragraph(f'Доходы: {total_income:.2f} руб.', style_n),
        Paragraph(f'Расходы: {total_expense:.2f} руб.', style_n),
        Paragraph(f'Баланс: {total_income - total_expense:.2f} руб.', style_n),
        Spacer(1, 0.4*cm),
    ]

    if txs:
        data = [['Дата', 'Тип', 'Категория', 'Сумма', 'Комментарий']]
        for tx in txs[:200]:
            data.append([
                tx.date.strftime('%d.%m.%Y'),
                'Доход' if tx.type == 'income' else 'Расход',
                tx.category.name if tx.category else '—',
                f'{float(tx.amount):.2f}',
                (tx.comment or '')[:40],
            ])
        t = Table(data, colWidths=[2.5*cm, 2.5*cm, 4*cm, 2.5*cm, 5.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0ff')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
