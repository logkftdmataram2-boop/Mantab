import os
import io
import base64
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st


# ============================================================
# KONFIGURASI
# ============================================================

st.set_page_config(
    page_title="Monitoring Analisa",
    page_icon="📊",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PDF_FOLDER = os.path.join(BASE_DIR, "pdf")
TEMPLATE_PENOLAKAN = os.path.join(
    BASE_DIR,
    "Surat Penolakan Obat - Google Dokumen.pdf"
)
DB_PATH = os.path.join(BASE_DIR, "data.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

@st.cache_resource
def get_conn():

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    # --------------------------------------------------------
    # TABEL DATA MONITORING
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            pelanggan TEXT,
            produk TEXT,
            qty INTEGER
        )
    """)

    # --------------------------------------------------------
    # TABEL ANALISA
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS analisa (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    conn.commit()

    return conn


conn = get_conn()


# ============================================================
# AUTO MIGRATION
# ============================================================

def ensure_column(table, column, col_type="TEXT"):

    try:

        columns = [
            row[1]
            for row in conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        ]

        if column not in columns:

            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )

            conn.commit()

    except Exception:
        pass


ANALISA_COLUMNS = {

    "tanggal": "TEXT",
    "pelanggan": "TEXT",
    "produk": "TEXT",

    "qty_order": "REAL",
    "avg_qty": "REAL",
    "ratio": "REAL",

    "score": "INTEGER",
    "kategori": "TEXT",
    "status": "TEXT",

    "izin": "TEXT",
    "alasan_izin": "TEXT",

    "pj": "TEXT",
    "alasan_pj": "TEXT",

    "frekuensi": "INTEGER",

    "faskes": "TEXT",
    "pemukiman": "TEXT",
    "alasan": "TEXT",

    "jenis_fasilitas": "TEXT",
    "no_pesanan": "TEXT",

    "bukti_faskes": "TEXT",
    "bukti_pemukiman": "TEXT",

    "surat_path": "TEXT",
    "surat_pernyataan": "TEXT"

}


for column, tipe in ANALISA_COLUMNS.items():

    ensure_column(
        "analisa",
        column,
        tipe
    )


# ============================================================
# USER
# ============================================================

USERS = {

    "admin": {
        "password": "123",
        "role": "admin"
    },

    "user1": {
        "password": "123",
        "role": "user"
    }

}


# ============================================================
# SESSION STATE
# ============================================================

if "login" not in st.session_state:
    st.session_state.login = False

if "role" not in st.session_state:
    st.session_state.role = None

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

if "hasil_penolakan" not in st.session_state:
    st.session_state.hasil_penolakan = None


# ============================================================
# FUNGSI UMUM
# ============================================================

def save_uploaded_file(uploaded_file, prefix):

    if uploaded_file is None:
        return ""

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    safe_name = os.path.basename(
        uploaded_file.name
    )

    filename = (
        f"{prefix}_{timestamp}_{safe_name}"
    )

    path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return path


def save_multiple_files(files, prefix):

    paths = []

    if not files:
        return ""

    for file in files:

        path = save_uploaded_file(
            file,
            prefix
        )

        if path:
            paths.append(path)

    return ",".join(paths)


def show_file(path, title="File"):

    if not path:
        return

    path = str(path).strip()

    if not os.path.exists(path):

        st.warning(
            f"{title} tidak ditemukan."
        )

        return

    try:

        with open(path, "rb") as f:
            data = f.read()

        extension = os.path.splitext(
            path
        )[1].lower()

        st.write(f"**{title}**")

        # ----------------------------------------------------
        # GAMBAR
        # ----------------------------------------------------

        if extension in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        ]:

            st.image(
                data,
                use_container_width=True
            )

        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        elif extension == ".pdf":

            encoded = base64.b64encode(
                data
            ).decode("utf-8")

            html = f"""
            <iframe
                src="data:application/pdf;base64,{encoded}"
                width="100%"
                height="600"
                style="
                    border:1px solid #ccc;
                    border-radius:8px;
                ">
            </iframe>
            """

            st.markdown(
                html,
                unsafe_allow_html=True
            )

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        st.download_button(
            f"⬇️ Download {title}",
            data=data,
            file_name=os.path.basename(path),
            key=f"download_{title}_{path}"
        )

    except Exception as e:

        st.error(
            f"Gagal menampilkan {title}: {e}"
        )


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.login:

    st.title("🔐 Login Monitoring Analisa")

    st.write(
        "Silakan masukkan username dan password."
    )

    username = st.text_input(
        "Username",
        placeholder="Masukkan username"
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Masukkan password"
    )

    if st.button(
        "🔑 Login",
        type="primary",
        use_container_width=True
    ):

        username = username.strip().lower()
        password = password.strip()

        if username not in USERS:

            st.error(
                "Username tidak ditemukan."
            )

        elif USERS[username]["password"] != password:

            st.error(
                "Password salah."
            )

        else:

            st.session_state.login = True
            st.session_state.role = USERS[
                username
            ]["role"]

            st.success(
                "Login berhasil."
            )

            st.rerun()

    st.info(
        "Demo: admin / 123 atau user1 / 123"
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.success(
    f"Login sebagai: {st.session_state.role}"
)


# ============================================================
# LOGOUT
# ============================================================

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    st.session_state.login = False
    st.session_state.role = None
    st.session_state.edit_id = None

    st.rerun()


st.sidebar.markdown("---")

st.sidebar.subheader(
    "📂 MENU APLIKASI"
)


# ============================================================
# MENU
# ============================================================

if st.session_state.role == "admin":

    menu = st.sidebar.radio(
        "Pilih Menu",
        [
            "Monitoring",
            "Analisa",
            "Approval",
            "Output",
            "Penolakan Pesanan"
        ],
        key="main_menu"
    )

else:

    menu = st.sidebar.radio(
        "Pilih Menu",
        [
            "Monitoring",
            "Analisa",
            "Penolakan Pesanan"
        ],
        key="main_menu"
    )


# ============================================================
# MENU MONITORING
# ============================================================

if menu == "Monitoring":

    st.title(
        "📊 Monitoring Pemakaian Produk"
    )

    st.caption(
        "Monitoring historis pemakaian dan transaksi produk."
    )

    # --------------------------------------------------------
    # UPLOAD EXCEL
    # --------------------------------------------------------

    if st.session_state.role == "admin":

        st.sidebar.markdown("---")

        st.sidebar.subheader(
            "📥 Upload Data"
        )

        file = st.sidebar.file_uploader(
            "Upload Excel",
            type=["xlsx"]
        )

        if file:

            try:

                df_upload = pd.read_excel(
                    file
                )

                required_columns = [
                    "Tanggal",
                    "Nama Pelanggan",
                    "Produk",
                    "Qty"
                ]

                missing = [
                    col
                    for col in required_columns
                    if col not in df_upload.columns
                ]

                if missing:

                    st.error(
                        "Kolom Excel tidak lengkap: "
                        + ", ".join(missing)
                    )

                else:

                    df_upload["Tanggal"] = pd.to_datetime(
                        df_upload["Tanggal"],
                        errors="coerce"
                    )

                    df_upload["Qty"] = pd.to_numeric(
                        df_upload["Qty"],
                        errors="coerce"
                    )

                    df_upload = df_upload.dropna(
                        subset=[
                            "Tanggal",
                            "Nama Pelanggan",
                            "Produk",
                            "Qty"
                        ]
                    )

                    df_upload = df_upload.rename(
                        columns={
                            "Tanggal": "tanggal",
                            "Nama Pelanggan": "pelanggan",
                            "Produk": "produk",
                            "Qty": "qty"
                        }
                    )

                    df_upload["tanggal"] = (
                        df_upload["tanggal"]
                        .dt.strftime("%Y-%m-%d")
                    )

                    # Hapus data lama
                    conn.execute(
                        "DELETE FROM data"
                    )

                    records = list(
                        df_upload[
                            [
                                "tanggal",
                                "pelanggan",
                                "produk",
                                "qty"
                            ]
                        ].itertuples(
                            index=False,
                            name=None
                        )
                    )

                    conn.executemany(
                        """
                        INSERT INTO data
                        (
                            tanggal,
                            pelanggan,
                            produk,
                            qty
                        )
                        VALUES (?,?,?,?)
                        """,
                        records
                    )

                    conn.commit()

                    st.success(
                        f"Upload berhasil. "
                        f"{len(records)} data disimpan."
                    )

            except Exception as e:

                st.error(
                    f"Gagal membaca Excel: {e}"
                )

    # --------------------------------------------------------
    # LOAD DATABASE
    # --------------------------------------------------------

    df_all = pd.read_sql(
        "SELECT * FROM data",
        conn
    )

    if df_all.empty:

        st.info(
            "Belum ada data monitoring."
        )

        if st.session_state.role != "admin":

            st.warning(
                "Silakan minta admin melakukan upload data Excel."
            )

    else:

        df_all["tanggal"] = pd.to_datetime(
            df_all["tanggal"],
            errors="coerce"
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        pelanggan_options = [
            "Semua"
        ] + sorted(
            df_all["pelanggan"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        produk_options = [
            "Semua"
        ] + sorted(
            df_all["produk"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        pelanggan = st.sidebar.selectbox(
            "Pelanggan",
            pelanggan_options
        )

        produk = st.sidebar.selectbox(
            "Produk",
            produk_options
        )

        min_date = df_all["tanggal"].min().date()
        max_date = df_all["tanggal"].max().date()

        tanggal_range = st.sidebar.date_input(
            "Tanggal",
            value=(min_date, max_date)
        )

        # ----------------------------------------------------
        # FILTER DATA
        # ----------------------------------------------------

        df = df_all.copy()

        if pelanggan != "Semua":

            df = df[
                df["pelanggan"] == pelanggan
            ]

        if produk != "Semua":

            df = df[
                df["produk"] == produk
            ]

        if isinstance(
            tanggal_range,
            tuple
        ) and len(tanggal_range) == 2:

            start_date = pd.to_datetime(
                tanggal_range[0]
            )

            end_date = pd.to_datetime(
                tanggal_range[1]
            )

            df = df[
                (df["tanggal"] >= start_date)
                &
                (df["tanggal"] <= end_date)
            ]

        # ----------------------------------------------------
        # METRIC
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Transaksi",
            len(df)
        )

        col2.metric(
            "Total Qty",
            int(df["qty"].sum())
            if not df.empty else 0
        )

        col3.metric(
            "Rata-rata Qty",
            round(
                df["qty"].mean(),
                2
            )
            if not df.empty else 0
        )

        # ----------------------------------------------------
        # GRAFIK
        # ----------------------------------------------------

        if not df.empty:

            df_chart = df.copy()

            df_chart["bulan"] = (
                df_chart["tanggal"]
                .dt.to_period("M")
                .astype(str)
            )

            chart_data = (
                df_chart
                .groupby("bulan")["qty"]
                .sum()
            )

            st.subheader(
                "📈 Grafik Pemakaian"
            )

            st.bar_chart(
                chart_data
            )

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        st.subheader(
            "📋 Data Monitoring"
        )

        def to_excel(dataframe):

            output = BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                dataframe.to_excel(
                    writer,
                    index=False
                )

            return output.getvalue()

        st.download_button(
            "⬇️ Download Excel",
            data=to_excel(df),
            file_name="monitoring.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.dataframe(
            df,
            use_container_width=True
        )


# ============================================================
# MENU ANALISA
# ============================================================

elif menu == "Analisa":

    st.title(
        "📋 Analisa Kewajaran"
    )

    st.caption(
        "Analisa kewajaran pesanan berdasarkan riwayat dan validasi administratif."
    )

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    df = pd.read_sql(
        "SELECT * FROM data",
        conn
    )

    if df.empty:

        st.warning(
            "Data monitoring masih kosong. "
            "Silakan upload data terlebih dahulu."
        )

    else:

        df["tanggal"] = pd.to_datetime(
            df["tanggal"],
            errors="coerce"
        )

        # ----------------------------------------------------
        # PILIH PELANGGAN
        # ----------------------------------------------------

        pelanggan_list = sorted(
            df["pelanggan"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        pelanggan = st.selectbox(
            "Pelanggan",
            pelanggan_list
        )

        produk_list = sorted(
            df[
                df["pelanggan"] == pelanggan
            ]["produk"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        produk = st.selectbox(
            "Produk",
            produk_list
        )

        # ----------------------------------------------------
        # RATA-RATA
        # ----------------------------------------------------

        st.subheader(
            "📅 Perhitungan Riwayat"
        )

        min_date = df["tanggal"].min().date()
        max_date = df["tanggal"].max().date()

        tanggal_range = st.date_input(
            "Range Tanggal",
            value=(min_date, max_date)
        )

        if isinstance(
            tanggal_range,
            tuple
        ) and len(tanggal_range) == 2:

            start = pd.to_datetime(
                tanggal_range[0]
            )

            end = pd.to_datetime(
                tanggal_range[1]
            )

        else:

            start = df["tanggal"].min()
            end = df["tanggal"].max()

        df_avg = df[
            (df["pelanggan"] == pelanggan)
            &
            (df["produk"] == produk)
            &
            (df["tanggal"] >= start)
            &
            (df["tanggal"] <= end)
        ]

        avg = (
            df_avg["qty"].mean()
            if not df_avg.empty
            else 0
        )

        frekuensi = len(
            df_avg
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Rata-rata Qty",
            round(avg, 2)
        )

        col2.metric(
            "Frekuensi Pesanan",
            frekuensi
        )

        # ----------------------------------------------------
        # PESANAN
        # ----------------------------------------------------

        st.subheader(
            "📝 Informasi Pesanan"
        )

        qty = st.number_input(
            "Qty Order",
            min_value=0,
            step=1
        )

        jenis = st.selectbox(
            "Jenis Fasilitas",
            [
                "Apotek",
                "RS",
                "Klinik",
                "PBF",
                "IFP",
                "Lainnya"
            ]
        )

        no_pesanan = st.text_input(
            "Tanggal & Nomor Pesanan"
        )

        # ----------------------------------------------------
        # SURAT PESANAN
        # ----------------------------------------------------

        st.subheader(
            "📄 Surat Pesanan"
        )

        surat_file = st.file_uploader(
            "Upload Surat Pesanan",
            type=[
                "pdf",
                "jpg",
                "jpeg",
                "png"
            ],
            key="analisa_surat"
        )

        # ----------------------------------------------------
        # VALIDASI ADMINISTRATIF
        # ----------------------------------------------------

        st.subheader(
            "🔎 Validasi Administratif"
        )

        izin = st.radio(
            "Perizinan berusaha valid?",
            ["Ya", "Tidak"],
            horizontal=True
        )

        alasan_izin = st.text_area(
            "Alasan Perizinan",
            key="alasan_izin"
        )

        pj = st.radio(
            "Penanggung Jawab sesuai?",
            ["Ya", "Tidak"],
            horizontal=True
        )

        alasan_pj = st.text_area(
            "Alasan Penanggung Jawab",
            key="alasan_pj"
        )

        # ----------------------------------------------------
        # FASKES
        # ----------------------------------------------------

        st.subheader(
            "🏥 Lokasi Faskes"
        )

        faskes = st.radio(
            "Dekat faskes?",
            ["Ya", "Tidak"],
            horizontal=True
        )

        alasan_faskes = st.text_area(
            "Alasan Faskes"
        )

        bukti_faskes = st.file_uploader(
            "Upload Bukti Faskes (minimal 3 foto)",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            accept_multiple_files=True,
            key="bukti_faskes"
        )

        # ----------------------------------------------------
        # PEMUKIMAN
        # ----------------------------------------------------

        st.subheader(
            "🏠 Lokasi Pemukiman"
        )

        pemukiman = st.radio(
            "Dekat pemukiman?",
            ["Ya", "Tidak"],
            horizontal=True
        )

        alasan_pemukiman = st.text_area(
            "Alasan Pemukiman"
        )

        bukti_pemukiman = st.file_uploader(
            "Upload Bukti Pemukiman (minimal 3 foto)",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            accept_multiple_files=True,
            key="bukti_pemukiman"
        )

        # ----------------------------------------------------
        # HITUNG SCORE
        # ----------------------------------------------------

        ratio = (
            qty / avg
            if avg > 0
            else 0
        )

        score = 0

        if ratio <= 1.1:
            score += 30

        if surat_file:
            score += 10

        if izin == "Ya":
            score += 10

        if pj == "Ya":
            score += 10

        jumlah_faskes = (
            len(bukti_faskes)
            if bukti_faskes
            else 0
        )

        jumlah_pemukiman = (
            len(bukti_pemukiman)
            if bukti_pemukiman
            else 0
        )

        if (
            faskes == "Ya"
            and jumlah_faskes >= 3
        ):
            score += 20

        if (
            pemukiman == "Ya"
            and jumlah_pemukiman >= 3
        ):
            score += 20

        kategori = (
            "Wajar"
            if score >= 75
            else "Tidak Wajar"
        )

        st.subheader(
            "📊 Hasil Scoring"
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Skor",
            score
        )

        col2.metric(
            "Kategori",
            kategori
        )

        # ----------------------------------------------------
        # SURAT PERNYATAAN
        # ----------------------------------------------------

        surat_pernyataan = None

        if score < 75:

            st.warning(
                "⚠️ Skor di bawah 75. "
                "Surat Pernyataan wajib diupload."
            )

            surat_pernyataan = st.file_uploader(
                "Upload Surat Pernyataan",
                type=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png"
                ],
                key="surat_pernyataan"
            )

        # ----------------------------------------------------
        # VALIDASI
        # ----------------------------------------------------

        errors = []

        if qty <= 0:
            errors.append(
                "Qty Order wajib lebih dari 0."
            )

        if not no_pesanan.strip():
            errors.append(
                "Tanggal & Nomor Pesanan wajib diisi."
            )

        if not surat_file:
            errors.append(
                "Surat Pesanan wajib diupload."
            )

        if (
            izin == "Tidak"
            and not alasan_izin.strip()
        ):
            errors.append(
                "Alasan perizinan wajib diisi."
            )

        if (
            pj == "Tidak"
            and not alasan_pj.strip()
        ):
            errors.append(
                "Alasan PJ wajib diisi."
            )

        if (
            faskes == "Ya"
            and jumlah_faskes < 3
        ):
            errors.append(
                "Foto faskes minimal 3."
            )

        if (
            pemukiman == "Ya"
            and jumlah_pemukiman < 3
        ):
            errors.append(
                "Foto pemukiman minimal 3."
            )

        if (
            score < 75
            and not surat_pernyataan
        ):
            errors.append(
                "Surat Pernyataan wajib diupload."
            )

        if errors:

            st.error(
                "\n".join(
                    [
                        f"• {x}"
                        for x in errors
                    ]
                )
            )

        # ----------------------------------------------------
        # SUBMIT
        # ----------------------------------------------------

        if st.button(
            "💾 Simpan Analisa",
            type="primary",
            use_container_width=True
        ):

            if errors:

                st.error(
                    "Data belum dapat disimpan. "
                    "Lengkapi validasi di atas."
                )

            else:

                try:

                    surat_path = save_uploaded_file(
                        surat_file,
                        "surat"
                    )

                    faskes_path = save_multiple_files(
                        bukti_faskes,
                        "faskes"
                    )

                    pemukiman_path = save_multiple_files(
                        bukti_pemukiman,
                        "pemukiman"
                    )

                    pernyataan_path = save_uploaded_file(
                        surat_pernyataan,
                        "pernyataan"
                    )

                    alasan = (
                        f"{alasan_faskes} | "
                        f"{alasan_pemukiman}"
                    )

                    conn.execute(
                        """
                        INSERT INTO analisa
                        (
                            tanggal,
                            pelanggan,
                            produk,
                            qty_order,
                            avg_qty,
                            ratio,
                            score,
                            kategori,
                            status,
                            izin,
                            alasan_izin,
                            pj,
                            alasan_pj,
                            frekuensi,
                            faskes,
                            pemukiman,
                            alasan,
                            jenis_fasilitas,
                            no_pesanan,
                            bukti_faskes,
                            bukti_pemukiman,
                            surat_path,
                            surat_pernyataan
                        )
                        VALUES
                        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            pelanggan,
                            produk,
                            qty,
                            avg,
                            ratio,
                            score,
                            kategori,
                            "Pending",
                            izin,
                            alasan_izin,
                            pj,
                            alasan_pj,
                            frekuensi,
                            faskes,
                            pemukiman,
                            alasan,
                            jenis,
                            no_pesanan,
                            faskes_path,
                            pemukiman_path,
                            surat_path,
                            pernyataan_path
                        )
                    )

                    conn.commit()

                    st.success(
                        "✅ Analisa berhasil disimpan "
                        "dan masuk ke Approval."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Gagal menyimpan analisa: {e}"
                    )


