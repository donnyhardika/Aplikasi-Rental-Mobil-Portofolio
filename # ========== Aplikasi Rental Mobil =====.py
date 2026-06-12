# ========== Aplikasi Rental Mobil ==========
# Versi 2.0 — dengan Database SQLite, Sistem Akun, dan Update Parsial

import sqlite3
import hashlib
import os

DB_FILE = "rental_mobil.db"

# KONEKSI & INISIALISASI DATABASE

def get_connection():
    """Mengembalikan koneksi ke database SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Agar hasil query bisa diakses seperti dict
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inisialisasi_database():
    """Membuat tabel-tabel yang diperlukan jika belum ada, lalu isi data awal."""
    conn = get_connection()
    cur = conn.cursor()

    # Tabel akun pengguna
    cur.execute("""
        CREATE TABLE IF NOT EXISTS akun (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT    NOT NULL UNIQUE,
            password  TEXT    NOT NULL,
            role      TEXT    NOT NULL CHECK(role IN ('staff', 'pelanggan')),
            id_pelanggan INTEGER DEFAULT NULL
        )
    """)

    # Tabel mobil
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mobil (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            merk    TEXT    NOT NULL UNIQUE,
            tahun   INTEGER NOT NULL,
            harga   INTEGER NOT NULL,
            status  TEXT    NOT NULL DEFAULT 'Tersedia' CHECK(status IN ('Tersedia', 'Dirental'))
        )
    """)

    # Tabel pelanggan
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pelanggan (
            id_pelanggan INTEGER PRIMARY KEY AUTOINCREMENT,
            nama         TEXT    NOT NULL UNIQUE,
            alamat       TEXT,
            no_telp      TEXT
        )
    """)

    # Tabel penyewaan
    cur.execute("""
        CREATE TABLE IF NOT EXISTS penyewaan (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pelanggan INTEGER NOT NULL,
            id_mobil     INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan),
            FOREIGN KEY (id_mobil)     REFERENCES mobil(id)
        )
    """)

    conn.commit()

    # Isi data awal hanya jika tabel masih kosong
    # Akun staff default
    if not cur.execute("SELECT 1 FROM akun WHERE role='staff'").fetchone():
        pw_hash = hash_password("admin123")
        cur.execute(
            "INSERT INTO akun (username, password, role) VALUES (?, ?, 'staff')",
            ("admin", pw_hash)
        )

    # Data mobil awal
    if not cur.execute("SELECT 1 FROM mobil").fetchone():
        mobil_awal = [
            ("Toyota Avanza",  2023, 400000, "Tersedia"),
            ("Honda Brio",     2024, 350000, "Tersedia"),
            ("Daihatsu Sigra", 2025, 300000, "Tersedia"),
            ("Mitsubishi Xpander", 2022, 450000, "Tersedia"),
            ("Suzuki Ertiga",  2023, 380000, "Tersedia"),
        ]
        cur.executemany(
            "INSERT INTO mobil (merk, tahun, harga, status) VALUES (?, ?, ?, ?)",
            mobil_awal
        )

    # Data pelanggan awal
    if not cur.execute("SELECT 1 FROM pelanggan").fetchone():
        pelanggan_awal = [
            ("Andi Sukirman", "Jakarta", "081234567890"),
            ("Budi Santoso",  "Bandung", "081234567891"),
            ("Citra Lestari", "Bogor",   "081234567892"),
        ]
        cur.executemany(
            "INSERT INTO pelanggan (nama, alamat, no_telp) VALUES (?, ?, ?)",
            pelanggan_awal
        )

    # Data penyewaan awal
    if not cur.execute("SELECT 1 FROM penyewaan").fetchone():
        penyewaan_awal = [
            (1, 1), # Andi menyewa Toyota Avanza
            (2, 4)  # Budi menyewa Mitsubishi Xpander
        ]
        cur.executemany(
            "INSERT INTO penyewaan (id_pelanggan, id_mobil) VALUES (?, ?)",
            penyewaan_awal
        )
        # Update status mobil sesuai penyewaan awal
        for id_pelanggan, id_mobil in penyewaan_awal:
            cur.execute(
                "UPDATE mobil SET status = 'Dirental' WHERE id = ?", (id_mobil,)
            )

    # Akun member untuk pelanggan yang sudah ada (password default = nama lowercase)
    for row in cur.execute("SELECT id_pelanggan, nama FROM pelanggan").fetchall():
        existing = cur.execute(
            "SELECT 1 FROM akun WHERE id_pelanggan = ?", (row["id_pelanggan"],)
        ).fetchone()
        if not existing:
            username = row["nama"].lower().replace(" ", "_")
            pw_hash  = hash_password(row["nama"].lower())
            cur.execute(
                "INSERT OR IGNORE INTO akun (username, password, role, id_pelanggan) "
                "VALUES (?, ?, 'pelanggan', ?)",
                (username, pw_hash, row["id_pelanggan"])
            )

    conn.commit()
    conn.close()


# UTILITAS

def hash_password(password: str) -> str:
    """Mengembalikan hash SHA-256 dari password."""
    return hashlib.sha256(password.encode()).hexdigest()


def cetak_garis(panjang=85):
    print("-" * panjang)


# AUTENTIKASI

def login() -> dict | None:
    """
    Meminta username & password, mengembalikan dict akun jika berhasil,
    atau None jika gagal.
    """
    print("\n=== LOGIN ===")
    username = input("Username : ").strip()
    password = input("Password : ").strip()
    pw_hash  = hash_password(password)

    conn = get_connection()
    akun = conn.execute(
        "SELECT * FROM akun WHERE username = ? AND password = ?",
        (username, pw_hash)
    ).fetchone()
    conn.close()

    if akun:
        print(f"\nSelamat datang, {username}! (Role: {akun['role'].upper()})")
        return dict(akun)
    else:
        print("! Username atau password salah.")
        return None


def register_pelanggan():
    """Mendaftarkan akun baru sebagai pelanggan sekaligus menambah data pelanggan."""
    print("\n=== DAFTAR AKUN PELANGGAN ===")

    # Data akun
    username = input("Username baru : ").strip()
    if not username:
        print("! Username tidak boleh kosong!")
        return

    password = input("Password baru : ").strip()
    if not password:
        print("! Password tidak boleh kosong!")
        return

    # Data pelanggan
    nama = input("Nama lengkap  : ").strip()
    if not nama:
        print("! Nama tidak boleh kosong!")
        return

    alamat  = input("Alamat        : ").strip()
    no_telp = input("No. Telepon   : ").strip()

    conn = get_connection()
    cur  = conn.cursor()

    # Cek username sudah dipakai
    if cur.execute("SELECT 1 FROM akun WHERE username = ?", (username,)).fetchone():
        print("! Username sudah digunakan, pilih username lain.")
        conn.close()
        return

    # Cek nama pelanggan sudah terdaftar
    if cur.execute(
        "SELECT 1 FROM pelanggan WHERE LOWER(nama) = ?", (nama.lower(),)
    ).fetchone():
        print("! Nama pelanggan sudah terdaftar!")
        conn.close()
        return

    konfirmasi = input("Simpan data? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Pendaftaran dibatalkan.")
        conn.close()
        return

    # Simpan pelanggan & akun dalam satu transaksi
    cur.execute(
        "INSERT INTO pelanggan (nama, alamat, no_telp) VALUES (?, ?, ?)",
        (nama, alamat, no_telp)
    )
    id_pelanggan = cur.lastrowid
    pw_hash      = hash_password(password)
    cur.execute(
        "INSERT INTO akun (username, password, role, id_pelanggan) "
        "VALUES (?, ?, 'pelanggan', ?)",
        (username, pw_hash, id_pelanggan)
    )
    conn.commit()
    conn.close()

    print(f"Akun '{username}' berhasil dibuat. Silakan login.")


def register_staff():
    """
    Mendaftarkan akun staff baru (hanya bisa dilakukan oleh staff yang sedang login).
    """
    print("\n=== TAMBAH AKUN STAFF ===")
    username = input("Username baru : ").strip()
    if not username:
        print("! Username tidak boleh kosong!")
        return
    password = input("Password baru : ").strip()
    if not password:
        print("! Password tidak boleh kosong!")
        return

    conn = get_connection()
    if conn.execute(
        "SELECT 1 FROM akun WHERE username = ?", (username,)
    ).fetchone():
        print("! Username sudah digunakan.")
        conn.close()
        return

    konfirmasi = input("Simpan akun staff baru? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    pw_hash = hash_password(password)
    conn.execute(
        "INSERT INTO akun (username, password, role) VALUES (?, ?, 'staff')",
        (username, pw_hash)
    )
    conn.commit()
    conn.close()
    print(f"Akun staff '{username}' berhasil ditambahkan.")


# MENU

def tampilkan_menu_staff():
    print("\n=== MENU STAFF ===")
    print("1.  Tampilkan Semua Mobil")
    print("2.  Cari Mobil")
    print("3.  Tambah Mobil")
    print("4.  Update Data Mobil")
    print("5.  Hapus Mobil")
    print("6.  Tampilkan Semua Pelanggan")
    print("7.  Tambah Pelanggan")
    print("8.  Update Pelanggan")
    print("9.  Hapus Pelanggan")
    print("10. Tampilkan Semua Transaksi Rental")
    print("11. Tambah Akun Staff")
    print("12. Keluar / Logout")


def tampilkan_menu_pelanggan():
    print("\n=== MENU PELANGGAN ===")
    print("1. Tampilkan Semua Mobil")
    print("2. Cari Mobil")
    print("3. Rental Mobil")
    print("4. Kembalikan Mobil")
    print("5. Lihat Mobil yang Saya Rental")
    print("6. Keluar / Logout")


# FITUR MOBIL

def tampilkan_semua_mobil():
    conn = get_connection()
    mobil_list = conn.execute("SELECT * FROM mobil ORDER BY id").fetchall()
    conn.close()

    if not mobil_list:
        print("Belum ada data mobil.")
        return

    print(f"\n{'ID':<5} {'Merk Mobil':<25} {'Tahun':<8} {'Harga/Hari':<15} {'Status':<12}")
    cetak_garis(75)
    for m in mobil_list:
        print(f"{m['id']:<5} {m['merk']:<25} {m['tahun']:<8} Rp{m['harga']:<13,} {m['status']:<12}")


def cari_mobil():
    kata = input("Masukkan kata kunci merk mobil: ").strip().lower()
    conn = get_connection()
    hasil = conn.execute(
        "SELECT * FROM mobil WHERE LOWER(merk) LIKE ?", (f"%{kata}%",)
    ).fetchall()
    conn.close()

    if not hasil:
        print("! Tidak ada mobil yang cocok.")
        return

    print(f"\n{'ID':<5} {'Merk Mobil':<25} {'Tahun':<8} {'Harga/Hari':<15} {'Status':<12}")
    cetak_garis(75)
    for m in hasil:
        print(f"{m['id']:<5} {m['merk']:<25} {m['tahun']:<8} Rp{m['harga']:<13,} {m['status']:<12}")


def tambah_mobil():
    merk = input("Merk mobil   : ").strip()
    if not merk:
        print("! Merk tidak boleh kosong!")
        return

    try:
        tahun = int(input("Tahun mobil  : "))
    except ValueError:
        print("! Tahun harus berupa angka!")
        return
    if not (1990 <= tahun <= 2025):
        print("! Tahun tidak valid (1990-2025)!")
        return

    try:
        harga = int(input("Harga per hari: "))
        if harga <= 0:
            print("! Harga harus lebih dari 0!")
            return
    except ValueError:
        print("! Harga harus berupa angka!")
        return

    status = input("Status (Tersedia/Dirental): ").strip().title()
    if status not in ["Tersedia", "Dirental"]:
        print("! Status harus 'Tersedia' atau 'Dirental'!")
        return

    conn = get_connection()
    if conn.execute(
        "SELECT 1 FROM mobil WHERE LOWER(merk) = ?", (merk.lower(),)
    ).fetchone():
        print("! Mobil dengan merk ini sudah ada!")
        conn.close()
        return

    konfirmasi = input("Simpan? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    cur = conn.execute(
        "INSERT INTO mobil (merk, tahun, harga, status) VALUES (?, ?, ?, ?)",
        (merk, tahun, harga, status)
    )
    conn.commit()
    print(f"Mobil '{merk}' berhasil ditambahkan dengan ID {cur.lastrowid}.")
    conn.close()


def update_mobil():
    """
    Update parsial: user hanya mengisi field yang ingin diubah.
    Jika dikosongkan, field tersebut tidak berubah.
    """
    try:
        id_mobil = int(input("ID mobil yang ingin diupdate: "))
    except ValueError:
        print("! ID harus berupa angka!")
        return

    conn = get_connection()
    mobil = conn.execute("SELECT * FROM mobil WHERE id = ?", (id_mobil,)).fetchone()
    if not mobil:
        print("! ID mobil tidak ditemukan.")
        conn.close()
        return

    print(f"\nData saat ini:")
    print(f"  Merk   : {mobil['merk']}")
    print(f"  Tahun  : {mobil['tahun']}")
    print(f"  Harga  : Rp{mobil['harga']:,}")
    print(f"  Status : {mobil['status']}")
    print("(Kosongkan field dan tekan Enter jika tidak ingin mengubahnya)\n")

    # Ambil nilai baru, gunakan nilai lama jika kosong
    merk_baru = input(f"Merk baru   [{mobil['merk']}]: ").strip()
    merk_baru = merk_baru if merk_baru else mobil["merk"]

    raw_tahun = input(f"Tahun baru  [{mobil['tahun']}]: ").strip()
    if raw_tahun:
        try:
            tahun_baru = int(raw_tahun)
        except ValueError:
            print("! Tahun harus berupa angka!")
            conn.close()
            return
        if not (1990 <= tahun_baru <= 2025):
            print("! Tahun tidak valid!")
            conn.close()
            return
    else:
        tahun_baru = mobil["tahun"]

    raw_harga = input(f"Harga baru  [{mobil['harga']}]: ").strip()
    if raw_harga:
        try:
            harga_baru = int(raw_harga)
            if harga_baru <= 0:
                print("! Harga tidak boleh 0 atau negatif!")
                conn.close()
                return
        except ValueError:
            print("! Harga harus berupa angka!")
            conn.close()
            return
    else:
        harga_baru = mobil["harga"]

    raw_status = input(f"Status baru (Tersedia/Dirental) [{mobil['status']}]: ").strip().title()
    if raw_status:
        if raw_status not in ["Tersedia", "Dirental"]:
            print("! Status harus 'Tersedia' atau 'Dirental'!")
            conn.close()
            return
        status_baru = raw_status
    else:
        status_baru = mobil["status"]

    konfirmasi = input("\nSimpan perubahan? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    conn.execute(
        "UPDATE mobil SET merk=?, tahun=?, harga=?, status=? WHERE id=?",
        (merk_baru, tahun_baru, harga_baru, status_baru, id_mobil)
    )
    conn.commit()
    conn.close()
    print("Data mobil berhasil diupdate.")


def hapus_mobil():
    try:
        id_mobil = int(input("ID mobil yang ingin dihapus: "))
    except ValueError:
        print("! ID harus berupa angka!")
        return

    conn = get_connection()
    mobil = conn.execute("SELECT * FROM mobil WHERE id = ?", (id_mobil,)).fetchone()
    if not mobil:
        print("! ID mobil tidak ditemukan.")
        conn.close()
        return

    if conn.execute(
        "SELECT 1 FROM penyewaan WHERE id_mobil = ?", (id_mobil,)
    ).fetchone():
        print("! Mobil ini sedang dirental, tidak bisa dihapus.")
        conn.close()
        return

    print(f"Data: ID={mobil['id']} | {mobil['merk']} | Tahun {mobil['tahun']}")
    konfirmasi = input("Hapus mobil ini? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    conn.execute("DELETE FROM mobil WHERE id = ?", (id_mobil,))
    conn.commit()
    conn.close()
    print(f"Mobil '{mobil['merk']}' berhasil dihapus.")


# FITUR PELANGGAN

def tampilkan_semua_pelanggan():
    conn = get_connection()
    pelanggan_list = conn.execute("SELECT * FROM pelanggan ORDER BY id_pelanggan").fetchall()

    print(f"\n{'ID':<6} {'Nama':<18} {'Alamat':<18} {'No. Telp':<16} Mobil Dirental")
    cetak_garis(85)
    for p in pelanggan_list:
        pinjaman = conn.execute(
            """SELECT m.merk FROM penyewaan sw
               JOIN mobil m ON m.id = sw.id_mobil
               WHERE sw.id_pelanggan = ?""",
            (p["id_pelanggan"],)
        ).fetchall()
        mobil_info = ", ".join(m["merk"] for m in pinjaman) if pinjaman else "-"
        print(f"{p['id_pelanggan']:<6} {p['nama']:<18} {p['alamat']:<18} {p['no_telp']:<16} {mobil_info}")
    conn.close()


def tambah_pelanggan():
    nama = input("Nama pelanggan: ").strip()
    if not nama:
        print("! Nama tidak boleh kosong!")
        return

    alamat  = input("Alamat        : ").strip()
    no_telp = input("No. Telepon   : ").strip()

    conn = get_connection()
    if conn.execute(
        "SELECT 1 FROM pelanggan WHERE LOWER(nama) = ?", (nama.lower(),)
    ).fetchone():
        print("! Nama pelanggan sudah terdaftar!")
        conn.close()
        return

    konfirmasi = input("Simpan? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    cur = conn.execute(
        "INSERT INTO pelanggan (nama, alamat, no_telp) VALUES (?, ?, ?)",
        (nama, alamat, no_telp)
    )
    conn.commit()
    print(f"Pelanggan '{nama}' berhasil ditambahkan dengan ID {cur.lastrowid}.")
    conn.close()


def update_pelanggan():
    """
    Update parsial: user hanya mengisi field yang ingin diubah.
    Jika dikosongkan, field tersebut tidak berubah.
    """
    try:
        id_pelanggan = int(input("ID pelanggan yang ingin diupdate: "))
    except ValueError:
        print("! ID harus berupa angka!")
        return

    conn = get_connection()
    pelanggan = conn.execute(
        "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
    ).fetchone()
    if not pelanggan:
        print("! ID pelanggan tidak ditemukan.")
        conn.close()
        return

    print(f"\nData saat ini:")
    print(f"  Nama    : {pelanggan['nama']}")
    print(f"  Alamat  : {pelanggan['alamat']}")
    print(f"  No Telp : {pelanggan['no_telp']}")
    print("(Kosongkan field dan tekan Enter jika tidak ingin mengubahnya)\n")

    nama_baru = input(f"Nama baru    [{pelanggan['nama']}]: ").strip()
    nama_baru = nama_baru if nama_baru else pelanggan["nama"]

    alamat_baru = input(f"Alamat baru  [{pelanggan['alamat']}]: ").strip()
    alamat_baru = alamat_baru if alamat_baru else pelanggan["alamat"]

    telp_baru = input(f"No. Telp baru[{pelanggan['no_telp']}]: ").strip()
    telp_baru = telp_baru if telp_baru else pelanggan["no_telp"]

    # Cek nama baru tidak bentrok dengan pelanggan lain
    if nama_baru.lower() != pelanggan["nama"].lower():
        if conn.execute(
            "SELECT 1 FROM pelanggan WHERE LOWER(nama) = ? AND id_pelanggan != ?",
            (nama_baru.lower(), id_pelanggan)
        ).fetchone():
            print("! Nama sudah digunakan pelanggan lain!")
            conn.close()
            return

    konfirmasi = input("\nSimpan perubahan? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    conn.execute(
        "UPDATE pelanggan SET nama=?, alamat=?, no_telp=? WHERE id_pelanggan=?",
        (nama_baru, alamat_baru, telp_baru, id_pelanggan)
    )
    conn.commit()
    conn.close()
    print(f"Data pelanggan berhasil diupdate.")


def hapus_pelanggan():
    try:
        id_pelanggan = int(input("ID pelanggan yang ingin dihapus: "))
    except ValueError:
        print("! ID harus berupa angka!")
        return

    conn = get_connection()
    pelanggan = conn.execute(
        "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
    ).fetchone()
    if not pelanggan:
        print("! ID pelanggan tidak ditemukan.")
        conn.close()
        return

    pinjaman = conn.execute(
        """SELECT m.merk FROM penyewaan sw
           JOIN mobil m ON m.id = sw.id_mobil
           WHERE sw.id_pelanggan = ?""",
        (id_pelanggan,)
    ).fetchall()
    if pinjaman:
        merk_list = ", ".join(p["merk"] for p in pinjaman)
        print(f"! Pelanggan masih merental: {merk_list}.")
        print("  Kembalikan mobil terlebih dahulu.")
        conn.close()
        return

    print(f"Data: ID={pelanggan['id_pelanggan']} | {pelanggan['nama']} | {pelanggan['alamat']}")
    konfirmasi = input("Hapus pelanggan ini? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("! Dibatalkan.")
        conn.close()
        return

    # Hapus akun terkait dan data pelanggan
    conn.execute("DELETE FROM akun      WHERE id_pelanggan = ?", (id_pelanggan,))
    conn.execute("DELETE FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,))
    conn.commit()
    conn.close()
    print(f"Pelanggan '{pelanggan['nama']}' berhasil dihapus.")


# FITUR PENYEWAAN (RENTAL)

def tampilkan_semua_penyewaan():
    conn = get_connection()
    rows = conn.execute(
        """SELECT sw.id, p.id_pelanggan, p.nama, m.id AS id_mobil, m.merk
           FROM penyewaan sw
           JOIN pelanggan p ON p.id_pelanggan = sw.id_pelanggan
           JOIN mobil     m ON m.id = sw.id_mobil
           ORDER BY sw.id"""
    ).fetchall()
    conn.close()

    if not rows:
        print("Tidak ada data rental aktif.")
        return

    print(f"\n{'No':<5} {'ID Pelanggan':<14} {'Nama':<18} {'ID Mobil':<10} Merk Mobil")
    cetak_garis(80)
    for i, r in enumerate(rows, 1):
        print(f"{i:<5} {r['id_pelanggan']:<14} {r['nama']:<18} {r['id_mobil']:<10} {r['merk']}")


def rental_mobil(akun_login: dict):
    """Pelanggan merental mobil. ID pelanggan diambil dari akun yang login."""
    id_pelanggan = akun_login["id_pelanggan"]

    conn = get_connection()
    pelanggan = conn.execute(
        "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
    ).fetchone()
    if not pelanggan:
        print("! Data pelanggan tidak ditemukan.")
        conn.close()
        return

    # Tampilkan mobil yang berstatus 'Tersedia'
    mobil_tersedia = conn.execute("SELECT * FROM mobil WHERE status = 'Tersedia' ORDER BY id").fetchall()
    if not mobil_tersedia:
        print("\n! Maaf, saat ini tidak ada mobil yang tersedia untuk dirental.")
        conn.close()
        return

    print("\nMobil tersedia saat ini:")
    print(f"{'ID':<5} {'Merk Mobil':<25} {'Tahun':<8} {'Harga/Hari':<15}")
    cetak_garis(60)
    for m in mobil_tersedia:
        print(f"{m['id']:<5} {m['merk']:<25} {m['tahun']:<8} Rp{m['harga']:<13,}")

    try:
        id_mobil = int(input("\nMasukkan ID mobil yang ingin dirental: "))
    except ValueError:
        print("! ID harus berupa angka!")
        conn.close()
        return

    mobil = conn.execute("SELECT * FROM mobil WHERE id = ?", (id_mobil,)).fetchone()
    if not mobil:
        print("! ID mobil tidak ditemukan.")
        conn.close()
        return

    if mobil["status"] == 'Dirental':
        print(f"! Maaf, mobil '{mobil['merk']}' sedang dirental orang lain.")
        conn.close()
        return

    # Jika sistem hanya membolehkan 1 mobil per rental bisa dicek di sini,
    # Namun kita biarkan pelanggan bisa merental >1 mobil sesuai arsitektur awal

    conn.execute(
        "INSERT INTO penyewaan (id_pelanggan, id_mobil) VALUES (?, ?)",
        (id_pelanggan, id_mobil)
    )
    conn.execute("UPDATE mobil SET status = 'Dirental' WHERE id = ?", (id_mobil,))
    conn.commit()
    conn.close()

    print(f"Mobil '{mobil['merk']}' berhasil dirental!")
    print(f"  Biaya sewa: Rp{mobil['harga']:,} per hari.")


def kembalikan_mobil(akun_login: dict):
    """Pelanggan mengembalikan mobil. ID pelanggan diambil dari akun yang login."""
    id_pelanggan = akun_login["id_pelanggan"]

    conn = get_connection()
    pelanggan = conn.execute(
        "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
    ).fetchone()
    if not pelanggan:
        print("! Data pelanggan tidak ditemukan.")
        conn.close()
        return

    # Tampilkan mobil yang sedang dirental pelanggan ini
    pinjaman = conn.execute(
        """SELECT m.id, m.merk FROM penyewaan sw
           JOIN mobil m ON m.id = sw.id_mobil
           WHERE sw.id_pelanggan = ?""",
        (id_pelanggan,)
    ).fetchall()

    if not pinjaman:
        print("! Anda tidak sedang merental mobil apapun.")
        conn.close()
        return

    print("\nMobil yang sedang Anda rental:")
    for p in pinjaman:
        print(f"  ID {p['id']}: {p['merk']}")

    try:
        id_mobil = int(input("\nMasukkan ID mobil yang ingin dikembalikan: "))
    except ValueError:
        print("! ID harus berupa angka!")
        conn.close()
        return

    record = conn.execute(
        "SELECT 1 FROM penyewaan WHERE id_pelanggan=? AND id_mobil=?",
        (id_pelanggan, id_mobil)
    ).fetchone()
    if not record:
        print("! Mobil tersebut tidak ada dalam daftar rental Anda.")
        conn.close()
        return

    mobil = conn.execute("SELECT * FROM mobil WHERE id=?", (id_mobil,)).fetchone()
    conn.execute(
        "DELETE FROM penyewaan WHERE id_pelanggan=? AND id_mobil=?",
        (id_pelanggan, id_mobil)
    )
    conn.execute("UPDATE mobil SET status = 'Tersedia' WHERE id = ?", (id_mobil,))
    conn.commit()
    conn.close()
    print(f"Mobil '{mobil['merk']}' berhasil dikembalikan. Terima kasih!")


def lihat_rental_saya(akun_login: dict):
    """Menampilkan mobil yang sedang dirental oleh pelanggan yang login."""
    id_pelanggan = akun_login["id_pelanggan"]
    conn = get_connection()
    pinjaman = conn.execute(
        """SELECT m.id, m.merk, m.harga FROM penyewaan sw
           JOIN mobil m ON m.id = sw.id_mobil
           WHERE sw.id_pelanggan = ?""",
        (id_pelanggan,)
    ).fetchall()
    conn.close()

    if not pinjaman:
        print("Anda belum merental mobil apapun.")
        return

    print(f"\n{'ID':<6} {'Merk Mobil':<25} Harga/Hari")
    cetak_garis(50)
    for p in pinjaman:
        print(f"{p['id']:<6} {p['merk']:<25} Rp{p['harga']:,}")


# LOOP UTAMA

def jalankan_staff(akun: dict):
    """Loop menu untuk staff rental."""
    while True:
        tampilkan_menu_staff()
        pilihan = input("Pilih menu (1-12): ").strip()

        if   pilihan == "1":  tampilkan_semua_mobil()
        elif pilihan == "2":  cari_mobil()
        elif pilihan == "3":  tambah_mobil()
        elif pilihan == "4":  update_mobil()
        elif pilihan == "5":  hapus_mobil()
        elif pilihan == "6":  tampilkan_semua_pelanggan()
        elif pilihan == "7":  tambah_anggota() # Diganti menjadi tambah_pelanggan() di bawah
        elif pilihan == "7":  tambah_pelanggan()
        elif pilihan == "8":  update_pelanggan()
        elif pilihan == "9":  hapus_pelanggan()
        elif pilihan == "10": tampilkan_semua_penyewaan()
        elif pilihan == "11": register_staff()
        elif pilihan == "12":
            print("Logout. Sampai jumpa!")
            break
        else:
            print("! Pilihan tidak valid.")


def jalankan_pelanggan(akun: dict):
    """Loop menu untuk pelanggan rental."""
    while True:
        tampilkan_menu_pelanggan()
        pilihan = input("Pilih menu (1-6): ").strip()

        if   pilihan == "1": tampilkan_semua_mobil()
        elif pilihan == "2": cari_mobil()
        elif pilihan == "3": rental_mobil(akun)
        elif pilihan == "4": kembalikan_mobil(akun)
        elif pilihan == "5": lihat_rental_saya(akun)
        elif pilihan == "6":
            print("Logout. Sampai jumpa!")
            break
        else:
            print("! Pilihan tidak valid.")


def main():
    inisialisasi_database()
    print("=" * 50)
    print("   APLIKASI RENTAL MOBIL — Selamat Datang!")
    print("=" * 50)

    while True:
        print("\n1. Login")
        print("2. Daftar Akun Pelanggan")
        print("3. Keluar Program")
        pilihan = input("Pilih (1-3): ").strip()

        if pilihan == "1":
            akun = login()
            if akun:
                if akun["role"] == "staff":
                    jalankan_staff(akun)
                else:
                    jalankan_pelanggan(akun)
        elif pilihan == "2":
            register_pelanggan()
        elif pilihan == "3":
            print("Terima kasih telah menggunakan aplikasi rental mobil.")
            break
        else:
            print("! Pilihan tidak valid.")


if __name__ == "__main__":
    main()