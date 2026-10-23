from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
        self._password_hash = generate_password_hash(password) #enkapsulasi

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

  


# ================= BOOKING =================
class Booking(BaseModel):
    __tablename__ = 'booking'

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


    # OVERLOADING
    def set_status(self, status, note=None):
        self.status = status
        if note:
            self.catatan = note

    # POLYMORPHISM
    def get_info(self):
        return f"Booking {self.kegiatan}"


# ================= DATA PENGAJUAN =================
class DataPengajuan(BaseModel):
    __tablename__ = 'data_pengajuan'

    EKSTENSI_DIIZINKAN = ('pdf', 'jpg', 'jpeg', 'png')
    UKURAN_MAKS_SIK = 5 * 1024 * 1024  # 5 MB

    id = db.Column(db.Integer, primary_key=True)

    # Relasi (pengganti atribut "ruangan : enum" di diagram,
    # karena data ruangan sudah ada di tabel Room)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)

    user = db.relationship('User', backref='pengajuan_list')
    room = db.relationship('Room', backref='pengajuan_list')

    nama_pengaju = db.Column(db.String(150), nullable=False)
    nim_nip = db.Column(db.String(50), nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)

    kategori_kegiatan = db.Column(
        db.Enum(
            'Rapat',
            'Seminar',
            'Perkuliahan',
            'Kegiatan Organisasi',
            name='kategori_kegiatan_enum'
        ),
        nullable=False
    )

    status_pengaju = db.Column(
        db.Enum(
            'Mahasiswa',
            'Dosen',
            'Staff',
            name='status_pengaju_enum'
        ),
        nullable=False
    )

    # Memakai DateTime (bukan Time) supaya tanggal peminjaman ikut tersimpan
    waktu_mulai = db.Column(db.DateTime, nullable=False)
    waktu_selesai = db.Column(db.DateTime, nullable=False)

    # Data file SIK (Surat Izin Kegiatan)
    sik = db.Column(db.String(255), nullable=False)        # nama/path file
    title_sik = db.Column(db.String(150), nullable=False)
    size_sik = db.Column(db.Integer, nullable=False)       # dalam byte
    ekstensi_sik = db.Column(db.String(10), nullable=False)

    # Tambahan: status hasil validasi admin
    status_validasi = db.Column(db.String(20), default='pending')

    # OVERRIDING
    def get_info(self):
        return f"Pengajuan {self.nama_pengaju} - {self.kategori_kegiatan}"

    # + perlihatkanDataPengajuan()
    def perlihatkan_data_pengajuan(self):
        return {
            'id': self.id,
            'nama_pengaju': self.nama_pengaju,
            'status_pengaju': self.status_pengaju,
            'nim_nip': self.nim_nip,
            'no_telepon': self.no_telepon,
            'ruangan': self.room.name if self.room else None,
            'kategori_kegiatan': self.kategori_kegiatan,
            'waktu_mulai': self.waktu_mulai,
            'waktu_selesai': self.waktu_selesai,
            'sik': self.sik,
            'title_sik': self.title_sik,
            'size_sik': self.size_sik,
            'ekstensi_sik': self.ekstensi_sik,
            'status_validasi': self.status_validasi,
        }

    # + validasiDataPengajuan()
    def validasi_data_pengajuan(self):
        """Mengembalikan (True, []) jika valid, atau (False, [daftar_error])."""
        errors = []

        if not self.nama_pengaju or not self.nama_pengaju.strip():
            errors.append("Nama pengaju tidak boleh kosong.")

        if not (self.nim_nip or '').strip().isdigit():
            errors.append("NIM/NIP harus berupa angka.")

        if not ((self.no_telepon or '').isdigit() and 10 <= len(self.no_telepon) <= 15):
            errors.append("No. telepon harus 10-15 digit angka.")

        if self.waktu_selesai <= self.waktu_mulai:
            errors.append("Waktu selesai harus lebih besar dari waktu mulai.")

        if (self.ekstensi_sik or '').lower() not in self.EKSTENSI_DIIZINKAN:
            errors.append("Ekstensi SIK harus: " + ", ".join(self.EKSTENSI_DIIZINKAN))

        if not self.size_sik or self.size_sik > self.UKURAN_MAKS_SIK:
            errors.append("Ukuran SIK maksimal 5 MB.")

        return (len(errors) == 0, errors)