# ============================================================
# DATA ANALISA
# ============================================================

elif menu == "Analisa":

    # Bagian ini sengaja tidak dibuat sebagai elif terpisah.
    # Data analisa ditampilkan di bawah form Analisa melalui
    # kode berikut di luar kondisi menu.
    pass


# ============================================================
# APPROVAL
# ============================================================

elif menu == "Approval":

    st.title(
        "✅ Approval Analisa"
    )

    st.caption(
        "Review data analisa sebelum disetujui."
    )

    df = pd.read_sql(
        """
        SELECT *
        FROM analisa
        ORDER BY id DESC
        """,
        conn
    )

    if df.empty:

        st.info(
            "Belum ada data analisa."
        )

    else:

        for _, row in df.iterrows():

            status = row.get(
                "status",
                "Pending"
            )

            with st.expander(
                f"📄 ID {row['id']} | "
                f"{row.get('pelanggan','')} | "
                f"{row.get('produk','')} | "
                f"Status: {status}"
            ):

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Qty Order",
                    row.get(
                        "qty_order",
                        0
                    )
                )

                col2.metric(
                    "Skor",
                    row.get(
                        "score",
                        0
                    )
                )

                col3.metric(
                    "Kategori",
                    row.get(
                        "kategori",
                        "-"
                    )
                )

                st.write(
                    "**Pelanggan:**",
                    row.get(
                        "pelanggan",
                        "-"
                    )
                )

                st.write(
                    "**Produk:**",
                    row.get(
                        "produk",
                        "-"
                    )
                )

                st.write(
                    "**Jenis Fasilitas:**",
                    row.get(
                        "jenis_fasilitas",
                        "-"
                    )
                )

                st.write(
                    "**No Pesanan:**",
                    row.get(
                        "no_pesanan",
                        "-"
                    )
                )

                # ------------------------------------------------
                # FILE
                # ------------------------------------------------

                st.subheader(
                    "📎 Lampiran"
                )

                if row.get("surat_path"):
                    show_file(
                        row["surat_path"],
                        "Surat Pesanan"
                    )

                if row.get("bukti_faskes"):

                    paths = str(
                        row["bukti_faskes"]
                    ).split(",")

                    cols = st.columns(3)

                    for i, path in enumerate(paths):

                        if path.strip():

                            with cols[
                                i % 3
                            ]:

                                show_file(
                                    path.strip(),
                                    f"Faskes {i+1}"
                                )

                if row.get("bukti_pemukiman"):

                    paths = str(
                        row["bukti_pemukiman"]
                    ).split(",")

                    cols = st.columns(3)

                    for i, path in enumerate(paths):

                        if path.strip():

                            with cols[
                                i % 3
                            ]:

                                show_file(
                                    path.strip(),
                                    f"Pemukiman {i+1}"
                                )

                if row.get(
                    "surat_pernyataan"
                ):

                    show_file(
                        row["surat_pernyataan"],
                        "Surat Pernyataan"
                    )

                # ------------------------------------------------
                # ACTION
                # ------------------------------------------------

                st.divider()

                if status == "Pending":

                    colA, colB = st.columns(2)

                    with colA:

                        if st.button(
                            "✅ Approve",
                            key=f"approve_{row['id']}",
                            use_container_width=True
                        ):

                            conn.execute(
                                """
                                UPDATE analisa
                                SET status='Approved'
                                WHERE id=?
                                """,
                                (row["id"],)
                            )

                            conn.commit()

                            st.success(
                                "Data berhasil di-approve."
                            )

                            st.rerun()

                    with colB:

                        if st.button(
                            "❌ Reject",
                            key=f"reject_{row['id']}",
                            use_container_width=True
                        ):

                            conn.execute(
                                """
                                UPDATE analisa
                                SET status='Rejected'
                                WHERE id=?
                                """,
                                (row["id"],)
                            )

                            conn.commit()

                            st.warning(
                                "Data berhasil direject."
                            )

                            st.rerun()

                elif status == "Approved":

                    st.success(
                        "Status: Approved"
                    )

                elif status == "Rejected":

                    st.error(
                        "Status: Rejected"
                    )


