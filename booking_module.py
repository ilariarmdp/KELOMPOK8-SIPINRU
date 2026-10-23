"""
Modul Peminjaman Ruangan (SIPINRU)
Implementasi dari Sequence Diagram "Mengajukan Peminjaman Ruangan"
dan "Validasi Pengajuan oleh Admin".

Penerapan konsep OOP:
- Encapsulation   : atribut Booking bersifat private, diakses lewat property/method
- Inheritance     : KTMDocument & SuratIzinDocument mewarisi UploadedDocument
- Polymorphism    : method validate() di-override oleh tiap subclass
- Exception       : BookingError dan turunannya untuk business logic
"""

from datetime import datetime


class BookingError(Exception):
    """Exception dasar untuk semua kesalahan pada modul booking."""


class DokumenWajibError(BookingError):
    """Dilempar jika dokumen wajib (KTM) tidak diunggah."""


class FormatFileError(BookingError):
    """Dilempar jika format file tidak didukung."""


class StatusTidakValidError(BookingError):
    """Dilempar jika booking bukan berstatus pending saat divalidasi."""


class BookingTidakDitemukanError(BookingError):
    """Dilempar jika booking dengan ID tertentu tidak ada."""


# ---------------------------------------------------------------
# Inheritance + Polymorphism
# ---------------------------------------------------------------
class UploadedDocument:
    """Kelas induk untuk dokumen yang diunggah user."""

    ALLOWED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
    PREFIX = "DOC"

    def __init__(self, filename):
        self._filename = filename  # private (encapsulation)

    @property
    def filename(self):
        return self._filename

    def validate(self):
        """Validasi dasar: cek format file."""
        if not self._filename.lower().endswith(self.ALLOWED_EXTENSIONS):
            raise FormatFileError(
                f"Format file tidak didukung: {self._filename}. "
                f"Gunakan {', '.join(self.ALLOWED_EXTENSIONS)}"
            )

    def stored_name(self):
        """Nama file aman + timestamp + prefix (sesuai sequence diagram)."""
        safe = self._filename.replace(" ", "_")
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{self.PREFIX}_{stamp}_{safe}"


class KTMDocument(UploadedDocument):
    """KTM: WAJIB diunggah."""

    PREFIX = "KTM"

    def validate(self):  # override
        if not self._filename:
            raise DokumenWajibError("Upload KTM wajib!")
        super().validate()


class SuratIzinDocument(UploadedDocument):
    """Surat izin: OPSIONAL. Divalidasi hanya jika ada."""

    PREFIX = "SURAT"

    def validate(self):  # override
        if self._filename:
            super().validate()


# ---------------------------------------------------------------
# Encapsulation
# ---------------------------------------------------------------
class Booking:
    """Entitas peminjaman ruangan."""

    _counter = 0

    def __init__(self, user_id, room_id, start_time, ktm, surat_izin=None):
        Booking._counter += 1
        self._id = Booking._counter
        self._user_id = user_id
        self._room_id = room_id
        self._start_time = start_time
        self._ktm = ktm
        self._surat_izin = surat_izin
        self._status = "pending"
        self._is_read = False

    # --- getter (read-only) ---
    @property
    def id(self):
        return self._id

    @property
    def user_id(self):
        return self._user_id

    @property
    def room_id(self):
        return self._room_id

    @property
    def start_time(self):
        return self._start_time

    @property
    def status(self):
        return self._status

    @property
    def is_read(self):
        return self._is_read

    # --- perubahan status hanya lewat method ini ---
    def approve(self):
        self._ensure_pending()
        self._status = "approved"
        self._is_read = False

    def reject(self):
        self._ensure_pending()
        self._status = "rejected"
        self._is_read = False

    def mark_as_read(self):
        self._is_read = True

    def _ensure_pending(self):
        if self._status != "pending":
            raise StatusTidakValidError(
                f"Booking #{self._id} berstatus '{self._status}', bukan pending."
            )

    def __str__(self):
        return (
            f"Booking #{self._id} | user={self._user_id} | room={self._room_id} "
            f"| {self._start_time:%d-%m-%Y %H:%M} | status={self._status}"
        )


# ---------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------
class BookingService:
    """Menjalankan alur dari sequence diagram.
    Penyimpanan memakai list (pengganti Database Booking);
    ganti dengan SQLAlchemy saat integrasi ke Flask."""

    def __init__(self):
        self._bookings = []

    def ajukan(self, user_id, room_id, start_time, ktm_name, surat_name=None):
        """Alur: validasi dokumen -> buat Booking pending -> simpan."""
        ktm = KTMDocument(ktm_name)
        surat = SuratIzinDocument(surat_name)

        for doc in (ktm, surat):  # polymorphism: validate() beda tiap kelas
            doc.validate()

        booking = Booking(user_id, room_id, start_time, ktm, surat)
        self._bookings.append(booking)
        return booking

    def daftar_milik_user(self, user_id):
        """Alur notifikasi: booking milik user, terbaru dulu (start_time)."""
        milik = [b for b in self._bookings if b.user_id == user_id]
        return sorted(milik, key=lambda b: b.start_time, reverse=True)

    def validasi_admin(self, booking_id, aksi):
        """Alur admin: approve / reject booking berstatus pending."""
        booking = self._cari(booking_id)
        if aksi == "approve":
            booking.approve()
        elif aksi == "reject":
            booking.reject()
        else:
            raise BookingError(f"Aksi tidak dikenal: {aksi}")
        return booking

    def tandai_dibaca(self, booking_id, user_id):
        """Alur mark_as_read: hanya jika booking milik user."""
        booking = self._cari(booking_id)
        if booking.user_id != user_id:
            raise BookingError("Booking bukan milik user ini.")
        booking.mark_as_read()
        return booking

    def _cari(self, booking_id):
        for b in self._bookings:
            if b.id == booking_id:
                return b
        raise BookingTidakDitemukanError(f"Booking #{booking_id} tidak ditemukan.")


# ---------------------------------------------------------------
# Demo / pengujian cepat
# ---------------------------------------------------------------
if __name__ == "__main__":
    service = BookingService()
    waktu = datetime(2026, 11, 5, 9, 0)

    print("== Skenario 1: pengajuan sukses ==")
    try:
        b = service.ajukan(1, 101, waktu, "ktm_cia.jpg", "surat_izin.pdf")
        print("Peminjaman berhasil diajukan ->", b)
    except BookingError as e:
        print("Gagal:", e)

    print("\n== Skenario 2: KTM tidak diunggah ==")
    try:
        service.ajukan(1, 102, waktu, "")
    except DokumenWajibError as e:
        print("Gagal:", e)

    print("\n== Skenario 3: format file salah ==")
    try:
        service.ajukan(1, 103, waktu, "ktm.exe")
    except FormatFileError as e:
        print("Gagal:", e)

    print("\n== Skenario 4: admin approve ==")
    print(service.validasi_admin(1, "approve"))

    print("\n== Skenario 5: approve ulang (bukan pending) ==")
    try:
        service.validasi_admin(1, "approve")
    except StatusTidakValidError as e:
        print("Gagal:", e)

    print("\n== Skenario 6: user tandai notifikasi dibaca ==")
    print(service.tandai_dibaca(1, user_id=1))
    print("is_read =", service.daftar_milik_user(1)[0].is_read)