from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import (
    StringField,
    SelectField,
    TextAreaField,
    SubmitField,
    IntegerField
)

from wtforms.validators import DataRequired, Email, Length
from wtforms.fields import DateTimeLocalField


# =========================
# AUTH
# =========================
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Daftar')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


# =========================
# BOOKING
# =========================
class BookingForm(FlaskForm):
    nama_pengaju = StringField('Nama Pengaju', validators=[DataRequired()])
    nim_nip = StringField('NIM / NIP', validators=[DataRequired()])
    no_telepon = StringField('No Telepon', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])

    jenis_kelamin = SelectField(
        'Jenis Kelamin',
        choices=[
            ('Laki-laki', 'Laki-laki'),
            ('Perempuan', 'Perempuan')
        ],
        validators=[DataRequired()]
    )

    status_pengaju = SelectField(
        'Status Pengaju',
        choices=[
            ('Mahasiswa', 'Mahasiswa'),
            ('Dosen', 'Dosen'),
            ('Staff', 'Staff')
        ],
        validators=[DataRequired()]
    )

    ruangan = SelectField(
        'Ruangan',
        coerce=int,
        validators=[DataRequired()]
    )

    kegiatan = StringField('Kegiatan', validators=[DataRequired()])

    start_time = DateTimeLocalField(
        'Waktu Mulai',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired()]
    )

    end_time = DateTimeLocalField(
        'Waktu Selesai',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired()]
    )

    catatan = TextAreaField('Catatan Tambahan')

    surat_izin = FileField(
        'Surat Izin (Opsional)',
        validators=[FileAllowed(['jpg', 'png', 'pdf'])]
    )

    ktm = FileField(
        'Upload KTM',
        validators=[DataRequired(), FileAllowed(['jpg', 'png', 'pdf'])]
    )

    submit = SubmitField('Ajukan Peminjaman')


# =========================
# RUANGAN (ADMIN)
# =========================
class RuanganForm(FlaskForm):
    nama_ruangan = StringField(
        'Nama Ruangan',
        validators=[DataRequired()]
    )

    kapasitas = IntegerField(
        'Kapasitas',
        validators=[DataRequired()]
    )

    fasilitas = TextAreaField(
        'Fasilitas',
        validators=[DataRequired()]
    )

    status = SelectField(
        'Status Ruangan',
        choices=[
            ('Bisa Dipakai', 'Bisa Dipakai'),
            ('Tidak Bisa Dipakai', 'Tidak Bisa Dipakai'),
            ('Sedang Diperbaiki', 'Sedang Diperbaiki')
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField('Simpan')