# ============================================================
# OUTPUT
# ============================================================

elif menu == "Output":

    st.title(
        "📄 Output Form Analisa"
    )

    try:

        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            Image,
            PageBreak
        )

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle
        )
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER

    except ImportError:

        st.error(
            "ReportLab belum terinstall."
        )

        st.code(
            "pip install reportlab"
        )

    else:

        df = pd.read_sql(
            """
            SELECT *
            FROM analisa
            WHERE status='Approved'
            ORDER BY id DESC
            """,
            conn
        )

        if df.empty:

            st.info(
                "Belum ada data yang Approved."
            )

        else:

            selected = st.selectbox(
                "Pilih Data",
                df["id"].tolist()
            )

            row = df[
                df["id"] == selected
            ].iloc[0]

            # ------------------------------------------------
            # INFORMASI
            # ------------------------------------------------

            st.subheader(
                "A. Informasi Pemesanan"
            )

            nama = st.text_input(
                "Nama Fasilitas",
                value=str(
                    row.get(
                        "pelanggan",
                        ""
                    )
                )
            )

            jenis = st.text_input(
                "Jenis Fasilitas",
                value=str(
                    row.get(
                        "jenis_fasilitas",
                        ""
                    )
                )
            )

            no_pesanan = st.text_input(
                "Tanggal & Nomor Pesanan",
                value=str(
                    row.get(
                        "no_pesanan",
                        ""
                    )
                )
            )

            produk = st.text_input(
                "Produk",
                value=str(
                    row.get(
                        "produk",
                        ""
                    )
                )
            )

            qty = st.number_input(
                "Qty",
                min_value=0,
                value=int(
                    row.get(
                        "qty_order",
                        0
                    ) or 0
                )
            )

            evaluator = st.text_input(
                "Nama Evaluator"
            )

            # ------------------------------------------------
            # CHECKLIST
            # ------------------------------------------------

            st.subheader(
                "B. Checklist Evaluasi"
            )

            rows = []

            def checklist_sync(
                no,
                teks,
                jawaban,
                catatan
            ):

                jawaban = (
                    jawaban
                    if jawaban
                    else "-"
                )

                catatan = (
                    catatan
                    if catatan
                    else "-"
                )

                st.markdown(
                    f"**{no}. {teks}**"
                )

                st.write(
                    f"Jawaban: **{jawaban}**"
                )

                st.write(
                    f"Catatan: {catatan}"
                )

                rows.append(
                    [
                        no,
                        teks,
                        jawaban,
                        catatan
                    ]
                )

            def checklist_manual(
                no,
                teks
            ):

                st.markdown(
                    f"**{no}. {teks}**"
                )

                colA, colB = st.columns(
                    [1, 3]
                )

                with colA:

                    jawaban = st.radio(
                        "Jawaban",
                        [
                            "Ya",
                            "Tidak"
                        ],
                        horizontal=True,
                        key=f"output_jaw_{no}"
                    )

                with colB:

                    catatan = st.text_input(
                        "Catatan",
                        key=f"output_cat_{no}"
                    )

                rows.append(
                    [
                        no,
                        teks,
                        jawaban,
                        catatan or "-"
                    ]
                )

            izin = row.get(
                "izin",
                "-"
            )

            alasan_izin = row.get(
                "alasan_izin",
                "-"
            )

            pj = row.get(
                "pj",
                "-"
            )

            alasan_pj = row.get(
                "alasan_pj",
                "-"
            )

            ratio = float(
                row.get(
                    "ratio",
                    0
                ) or 0
            )

            avg = float(
                row.get(
                    "avg_qty",
                    0
                ) or 0
            )

            faskes = row.get(
                "faskes",
                "-"
            )

            pemukiman = row.get(
                "pemukiman",
                "-"
            )

            alasan_full = str(
                row.get(
                    "alasan",
                    ""
                ) or ""
            )

            alasan_faskes = "-"
            alasan_pemukiman = "-"

            if "|" in alasan_full:

                parts = alasan_full.split(
                    "|"
                )

                if len(parts) >= 1:
                    alasan_faskes = (
                        parts[0].strip()
                        or "-"
                    )

                if len(parts) >= 2:
                    alasan_pemukiman = (
                        parts[1].strip()
                        or "-"
                    )

            checklist_sync(
                1,
                "Pelanggan memiliki Perizinan Berusaha yang masih berlaku",
                izin,
                alasan_izin
            )

            checklist_sync(
                2,
                "Penanggung Jawab fasilitas pemesan sesuai ketentuan",
                pj,
                alasan_pj
            )

            checklist_manual(
                3,
                "Jumlah dan frekuensi pesanan sesuai kapasitas penyimpanan"
            )

            lonjakan = (
                "Ya"
                if ratio <= 1.5
                else "Tidak"
            )

            checklist_sync(
                4,
                "Tidak terdapat lonjakan jumlah dan frekuensi pesanan yang tidak wajar",
                lonjakan,
                f"{qty} vs {round(avg,2)}"
            )

            checklist_manual(
                5,
                "Jenis obat sesuai kualifikasi fasilitas"
            )

            checklist_manual(
                6,
                "Narkotika/Psikotropika/Prekursor/OOT sesuai kebutuhan"
            )

            checklist_manual(
                7,
                "Pesanan antibiotik rasional dan tidak berpotensi mendorong resistensi"
            )

            checklist_manual(
                8,
                "Sediaan khusus dapat ditangani fasilitas"
            )

            checklist_sync(
                9,
                "Lokasi dan kondisi pelayanan mendukung kewajaran pesanan",
                pemukiman,
                alasan_pemukiman
            )

            checklist_sync(
                10,
                "Tersedia praktik dokter/kerja sama fasyankes jika relevan",
                faskes,
                alasan_faskes
            )

            # ------------------------------------------------
            # KESIMPULAN
            # ------------------------------------------------

            st.subheader(
                "C. Kesimpulan"
            )

            keputusan = st.radio(
                "Hasil Evaluasi",
                [
                    "Disetujui",
                    "Ditolak"
                ],
                horizontal=True
            )

            catatan_akhir = st.text_area(
                "Catatan Akhir"
            )

            # ------------------------------------------------
            # GENERATE PDF
            # ------------------------------------------------

            if st.button(
                "📄 Generate PDF Form",
                type="primary",
                use_container_width=True
            ):

                file_path = os.path.join(
                    PDF_FOLDER,
                    "Form_"
                    + datetime.now().strftime(
                        "%Y%m%d_%H%M%S"
                    )
                    + ".pdf"
                )

                doc = SimpleDocTemplate(
                    file_path,
                    pagesize=A4,
                    leftMargin=20,
                    rightMargin=20,
                    topMargin=20,
                    bottomMargin=15
                )

                styles = getSampleStyleSheet()

                normal = ParagraphStyle(
                    name="NormalSmall",
                    fontSize=8,
                    leading=10
                )

                header = ParagraphStyle(
                    name="Header",
                    fontSize=10,
                    alignment=TA_CENTER
                )

                elements = []

                elements.append(
                    Paragraph(
                        "<b>PT. KIMIA FARMA TRADING & DISTRIBUTION</b>",
                        header
                    )
                )

                elements.append(
                    Paragraph(
                        "Kantor Cabang Mataram",
                        header
                    )
                )

                elements.append(
                    Paragraph(
                        "Jl. I.G.M Jelantik Gosa No.10 X Mataram - NTB",
                        header
                    )
                )

                elements.append(
                    Paragraph(
                        "Telp (0370)624925",
                        header
                    )
                )

                elements.append(
                    Spacer(1, 8)
                )

                elements.append(
                    Paragraph(
                        "<b>FORM ANALISA KEWAJARAN</b>",
                        styles["Title"]
                    )
                )

                elements.append(
                    Spacer(1, 8)
                )

                info = Table(
                    [
                        ["Fasilitas", nama],
                        ["Jenis", jenis],
                        ["No. Pesanan", no_pesanan],
                        ["Produk", produk],
                        ["Qty", qty],
                        ["Evaluator", evaluator]
                    ],
                    colWidths=[
                        100,
                        320
                    ]
                )

                info.setStyle(
                    [
                        (
                            "GRID",
                            (0,0),
                            (-1,-1),
                            0.5,
                            colors.black
                        ),
                        (
                            "FONTSIZE",
                            (0,0),
                            (-1,-1),
                            8
                        )
                    ]
                )

                elements.append(
                    info
                )

                elements.append(
                    Spacer(1, 8)
                )

                table_data = [
                    [
                        "No",
                        "Aspek",
                        "Jawaban",
                        "Catatan"
                    ]
                ]

                for item in rows:

                    table_data.append(
                        [
                            item[0],
                            Paragraph(
                                str(item[1]),
                                normal
                            ),
                            item[2],
                            Paragraph(
                                str(item[3]),
                                normal
                            )
                        ]
                    )

                table = Table(
                    table_data,
                    colWidths=[
                        25,
                        210,
                        50,
                        135
                    ]
                )

                table.setStyle(
                    [
                        (
                            "GRID",
                            (0,0),
                            (-1,-1),
                            0.5,
                            colors.black
                        ),
                        (
                            "BACKGROUND",
                            (0,0),
                            (-1,0),
                            colors.lightgrey
                        ),
                        (
                            "FONTSIZE",
                            (0,0),
                            (-1,-1),
                            7
                        )
                    ]
                )

                elements.append(
                    table
                )

                elements.append(
                    Spacer(1, 8)
                )

                elements.append(
                    Paragraph(
                        f"Hasil: <b>{keputusan}</b>",
                        normal
                    )
                )

                elements.append(
                    Paragraph(
                        f"Catatan: {catatan_akhir or '-'}",
                        normal
                    )
                )

                elements.append(
                    Spacer(1, 30)
                )

                ttd = Table(
                    [
                        [
                            "Evaluator",
                            "",
                            "Penanggung Jawab"
                        ],
                        [
                            "",
                            "",
                            ""
                        ],
                        [
                            "(______________)",
                            "",
                            "(______________)"
                        ]
                    ],
                    colWidths=[
                        180,
                        60,
                        180
                    ]
                )

                elements.append(
                    ttd
                )

                doc.build(
                    elements
                )

                with open(
                    file_path,
                    "rb"
                ) as f:

                    pdf_data = f.read()

                st.success(
                    "✅ PDF berhasil dibuat."
                )

                st.download_button(
                    "⬇️ Download Form PDF",
                    data=pdf_data,
                    file_name=os.path.basename(
                        file_path
                    ),
                    mime="application/pdf",
                    use_container_width=True
                )


