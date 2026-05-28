from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

DEFAULT_CATEGORIES = [
    {'name': 'Продукты',      'color': '#4CAF50', 'icon': '🛒'},
    {'name': 'Транспорт',     'color': '#2196F3', 'icon': '🚌'},
    {'name': 'Кафе',          'color': '#FF9800', 'icon': '☕'},
    {'name': 'Здоровье',      'color': '#E91E63', 'icon': '💊'},
    {'name': 'Одежда',        'color': '#9C27B0', 'icon': '👗'},
    {'name': 'Развлечения',   'color': '#00BCD4', 'icon': '🎬'},
    {'name': 'Связь',         'color': '#607D8B', 'icon': '📱'},
    {'name': 'ЖКХ',           'color': '#795548', 'icon': '🏠'},
    {'name': 'Образование',   'color': '#3F51B5', 'icon': '📚'},
    {'name': 'Прочее',        'color': '#9E9E9E', 'icon': '📦'},
]


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    categories = db.relationship('Category', backref='owner', lazy='dynamic',
                                 foreign_keys='Category.user_id')
    transactions = db.relationship('Transaction', backref='owner', lazy='dynamic')
    notifications = db.relationship('Notification', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    monthly_limit = db.Column(db.Numeric(12, 2), default=0)
    color = db.Column(db.String(7), default='#9E9E9E')
    icon = db.Column(db.String(10), default='📦')
    is_default = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' | 'expense'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    comment = db.Column(db.String(500))
    receipt_url = db.Column(db.String(500))  # Google Drive URL (заглушка)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.type} {self.amount}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    message = db.Column(db.String(500), nullable=False)
    threshold = db.Column(db.Integer)  # 80, 90 или 100
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship('Category')

    def __repr__(self):
        return f'<Notification {self.threshold}% {self.message[:30]}>'
