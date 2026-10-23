from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ================= ABSTRACTION =================
class BaseModel(db.Model):
    __abstract__ = True

    def get_info(self):
        raise NotImplementedError


# ================= USER =================
class User(BaseModel, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    _password_hash = db.Column("password_hash", db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')

    def set_password(self, password):
        self._password_hash = generate_password_hash(password)  # enkapsulasi

    def check_password(self, password):
        return check_password_hash(self._password_hash, password)

    # POLYMORPHISM
    def get_role_info(self):
        if self.role == "admin":
            return "Administrator"
        return "Pengguna biasa"

    # OVERRIDING
    def get_info(self):
        return f"User {self.username}"


# ================= ROOM =================
class Room(BaseModel):
    __tablename__ = 'room'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    capacity = db.Column(db.Integer)
    description = db.Column(db.Text)

    status = db.Column(
        db.Enum(
            'Bisa Dipakai',
            'Tidak Bisa Dipakai',
            'Sedang Diperbaiki',
            name='room_status_enum'
        ),
        nullable=False,
        default='Bisa Dipakai'
    )

    # OVERRIDING
    def get_info(self):
        return f"Room {self.name}"


# ================= BOOKING =================
class Booking(BaseModel):
    __tablename__ = 'booking'

    STATUS_VALID = ('pending', 'approved', 'rejected')

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)

    room = db.relationship('Room', backref='bookings')
    user = db.relationship('User', backref='bookings')

    nama_pengaju = db.Column(db.String(150))
    kegiatan = db.Column(db.String(150), nullable=False)

    status = db.Column(db.String(20), default='pending')
    is_read = db.Column(db.Boolean, default=False)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    catatan = db.Column(db.Text)

    # nama file upload (dipakai di app.py: booking.surat_izin / booking.ktm)
    surat_izin = db.Column(db.String(255))
    ktm = db.Column(db.String(255))

    # alias agar template bisa memakai booking.notes
    @property
    def notes(self):
        return self.catatan

    # OVERLOADING (versi Python: parameter opsional) + validasi
    def set_status(self, status, note=None):
        if status not in self.STATUS_VALID:
            raise ValueError(f"Status tidak valid: {status}")
        self.status = status
        if note:
            self.catatan = note

    # POLYMORPHISM
    def get_info(self):
        return f"Booking {self.kegiatan}"