# ============================================================
# PENOLAKAN PESANAN
# ============================================================

elif menu == "Penolakan Pesanan":

    st.title(
        "❌ Surat Penolakan Pesanan"
    )

    st.caption(
        "Pembuatan Surat Penolakan Pesanan berdasarkan template PDF."
    )

    # --------------------------------------------------------
    # CEK PYMUPDF
    # --------------------------------------------------------

    try:

        import fitz

    except ImportError:

        st.error(
            "PyMuPDF belum terinstall."
        )

        st.code(
            "pip install PyMuPDF"
        )

        st.stop()

    # --------------------------------------------------------
    # CEK TEMPLATE
    # --------------------------------------------------------

    if not os.path.isfile(
        TEMPLATE_PENOLAKAN
    ):

        st.error(
            "Template Surat Penolakan tidak ditemukan."
        )

        st.info(
            "Letakkan file berikut satu folder dengan app.py:"
        )

        st.code(
            "Surat Penolakan Obat - Google Dokumen.pdf"
        )

        st.write(
            "Path yang dicari:"
        )

        st.code(
            TEMPLATE_PENOLAKAN
        )

    else:

        # ----------------------------------------------------
        # INFORMASI
        # ----------------------------------------------------

        st.subheader(
            "A. Informasi Surat"
        )

        col1, col2 = st.columns(2)

        with col1:

            nama_sarana = st.text_input(
                "Nama Sarana",
                placeholder="Contoh: Apotek Sehat",
                key="penolakan_nama"
            )

            nomor_sp = st.text_input(
                "Nomor Surat Pesanan",
                placeholder="Contoh: SP/001/IX/2026",
                key="penolakan_nomor"
            )

        with col2:

            tanggal_sp = st.date_input(
                "Tanggal Surat Pesanan",
                value=datetime.now().date(),
                key="penolakan_tanggal_sp"
            )

            tanggal_surat = st.date_input(
                "Tanggal Surat Penolakan",
                value=datetime.now().date(),
                key="penolakan_tanggal_surat"
            )

        # ----------------------------------------------------
        # PRODUK
        # ----------------------------------------------------

        st.subheader(
            "B. Item Pesanan"
        )

        st.caption(
            "Maksimal 5 produk."
        )

        produk_data = []

        for i in range(1, 6):

            with st.container(
                border=True
            ):

                st.markdown(
                    f"**Produk {i}**"
                )

                col1, col2, col3 = st.columns(
                    [5, 2, 2]
                )

                with col1:

                    nama_produk = st.text_input(
                        f"Nama Produk / Barang {i}",
                        key=f"penolakan_produk_{i}"
                    )

                with col2:

                    jumlah_pesanan = st.text_input(
                        f"Jumlah Pesanan {i}",
                        key=f"penolakan_qty_{i}"
                    )

                with col3:

                    jumlah_faktur = st.text_input(
                        f"Jumlah Difakturkan {i}",
                        key=f"penolakan_faktur_{i}"
                    )

                produk_data.append(
                    {
                        "produk": nama_produk.strip(),
                        "pesanan": jumlah_pesanan.strip(),
                        "faktur": jumlah_faktur.strip()
                    }
                )

        # ----------------------------------------------------
        # ALASAN
        # ----------------------------------------------------

        st.subheader(
            "C. Alasan Penolakan"
        )

        alasan_ditolak = st.text_area(
            "Alasan Penolakan",
            placeholder="Tuliskan alasan penolakan pesanan...",
            height=120,
            key="penolakan_alasan"
        )

        # ----------------------------------------------------
        # VALIDASI
        # ----------------------------------------------------

        errors = []

        if not nama_sarana.strip():

            errors.append(
                "Nama Sarana wajib diisi."
            )

        if not nomor_sp.strip():

            errors.append(
                "Nomor Surat Pesanan wajib diisi."
            )

        if not any(
            x["produk"]
            for x in produk_data
        ):

            errors.append(
                "Minimal 1 produk harus diisi."
            )

        if not alasan_ditolak.strip():

            errors.append(
                "Alasan penolakan wajib diisi."
            )

        if errors:

            st.error(
                "\n".join(
                    [
                        f"• {x}"
                        for x in errors
                    ]
                )
            )

        # ----------------------------------------------------
        # FUNGSI PDF
        # ----------------------------------------------------

        def tutup_area(
            page,
            rect
        ):

            page.draw_rect(
                fitz.Rect(rect),
                color=None,
                fill=(1, 1, 1),
                overlay=True
            )


        def isi_teks(
            page,
            rect,
            text,
            fontsize=9,
            align=0
        ):

            page.insert_textbox(
                fitz.Rect(rect),
                str(text or ""),
                fontsize=fontsize,
                fontname="helv",
                color=(0, 0, 0),
                align=align,
                overlay=True
            )


        def buat_surat_penolakan():

            doc = fitz.open(
                TEMPLATE_PENOLAKAN
            )

            try:

                if len(doc) == 0:

                    raise Exception(
                        "Template PDF tidak memiliki halaman."
                    )

                page = doc[0]

                # ------------------------------------------------
                # NAMA SARANA
                # ------------------------------------------------

                tutup_area(
                    page,
                    (130, 136, 300, 158)
                )

                isi_teks(
                    page,
                    (130, 136, 300, 158),
                    nama_sarana,
                    9
                )

                # ------------------------------------------------
                # NOMOR SP
                # ------------------------------------------------

                tutup_area(
                    page,
                    (275, 166, 370, 186)
                )

                isi_teks(
                    page,
                    (275, 166, 370, 186),
                    nomor_sp,
                    9
                )

                # ------------------------------------------------
                # TANGGAL SP
                # ------------------------------------------------

                tutup_area(
                    page,
                    (405, 166, 505, 186)
                )

                isi_teks(
                    page,
                    (405, 166, 505, 186),
                    tanggal_sp.strftime(
                        "%d/%m/%Y"
                    ),
                    9
                )

                # ------------------------------------------------
                # PRODUK
                # ------------------------------------------------

                baris_y = [
                    (239, 269),
                    (269, 300),
                    (300, 330),
                    (330, 360),
                    (360, 391)
                ]

                for i, item in enumerate(
                    produk_data
                ):

                    y1, y2 = baris_y[i]

                    # Nama Produk
                    tutup_area(
                        page,
                        (
                            166,
                            y1 + 1,
                            350,
                            y2 - 1
                        )
                    )

                    isi_teks(
                        page,
                        (
                            170,
                            y1 + 2,
                            348,
                            y2 - 2
                        ),
                        item["produk"],
                        8,
                        1
                    )

                    # Jumlah Pesanan
                    tutup_area(
                        page,
                        (
                            330,
                            y1 + 1,
                            405,
                            y2 - 1
                        )
                    )

                    isi_teks(
                        page,
                        (
                            332,
                            y1 + 2,
                            403,
                            y2 - 2
                        ),
                        item["pesanan"],
                        8,
                        1
                    )

                    # Jumlah Faktur
                    tutup_area(
                        page,
                        (
                            407,
                            y1 + 1,
                            505,
                            y2 - 1
                        )
                    )

                    isi_teks(
                        page,
                        (
                            409,
                            y1 + 2,
                            503,
                            y2 - 2
                        ),
                        item["faktur"],
                        8,
                        1
                    )

                # ------------------------------------------------
                # ALASAN
                # ------------------------------------------------

                tutup_area(
                    page,
                    (245, 402, 510, 424)
                )

                isi_teks(
                    page,
                    (245, 402, 510, 424),
                    alasan_ditolak,
                    8
                )

                # ------------------------------------------------
                # TANGGAL SURAT
                # ------------------------------------------------

                tutup_area(
                    page,
                    (425, 476, 510, 497)
                )

                isi_teks(
                    page,
                    (425, 476, 510, 497),
                    tanggal_surat.strftime(
                        "%d/%m/%Y"
                    ),
                    9
                )

                # ------------------------------------------------
                # NAMA FILE
                # ------------------------------------------------

                nomor_aman = (
                    nomor_sp
                    .replace("/", "_")
                    .replace("\\", "_")
                    .replace(" ", "_")
                )

                filename = (
                    "Surat_Penolakan_"
                    f"{nomor_aman}_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    ".pdf"
                )

                output_path = os.path.join(
                    PDF_FOLDER,
                    filename
                )

                # ------------------------------------------------
                # SAVE
                # ------------------------------------------------

                doc.save(
                    output_path,
                    garbage=4,
                    deflate=True
                )

                return output_path

            finally:

                doc.close()

        # ----------------------------------------------------
        # GENERATE
        # ----------------------------------------------------

        st.divider()

        if st.button(
            "📄 Generate Surat Penolakan",
            type="primary",
            use_container_width=True
        ):

            if errors:

                st.error(
                    "Surat belum dapat dibuat. "
                    "Lengkapi data terlebih dahulu."
                )

            else:

                try:

                    hasil_pdf = (
                        buat_surat_penolakan()
                    )

                    st.session_state.hasil_penolakan = (
                        hasil_pdf
                    )

                    st.success(
                        "✅ Surat Penolakan berhasil dibuat."
                    )

                except Exception as e:

                    st.error(
                        "❌ Gagal membuat Surat Penolakan."
                    )

                    st.exception(e)

        # ----------------------------------------------------
        # HASIL PDF
        # ----------------------------------------------------

        if st.session_state.hasil_penolakan:

            hasil_pdf = (
                st.session_state.hasil_penolakan
            )

            if os.path.exists(
                hasil_pdf
            ):

                with open(
                    hasil_pdf,
                    "rb"
                ) as f:

                    pdf_data = f.read()

                st.subheader(
                    "👁️ Preview Surat"
                )

                st.download_button(
                    "⬇️ Download Surat Penolakan",
                    data=pdf_data,
                    file_name=os.path.basename(
                        hasil_pdf
                    ),
                    mime="application/pdf",
                    use_container_width=True
                )

                encoded = base64.b64encode(
                    pdf_data
                ).decode("utf-8")

                html = f"""
                <iframe
                    src="data:application/pdf;base64,{encoded}"
                    width="100%"
                    height="800"
                    style="
                        border:1px solid #ccc;
                        border-radius:8px;
                    ">
                </iframe>
                """

                st.markdown(
                    html,
                    unsafe_allow_html=True
                )


