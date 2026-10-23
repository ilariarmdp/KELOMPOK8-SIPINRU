from abc import ABC, abstractmethod
from sqlalchemy.exc import SQLAlchemyError
from models import db, Room


# ===== Exception handling =====
class RuanganError(Exception):
    """Error dasar untuk fitur ruangan."""


class DataRuanganTidakValidError(RuanganError):
    """Dilempar saat data yang diisi admin tidak valid."""


class GagalMenyimpanRuanganError(RuanganError):
    """Dilempar saat penyimpanan ke database gagal."""


# ===== Inheritance dan polymorphism =====
class AturanKapasitas(ABC):
    """Class induk: aturan batas kapasitas ruangan."""

    @abstractmethod
    def batas_maksimal(self):
        pass

    def periksa(self, kapasitas):
        if kapasitas is None or kapasitas < 1:
            raise DataRuanganTidakValidError("Kapasitas minimal 1 orang.")
        if kapasitas > self.batas_maksimal():
            raise DataRuanganTidakValidError(
                f"Kapasitas maksimal untuk ruangan ini {self.batas_maksimal()} orang."
            )


class AturanRuangUmum(AturanKapasitas):
    def batas_maksimal(self):
        return 100


class AturanRuangLab(AturanKapasitas):
    def batas_maksimal(self):
        return 40


# ===== Encapsulation =====
class RuanganService:
    def __init__(self):
        self.__session = db.session          # private

    def __pilih_aturan(self, nama_ruangan):  # private method
        if nama_ruangan.strip().lower().startswith("lab"):
            return AturanRuangLab()
        return AturanRuangUmum()

    def tambah_ruangan(self, nama, kapasitas, fasilitas, status):
        if not nama or not nama.strip():
            raise DataRuanganTidakValidError("Nama ruangan wajib diisi.")

        aturan = self.__pilih_aturan(nama)   # polymorphism
        aturan.periksa(kapasitas)

        if Room.query.filter(Room.name.ilike(nama.strip())).first():
            raise DataRuanganTidakValidError("Nama ruangan sudah digunakan.")

        ruangan_baru = Room(
            name=nama.strip(),
            capacity=kapasitas,
            description=fasilitas,
            status=status
        )
        try:
            self.__session.add(ruangan_baru)
            self.__session.commit()
        except SQLAlchemyError as e:
            self.__session.rollback()
            raise GagalMenyimpanRuanganError("Gagal menyimpan ruangan ke database.") from e