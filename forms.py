from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import (
    StringField,
    SelectField,
    TextAreaField,
    SubmitField,
    IntegerField,
)

from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    ValidationError,
    Regexp,
    NumberRange,
)
from wtforms.fields import DateTimeLocalField

# =========================
# KONSTANTA
# =========================
ANGKA_SAJA = r'^[0-9]+$'
EKSTENSI_FILE = ['jpg', 'png', 'pdf']
FORMAT_WAKTU = '%Y-%m-%dT%H:%M'
STATUS_MAHASISWA = 'Mahasiswa'
PANJANG_NIM_MAHASISWA = 10


# =========================
# FIELD YANG DIPAKAI BERULANG
# =========================
def buat_field_email():
    return StringField('Email', validators=[DataRequired(), Email()])


def buat_field_angka(label, pesan_error):
    return StringField(
        label,
        validators=[
            DataRequired(),
            Regexp(ANGKA_SAJA, message=pesan_error),
        ],
    )


# =========================
# AUTH
# =========================
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    email = buat_field_email()
    password = StringField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Daftar')


class LoginForm(FlaskForm):
    email = buat_field_email()
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


# =========================
# BOOKING
# =========================
class BookingForm(FlaskForm):
    nama_pengaju = StringField('Nama Pengaju', validators=[DataRequired()])
    nim_nip = buat_field_angka('NIM / NIP', 'NIM/NIP harus berupa angka.')
    no_telepon = buat_field_angka('No Telepon', 'Nomor telepon harus berupa angka.')
    email = buat_field_email()

    jenis_kelamin = SelectField(
        'Jenis Kelamin',
        choices=[
            ('Laki-laki', 'Laki-laki'),
            ('Perempuan', 'Perempuan'),
        ],
        validators=[DataRequired()],
    )

    status_pengaju = SelectField(
        'Status Pengaju',
        choices=[
            (STATUS_MAHASISWA, STATUS_MAHASISWA),
            ('Dosen', 'Dosen'),
            ('Staff', 'Staff'),
        ],
        validators=[DataRequired()],
    )

    ruangan = SelectField(
        'Ruangan',
        coerce=int,
        validators=[DataRequired()],
    )

    kegiatan = StringField('Kegiatan', validators=[DataRequired()])

    start_time = DateTimeLocalField(
        'Waktu Mulai',
        format=FORMAT_WAKTU,
        validators=[DataRequired()],
    )

    end_time = DateTimeLocalField(
        'Waktu Selesai',
        format=FORMAT_WAKTU,
        validators=[DataRequired()],
    )

    catatan = TextAreaField('Catatan Tambahan')

    surat_izin = FileField(
        'Surat Izin (Opsional)',
        validators=[FileAllowed(EKSTENSI_FILE)],
    )

    ktm = FileField(
        'Upload KTM',
        validators=[DataRequired(), FileAllowed(EKSTENSI_FILE)],
    )

    submit = SubmitField('Ajukan Peminjaman')

    def validate_nim_nip(self, field):
        """Mahasiswa wajib memakai NIM tepat 10 digit angka."""
        if self.status_pengaju.data != STATUS_MAHASISWA:
            return

        nim = (field.data or '').strip()
        if not nim.isdigit() or len(nim) != PANJANG_NIM_MAHASISWA:
            raise ValidationError(
                'NIM mahasiswa harus terdiri dari tepat 10 digit angka.'
            )


# =========================
# RUANGAN (ADMIN)
# =========================
class RuanganForm(FlaskForm):
    nama_ruangan = StringField('Nama Ruangan', validators=[DataRequired()])

    kapasitas = IntegerField(
        'Kapasitas',
        validators=[
            DataRequired(),
            NumberRange(min=1, message='Kapasitas harus berupa angka minimal 1.'),
        ],
    )

    fasilitas = TextAreaField('Fasilitas', validators=[DataRequired()])

    status = SelectField(
        'Status Ruangan',
        choices=[
            ('Bisa Dipakai', 'Bisa Dipakai'),
            ('Tidak Bisa Dipakai', 'Tidak Bisa Dipakai'),
            ('Sedang Diperbaiki', 'Sedang Diperbaiki'),
        ],
        validators=[DataRequired()],
    )

    submit = SubmitField('Simpan')