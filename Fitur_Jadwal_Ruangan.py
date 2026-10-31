"""
SIPINRU - Fitur Jadwal Ruangan (modul mandiri, 1 file).

Hanya memakai library bawaan Python; tidak bergantung/mengubah file lain.
Isi: exception -> entity (DataJadwalRuangan) -> aktor (User/Admin, inheritance
& polymorphism) -> repository (interface/ABC) -> service (business logic).

Jalankan demo : python fitur_jadwal_ruangan.py
Jalankan test : python -m unittest fitur_jadwal_ruangan -v
"""
import unittest
from abc import ABC, abstractmethod
from datetime import time
from enum import Enum

# ======================= EXCEPTION =======================
class JadwalError(Exception):
    """Base exception semua error pada modul jadwal."""


class DataTidakValidError(JadwalError):
    """Input jadwal tidak valid (kosong, jam terbalik, enum salah)."""


class JadwalBentrokError(JadwalError):
    """Jadwal bertabrakan dengan jadwal lain di ruangan yang sama."""


class JadwalTidakDitemukanError(JadwalError):
    """ID jadwal tidak ada di repository."""


class AksesDitolakError(JadwalError):
    """Pengguna tidak punya hak untuk operasi ini."""


# ======================= ENTITY =======================
class KategoriKegiatan(Enum):
    KULIAH = "kuliah"
    RAPAT = "rapat"
    SEMINAR = "seminar"
    LAINNYA = "lainnya"


class StatusPengaju(Enum):
    DOSEN = "dosen"
    MAHASISWA = "mahasiswa"
    STAFF = "staff"


class StatusRuang(Enum):
    TERSEDIA = "tersedia"
    DIPAKAI = "dipakai"
    MAINTENANCE = "maintenance"


class DataJadwalRuangan:
    """Atribut private + property -> encapsulation."""

    def __init__(self, id_: int, nama_ruang: str, waktu_mulai: time,
                 waktu_selesai: time, kategori_kegiatan: KategoriKegiatan,
                 status_pengaju: StatusPengaju,
                 status_ruang: StatusRuang = StatusRuang.TERSEDIA):
        self.__id = id_
        self.nama_ruang = nama_ruang
        self.set_waktu(waktu_mulai, waktu_selesai)
        self.kategori_kegiatan = kategori_kegiatan
        self.status_pengaju = status_pengaju
        self.status_ruang = status_ruang

    # --- read-only id ---
    @property
    def id(self) -> int:
        return self.__id

    # --- nama_ruang ---
    @property
    def nama_ruang(self) -> str:
        return self.__nama_ruang

    @nama_ruang.setter
    def nama_ruang(self, value: str):
        if not isinstance(value, str) or not value.strip():
            raise DataTidakValidError("Nama ruang tidak boleh kosong.")
        self.__nama_ruang = value.strip()

    # --- waktu (divalidasi bersama) ---
    @property
    def waktu_mulai(self) -> time:
        return self.__waktu_mulai

    @property
    def waktu_selesai(self) -> time:
        return self.__waktu_selesai

    def set_waktu(self, mulai: time, selesai: time):
        if not isinstance(mulai, time) or not isinstance(selesai, time):
            raise DataTidakValidError("Waktu harus bertipe datetime.time.")
        if mulai >= selesai:
            raise DataTidakValidError("Waktu mulai harus lebih awal dari waktu selesai.")
        self.__waktu_mulai, self.__waktu_selesai = mulai, selesai

    # --- enum fields ---
    @property
    def kategori_kegiatan(self) -> KategoriKegiatan:
        return self.__kategori

    @kategori_kegiatan.setter
    def kategori_kegiatan(self, value):
        if not isinstance(value, KategoriKegiatan):
            raise DataTidakValidError("Kategori kegiatan tidak valid.")
        self.__kategori = value

    @property
    def status_pengaju(self) -> StatusPengaju:
        return self.__status_pengaju

    @status_pengaju.setter
    def status_pengaju(self, value):
        if not isinstance(value, StatusPengaju):
            raise DataTidakValidError("Status pengaju tidak valid.")
        self.__status_pengaju = value

    @property
    def status_ruang(self) -> StatusRuang:
        return self.__status_ruang

    @status_ruang.setter
    def status_ruang(self, value):
        if not isinstance(value, StatusRuang):
            raise DataTidakValidError("Status ruang tidak valid.")
        self.__status_ruang = value

    def bentrok_dengan(self, nama_ruang: str, mulai: time, selesai: time) -> bool:
        return (self.nama_ruang.lower() == nama_ruang.strip().lower()
                and mulai < self.waktu_selesai and selesai > self.waktu_mulai)

    def __str__(self):
        return (f"[{self.id}] {self.nama_ruang} | {self.waktu_mulai:%H:%M}-"
                f"{self.waktu_selesai:%H:%M} | {self.kategori_kegiatan.value} | "
                f"{self.status_pengaju.value} | {self.status_ruang.value}")


