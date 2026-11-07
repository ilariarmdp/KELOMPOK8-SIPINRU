from models import db, Booking


class ValidasiError(Exception):
    """Kesalahan pada proses validasi pengajuan."""


class ValidasiService:
    """Kelas induk: satu tahap validasi pengajuan."""
    STATUS_MASUK = None    # status yang boleh diproses tahap ini
    STATUS_SETUJU = None   # status hasil jika disetujui
    STATUS_TOLAK = None    # status hasil jika ditolak

    def antrean(self):
        return (Booking.query
                .filter_by(status=self.STATUS_MASUK)
                .order_by(Booking.start_time.asc())
                .all())

    def proses(self, booking_id, aksi):
        booking = db.session.get(Booking, booking_id) if booking_id else None
        if not booking:
            raise ValidasiError("Pengajuan tidak ditemukan.")
        if booking.status != self.STATUS_MASUK:
            raise ValidasiError("Pengajuan ini tidak berada pada tahap validasi Anda.")

        if aksi == 'approve':
            booking.set_status(self.STATUS_SETUJU)
        elif aksi == 'reject':
            booking.set_status(self.STATUS_TOLAK)
        else:
            raise ValidasiError(f"Aksi tidak dikenal: {aksi}")

        booking.is_read = False  # memicu notifikasi ke mahasiswa
        db.session.commit()
        return booking


class AdminValidasiService(ValidasiService):
    STATUS_MASUK = 'pending'
    STATUS_SETUJU = 'approved_admin'
    STATUS_TOLAK = 'rejected'


class FakultasValidasiService(ValidasiService):
    STATUS_MASUK = 'approved_admin'
    STATUS_SETUJU = 'approved'
    STATUS_TOLAK = 'rejected_fakultas'