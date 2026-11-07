from app import app, db
from models import User
from werkzeug.security import generate_password_hash

akun = [
    ("admin",    "admin@unjani.ac.id",    "admin123",    "admin",    "Admin Test"),
    ("fakultas", "fakultas@unjani.ac.id", "fakultas123", "fakultas", "Fakultas Test"),
    ("user",     "user@unjani.ac.id",     "user123",     "user",     "User Test"),
]

with app.app_context():
    for username, email, pw, role, nama in akun:
        if User.query.filter_by(email=email).first():
            print("sudah ada:", email)
            continue
        u = User(username=username, email=email, role=role, nama_lengkap=nama)
        u._password_hash = generate_password_hash(pw)
        db.session.add(u)
    db.session.commit()
    print("selesai")