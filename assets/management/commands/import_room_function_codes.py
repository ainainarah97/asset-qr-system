from django.core.management.base import BaseCommand

from assets.models import RoomFunctionCode


SPACE_TYPES = {
    "A": "Ruang Kebudayaan / Keagamaan",
    "C": "Ruang Sirkulasi",
    "F": "Ruang Servis Fasiliti",
    "H": "Ruang Penjagaan / Rawatan",
    "L": "Ruang Perlindungan / Larangan",
    "N": "Ruang Niaga",
    "P": "Ruang Interaksi",
    "Q": "Ruang Istirahat / Penginapan",
    "R": "Ruang Rekreasi",
    "S": "Ruang Penyimpanan",
    "W": "Ruang Kerja Khusus",
}


CATEGORIES = {
    "A 01 00": "Ruang Ibadat",
    "A 02 00": "Ruang Transformasi",
    "A 03 00": "Ruang Contemplation",

    "C 01 00": "Ruang Sirkulasi Mendatar",
    "C 02 00": "Ruang Sirkulasi Menegak",
    "C 03 00": "Ruang Sirkulasi Transit",
    "C 04 00": "Ruang Pejalan Kaki (Luar Bangunan)",

    "F 01 00": "Ruang Kemudahan Perkhidmatan",
    "F 02 00": "Ruang Perkhidmatan Peralatan Infrastruktur",
    "F 03 00": "Ruang Pengagihan Perkhidmatan",

    "H 01 00": "Ruang Rapi Diri (Grooming)",
    "H 02 00": "Ruang Penjagaan Kanak-kanak",
    "H 03 00": "Ruang Pemulihan Diri",

    "L 01 00": "Ruang Perlindungan Cuaca",
    "L 02 00": "Ruang Perlindungan",
    "L 03 00": "Ruang Perlindungan Haiwan",

    "N 01 00": "Ruang Jual Beli",
    "N 02 00": "Ruang Kafeteria / Kantin",
    "N 03 00": "Ruang Perbankan",

    "P 01 00": (
        "Ruang Perjumpaan (Gathering Space) & Ruang Mesyuarat"
    ),
    "P 02 00": "Ruang Persembahan Dan Jamuan",

    "Q 01 00": "Ruang Rehat Umum",
    "Q 02 00": "Ruang Penginapan",
    "Q 03 00": "Ruang Menunggu",

    "R 01 00": "Ruang Bukan Olahraga",
    "R 02 00": "Ruang Olahraga",
    "R 03 00": "Ruang Kecergasan",

    "S 01 00": "Ruang Simpanan Tetap",
    "S 02 00": "Ruang Simpanan Kawalan Alam Sekitar",
    "S 03 00": "Ruang Simpanan Khas",

    "W 01 00": "Ruang Pentadbiran dan Pejabat",
    "W 02 00": "Ruang Pendidikan dan Kreatif",
    "W 03 00": "Ruang Badan Kehakiman",
    "W 04 00": "Ruang Kesihatan",
    "W 05 00": "Ruang Perpustakaan",
    "W 06 00": (
        "Ruang Pengeluaran, Pembuatan dan Pemprosesan"
    ),
    "W 07 00": "Ruang Memasak",
    "W 08 00": "Ruang Operasi dan Kawalan",
    "W 09 00": "Ruang Keselamatan",
}