# ======================= AKTOR =======================
class PenggunaJadwal(ABC):
    def __init__(self, id_: int, nama: str, email: str):
        self._id = id_
        self._nama = nama
        self._email = email
        self._login = False

    @property
    def nama(self) -> str:
        return self._nama

    def login(self):
        self._login = True

    def logout(self):
        self._login = False

    @property
    def sudah_login(self) -> bool:
        return self._login

    @property
    @abstractmethod
    def boleh_kelola_jadwal(self) -> bool:
        """Dioverride tiap subclass (polymorphism)."""

    @abstractmethod
    def daftar_menu(self) -> list[str]:
        ...


class UserJadwal(PenggunaJadwal):
    @property
    def boleh_kelola_jadwal(self) -> bool:
        return False

    def daftar_menu(self) -> list[str]:
        return ["Lihat Jadwal Ruangan", "Isi Form Peminjaman", "Lihat Notifikasi", "Logout"]


class AdminJadwal(PenggunaJadwal):
    @property
    def boleh_kelola_jadwal(self) -> bool:
        return True

    def daftar_menu(self) -> list[str]:
        return ["Lihat Jadwal Ruangan", "Input Jadwal", "Edit Jadwal",
                "Hapus Jadwal", "Logout"]


# ======================= REPOSITORY =======================
class JadwalRepository(ABC):
    @abstractmethod
    def simpan(self, jadwal: DataJadwalRuangan) -> None: ...

    @abstractmethod
    def ambil(self, id_: int) -> DataJadwalRuangan: ...

    @abstractmethod
    def hapus(self, id_: int) -> None: ...

    @abstractmethod
    def semua(self) -> list[DataJadwalRuangan]: ...

    @abstractmethod
    def id_berikutnya(self) -> int: ...


class InMemoryJadwalRepository(JadwalRepository):
    def __init__(self):
        self.__data: dict[int, DataJadwalRuangan] = {}
        self.__counter = 0

    def simpan(self, jadwal):
        self.__data[jadwal.id] = jadwal

    def ambil(self, id_):
        try:
            return self.__data[id_]
        except KeyError:
            raise JadwalTidakDitemukanError(f"Jadwal dengan id {id_} tidak ditemukan.") from None

    def hapus(self, id_):
        self.ambil(id_)  # raise jika tidak ada
        del self.__data[id_]

    def semua(self):
        return sorted(self.__data.values(), key=lambda j: (j.nama_ruang, j.waktu_mulai))

    def id_berikutnya(self):
        self.__counter += 1
        return self.__counter


# ======================= SERVICE =======================
class JadwalRuanganService:
    def __init__(self, repo: JadwalRepository):
        self.__repo = repo  # dependency injection ke interface

    @staticmethod
    def __cek_akses(pelaku: PenggunaJadwal):
        if not pelaku.sudah_login:
            raise AksesDitolakError("Silakan login terlebih dahulu.")
        if not pelaku.boleh_kelola_jadwal:
            raise AksesDitolakError(f"{pelaku.nama} tidak berhak mengelola jadwal.")

    def __validasi_bentrok(self, nama_ruang, mulai, selesai, abaikan_id=None):
        """validasiDataJadwalRuangan()"""
        for j in self.__repo.semua():
            if j.id != abaikan_id and j.bentrok_dengan(nama_ruang, mulai, selesai):
                raise JadwalBentrokError(
                    f"Bentrok dengan jadwal {j.id} ({j.waktu_mulai:%H:%M}-{j.waktu_selesai:%H:%M}).")

    def input_jadwal(self, pelaku: PenggunaJadwal, nama_ruang: str, mulai: time,
                     selesai: time, kategori: KategoriKegiatan,
                     status_pengaju: StatusPengaju,
                     status_ruang: StatusRuang = StatusRuang.TERSEDIA) -> DataJadwalRuangan:
        self.__cek_akses(pelaku)
        jadwal = DataJadwalRuangan(self.__repo.id_berikutnya(), nama_ruang, mulai,
                                   selesai, kategori, status_pengaju, status_ruang)
        self.__validasi_bentrok(jadwal.nama_ruang, mulai, selesai)
        self.__repo.simpan(jadwal)
        return jadwal

    def edit_jadwal(self, pelaku: PenggunaJadwal, id_: int, **perubahan) -> DataJadwalRuangan:
        self.__cek_akses(pelaku)
        jadwal = self.__repo.ambil(id_)
        mulai = perubahan.get("waktu_mulai", jadwal.waktu_mulai)
        selesai = perubahan.get("waktu_selesai", jadwal.waktu_selesai)
        ruang = perubahan.get("nama_ruang", jadwal.nama_ruang)
        # validasi dulu pada objek sementara agar data asli tidak rusak
        DataJadwalRuangan(id_, ruang, mulai, selesai, jadwal.kategori_kegiatan,
                          jadwal.status_pengaju, jadwal.status_ruang)
        self.__validasi_bentrok(ruang, mulai, selesai, abaikan_id=id_)
        jadwal.nama_ruang = ruang
        jadwal.set_waktu(mulai, selesai)
        if "kategori_kegiatan" in perubahan:
            jadwal.kategori_kegiatan = perubahan["kategori_kegiatan"]
        if "status_pengaju" in perubahan:
            jadwal.status_pengaju = perubahan["status_pengaju"]
        if "status_ruang" in perubahan:
            jadwal.status_ruang = perubahan["status_ruang"]
        self.__repo.simpan(jadwal)
        return jadwal

    def hapus_jadwal(self, pelaku: PenggunaJadwal, id_: int) -> None:
        self.__cek_akses(pelaku)
        self.__repo.hapus(id_)

    def lihat_list(self, nama_ruang: str | None = None) -> list[DataJadwalRuangan]:
        """perlihatkanListDataJadwalRuangan() - boleh diakses UserJadwal & AdminJadwal."""
        data = self.__repo.semua()
        if nama_ruang:
            data = [j for j in data if j.nama_ruang.lower() == nama_ruang.strip().lower()]
        return data


