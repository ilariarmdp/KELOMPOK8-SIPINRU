import os
import re
from datetime import datetime
from functools import wraps

import click
from flask import Flask, render_template, redirect, url_for, flash, request, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask import jsonify   # tambahkan ke baris import flask yang sudah ada
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.utils import secure_filename

from config import Config
from forms import RegisterForm, LoginForm, BookingForm, RuanganForm
from models import db, User, Room, Booking
from ruangan_service import RuanganService, RuanganError
from validasi_service import AdminValidasiService, FakultasValidasiService, ValidasiError


VALID_LOGIN_MODES = {"admin", "user", "fakultas"}
FLASH_SUCCESS = "success"
FLASH_DANGER = "danger"

#Inisialisasi Aplikasi
app = Flask(__name__)
app.config.from_object(Config)

#Inisialisasi Database & Migrate
db.init_app(app)
migrate = Migrate(app, db)
ruangan_service = RuanganService()
admin_validasi = AdminValidasiService()
fakultas_validasi = FakultasValidasiService()

# Konstanta Status Booking
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'

#Login Manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Silakan login terlebih dahulu untuk mengakses halaman ini."
login_manager.login_message_category = "warning"

#Folder Upload
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
PROFIL_FOLDER = os.path.join(UPLOAD_FOLDER, 'profil')
os.makedirs(PROFIL_FOLDER, exist_ok=True)
FOTO_EXT = {'jpg', 'jpeg', 'png', 'webp'}
FOTO_MAX = 1 * 1024 * 1024  # 1 MB

#Serializer Token Reset Password
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

def send_email_dummy(to_email: str, subject: str, body: str):
    """Simulasi pengiriman email (debug)."""
    print("=== EMAIL DEBUG ===")
    print("To:", to_email)
    print("Subject:", subject)
    print("Body:", body)
    print("===================")

#Fungsi Login Manager
@login_manager.user_loader
def load_user(user_id):
    # PERBAIKAN: Hindari Query.get() yang deprecated
    return db.session.get(User, int(user_id))

