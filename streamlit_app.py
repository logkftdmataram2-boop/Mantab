import pandas as pd
import streamlit as st
import sqlite3
import os
from datetime import datetime
from io import BytesIO

st.set_page_config(
    page_title="WAJARLAH. KF",
    page_icon="Wajarlah. KF.png",  # bisa emoji atau file
    layout="wide"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE
# =========================
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT,
        pelanggan TEXT,
        produk TEXT,
        qty INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS analisa (
        id INTEGER PRIMARY KEY AUTOINCREMENT
    )
    """)

    conn.commit()
    return conn

conn = get_conn()

# =========================
# AUTO MIGRATION
# =========================
def ensure(col, tipe):
    try:
        conn.execute(f"ALTER TABLE analisa ADD COLUMN {col} {tipe}")
    except:
        pass

for c,t in {
    "tanggal":"TEXT","pelanggan":"TEXT","produk":"TEXT",
    "qty_order":"INTEGER","avg_qty":"REAL","ratio":"REAL",
    "score":"INTEGER","kategori":"TEXT","status":"TEXT",
    "faskes":"TEXT","pemukiman":"TEXT","alasan":"TEXT",
    "foto1":"TEXT","foto2":"TEXT","foto3":"TEXT","foto4":"TEXT","foto5":"TEXT",
    "jenis_fasilitas":"TEXT","no_pesanan":"TEXT",
    "surat":"TEXT","bukti_faskes":"TEXT","bukti_pemukiman":"TEXT"
}.items():
    ensure(c,t)

conn.commit()

# =========================
# LOGIN
# =========================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = None

users = {
    "admin": {"password": "123", "role": "admin"},
    "user1": {"password": "123", "role": "user"}
}

if not st.session_state.login:
    st.image("Header.png", width=150)
    st.title("Wajarlah KF Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in users and users[u]["password"] == p:
            st.session_state.login = True
            st.session_state.role = users[u]["role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

st.sidebar.success(f"Login: {st.session_state.role}")

if st.sidebar.button("Logout"):
    st.session_state.login=False
    st.rerun()

menu = st.sidebar.radio(
    "Menu",
    ["Monitoring","Analisa","Approval","Output"] if st.session_state.role=="admin"
    else ["Monitoring","Analisa"]
)

# =========================
# MONITORING (FAST)
# =========================
if menu=="Monitoring":

    st.title("📊 Monitoring Pemakaian Produk")

    # UPLOAD
    if st.session_state.role=="admin":
        file=st.sidebar.file_uploader("Upload Excel",type=["xlsx"])
        if file:
            df=pd.read_excel(file)
            df["Tanggal"]=pd.to_datetime(df["Tanggal"],errors="coerce")
            df=df.dropna()
            df["Tanggal"]=df["Tanggal"].dt.strftime("%Y-%m-%d")

            df=df.rename(columns={
                "Tanggal":"tanggal",
                "Nama Pelanggan":"pelanggan",
                "Produk":"produk",
                "Qty":"qty"
            })

            conn.execute("DELETE FROM data")
            conn.executemany(
                "INSERT INTO data (tanggal,pelanggan,produk,qty) VALUES (?,?,?,?)",
                list(df.itertuples(index=False,name=None))
            )
            conn.commit()

            st.success("Upload berhasil")

    df_all=pd.read_sql("SELECT * FROM data",conn)

    if df_all.empty:
        st.warning("Tidak ada data")
        st.stop()

    df_all["tanggal"]=pd.to_datetime(df_all["tanggal"])

    # FILTER
    pelanggan=st.sidebar.selectbox("Pelanggan",["Semua"]+sorted(df_all["pelanggan"].unique()))
    produk=st.sidebar.selectbox("Produk",["Semua"]+sorted(df_all["produk"].unique()))

    tgl=st.sidebar.date_input("Tanggal",(df_all["tanggal"].min(),df_all["tanggal"].max()))

    if st.sidebar.button("Reset Filter"):
        st.rerun()

    # QUERY CEPAT
    q="SELECT * FROM data WHERE tanggal BETWEEN ? AND ?"
    p=[str(tgl[0]),str(tgl[1])]

    if pelanggan!="Semua":
        q+=" AND pelanggan=?"
        p.append(pelanggan)

    if produk!="Semua":
        q+=" AND produk=?"
        p.append(produk)

    df=pd.read_sql(q,conn,params=p)
    df["tanggal"]=pd.to_datetime(df["tanggal"])

    # DASHBOARD
    col1,col2,col3=st.columns(3)
    col1.metric("Transaksi",len(df))
    col2.metric("Total Qty",int(df["qty"].sum()) if not df.empty else 0)
    col3.metric("Rata-rata",round(df["qty"].mean(),2) if not df.empty else 0)

    # GRAFIK
    if not df.empty:
        df["bulan"]=df["tanggal"].dt.to_period("M").astype(str)
        st.bar_chart(df.groupby("bulan")["qty"].sum())

    # DOWNLOAD
    def to_excel(x):
        out=BytesIO()
        with pd.ExcelWriter(out,engine="openpyxl") as w:
            x.to_excel(w,index=False)
        return out.getvalue()

    st.download_button("Download Excel",to_excel(df),"monitoring.xlsx")

    st.dataframe(df,use_container_width=True)

import os
from datetime import datetime
import pandas as pd
import streamlit as st

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# MENU ANALISA FINAL (FULL FIX + VIEW FILE AMAN)
# =========================
if menu == "Analisa":

    import os
    import io
    from datetime import datetime
    import pandas as pd
    import streamlit as st
    from PIL import Image, UnidentifiedImageError

    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # =========================
    # AUTO FIX DB
    # =========================
    def ensure_column(conn, table, column, col_type="TEXT"):
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()

    conn.execute("CREATE TABLE IF NOT EXISTS analisa (id INTEGER PRIMARY KEY AUTOINCREMENT)")

    columns = [
        ("tanggal","TEXT"),("pelanggan","TEXT"),("produk","TEXT"),
        ("qty_order","REAL"),("avg_qty","REAL"),("ratio","REAL"),
        ("score","INTEGER"),("kategori","TEXT"),("status","TEXT"),
        ("izin","TEXT"),("alasan_izin","TEXT"),
        ("pj","TEXT"),("alasan_pj","TEXT"),
        ("frekuensi","INTEGER"),
        ("faskes","TEXT"),("pemukiman","TEXT"),("alasan","TEXT"),
        ("jenis_fasilitas","TEXT"),("no_pesanan","TEXT"),
        ("bukti_faskes","TEXT"),("bukti_pemukiman","TEXT"),
        ("surat_path","TEXT"),
        ("surat_pernyataan","TEXT")
    ]

    for col, typ in columns:
        ensure_column(conn,"analisa",col,typ)

    st.title("📋 Analisa Kewajaran")

    # =========================
    # FUNGSI TAMPIL FILE (FIX ERROR GAMBAR)
    # =========================
    def tampilkan_file(file_path, nama="File"):
        if not file_path:
            st.warning(f"{nama} kosong")
            return

        try:
            # Kalau path
            if isinstance(file_path, str):

                if not os.path.exists(file_path):
                    st.error(f"{nama} tidak ditemukan")
                    return

                # Baca file
                with open(file_path, "rb") as f:
                    data = f.read()

                # PDF
                if data[:4] == b"%PDF":
                    st.info(f"{nama} (PDF)")
                    st.download_button(f"Download {nama}", data, file_name=os.path.basename(file_path))

                else:
                    image = Image.open(io.BytesIO(data))
                    st.image(image, caption=nama)

            else:
                st.error(f"{nama} format tidak dikenali")

        except UnidentifiedImageError:
            st.error(f"{nama} bukan gambar valid")
        except Exception as e:
            st.error(f"Error {nama}: {e}")

    # =========================
    # LOAD DATA
    # =========================
    df = pd.read_sql("SELECT * FROM data", conn)

    if df.empty:
        st.warning("Data kosong")
        st.stop()

    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")

    pelanggan = st.selectbox("Pelanggan", sorted(df["pelanggan"].dropna().unique()))
    produk = st.selectbox("Produk", sorted(df[df["pelanggan"]==pelanggan]["produk"].dropna().unique()))

    # =========================
    # RATA-RATA
    # =========================
    st.subheader("📅 Perhitungan Rata-rata")

    tgl_avg = st.date_input("Range Tanggal", (df["tanggal"].min(), df["tanggal"].max()))

    df_avg = df[
        (df["pelanggan"]==pelanggan) &
        (df["produk"]==produk) &
        (df["tanggal"]>=pd.to_datetime(tgl_avg[0])) &
        (df["tanggal"]<=pd.to_datetime(tgl_avg[1]))
    ]

    avg = df_avg["qty"].mean() if not df_avg.empty else 0
    frekuensi = len(df_avg)

    st.info(f"Rata-rata: {round(avg,2)} | Frekuensi: {frekuensi}")

    # =========================
    # INPUT
    # =========================
    qty = st.number_input("Qty Order", 0)

    st.subheader("Informasi Pesanan")
    jenis = st.radio("Jenis Fasilitas", ["Apotek","RS","Klinik","PBF","IFP","Lainnya"])
    no_pesanan = st.text_input("Tanggal & Nomor Pesanan")

    # =========================
    # SURAT PESANAN
    # =========================
    surat_file = st.file_uploader("Upload Surat Pesanan", type=["pdf","jpg","png"])
    surat_path = ""

    if surat_file:
        surat_path = os.path.join(UPLOAD_FOLDER, f"surat_{datetime.now().timestamp()}_{surat_file.name}")
        with open(surat_path,"wb") as f:
            f.write(surat_file.read())

    # =========================
    # VALIDASI ADMIN
    # =========================
    st.subheader("Validasi Administratif")

    izin = st.radio("Perizinan berusaha valid?", ["Ya","Tidak"])
    alasan_izin = st.text_area("Alasan Perizinan")

    pj = st.radio("Penanggung jawab sesuai?", ["Ya","Tidak"])
    alasan_pj = st.text_area("Alasan Penanggung Jawab")

    # =========================
    # FASKES
    # =========================
    st.subheader("Lokasi Faskes")

    faskes = st.radio("Dekat faskes?", ["Ya","Tidak"])
    alasan_faskes = st.text_area("Alasan Faskes")

    bukti_faskes = st.file_uploader("Upload Bukti Faskes (minimal 3 foto)", accept_multiple_files=True)

    path_faskes_list = []
    if bukti_faskes:
        for file in bukti_faskes:
            path = os.path.join(UPLOAD_FOLDER, f"faskes_{datetime.now().timestamp()}_{file.name}")
            with open(path,"wb") as f:
                f.write(file.read())
            path_faskes_list.append(path)

    # =========================
    # PEMUKIMAN
    # =========================
    st.subheader("Lokasi Pemukiman")

    pemukiman = st.radio("Dekat pemukiman?", ["Ya","Tidak"])
    alasan_pemukiman = st.text_area("Alasan Pemukiman")

    bukti_pemukiman = st.file_uploader("Upload Bukti Pemukiman (minimal 3 foto)", accept_multiple_files=True)

    path_pemukiman_list = []
    if bukti_pemukiman:
        for file in bukti_pemukiman:
            path = os.path.join(UPLOAD_FOLDER, f"pemukiman_{datetime.now().timestamp()}_{file.name}")
            with open(path,"wb") as f:
                f.write(file.read())
            path_pemukiman_list.append(path)

    # =========================
    # SCORING
    # =========================
    ratio = qty/avg if avg > 0 else 0

    score = 0
    if ratio <= 1.1: score += 30
    if surat_file: score += 10
    if izin == "Ya": score += 10
    if pj == "Ya": score += 10
    if faskes == "Ya" and len(path_faskes_list) >= 3: score += 20
    if pemukiman == "Ya" and len(path_pemukiman_list) >= 3: score += 20

    kategori = "Wajar" if score >= 75 else "Tidak Wajar"

    st.metric("Skor", score)
    st.write("Kategori:", kategori)

    # =========================
    # SURAT PERNYATAAN
    # =========================
    surat_pernyataan_path = ""

    if score < 75:
        st.warning("⚠️ Skor < 75 wajib upload Surat Pernyataan")

        surat_pernyataan = st.file_uploader("Upload Surat Pernyataan", type=["pdf","jpg","png"])

        if surat_pernyataan:
            surat_pernyataan_path = os.path.join(
                UPLOAD_FOLDER,
                f"pernyataan_{datetime.now().timestamp()}_{surat_pernyataan.name}"
            )
            with open(surat_pernyataan_path,"wb") as f:
                f.write(surat_pernyataan.read())

    # =========================
    # VALIDASI
    # =========================
    errors = []

    if qty == 0: errors.append("Qty kosong")
    if no_pesanan.strip() == "": errors.append("No pesanan kosong")
    if izin == "Tidak" and alasan_izin.strip()=="": errors.append("Alasan perizinan wajib diisi")
    if pj == "Tidak" and alasan_pj.strip()=="": errors.append("Alasan PJ wajib diisi")
    if faskes == "Ya" and len(path_faskes_list) < 3: errors.append("Foto faskes minimal 3")
    if pemukiman == "Ya" and len(path_pemukiman_list) < 3: errors.append("Foto pemukiman minimal 3")
    if score < 75 and surat_pernyataan_path == "": errors.append("Wajib upload surat pernyataan")

    if errors:
        st.error(" | ".join(errors))

    # =========================
    # SUBMIT
    # =========================
    if st.button("Submit"):
        if not errors:

            conn.execute("""
            INSERT INTO analisa (
                tanggal,pelanggan,produk,
                qty_order,avg_qty,ratio,score,kategori,status,
                izin,alasan_izin,
                pj,alasan_pj,
                frekuensi,
                faskes,pemukiman,alasan,
                jenis_fasilitas,no_pesanan,
                bukti_faskes,bukti_pemukiman,
                surat_path,
                surat_pernyataan
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(
                datetime.now(),pelanggan,produk,
                qty,avg,ratio,score,kategori,"Pending",
                izin,alasan_izin,
                pj,alasan_pj,
                frekuensi,
                faskes,pemukiman,
                f"{alasan_faskes} | {alasan_pemukiman}",
                jenis,no_pesanan,
                ",".join(path_faskes_list),
                ",".join(path_pemukiman_list),
                surat_path,
                surat_pernyataan_path
            ))

            conn.commit()
            st.success("✅ Data berhasil disimpan & masuk approval")
# =========================
# Edit dan Status Data Submit (DETAIL + EDIT + DELETE)
# =========================
st.subheader("📊 Data Analisa")

df_analisa = pd.read_sql("SELECT * FROM analisa ORDER BY id DESC", conn)

if df_analisa.empty:
    st.info("Belum ada data analisa")
else:

    selected_id = st.selectbox("Pilih Data Analisa", df_analisa["id"].tolist())
    row = df_analisa[df_analisa["id"] == selected_id].iloc[0]

    status = row.get("status", "Pending")

    # =========================
    # STATUS
    # =========================
    if status == "Approved":
        st.success(f"Status: {status}")
    elif status == "Rejected":
        st.error(f"Status: {status}")
    else:
        st.warning(f"Status: {status}")

    # =========================
    # DETAIL DATA
    # =========================
    if st.checkbox("👁️ Lihat Detail"):

        st.write("### Informasi")
        st.write("Pelanggan:", row["pelanggan"])
        st.write("Produk:", row["produk"])
        st.write("Qty:", row["qty_order"])
        st.write("No Pesanan:", row["no_pesanan"])

        # =========================
        # PREVIEW FILE
        # =========================
        def show_file(path, title):
            if path and os.path.exists(path):
                ext = os.path.splitext(path)[1].lower()

                st.write(f"**{title}**")

                if ext in [".jpg",".jpeg",".png"]:
                    st.image(path)
                elif ext == ".pdf":
                    with open(path,"rb") as f:
                        st.download_button(f"Download {title}", f, file_name=os.path.basename(path))

        show_file(row.get("surat_path"), "Surat Pesanan")

        # Faskes
        if row.get("bukti_faskes"):
            for i,p in enumerate(row["bukti_faskes"].split(",")):
                show_file(p.strip(), f"Faskes {i+1}")

        # Pemukiman
        if row.get("bukti_pemukiman"):
            for i,p in enumerate(row["bukti_pemukiman"].split(",")):
                show_file(p.strip(), f"Pemukiman {i+1}")

        # Surat Pernyataan
        show_file(row.get("surat_pernyataan"), "Surat Pernyataan")

    # =========================
    # AKSI
    # =========================
    col1, col2 = st.columns(2)

    # DELETE
    with col1:
        if st.button("🗑️ Hapus Data"):
            conn.execute("DELETE FROM analisa WHERE id=?", (selected_id,))
            conn.commit()
            st.success("Data berhasil dihapus")
            st.rerun()

    # =========================
    # EDIT MODE
    # =========================
    with col2:

        allow_edit = status in ["Pending","Rejected"]

        if not allow_edit:
            st.info("Data Approved tidak bisa diedit")
        else:

            if st.button("✏️ Edit Data"):

                st.warning("Mode Edit Aktif")

                # =========================
                # FORM EDIT
                # =========================
                new_qty = st.number_input("Edit Qty", value=int(row["qty_order"] or 0))
                new_no = st.text_input("Edit No Pesanan", value=row["no_pesanan"] or "")

                # =========================
                # UPLOAD ULANG FILE
                # =========================
                st.write("### Upload Ulang (Opsional)")

                new_surat = st.file_uploader("Surat Pesanan Baru", type=["pdf","jpg","png"])

                new_faskes = st.file_uploader(
                    "Foto Faskes Baru",
                    accept_multiple_files=True
                )

                new_pemukiman = st.file_uploader(
                    "Foto Pemukiman Baru",
                    accept_multiple_files=True
                )

                new_pernyataan = st.file_uploader(
                    "Surat Pernyataan Baru",
                    type=["pdf","jpg","png"]
                )

                if st.button("💾 Simpan Perubahan"):

                    UPLOAD_FOLDER = "uploads"

                    # =========================
                    # SIMPAN FILE BARU (JIKA ADA)
                    # =========================
                    def save_file(file, prefix):
                        if not file:
                            return None
                        path = os.path.join(
                            UPLOAD_FOLDER,
                            f"{prefix}_{datetime.now().timestamp()}_{file.name}"
                        )
                        with open(path,"wb") as f:
                            f.write(file.read())
                        return path

                    surat_path = row["surat_path"]
                    if new_surat:
                        surat_path = save_file(new_surat,"surat")

                    # multi file
                    def save_multi(files, prefix, old):
                        if not files:
                            return old
                        paths = []
                        for f in files:
                            p = save_file(f, prefix)
                            paths.append(p)
                        return ",".join(paths)

                    faskes_path = save_multi(new_faskes,"faskes",row["bukti_faskes"])
                    pemukiman_path = save_multi(new_pemukiman,"pemukiman",row["bukti_pemukiman"])

                    pernyataan_path = row["surat_pernyataan"]
                    if new_pernyataan:
                        pernyataan_path = save_file(new_pernyataan,"pernyataan")

                    # =========================
                    # HITUNG ULANG
                    # =========================
                    avg_val = float(row["avg_qty"] or 0)
                    ratio_val = new_qty/avg_val if avg_val > 0 else 0

                    score_val = 0
                    if ratio_val <= 1.1:
                        score_val += 30

                    kategori_val = "Wajar" if score_val >= 75 else "Tidak Wajar"

                    # =========================
                    # UPDATE DB
                    # =========================
                    conn.execute("""
                        UPDATE analisa SET
                            qty_order=?,
                            no_pesanan=?,
                            ratio=?,
                            score=?,
                            kategori=?,
                            surat_path=?,
                            bukti_faskes=?,
                            bukti_pemukiman=?,
                            surat_pernyataan=?,
                            status='Pending'
                        WHERE id=?
                    """,(
                        new_qty,
                        new_no,
                        ratio_val,
                        score_val,
                        kategori_val,
                        surat_path,
                        faskes_path,
                        pemukiman_path,
                        pernyataan_path,
                        selected_id
                    ))

                    conn.commit()

                    st.success("Data berhasil diupdate")
                    st.rerun()

# =========================
# FUNGSI TAMPIL FILE (GLOBAL - WAJIB ADA)
# =========================
import base64
import os
import io
import streamlit as st
from PIL import Image, UnidentifiedImageError

def tampilkan_file(file_path, nama="File"):
    if not file_path:
        st.warning(f"{nama} kosong")
        return

    if not os.path.exists(file_path):
        st.error(f"{nama} tidak ditemukan")
        return

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        # =========================
        # PDF → PREVIEW
        # =========================
        if data[:4] == b"%PDF":
            base64_pdf = base64.b64encode(data).decode("utf-8")
            pdf_display = f"""
                <iframe 
                    src="data:application/pdf;base64,{base64_pdf}" 
                    width="100%" 
                    height="500px">
                </iframe>
            """
            st.markdown(pdf_display, unsafe_allow_html=True)

            # tombol download
            st.download_button(
                f"Download {nama}",
                data,
                file_name=os.path.basename(file_path)
            )

        # =========================
        # GAMBAR
        # =========================
        else:
            image = Image.open(io.BytesIO(data))
            st.image(image, caption=nama)

    except UnidentifiedImageError:
        st.error(f"{nama} bukan gambar valid")
    except Exception as e:
        st.error(f"Error {nama}: {e}")


# =========================
# MENU APPROVAL FINAL
# =========================
if menu == "Approval":

    st.title("✅ Approval + Preview Analisa")

    df = pd.read_sql("SELECT * FROM analisa ORDER BY id DESC", conn)

    if df.empty:
        st.warning("Tidak ada data")
        st.stop()

    for _, r in df.iterrows():

        with st.expander(f"📄 {r['pelanggan']} | {r['produk']} | Status: {r['status']}"):

            # =========================
            # A. INFORMASI
            # =========================
            st.subheader("A. Informasi")
            st.write("**Pelanggan:**", r["pelanggan"])
            st.write("**Produk:**", r["produk"])
            st.write("**Qty Order:**", r["qty_order"])

            # =========================
            # B. HASIL ANALISA
            # =========================
            st.subheader("B. Hasil Analisa")
            st.write("Skor:", r.get("score", 0))
            st.write("Kategori:", r.get("kategori", "-"))

            # =========================
            # C. LAMPIRAN
            # =========================
            st.subheader("C. Lampiran")

            # -------------------------
            # SURAT PESANAN
            # -------------------------
            if r.get("surat_path"):
                tampilkan_file(r["surat_path"], "Surat Pesanan")

            # -------------------------
            # FOTO FASKES (MULTI)
            # -------------------------
            if r.get("bukti_faskes"):
                st.write("📍 Foto Faskes:")
                paths = r["bukti_faskes"].split(",")

                cols = st.columns(3)
                for i, p in enumerate(paths):
                    if p.strip():
                        with cols[i % 3]:
                            tampilkan_file(p, f"Faskes {i+1}")

            # -------------------------
            # FOTO PEMUKIMAN (MULTI)
            # -------------------------
            if r.get("bukti_pemukiman"):
                st.write("🏠 Foto Pemukiman:")
                paths = r["bukti_pemukiman"].split(",")

                cols = st.columns(3)
                for i, p in enumerate(paths):
                    if p.strip():
                        with cols[i % 3]:
                            tampilkan_file(p, f"Pemukiman {i+1}")

            # -------------------------
            # SURAT PERNYATAAN
            # -------------------------
            if r.get("surat_pernyataan"):
                tampilkan_file(r["surat_pernyataan"], "Surat Pernyataan")

            st.divider()

            # =========================
            # APPROVAL ACTION
            # =========================
            if r["status"] == "Pending":

                colA, colB = st.columns(2)

                with colA:
                    if st.button(f"✅ Approve {r['id']}", key=f"appr{r['id']}"):
                        conn.execute(
                            "UPDATE analisa SET status='Approved' WHERE id=?",
                            (r["id"],)
                        )
                        conn.commit()
                        st.rerun()

                with colB:
                    if st.button(f"❌ Reject {r['id']}", key=f"rej{r['id']}"):
                        conn.execute(
                            "UPDATE analisa SET status='Rejected' WHERE id=?",
                            (r["id"],)
                        )
                        conn.commit()
                        st.rerun()

# =========================
# OUTPUT FORM FINAL (FULL FIXED)
# =========================
if menu=="Output":

    import os
    from datetime import datetime
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER

    st.title("📄 Output Form Analisa Kewajaran")

    PDF_FOLDER = "pdf"
    os.makedirs(PDF_FOLDER, exist_ok=True)

    df = pd.read_sql("SELECT * FROM analisa WHERE status='Approved'", conn)

    if df.empty:
        st.warning("Tidak ada data approved")
        st.stop()

    selected = st.selectbox("Pilih Data", df["id"].tolist())
    r = df[df["id"] == selected].iloc[0]

    # =========================
    # SAFE VALUE
    # =========================
    nama = r.get("pelanggan", "")
    jenis_val = r.get("jenis_fasilitas", "")
    no_pesanan_val = r.get("no_pesanan", "")
    produk_val = r.get("produk", "")
    qty_val = int(r.get("qty_order", 0) or 0)

    izin = r.get("izin", "-")
    alasan_izin = r.get("alasan_izin", "")
    pj = r.get("pj", "-")
    alasan_pj = r.get("alasan_pj", "")

    avg = float(r.get("avg_qty", 0) or 0)
    ratio = float(r.get("ratio", 0) or 0)

    faskes = r.get("faskes", "")
    pemukiman = r.get("pemukiman", "")

    # =========================
    # SPLIT ALASAN
    # =========================
    alasan_full = str(r.get("alasan", "") or "")
    alasan_faskes = "-"
    alasan_pemukiman = "-"

    if "|" in alasan_full:
        parts = alasan_full.split("|")
        if len(parts) >= 1:
            alasan_faskes = parts[0].strip() or "-"
        if len(parts) >= 2:
            alasan_pemukiman = parts[1].strip() or "-"
    else:
        alasan_pemukiman = alasan_full.strip() or "-"

    # =========================
    # INPUT UI
    # =========================
    st.subheader("A. Informasi Pemesanan")

    nama = st.text_input("Nama Fasilitas", nama)
    jenis = st.text_input("Jenis Fasilitas", jenis_val)
    no_pesanan = st.text_input("Tanggal & Nomor Pesanan", no_pesanan_val)
    produk = st.text_input("Produk", produk_val)
    qty = st.number_input("Qty", value=qty_val)

    evaluator_final = st.text_input("Nama Evaluator")

    # =========================
    # CHECKLIST
    # =========================
    st.subheader("B. Checklist Evaluasi")

    rows = []

    def tampil_sinkron(no, teks, jawaban, catatan):
        jawaban = jawaban if jawaban else "-"
        catatan = catatan if catatan else "-"
        st.markdown(f"**{no}. {teks}**")
        st.write(f"Jawaban: **{jawaban}**")
        st.write(f"Catatan: {catatan}")
        rows.append([no, teks, jawaban, catatan])

    def tampil_manual(no, teks):
        st.markdown(f"**{no}. {teks}**")
        col1,col2 = st.columns([1,3])
        with col1:
            jaw = st.radio("",["Ya","Tidak"], key=f"j{no}")
        with col2:
            note = st.text_input("Catatan", key=f"c{no}")
        rows.append([no, teks, jaw, note if note else "-"])

    tampil_sinkron(1,"Pelanggan memiliki Perizinan Berusaha yang masih berlaku", izin, alasan_izin)
    tampil_sinkron(2,"Penanggung Jawab fasilitas pemesan sesuai ketentuan peraturan perundang-undangan", pj, alasan_pj)
    tampil_manual(3,"Jumlah dan frekuensi pesanan sesuai kapasitas penyimpanan")

    lonjakan = "Ya" if ratio <= 1.5 else "Tidak"

    tampil_sinkron(
    4,
    "Tidak terdapat lonjakan jumlah dan frekuensi pesanan yang tidak wajar berdasarkan riwayat pesanan sebelumnya",
    lonjakan,
    f"{qty} vs {round(avg,2)}"
)
    tampil_manual(5,"Jenis obat sesuai kualifikasi fasilitas")
    tampil_manual(6,"Narkotika/Psikotropika/Prekursor/OOT sesuai kebutuhan")
    tampil_manual(7,"Pesanan antibiotik rasional tidak berpotensi mendorong resistensi antimikroba")
    tampil_manual(8,"Sediaan khusus dapat ditangani oleh fasilitas / terdapat praktik tenaga kesehatan")

    tampil_sinkron(9,"Lokasi dan kondisi pelayanan mendukung kewajaran pesanan", pemukiman, alasan_pemukiman)
    tampil_sinkron(10,"Tersedia praktik dokter/kerja sama fasyankes jika relevan", faskes, alasan_faskes)

    # =========================
    # KESIMPULAN
    # =========================
    st.subheader("C. Kesimpulan")

    keputusan = st.radio("Hasil Evaluasi", ["Disetujui","Ditolak"])
    catatan_akhir = st.text_area("Catatan Akhir")

    # =========================
    # PDF FORM (FINAL FIX)
    # =========================
    def generate_pdf():

        file_path = os.path.join(
            PDF_FOLDER,
            f"Form_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
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

        normal = ParagraphStyle(name='NormalSmall', fontSize=8, leading=10)
        header = ParagraphStyle(name='Header', fontSize=10, alignment=TA_CENTER)

        elements = []

        # KOP
        elements.append(Paragraph("<b>PT. KIMIA FARMA TRADING & DISTRIBUTION</b>", header))
        elements.append(Paragraph("Kantor Cabang Mataram", header))
        elements.append(Paragraph("Jl. I.G.M Jelantik Gosa No.10 X Mataram - NTB", header))
        elements.append(Paragraph("Telp (0370)624925", header))

        elements.append(Spacer(1,6))

        garis = Table([[""]], colWidths=[500])
        garis.setStyle([("LINEABOVE",(0,0),(-1,-1),1,colors.black)])
        elements.append(garis)

        elements.append(Spacer(1,6))
        elements.append(Paragraph("<b>FORM ANALISA KEWAJARAN</b>", styles["Title"]))
        elements.append(Spacer(1,6))

        # INFO
        info = Table([
            ["Fasilitas", nama],
            ["Jenis", jenis],
            ["No. Pesanan", no_pesanan],
            ["Produk", produk],
            ["Qty", qty],
            ["Evaluator", evaluator_final]
        ], colWidths=[100,320])

        info.setStyle([
            ("GRID",(0,0),(-1,-1),0.5,colors.black),
            ("FONTSIZE",(0,0),(-1,-1),8),
        ])

        elements.append(info)
        elements.append(Spacer(1,6))

        # TABLE
        data = [["No","Aspek","Jawaban","Catatan"]]

        for d in rows:
            data.append([
                d[0],
                Paragraph(d[1], normal),
                d[2],
                Paragraph(str(d[3]), normal)
            ])

        t = Table(data, colWidths=[25,210,50,135])
        t.setStyle([
            ("GRID",(0,0),(-1,-1),0.5,colors.black),
            ("BACKGROUND",(0,0),(-1,0),colors.grey),
            ("FONTSIZE",(0,0),(-1,-1),7),
        ])

        elements.append(t)

        elements.append(Spacer(1,6))
        elements.append(Paragraph(f"Hasil: <b>{keputusan}</b>", normal))
        elements.append(Paragraph(f"Catatan: {catatan_akhir}", normal))

        elements.append(Spacer(1,20))

        # TTD
        ttd = Table([
            ["Evaluator","","Penanggung Jawab"],
            ["","",""],
            ["(______________)","","(______________)"]
        ], colWidths=[180,60,180])

        elements.append(ttd)

        # BUILD WAJIB
        doc.build(elements)

        return file_path

    # =========================
    # PDF LAMPIRAN (RAPI)
    # =========================
    def generate_lampiran_pdf():

        file_path = os.path.join(
            PDF_FOLDER,
            f"Lampiran_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        )

        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()

        elements = []

        def add_page(section, title, path):
            try:
                if not path or not os.path.exists(path):
                    return

                ext = os.path.splitext(path)[1].lower()
                if ext not in [".jpg",".jpeg",".png"]:
                    return

                elements.append(Paragraph(f"<b>{section}</b>", styles["Heading2"]))
                elements.append(Spacer(1,5))
                elements.append(Paragraph(title, styles["Normal"]))
                elements.append(Spacer(1,5))
                elements.append(Image(path, width=16*cm, height=11*cm))
                elements.append(PageBreak())

            except:
                pass

        add_page("Surat Pesanan","Dokumen Pesanan", r.get("surat_path"))

        for i,p in enumerate((r.get("bukti_faskes") or "").split(",")):
            if p.strip():
                add_page("Foto Faskes", f"Faskes {i+1}", p)

        for i,p in enumerate((r.get("bukti_pemukiman") or "").split(",")):
            if p.strip():
                add_page("Foto Pemukiman", f"Pemukiman {i+1}", p)

        doc.build(elements)
        return file_path

    # =========================
    # BUTTON
    # =========================
    if st.button("📄 Generate PDF Form"):
        pdf_path = generate_pdf()
        with open(pdf_path,"rb") as f:
            st.download_button("⬇️ Download Form", f, file_name=os.path.basename(pdf_path))

    if st.button("🖼️ Generate PDF Lampiran"):
        lampiran_path = generate_lampiran_pdf()
        with open(lampiran_path,"rb") as f:
            st.download_button("⬇️ Download Lampiran", f, file_name=os.path.basename(lampiran_path))

    # Surat Pernyataan
    sp = r.get("surat_pernyataan")
    if sp and os.path.exists(sp):
        with open(sp,"rb") as f:
            st.download_button("📄 Download Surat Pernyataan", f, file_name=os.path.basename(sp))