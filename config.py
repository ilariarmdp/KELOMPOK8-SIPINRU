import os

class Config:
    # Secret key
    SECRET_KEY = 'supersecretkey_sipinru_2025'

    # === Konfigurasi MySQL ===
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/sipinru'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # === Upload ===
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    DEBUG = True

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
