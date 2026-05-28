import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/finance_app')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'ruzanova.nastya2006@gmail.com')
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')

    GOOGLE_DRIVE_CREDENTIALS_FILE = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_FILE', 'credentials.json')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    NOTIFICATION_THRESHOLDS = [80, 90, 100]
