from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import os
import click
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from forms import RuanganForm
from ruangan_service import RuanganService, RuanganError


# Import konfigurasi & modul
from config import Config
from models import db, User, Room, Booking
from forms import RegisterForm, LoginForm, BookingForm
from models import Room


#Inisialisasi Aplikasi
app = Flask(__name__)
app.config.from_object(Config)

#Inisialisasi Database & Migrate
db.init_app(app)
migrate = Migrate(app, db)
ruangan_service = RuanganService()

#Login Manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Silakan login terlebih dahulu untuk mengakses halaman ini."
login_manager.login_message_category = "warning"

#Folder Upload
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

#LOGIN (support mode admin/user untuk menampilkan form langsung)
@app.route('/login', defaults={'mode': None}, methods=['GET', 'POST'])
@app.route('/login/<mode>', methods=['GET', 'POST'])
def login(mode):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    mode = (mode or "").lower()
    show_form = mode in {"admin", "user"}

    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Selamat datang, {user.username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash('Email atau password salah. Mohon coba lagi', 'danger')

    return render_template('login.html', form=form, title="Login", show_form=show_form, mode=mode)

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
        return render_template('dashboard_admin.html')
    else:
        rooms = Room.query.all()
        return render_template('dashboard_user.html', rooms=rooms)

#PEMINJAMAN RUANGAN (untuk user)
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book_room():
    form = BookingForm()

    # UPDATE pilihan dropdown ruangan
    form.ruangan.choices = [(r.id, r.name) for r in Room.query.all()]

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

#PANEL ADMIN / DATA PENGAJUAN
@app.route('/admin', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin():
    bookings = Booking.query.order_by(Booking.start_time.desc()).all()

    if request.method == 'POST':
        booking_id = request.form.get('booking_id', type=int)
        action = request.form.get('action')
        booking = db.session.get(Booking, booking_id) if booking_id else None

        if booking and booking.status == 'pending':
            try:
                if action == 'approve':
                    booking.set_status('approved')
                    booking.is_read = False
                elif action == 'reject':
                    booking.set_status('rejected')
                    booking.is_read = False
                db.session.commit()
            except ValueError as e:
                db.session.rollback()
                flash(str(e), 'danger')

        return redirect(url_for('admin'))

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
    
    rooms = Room.query.all()
    return render_template('data_ruangan.html', rooms=rooms)

@app.route('/laporan_peminjaman')
@login_required
@role_required('admin')
def laporan_peminjaman():
    bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    return render_template('laporan_peminjaman.html', bookings=bookings, title="Laporan Peminjaman")

#NOTIFIKASI NAVBAR
@app.context_processor
def inject_notifications():
    # Admin: tidak perlu notifikasi user
    if current_user.is_authenticated and getattr(current_user, "role", "") != 'admin':
        notifications = Booking.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(Booking.start_time.desc()).all()
        return dict(nav_notifications=notifications)
    return dict(nav_notifications=[])

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
        'jadwal_admin.html',
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

#RUN APP
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

 