# ============================================================
# DATA ANALISA - DITAMPILKAN DI MENU ANALISA
# ============================================================

if menu == "Analisa":

    st.divider()

    st.subheader(
        "📊 Data Analisa"
    )

    df_analisa = pd.read_sql(
        """
        SELECT *
        FROM analisa
        ORDER BY id DESC
        """,
        conn
    )

    if df_analisa.empty:

        st.info(
            "Belum ada data analisa."
        )

    else:

        # ----------------------------------------------------
        # RINGKASAN
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total",
            len(df_analisa)
        )

        col2.metric(
            "Pending",
            len(
                df_analisa[
                    df_analisa["status"]
                    == "Pending"
                ]
            )
        )

        col3.metric(
            "Approved",
            len(
                df_analisa[
                    df_analisa["status"]
                    == "Approved"
                ]
            )
        )

        col4.metric(
            "Rejected",
            len(
                df_analisa[
                    df_analisa["status"]
                    == "Rejected"
                ]
            )
        )

        # ----------------------------------------------------
        # PILIH DATA
        # ----------------------------------------------------

        selected_id = st.selectbox(
            "Pilih ID Data",
            df_analisa["id"].tolist(),
            key="analisa_selected_id"
        )

        row = df_analisa[
            df_analisa["id"]
            == selected_id
        ].iloc[0]

        status = row.get(
            "status",
            "Pending"
        )

        if status == "Approved":

            st.success(
                f"Status: {status}"
            )

        elif status == "Rejected":

            st.error(
                f"Status: {status}"
            )

        else:

            st.warning(
                f"Status: {status}"
            )

        # ----------------------------------------------------
        # DETAIL
        # ----------------------------------------------------

        if st.checkbox(
            "👁️ Lihat Detail",
            key=f"detail_{selected_id}"
        ):

            st.write(
                "**Pelanggan:**",
                row.get(
                    "pelanggan",
                    "-"
                )
            )

            st.write(
                "**Produk:**",
                row.get(
                    "produk",
                    "-"
                )
            )

            st.write(
                "**Qty:**",
                row.get(
                    "qty_order",
                    0
                )
            )

            st.write(
                "**No Pesanan:**",
                row.get(
                    "no_pesanan",
                    "-"
                )
            )

            st.write(
                "**Skor:**",
                row.get(
                    "score",
                    0
                )
            )

            st.write(
                "**Kategori:**",
                row.get(
                    "kategori",
                    "-"
                )
            )

            st.write(
                "**Perizinan:**",
                row.get(
                    "izin",
                    "-"
                )
            )

            st.write(
                "**PJ:**",
                row.get(
                    "pj",
                    "-"
                )
            )

            if row.get("surat_path"):

                show_file(
                    row["surat_path"],
                    "Surat Pesanan"
                )

            if row.get(
                "bukti_faskes"
            ):

                for i, path in enumerate(
                    str(
                        row["bukti_faskes"]
                    ).split(",")
                ):

                    if path.strip():

                        show_file(
                            path.strip(),
                            f"Faskes {i+1}"
                        )

            if row.get(
                "bukti_pemukiman"
            ):

                for i, path in enumerate(
                    str(
                        row["bukti_pemukiman"]
                    ).split(",")
                ):

                    if path.strip():

                        show_file(
                            path.strip(),
                            f"Pemukiman {i+1}"
                        )

            if row.get(
                "surat_pernyataan"
            ):

                show_file(
                    row["surat_pernyataan"],
                    "Surat Pernyataan"
                )

        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        st.divider()

        if st.session_state.role == "admin":

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "🗑️ Hapus Data",
                    key=f"delete_{selected_id}"
                ):

                    conn.execute(
                        "DELETE FROM analisa WHERE id=?",
                        (selected_id,)
                    )

                    conn.commit()

                    st.success(
                        "Data berhasil dihapus."
                    )

                    st.rerun()

            # ------------------------------------------------
            # EDIT
            # ------------------------------------------------

            with col2:

                if status in [
                    "Pending",
                    "Rejected"
                ]:

                    if st.button(
                        "✏️ Edit Data",
                        key=f"edit_{selected_id}"
                    ):

                        st.session_state.edit_id = (
                            selected_id
                        )

                        st.rerun()

                else:

                    st.info(
                        "Data Approved tidak dapat diedit."
                    )

        # ----------------------------------------------------
        # FORM EDIT
        # ----------------------------------------------------

        if (
            st.session_state.edit_id
            == selected_id
            and status in [
                "Pending",
                "Rejected"
            ]
        ):

            st.divider()

            st.subheader(
                "✏️ Edit Data Analisa"
            )

            new_qty = st.number_input(
                "Edit Qty",
                min_value=0,
                value=int(
                    row.get(
                        "qty_order",
                        0
                    )
                    or 0
                ),
                key="edit_qty"
            )

            new_no = st.text_input(
                "Edit No Pesanan",
                value=str(
                    row.get(
                        "no_pesanan",
                        ""
                    )
                    or ""
                ),
                key="edit_no"
            )

            st.write(
                "Upload file baru bersifat opsional."
            )

            new_surat = st.file_uploader(
                "Surat Pesanan Baru",
                type=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png"
                ],
                key="edit_surat"
            )

            new_faskes = st.file_uploader(
                "Foto Faskes Baru",
                type=[
                    "jpg",
                    "jpeg",
                    "png"
                ],
                accept_multiple_files=True,
                key="edit_faskes"
            )

            new_pemukiman = st.file_uploader(
                "Foto Pemukiman Baru",
                type=[
                    "jpg",
                    "jpeg",
                    "png"
                ],
                accept_multiple_files=True,
                key="edit_pemukiman"
            )

            new_pernyataan = st.file_uploader(
                "Surat Pernyataan Baru",
                type=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png"
                ],
                key="edit_pernyataan"
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "💾 Simpan Perubahan",
                    type="primary",
                    key="save_edit"
                ):

                    try:

                        surat_path = row.get(
                            "surat_path",
                            ""
                        ) or ""

                        if new_surat:

                            surat_path = (
                                save_uploaded_file(
                                    new_surat,
                                    "surat"
                                )
                            )

                        faskes_path = row.get(
                            "bukti_faskes",
                            ""
                        ) or ""

                        if new_faskes:

                            faskes_path = (
                                save_multiple_files(
                                    new_faskes,
                                    "faskes"
                                )
                            )

                        pemukiman_path = row.get(
                            "bukti_pemukiman",
                            ""
                        ) or ""

                        if new_pemukiman:

                            pemukiman_path = (
                                save_multiple_files(
                                    new_pemukiman,
                                    "pemukiman"
                                )
                            )

                        pernyataan_path = row.get(
                            "surat_pernyataan",
                            ""
                        ) or ""

                        if new_pernyataan:

                            pernyataan_path = (
                                save_uploaded_file(
                                    new_pernyataan,
                                    "pernyataan"
                                )
                            )

                        avg_value = float(
                            row.get(
                                "avg_qty",
                                0
                            )
                            or 0
                        )

                        ratio_value = (
                            new_qty / avg_value
                            if avg_value > 0
                            else 0
                        )

                        # Pertahankan logika
                        # score sebelumnya.
                        old_score = int(
                            row.get(
                                "score",
                                0
                            )
                            or 0
                        )

                        kategori = (
                            "Wajar"
                            if old_score >= 75
                            else "Tidak Wajar"
                        )

                        conn.execute(
                            """
                            UPDATE analisa
                            SET
                                qty_order=?,
                                no_pesanan=?,
                                ratio=?,
                                kategori=?,
                                surat_path=?,
                                bukti_faskes=?,
                                bukti_pemukiman=?,
                                surat_pernyataan=?,
                                status='Pending'
                            WHERE id=?
                            """,
                            (
                                new_qty,
                                new_no,
                                ratio_value,
                                kategori,
                                surat_path,
                                faskes_path,
                                pemukiman_path,
                                pernyataan_path,
                                selected_id
                            )
                        )

                        conn.commit()

                        st.session_state.edit_id = None

                        st.success(
                            "✅ Perubahan berhasil disimpan."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Gagal menyimpan perubahan: {e}"
                        )

            with col2:

                if st.button(
                    "❌ Batal Edit",
                    key="cancel_edit"
                ):

                    st.session_state.edit_id = None

                    st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "Monitoring Analisa"
)

st.sidebar.caption(
    "PT Kimia Farma Trading & Distribution"
)

st.sidebar.caption(
    "Cabang Mataram"
)