#Helper: Guard role
def role_required(role_name):
    """Gunakan @role_required('admin') untuk membatasi akses per role."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if getattr(current_user, "role", None) != role_name:
                abort(403)  # 403 Forbidden
            return fn(*args, **kwargs)
        return wrapper
    return deco

# Optional: agar UX lebih baik
@app.errorhandler(403)
def forbidden(_e):
    flash("Akses ditolak. Kamu tidak memiliki izin ke halaman tersebut.", "danger")
    return redirect(url_for('dashboard'))

# Halaman setelah login jangan disimpan di cache browser, supaya bulatan merah
# notifikasi selalu terbaru saat user menekan tombol Back atau pindah halaman.
@app.after_request
def no_cache_halaman_login(response):
    if current_user.is_authenticated and response.mimetype == 'text/html':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response

#Helper: daftar ruangan urut abjad (paham angka: "Lab 2" sebelum "Lab 10")
def kunci_abjad(room):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', room.name or '')]


def semua_ruangan():
    return sorted(Room.query.all(), key=kunci_abjad)


#Command Init DB
@app.cli.command("init-db")
def init_db():
    with app.app_context():
        db.create_all()

        # Admin default
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@unjani.ac.id', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            click.echo("Admin default dibuat (username: admin, password: admin123)")

        # Ruangan contoh
        if not Room.query.first():
            db.session.add(Room(name='Lab Komputer 1', description='Lab untuk studi komputer', capacity=30))
            db.session.add(Room(name='Ruang Studi 1', description='Ruang diskusi mahasiswa', capacity=20))
            click.echo("Ruangan contoh dibuat")

        db.session.commit()
        click.echo("Database berhasil diinisialisasi!")


@app.cli.command("create-fakultas")
def create_fakultas():
    if User.query.filter_by(username='fakultas').first():
        click.echo("Akun fakultas sudah ada.")
        return
    u = User(username='fakultas', email='fakultas@unjani.ac.id', role='fakultas')
    u.set_password('fakultas123')
    db.session.add(u)
    db.session.commit()
    click.echo("Akun fakultas dibuat (fakultas@unjani.ac.id / fakultas123)")


#ROUTES / RUTE WEB

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

#REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email sudah digunakan. Silakan gunakan email lain!", "warning")
            return redirect(url_for('register'))

        user = User(username=form.username.data, email=form.email.data, role='user')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Akun berhasil dibuat! Silakan login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', form=form, title="Daftar Akun")

def redirect_to_dashboard():
    return redirect(url_for('dashboard'))


def authenticate_user(email, password):
    """Kembalikan user jika email dan password cocok, selain itu None."""
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        return user
    return None

# LOGIN (support mode admin/user/fakultas untuk menampilkan form langsung)
@app.route('/login', defaults={'mode': None}, methods=['GET', 'POST'])
@app.route('/login/<mode>', methods=['GET', 'POST'])
def login(mode):
    if current_user.is_authenticated:
        return redirect_to_dashboard()

    login_mode = (mode or "").lower()
    is_valid_mode = login_mode in VALID_LOGIN_MODES

    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = authenticate_user(form.email.data, form.password.data)
        if user and is_valid_mode and user.role != login_mode:
            flash(f"Akun ini bukan akun {login_mode}. Gunakan tombol login yang sesuai.", FLASH_DANGER)
        elif user:
            login_user(user)
            flash(f"Selamat datang, {user.username}!", FLASH_SUCCESS)
            return redirect_to_dashboard()
        else:
            flash('Email atau password salah. Mohon coba lagi', FLASH_DANGER)

    return render_template('login.html', form=form, title="Login", show_form=is_valid_mode, mode=login_mode)

#LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Kamu berhasil logout.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return render_template(
            'dashboard_admin.html',
            pending_count=Booking.query.filter_by(status='pending').count(),
            user_count=User.query.count(),
            room_count=Room.query.count(),
        )
    if current_user.role == 'fakultas':
        return render_template('dashboard_fakultas.html')
    rooms = Room.query.all()
    return render_template('dashboard_user.html', rooms=rooms)

#PEMINJAMAN RUANGAN (untuk user)
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book_room():
    form = BookingForm()

    # UPDATE pilihan dropdown ruangan
    form.ruangan.choices = [(r.id, r.name) for r in semua_ruangan()]

    if form.validate_on_submit():
        booking = Booking(
            user_id=current_user.id,
            room_id=form.ruangan.data,
            nama_pengaju=form.nama_pengaju.data,
            kegiatan=form.kegiatan.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            catatan=form.catatan.data,
            status='pending',
            is_read=False
        )


        # Upload surat izin (opsional)
        if form.surat_izin.data:
            file = form.surat_izin.data
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{filename}"

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            booking.surat_izin = filename

        # Upload KTM (WAJIB)
        if form.ktm.data:
            file = form.ktm.data
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_KTM_{filename}"

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            booking.ktm = filename
        else:
            flash("Upload KTM wajib!", "danger")
            return redirect(request.url)

        # 🔴 INI YANG KRUSIAL
        db.session.add(booking)
        db.session.commit()

        flash('Peminjaman berhasil diajukan! Tunggu konfirmasi admin.', 'success')
        return redirect(url_for('notifications'))

    return render_template('book_room.html', form=form, title="Peminjaman Ruangan")

#NOTIFIKASI (khusus user)
@app.route('/notifications')
@login_required
def notifications():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.start_time.desc()).all()

    # Tandai semua notifikasi sudah dibaca saat halaman dibuka,
    # supaya bulatan merah di lonceng hilang.
    Booking.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    return render_template('notifications.html', bookings=bookings, title="Notifikasi")

@app.route('/mark_as_read/<int:booking_id>')
@login_required
def mark_as_read(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking and booking.user_id == current_user.id:
        booking.is_read = True
        db.session.commit()
        flash("Notifikasi sudah ditandai sebagai dibaca.", "info")
    return redirect(url_for('notifications'))

# Jumlah notifikasi baru (disetujui admin DAN fakultas, belum dibaca).
# Dipakai JavaScript untuk memperbarui bulatan merah tanpa reload halaman.
@app.route('/notifications/count')
@login_required
def notifications_count():
    if current_user.role in ('admin', 'fakultas'):
        return jsonify(count=0)
    n = Booking.query.filter_by(
        user_id=current_user.id, is_read=False, status='approved'
    ).count()
    return jsonify(count=n)

#PANEL ADMIN / DATA PENGAJUAN
@app.route('/admin', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin():
    if request.method == 'POST':
        try:
            admin_validasi.proses(request.form.get('booking_id', type=int),
                                  request.form.get('action'))
        except ValidasiError as e:
            db.session.rollback()
            flash(str(e), 'danger')
        return redirect(url_for('admin'))

    bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    return render_template(
        'data_pengajuan.html',
        data=bookings,
        title="Validasi Data Pengajuan"
    )

#Alias URL khusus data pengajuan
@app.route('/data_pengajuan')
@login_required
@role_required('admin')
def data_pengajuan():
    return redirect(url_for('admin'))

#DATA USER (khusus admin)
@app.route('/data_user')
@login_required
@role_required('admin')
def data_user():
    users = User.query.order_by(User.username.asc()).all()
    return render_template('data_user.html', users=users, title="Data User")

#DATA & JADWAL RUANGAN
@app.route('/data-ruangan')
@login_required
def data_ruangan():
    if current_user.role != 'admin':
        flash("Akses ditolak. Halaman ini khusus admin.", "danger")
        return redirect(url_for('dashboard'))
    
    rooms = semua_ruangan()
    return render_template('data_ruangan.html', rooms=rooms)

#STATUS RUANGAN "SEDANG DIPAKAI"
def ruangan_sedang_dipakai():
    """{room_id: booking} untuk peminjaman yang sudah disetujui dan sedang berlangsung sekarang."""
    sekarang = datetime.now()
    aktif = Booking.query.filter(
        Booking.status == 'approved',
        Booking.start_time <= sekarang,
        Booking.end_time >= sekarang
    ).all()
    return {b.room_id: b for b in aktif}


#DATA RUANGAN (untuk user, read only)
@app.route('/ruangan-user')
@login_required
def ruangan_user():
    rooms = semua_ruangan()
    return render_template('ruangan_user.html', rooms=rooms, title="Data Ruangan",
                           dipakai=ruangan_sedang_dipakai())


@app.route('/ruangan-user/status')
@login_required
def ruangan_user_status():
    return jsonify({
        str(room_id): {'sampai': b.end_time.strftime('%H:%M'), 'kegiatan': b.kegiatan}
        for room_id, b in ruangan_sedang_dipakai().items()
    })

@app.route('/laporan_peminjaman')
@login_required
@role_required('admin')
def laporan_peminjaman():
    bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    return render_template('laporan_peminjaman.html', bookings=bookings, title="Laporan Peminjaman")

#NOTIFIKASI NAVBAR
@app.context_processor
def inject_notifications():
    # Admin & fakultas: tidak perlu notifikasi user
    if current_user.is_authenticated and getattr(current_user, "role", "") not in ('admin', 'fakultas'):
        # Bulatan merah di lonceng HANYA untuk pengajuan yang sudah
        # disetujui admin DAN fakultas (status 'approved') dan belum dibaca.
        notifications = Booking.query.filter_by(
            user_id=current_user.id,
            is_read=False,
            status='approved'
        ).order_by(Booking.start_time.desc()).all()
        return dict(nav_notifications=notifications)
    return dict(nav_notifications=[])

#DATA RINGKASAN & BADGE (khusus fakultas)
@app.context_processor
def inject_fakultas_counts():
    if current_user.is_authenticated and getattr(current_user, "role", "") == 'fakultas':
        pending = Booking.query.filter_by(status='approved_admin').count()
        approved = Booking.query.filter_by(status='approved').count()
        rejected = Booking.query.filter_by(status='rejected_fakultas').count()
        return dict(pending_count=pending, notif_count=pending,
                    approved_count=approved, rejected_count=rejected)
    return {}

@app.context_processor
def inject_admin_pending():
    # jumlah pengajuan menunggu, tersedia di semua template untuk admin
    if current_user.is_authenticated and current_user.role == 'admin':
        return {'admin_pending': Booking.query.filter_by(status='pending').count()}
    return {}

@app.route('/admin/notifikasi')
@login_required
@role_required('admin')
def admin_notifikasi():
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('admin_notifikasi.html', bookings=bookings, title='Notifikasi')

@app.route('/admin/notifikasi/count')
@login_required
@role_required('admin')
def admin_notifikasi_count():
    return jsonify(pending=Booking.query.filter_by(status='pending').count())

#FORGOT PASSWORD
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = serializer.dumps({'uid': user.id})
            reset_url = url_for('reset_password', token=token, _external=True)
            subject = "Reset Password SIPINRU"
            body = f"Halo,\n\nKlik tautan berikut untuk mengatur ulang password (berlaku 30 menit):\n{reset_url}\n\nAbaikan jika kamu tidak meminta reset."
            send_email_dummy(email, subject, body)

        flash('Jika email terdaftar, tautan reset sudah dikirim.', 'info')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', title='Lupa Password')

#RESET PASSWORD
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        data = serializer.loads(token, max_age=1800)
        uid = data.get('uid')
    except SignatureExpired:
        flash('Tautan reset kadaluarsa. Silakan minta ulang.', 'warning')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Tautan reset tidak valid.', 'danger')
        return redirect(url_for('forgot_password'))

    user = db.session.get(User, uid)
    if not user:
        flash('Pengguna tidak ditemukan.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        pwd1 = request.form.get('password') or ''
        pwd2 = request.form.get('password_confirm') or ''
        if len(pwd1) < 6:
            flash('Password minimal 6 karakter.', 'warning')
            return redirect(request.url)
        if pwd1 != pwd2:
            flash('Konfirmasi password tidak cocok.', 'warning')
            return redirect(request.url)

        user.set_password(pwd1)
        db.session.commit()
        flash('Password berhasil diubah. Silakan login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', title='Atur Ulang Password')

@app.route('/jadwal')
@login_required
def jadwal():
    jadwal = (
        Booking.query
        .filter(Booking.status == 'approved')
        .order_by(Booking.start_time.asc())
        .all()
    )

    return render_template(
        'jadwal.html',
        jadwal=jadwal
    )

# =========================
# JADWAL RUANGAN (ADMIN)
# =========================
@app.route('/admin/jadwal')
@login_required
@role_required('admin')
def jadwal_admin():
    jadwal = (
        Booking.query
        .filter_by(status='approved')
        .order_by(Booking.start_time.asc())
        .all()
    )

    return render_template(
        'jadwal.html',
        jadwal=jadwal,
        title='Jadwal Ruangan'
    )

# =========================
# LAPORAN PEMINJAMAN
# =========================
@app.route('/admin/laporan')
@login_required
@role_required('admin')
def laporan_admin():
    bookings = (
        Booking.query
        .filter_by(status='approved')   # laporan = data final
        .order_by(Booking.start_time.desc())
        .all()
    )

    return render_template(
        'laporan_peminjaman.html',
        bookings=bookings
    )


@app.route('/admin/ruangan/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_ruangan(id):
    room = Room.query.get_or_404(id)
    form = RuanganForm(obj=room)   # ← SATU-SATUNYA YANG BENAR

    if form.validate_on_submit():
        room.name = form.nama_ruangan.data
        room.capacity = form.kapasitas.data
        room.description = form.fasilitas.data
        room.status = form.status.data

        db.session.commit()
        flash('Data ruangan berhasil diperbarui', 'success')
        return redirect(url_for('data_ruangan'))

    return render_template('ruangan_edit.html', form=form, title="Edit Ruangan")



@app.route('/hapus-ruangan/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def hapus_ruangan(id):
    room = Room.query.get_or_404(id)

    if room.bookings:
        flash('Ruangan tidak bisa dihapus karena masih memiliki data peminjaman.', 'danger')
        return redirect(url_for('data_ruangan'))

    db.session.delete(room)
    db.session.commit()
    flash('Ruangan berhasil dihapus', 'success')
    return redirect(url_for('data_ruangan'))

@app.route('/admin/ruangan/tambah', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def tambah_ruangan():
    form = RuanganForm()

    if form.validate_on_submit():
        try:
            ruangan_service.tambah_ruangan(
                nama=form.nama_ruangan.data,
                kapasitas=form.kapasitas.data,
                fasilitas=form.fasilitas.data,
                status=form.status.data
            )
            flash('Ruangan berhasil ditambahkan', 'success')
            return redirect(url_for('data_ruangan'))
        except RuanganError as e:
            flash(str(e), 'danger')

    return render_template('ruangan_edit.html', form=form, title="Tambah Ruangan")

# =========================
# FAKULTAS
# =========================
@app.route('/fakultas/validasi', methods=['GET', 'POST'])
@login_required
@role_required('fakultas')
def fakultas_validasi_page():
    if request.method == 'POST':
        try:
            fakultas_validasi.proses(request.form.get('booking_id', type=int),
                                     request.form.get('action'))
            flash("Validasi berhasil disimpan.", "success")
        except ValidasiError as e:
            db.session.rollback()
            flash(str(e), 'danger')
        return redirect(url_for('fakultas_validasi_page'))

    return render_template('validasi_fakultas.html',
                           data=fakultas_validasi.antrean(),
                           title="Validasi Fakultas")


@app.route('/fakultas/notifikasi')
@login_required
@role_required('fakultas')
def fakultas_notifikasi():
    bookings = (Booking.query
                .filter(Booking.status.in_(['approved_admin', 'approved', 'rejected_fakultas']))
                .order_by(Booking.start_time.desc())
                .all())
    return render_template('notifications_fakultas.html',
                           bookings=bookings, title="Notifikasi Fakultas")

# =========================
# BERKAS (KTM & SURAT IZIN): buka / unduh
# =========================
@app.route('/berkas/<path:filename>')
@login_required
def berkas(filename):
    safe_name = secure_filename(filename)
    booking = Booking.query.filter(
        (Booking.ktm == safe_name) | (Booking.surat_izin == safe_name)
    ).first_or_404()

    # admin & fakultas boleh semua; mahasiswa hanya berkas miliknya
    if current_user.role not in ('admin', 'fakultas') and booking.user_id != current_user.id:
        abort(403)

    unduh = request.args.get('download') == '1'
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name, as_attachment=unduh)


# =========================
# PROFIL (semua role)
# =========================
def hitung_ringkasan(user):
    """Tiga angka ringkas di kartu profil, berbeda tiap role."""
    if user.role == 'admin':
        return [
            ('Perlu divalidasi', Booking.query.filter_by(status='pending').count()),
            ('Diteruskan ke fakultas', Booking.query.filter(
                Booking.status.in_(['approved_admin', 'approved', 'rejected_fakultas'])).count()),
            ('Ditolak', Booking.query.filter_by(status='rejected').count()),
        ]
    if user.role == 'fakultas':
        return [
            ('Menunggu validasi', Booking.query.filter_by(status='approved_admin').count()),
            ('Disetujui', Booking.query.filter_by(status='approved').count()),
            ('Ditolak', Booking.query.filter_by(status='rejected_fakultas').count()),
        ]
    mine = Booking.query.filter_by(user_id=user.id)
    return [
        ('Total pengajuan', mine.count()),
        ('Disetujui', mine.filter_by(status='approved').count()),
        ('Sedang diproses', mine.filter(Booking.status.in_(['pending', 'approved_admin'])).count()),
    ]


def hapus_file_foto(user):
    if user.foto:
        lama = os.path.join(PROFIL_FOLDER, user.foto)
        if os.path.isfile(lama):
            os.remove(lama)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = db.session.get(User, current_user.id)

    if request.method == 'POST':
        aksi = request.form.get('aksi')

        if aksi == 'data':
            nama = (request.form.get('nama_lengkap') or '').strip()
            hp = (request.form.get('no_hp') or '').strip()
            if not nama:
                flash('Nama lengkap wajib diisi.', 'danger')
            elif hp and not re.fullmatch(r'[0-9+\-\s]{8,20}', hp):
                flash('Nomor HP tidak valid.', 'danger')
            else:
                user.nama_lengkap = nama[:150]
                user.nim_nip = (request.form.get('nim_nip') or '').strip()[:50] or None
                user.prodi = (request.form.get('prodi') or '').strip()[:100] or None
                user.no_hp = hp or None
                db.session.commit()
                flash('Profil berhasil diperbarui.', 'success')
            return redirect(url_for('profile'))

        if aksi == 'foto':
            file = request.files.get('foto')
            if not file or not file.filename:
                flash('Pilih file foto terlebih dahulu.', 'danger')
            else:
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
                file.seek(0, os.SEEK_END)
                ukuran = file.tell()
                file.seek(0)
                if ext not in FOTO_EXT:
                    flash('Format foto harus JPG, PNG, atau WEBP.', 'danger')
                elif ukuran > FOTO_MAX:
                    flash('Ukuran foto maksimal 1 MB.', 'danger')
                else:
                    nama_file = f"u{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"
                    file.save(os.path.join(PROFIL_FOLDER, nama_file))
                    hapus_file_foto(user)
                    user.foto = nama_file
                    db.session.commit()
                    flash('Foto profil berhasil diperbarui.', 'success')
            return redirect(url_for('profile'))

        if aksi == 'hapus_foto':
            hapus_file_foto(user)
            user.foto = None
            db.session.commit()
            flash('Foto profil dihapus.', 'info')
            return redirect(url_for('profile'))

        if aksi == 'password':
            lama = request.form.get('password_lama') or ''
            baru = request.form.get('password_baru') or ''
            konf = request.form.get('password_konfirmasi') or ''
            if not user.check_password(lama):
                flash('Password saat ini salah.', 'danger')
            elif len(baru) < 6:
                flash('Password baru minimal 6 karakter.', 'warning')
            elif baru != konf:
                flash('Konfirmasi password tidak cocok.', 'warning')
            elif baru == lama:
                flash('Password baru harus berbeda dari yang lama.', 'warning')
            else:
                user.set_password(baru)
                db.session.commit()
                flash('Password berhasil diubah.', 'success')
            return redirect(url_for('profile', _anchor='keamanan'))

    return render_template('profile.html', user=user,
                           ringkasan=hitung_ringkasan(user), title="Profil Saya")

# =========================
# LAPORAN PEMINJAMAN (FAKULTAS)
# =========================
NAMA_BULAN = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']


def label_bulan(ym):
    try:
        tahun, bln = ym.split('-')
        return f"{NAMA_BULAN[int(bln) - 1]} {tahun}"
    except (ValueError, IndexError):
        return ym


def ambil_laporan_fakultas(bulan='', status='all'):
    """Pengajuan yang sudah diputuskan fakultas, bisa difilter bulan & status."""
    statuses = [status] if status in ('approved', 'rejected_fakultas') else ['approved', 'rejected_fakultas']
    q = Booking.query.filter(Booking.status.in_(statuses))
    if bulan:
        try:
            tahun, bln = [int(x) for x in bulan.split('-')]
            awal = datetime(tahun, bln, 1)
            akhir = datetime(tahun + 1, 1, 1) if bln == 12 else datetime(tahun, bln + 1, 1)
            q = q.filter(Booking.start_time >= awal, Booking.start_time < akhir)
        except ValueError:
            pass
    return q.order_by(Booking.start_time.desc()).all()


@app.route('/fakultas/laporan')
@login_required
@role_required('fakultas')
def fakultas_laporan():
    status = request.args.get('status', 'all')
    if status not in ('approved', 'rejected_fakultas'):
        status = 'all'

    opsi = sorted({b.start_time.strftime('%Y-%m') for b in ambil_laporan_fakultas()}, reverse=True)
    bulan = request.args.get('bulan', '')
    if bulan not in opsi:
        bulan = ''

    semua_bulan = ambil_laporan_fakultas(bulan)
    data = [b for b in semua_bulan if status == 'all' or b.status == status]

    total = len(semua_bulan)
    n_ok = sum(1 for b in semua_bulan if b.status == 'approved')
    stat = {'total': total, 'ok': n_ok, 'no': total - n_ok,
            'rate': round(n_ok * 100 / total) if total else 0}

    return render_template(
        'laporan_fakultas.html',
        data=data, stat=stat, status=status, bulan=bulan,
        bulan_opsi=[(v, label_bulan(v)) for v in opsi],
        periode=label_bulan(bulan) if bulan else 'Semua periode',
        dicetak=datetime.now().strftime('%d-%m-%Y %H:%M'),
        title="Laporan Peminjaman"
    )


@app.route('/fakultas/laporan/export')
@login_required
@role_required('fakultas')
def fakultas_laporan_export():
    import csv, io
    from flask import Response

    data = ambil_laporan_fakultas(request.args.get('bulan', ''), request.args.get('status', 'all'))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(['No', 'Nama Pengaju', 'Ruangan', 'Kegiatan', 'Tanggal',
                'Jam Mulai', 'Jam Selesai', 'Catatan', 'Status'])
    for i, b in enumerate(data, 1):
        catatan = getattr(b, 'catatan', None) or getattr(b, 'notes', None) or ''
        w.writerow([i, b.nama_pengaju, b.room.name if b.room else '-', b.kegiatan,
                    b.start_time.strftime('%d-%m-%Y'), b.start_time.strftime('%H:%M'),
                    b.end_time.strftime('%H:%M'), catatan,
                    'Disetujui' if b.status == 'approved' else 'Ditolak Fakultas'])

    nama = f"laporan_peminjaman_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response('\ufeff' + buf.getvalue(), mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename={nama}'})


# RUN APP
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)