# ======================= DEMO =======================
def jalankan():
    svc = JadwalRuanganService(InMemoryJadwalRepository())
    admin, user = AdminJadwal(1, "AdminJadwal", "admin@kampus.ac.id"), UserJadwal(2, "Budi", "budi@kampus.ac.id")
    admin.login(); user.login()

    for p in (admin, user):  # polymorphism
        print(type(p).__name__, "->", p.daftar_menu())

    def coba(judul, fn):
        try:
            hasil = fn()
            print(f"OK   {judul}: {hasil if hasil else ''}")
        except JadwalError as e:
            print(f"GAGAL {judul}: {type(e).__name__} - {e}")

    coba("input A", lambda: svc.input_jadwal(admin, "Lab 1", time(8), time(10), KategoriKegiatan.KULIAH, StatusPengaju.DOSEN))
    coba("input bentrok", lambda: svc.input_jadwal(admin, "Lab 1", time(9), time(11), KategoriKegiatan.RAPAT, StatusPengaju.STAFF))
    coba("input jam terbalik", lambda: svc.input_jadwal(admin, "Lab 1", time(12), time(11), KategoriKegiatan.RAPAT, StatusPengaju.STAFF))
    coba("user input", lambda: svc.input_jadwal(user, "Lab 2", time(8), time(9), KategoriKegiatan.RAPAT, StatusPengaju.MAHASISWA))
    coba("edit", lambda: svc.edit_jadwal(admin, 1, waktu_selesai=time(11)))
    coba("hapus id 99", lambda: svc.hapus_jadwal(admin, 99))
    print("\nJadwal (dilihat UserJadwal):")
    for j in svc.lihat_list(): print(" ", j)


# ======================= UNIT TEST =======================
K, S = KategoriKegiatan, StatusPengaju



class TestJadwal(unittest.TestCase):
    def setUp(self):
        self.svc = JadwalRuanganService(InMemoryJadwalRepository())
        self.admin, self.user = AdminJadwal(1, "A", "a@x"), UserJadwal(2, "U", "u@x")
        self.admin.login(); self.user.login()
        self.j = self.svc.input_jadwal(self.admin, "R1", time(8), time(10), K.KULIAH, S.DOSEN)

    def test_bentrok(self):
        with self.assertRaises(JadwalBentrokError):
            self.svc.input_jadwal(self.admin, "R1", time(9), time(11), K.RAPAT, S.STAFF)

    def test_ruang_lain_tidak_bentrok(self):
        self.svc.input_jadwal(self.admin, "R2", time(9), time(11), K.RAPAT, S.STAFF)

    def test_jam_terbalik(self):
        with self.assertRaises(DataTidakValidError):
            self.svc.input_jadwal(self.admin, "R1", time(12), time(11), K.RAPAT, S.STAFF)

    def test_user_ditolak(self):
        with self.assertRaises(AksesDitolakError):
            self.svc.hapus_jadwal(self.user, self.j.id)

    def test_edit_dan_hapus(self):
        self.svc.edit_jadwal(self.admin, self.j.id, waktu_selesai=time(11))
        self.assertEqual(self.j.waktu_selesai, time(11))
        self.svc.hapus_jadwal(self.admin, self.j.id)
        with self.assertRaises(JadwalTidakDitemukanError):
            self.svc.hapus_jadwal(self.admin, self.j.id)

    def test_edit_gagal_tidak_merusak_data(self):
        with self.assertRaises(DataTidakValidError):
            self.svc.edit_jadwal(self.admin, self.j.id, waktu_mulai=time(23))
        self.assertEqual(self.j.waktu_mulai, time(8))




if __name__ == "__main__":
    jalankan()