FUNCTIONS = [
    # =====================================================
    # A - RUANG KEBUDAYAAN / KEAGAMAAN
    # =====================================================
    ("A 01 01", "Meditasi"),
    ("A 01 05", "Ruang Sembahyang / Surau"),
    ("A 01 09", "Altar"),
    ("A 01 13", "Ruang Refleksi"),
    ("A 01 99", "Ruang Ibadat Lain"),

    ("A 02 01", "Ruang Perkahwinan"),
    ("A 02 99", "Ruang Transformasi Lain"),

    ("A 03 01", "Galeri Seni"),
    ("A 03 05", "Galeri Muzium"),
    ("A 03 09", "Galeri Pameran"),
    ("A 03 13", "Sculpture Garden"),
    ("A 03 17", "Taman Hiasan"),
    ("A 03 21", "Dek Pemerhatian"),
    ("A 03 25", "Zen Garden"),
    ("A 03 99", "Ruang Renungan Lain"),

    # =====================================================
    # C - RUANG SIRKULASI
    # =====================================================
    ("C 01 01", "Koridor/ Langkan / Lorong"),
    ("C 01 05", "Dataran"),
    ("C 01 09", "Ruang Legar"),
    (
        "C 01 13",
        "Laluan Pejalan Kaki Bermotor / Bergerak",
    ),
    ("C 01 17", "Laluan OKU"),
    ("C 01 99", "Ruang Sirkulasi Mendatar Lain"),

    ("C 02 01", "Tangga"),
    ("C 02 05", "Tangga Jalan Keluar"),
    ("C 02 09", "Tangga Istiadat"),
    ("C 02 13", "Tangga Bermotor / Bergerak"),
    ("C 02 17", "Tanjakan (Ramp)"),
    ("C 02 21", "Gabungan Tangga dan Tanjakan"),
    ("C 02 25", "Dumbwaiter"),
    ("C 02 99", "Ruang Sirkulasi Menegak Lain"),

    ("C 03 01", "Lobi Masuk"),
    ("C 03 05", "Lobi lif"),
    ("C 03 09", "Landing"),
    ("C 03 13", "Ruang Antara (Ante - Room)"),
    ("C 03 17", "Ruang Jaringan Udara (Air Lock)"),
    ("C 03 99", "Ruang Edaran Transit Lain"),

    ("C 04 01", "Kaki Lima"),
    (
        "C 04 05",
        (
            "Laluan Pejalan Kaki "
            "(Pedastrian Way, Footpath, Gang way, Trail, Walkway)"
        ),
    ),
    ("C 04 99", "Laluan Pejalan Kaki Lain"),

    # =====================================================
    # F - RUANG SERVIS FASILITI
    # =====================================================
    ("F 01 01", "Akses Servis (Access Chamber)"),
    ("F 01 05", "Laluan Servis"),
    ("F 01 09", "Ruang Servis"),
    ("F 01 13", "Laluan Udara (Air Shaft)"),
    ("F 01 17", "Ruang Cahaya (Light Well)"),
    ("F 01 99", "Ruang Kemudahan Perkhidmatan Lain"),

    ("F 02 01", "Bilik Peralatan"),
    ("F 02 05", "Bilik Server"),
    ("F 02 09", "Bilik Mekanikal"),
    ("F 02 13", "Bilik Elektrik"),
    ("F 02 17", "Bilik Komunikasi"),
    ("F 02 21", "Laluan Pemindahan ( Transfer Vault)"),
    ("F 02 25", "Laluan Lif (Lift Shaft)"),
    ("F 02 99", "Ruang Kemudahan Peralatan Lain-lain"),

    ("F 03 01", "Ruang Pengagihan Kuasa"),
    (
        "F 03 05",
        "Ruang Pengedaran Maklumat Bersyarat",
    ),
    ("F 03 09", "Ruang Pengagihan Gas"),
    ("F 03 13", "Ruang Pengagihan Cecair"),
    (
        "F 03 99",
        "Ruang Pengagihan Perkhidmatan Lain",
    ),

    # =====================================================
    # H - RUANG PENJAGAAN / RAWATAN
    # =====================================================
    ("H 01 01", "Ruang Solek"),
    ("H 01 05", "Ruang Memotong Rambut"),
    (
        "H 01 09",
        "Ruang Bersih Diri (Tandas / Bilik Air / Wuduk / Bilik Basuh)",
    ),
    ("H 01 13", "Ruang Persalinan"),
    ("H 01 99", "Ruang Rapi Lain"),

    (
        "H 02 01",
        "Ruang Penjagaan Harian Kanak-kanak / Pra Sekolah",
    ),
    ("H 02 05", "Bilik Bermain"),
    ("H 02 09", "Bilik Menyusu"),
    (
        "H 02 99",
        "Ruang Penjagaan Kanak-kanak Lain",
    ),

    ("H 03 01", "Bilik Wap"),
    ("H 03 05", "Kolam Berpusar"),
    ("H 03 09", "Sauna"),
    ("H 03 99", "Ruang Pemulihan Lain"),

    # =====================================================
    # L - RUANG PERLINDUNGAN / LARANGAN
    # =====================================================
    ("L 01 01", "Parkir Berbumbung"),
    ("L 01 05", "Anjung Masuk (Porch)"),
    ("L 01 09", "Garaj"),
    ("L 01 13", "Laluan Pejalan Kaki Berlindung"),
    ("L 01 17", "Kanopi"),
    ("L 01 99", "Ruang Perlindungan Cuaca Lain"),

    ("L 02 01", "Bilik Selamat (Safe Room)"),
    ("L 02 05", "Bilik Keselamatan"),
    ("L 02 09", "Bunker"),
    ("L 02 13", "Tempat Perlindungan Bom"),
    ("L 02 99", "Ruang Perlindungan Lain"),

    ("L 03 01", "Sangkar"),
    ("L 03 05", "Kandang"),
    ("L 03 09", "Akuarium"),
    ("L 03 99", "Ruang Perlindungan Haiwan Lain"),

    # =====================================================
    # N - RUANG NIAGA
    # =====================================================
    ("N 01 01", "Ruang Niaga Am / Kedai"),
    ("N 01 05", "Kawasan Mesin Runcit"),
    ("N 01 09", "Dewan / Ruang Pameran Niaga"),
    ("N 01 13", "Ruang Demonstrasi"),
    ("N 01 17", "Ruang Lelong"),
    (
        "N 01 99",
        "Ruang Membeli, Menjual dan Lain –lain",
    ),

    ("N 02 01", "Ruang Mencuci Tangan"),
    ("N 02 05", "Ruang Makanan dan Minuman"),
    ("N 02 09", "Ruang Kuih dan Lauk Pauk"),
    ("N 02 99", "Ruang Kafeteria / Kantin Lain"),

    ("N 03 01", "Ruang Mesin ATM"),
    (
        "N 03 05",
        "Bilik Kebal Barang Berharga dan Wang (Bank)",
    ),
    ("N 03 99", "Ruang Perbankan Lain"),

    # =====================================================
    # P - RUANG INTERAKSI
    # =====================================================
    ("P 01 01", "Ruang Taklimat"),
    ("P 01 05", "Ruang Seminar"),
    ("P 01 09", "Ruang Bilik Darjah/ Kuliah / Kelas"),
    (
        "P 01 13",
        (
            "Ruang Dewan / Dewan Perhimpunan / "
            "Serba Guna (Selain Dewan Makan)"
        ),
    ),
    (
        "P 01 17",
        (
            "Ruang Kaunter Pertanyaan / Pendaftaran / "
            "Penerimaan / Resepsi"
        ),
    ),
    ("P 01 21", "Ruang Mesyuarat / Perbincangan"),
    ("P 01 25", "Ruang Persidangan"),
    ("P 01 29", "Ruang Sidang Media"),
    ("P 01 33", "Ruang Media"),
    ("P 01 37", "War Room / Operasi"),
    ("P 01 41", "Ruang Pemprosesan"),
    ("P 01 45", "Ruang Perundingan"),
    (
        "P 01 49",
        (
            "Ruang / Bilik Perkhidmatan "
            "(Khidmat Pelanggan / Kaunter)"
        ),
    ),
    (
        "P 01 53",
        "Ruang Pelawat / Balai Pelawat / Melawat",
    ),
    ("P 01 99", "Ruang Perjumpaan Lain"),

    ("P 02 01", "Ruang Persembahan Umum"),
    ("P 02 05", "Ruang Orang Kenamaan"),
    ("P 02 09", "Ruang Penonton"),
    ("P 02 13", "Ruang Sokongan Persembahan"),
    ("P 02 17", "Ruang Bankuet"),
    ("P 02 21", "Dewan Makan / Ruang Jamuan"),
    (
        "P 02 99",
        "Ruang Persembahan dan Jamuan Lain",
    ),

    # =====================================================
    # Q - RUANG ISTIRAHAT / PENGINAPAN
    # =====================================================
    ("Q 01 01", "Kawasan Rehat"),
    ("Q 01 05", "Hentian Rehat"),
    ("Q 01 09", "Ruang Rehat Umum"),
    ("Q 01 13", "Bilik Rehat / Pantry"),
    (
        "Q 01 17",
        "Ruang Kenamaan (Duta / Pesuruhjaya Tinggi / VIP)",
    ),
    ("Q 01 99", "Ruang Rehat Lain"),

    ("Q 02 01", "Bilik Tidur"),
    ("Q 02 05", "Kuarters"),
    ("Q 02 09", "Loteng"),
    ("Q 02 13", "Rumah Askar"),
    ("Q 02 17", "Domitori"),
    ("Q 02 21", "Hotel / Peranginan"),
    ("Q 02 25", "Ruang Jemuran"),
    ("Q 02 99", "Ruang Penginapan Lain"),

    ("Q 03 01", "Bilik Menunggu"),
    ("Q 03 05", "Ruang Beratur"),
    ("Q 03 09", "Bilik Persediaan"),
    ("Q 03 99", "Ruang Menunggu Lain"),

    # =====================================================
    # R - RUANG REKREASI
    # =====================================================
    ("R 01 01", "Taman Permainan"),
    ("R 01 05", "Astaka"),
    ("R 01 09", "Taman Awam"),
    (
        "R 01 13",
        "Bilik Media (Wartawan / TV / Radio / Akhbar)",
    ),
    ("R 01 17", "Ruang Rekreasi / Sukan"),
    ("R 01 21", "Taman Permainan"),
    (
        "R 01 25",
        "Bilik / Ruang Permainan / Gelanggang / Padang",
    ),
    ("R 01 29", "Lapang Sasar"),
    ("R 01 33", "Ruang Hiburan"),
    ("R 01 37", "Ruang Rekreasi Maya"),
    ("R 01 99", "Ruang Bukan Olahraga Lain"),

    ("R 02 01", "Ruang Olahraga Berpasukan"),
    ("R 02 05", "Ruang Olahraga Individu"),
    ("R 02 99", "Ruang Olahraga Lain"),

    ("R 03 01", "Ruang Senaman"),
    ("R 03 05", "Ruang Latih Tubi"),
    ("R 03 09", "Studio Aerobik"),
    ("R 03 13", "Bilik Latihan (Kecergasan)"),
    ("R 03 99", "Ruang Kecergasan Lain"),

    # =====================================================
    # S - RUANG PENYIMPANAN
    # =====================================================
    ("S 01 01", "Ruang / Bilik Simpanan / Stor"),
    ("S 01 05", "Bilik Kebal"),
    (
        "S 01 09",
        (
            "Ruang Simpanan Pakaian "
            "(Kot / Almari Pakaian / Coat Check)"
        ),
    ),
    ("S 01 13", "Bilik Loker"),
    ("S 01 17", "Ruang Fail"),
    ("S 01 21", "Bilik Bekalan"),
    ("S 01 25", "Ruang Gudang"),
    ("S 01 29", "Ruang Kenderaan"),
    ("S 01 33", "Ruang Sisa"),
    ("S 01 37", "Ruang Kitar Semula"),
    ("S 01 99", "Ruang Simpanan Tetap Lain"),

    ("S 02 01", "Bilik Alam Sekitar"),
    ("S 02 05", "Kompartmen Penyejukbekuan"),
    ("S 02 09", "Kompartmen Sejuk"),
    (
        "S 02 13",
        "Ruang Simpanan Kompartmen Kering",
    ),
    ("S 02 17", "Ruang Simpanan Kawalan"),
    (
        "S 02 21",
        "Ruang Simpanan Kompartmen Vakum",
    ),
    (
        "S 02 99",
        "Ruang Simpanan Alam Sekitar Lain",
    ),

    (
        "S 03 01",
        "Ruang Simpanan Bilik Sanitari",
    ),
    ("S 03 05", "Ruang Simpanan Bilik Kotor"),
    (
        "S 03 09",
        "Ruang Simpanan Bahan Berbahaya",
    ),
    (
        "S 03 13",
        "Ruang Simpanan Organik Kekal",
    ),
    ("S 03 17", "Tuntutan Bagasi"),
    ("S 03 21", "Bilik Bukti"),
    ("S 03 99", "Ruang Simpanan Khas Lain"),

    # =====================================================
    # W - RUANG KERJA KHUSUS
    # =====================================================
    (
        "W 01 01",
        "Ruang Kaunter Penyambut Tetamu / Pas Keselamatan",
    ),
    (
        "W 01 05",
        "Ruang Guru / Tenaga Pengajar / Pensyarah",
    ),
    ("W 01 09", "Bilik Pegawai"),
    (
        "W 01 13",
        "Bilik Pembantu / Tutor / Pengawas / Penolong",
    ),
    ("W 01 17", "Bilik Pendaftar"),
    ("W 01 21", "Bilik / Pejabat Ketua Bidang"),
    ("W 01 25", "Pejabat Pengetua"),
    ("W 01 29", "Bilik Jurubahasa"),
    (
        "W 01 99",
        "Ruang Pentadbiran dan Pejabat Lain",
    ),

    ("W 02 01", "Ruang Kreatif (Studio / Suntingan)"),
    ("W 02 05", "Ruang Belajar / Study"),
    ("W 02 09", "Ruang Komputer (Bilik / Makmal)"),
    ("W 02 13", "Makmal (Selain Komputer)"),
    ("W 02 17", "Bengkel"),
    ("W 02 21", "Pendidikan Khas"),
    ("W 02 25", "Bilik Kaunseling"),
    (
        "W 02 99",
        "Ruang Pendidikan dan Kreatif Lain",
    ),

    ("W 03 01", "Ruang Bicara"),
    ("W 03 05", "Bilik Keselamatan Juri"),
    ("W 03 09", "Ruang Juri"),
    ("W 03 13", "Kerusi Hakim"),
    ("W 03 17", "Kamar Hakim / Majistret"),
    ("W 03 21", "Ruang / Kandang Saksi"),
    ("W 03 25", "Bilik Mendengar"),
    ("W 03 99", "Ruang Badan Kehakiman Lain"),

    ("W 04 01", "Ruang / Bilik Rawatan"),
    ("W 04 05", "Ruang Pengimejan"),
    ("W 04 09", "Ruang Kecemasan"),
    ("W 04 13", "Ruang Pemeriksaan Fizikal"),
    ("W 04 17", "Labour & Delivery"),
    (
        "W 04 21",
        "Neonatal Intencive Care Unit (NICU)",
    ),
    (
        "W 04 25",
        "Intensive / Cardiac Care Unit (ICU / CCU)",
    ),
    (
        "W 04 29",
        "Central Sterile Services (CSS)",
    ),
    ("W 04 33", "Anaesthetist"),
    ("W 04 37", "Patholagy & Blood Bank"),
    ("W 04 41", "Haemodialysis"),
    ("W 04 45", "Pergigian"),
    ("W 04 49", "Mortuary"),
    ("W 04 53", "Ruang Pemulihan"),
    ("W 04 57", "Bilik Kaunseling"),
    ("W 04 61", "Ruang Penjagaan / Wad"),
    ("W 04 65", "Bilik Pengasingan"),
    ("W 04 69", "Ruang Penjagaan Harian"),
    (
        "W 04 73",
        "Ruang Pembedahan / Dewan Bedah",
    ),
    ("W 04 77", "Dewan / Bilik Bersalin"),
    ("W 04 81", "Bilik Rehabilasi"),
    (
        "W 04 85",
        "Bilik Pengimejan dan Pengimbasan",
    ),
    ("W 04 89", "Farmasi"),
    ("W 04 93", "Rekod Perubatan"),
    ("W 04 99", "Bilik Kesihatan Lain"),

    ("W 05 01", "Ruang Pembaca"),
    ("W 05 05", "Ruang Koleksi"),
    ("W 05 09", "Ruang Kawalan"),
    ("W 05 13", "Ruang Audio / Video"),
    ("W 05 17", "Ruang Proses"),
    ("W 05 21", "Bilik Tayangan"),
    ("W 05 25", "Bilik Rakaman"),
    (
        "W 05 29",
        "Ruang Penyelenggaraan Bahan Media",
    ),
    ("W 05 33", "Ruang Bercerita"),
    ("W 05 37", "Ruang Pemprosesan Data"),
    (
        "W 05 41",
        "Ruang Untuk Golongan Istimewa",
    ),
    ("W 05 45", "Ruang Pembaikan Bahan"),
    (
        "W 05 49",
        "Ruang Pembelajaran Jarak jauh",
    ),
    ("W 05 53", "Bilik Karel"),
    (
        "W 05 57",
        "Bilik Sumber / Bilik / Ruang Bacaan",
    ),
    ("W 05 99", "Ruang Perpustakaan Lain"),

    ("W 06 01", "Ruang Pengeluaran"),
    ("W 06 05", "Ruang Pembuatan"),
    ("W 06 09", "Ruang Pemprosesan"),
    (
        "W 06 99",
        (
            "Ruang Pengeluaran, Pembuatan dan "
            "Pemprosesan yang Lain"
        ),
    ),

    ("W 07 01", "Ruang Dapur Kering"),
    ("W 07 05", "Ruang Dapur Basah"),
    ("W 07 09", "Ruang Mencuci"),
    ("W 07 13", "Ruang Penyediaan"),
    ("W 07 99", "Ruang Masak Lain"),

    ("W 08 01", "Ruang Bilik Kawalan"),
    ("W 08 05", "Ruang Kokpit"),
    ("W 08 09", "Ruang Memandu"),
    ("W 08 13", "Ruang Kawalan Kapal"),
    (
        "W 08 99",
        "Ruang Operasi dan Kawalan Lain",
    ),

    (
        "W 09 01",
        "Ruang Tahanan / Lokap /Jel /reman",
    ),
    ("W 09 05", "Bilik Detil"),
    ("W 09 09", "Bilik Kebajikan"),
    (
        "W 09 13",
        "Bilik Pemeriksaan (Selain Kesihatan)",
    ),
    ("W 09 17", "Bilik Gerakan"),
    ("W 09 21", "Bilik Siap Siaga"),
    ("W 09 25", "Ruang Merotan"),
    ("W 09 29", "Ruang Gantung"),
    ("W 09 33", "Sally Port"),
    ("W 09 37", "Ruang Soal Siasat"),
    ("W 09 41", "Bilik Maklumat"),
    ("W 09 45", "Bilik Gelap"),
    (
        "W 09 49",
        "Bilik Pengecaman / Pemerhati",
    ),
    (
        "W 09 53",
        "Bilik Mengosongkan Senjata",
    ),
    ("W 09 57", "Tempat Barang Kes"),
    (
        "W 09 61",
        "Stor Keselamatan (Senjata / Barang Kes / CSI)",
    ),
    ("W 09 65", "Stesen Minyak"),
    ("W 09 69", "Sel / Penjara"),
    ("W 09 99", "Ruang Keselamatan Lain"),
]


class Command(BaseCommand):
    help = (
        "Import official SKATA room function codes "
        "into RoomFunctionCode."
    )

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for code, name in FUNCTIONS:
            parts = code.split()

            space_type_code = parts[0]

            category_code = (
                f"{parts[0]} {parts[1]} 00"
            )

            space_type_name = SPACE_TYPES.get(
                space_type_code,
                "",
            )

            category_name = CATEGORIES.get(
                category_code,
                "",
            )

            obj, created = (
                RoomFunctionCode.objects.update_or_create(
                    code=code,
                    defaults={
                        "space_type_code": space_type_code,
                        "space_type_name": space_type_name,
                        "category_code": category_code,
                        "category": category_name,
                        "name": name,
                        "is_active": True,
                    },
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Room function code import completed. "
                    f"Created: {created_count}, "
                    f"Updated: {updated_count}, "
                    f"Total: {len(FUNCTIONS)}."
                )
            )
        )