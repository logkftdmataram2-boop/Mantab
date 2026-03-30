import pandas as pd
import streamlit as st
import sqlite3
import os
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Monitoring Produk", layout="wide")

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
    st.session_state.login=False
    st.session_state.role=None

users={"admin":{"password":"123","role":"admin"},"user1":{"password":"123","role":"user"}}

if not st.session_state.login:
    st.title("🔐 Login")
    u=st.text_input("Username")
    p=st.text_input("Password",type="password")

    if st.button("Login"):
        if u in users and users[u]["password"]==p:
            st.session_state.login=True
            st.session_state.role=users[u]["role"]
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

    st.title("📊 Monitoring Produk")

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
# MENU ANALISA FINAL (ANTI ERROR)
# =========================
if menu == "Analisa":

    import os
    from datetime import datetime
    import pandas as pd
    import streamlit as st

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
        ("surat_path","TEXT")
    ]

    for col, typ in columns:
        ensure_column(conn,"analisa",col,typ)

    st.title("📋 Analisa Kewajaran")

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
    # SURAT
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
    bukti_faskes = st.file_uploader("Upload Bukti Faskes")

    path_faskes = ""
    if bukti_faskes:
        path_faskes = os.path.join(UPLOAD_FOLDER, f"faskes_{datetime.now().timestamp()}_{bukti_faskes.name}")
        with open(path_faskes,"wb") as f:
            f.write(bukti_faskes.read())

    # =========================
    # PEMUKIMAN
    # =========================
    st.subheader("Lokasi Pemukiman")

    pemukiman = st.radio("Dekat pemukiman?", ["Ya","Tidak"])
    alasan_pemukiman = st.text_area("Alasan Pemukiman")
    bukti_pemukiman = st.file_uploader("Upload Bukti Pemukiman")

    path_pemukiman = ""
    if bukti_pemukiman:
        path_pemukiman = os.path.join(UPLOAD_FOLDER, f"pemukiman_{datetime.now().timestamp()}_{bukti_pemukiman.name}")
        with open(path_pemukiman,"wb") as f:
            f.write(bukti_pemukiman.read())

    # =========================
    # SCORING
    # =========================
    ratio = qty/avg if avg>0 else 0

    score = 100
    if ratio > 1.25: score -= 30
    if not surat_file: score -= 20
    if izin == "Tidak": score -= 20
    if pj == "Tidak": score -= 20

    kategori = "Wajar" if score>=80 else "Perlu Review" if score>=60 else "Tidak Wajar"

    st.metric("Skor", score)
    st.write("Kategori:", kategori)

    # =========================
    # VALIDASI
    # =========================
    errors = []

    if qty == 0:
        errors.append("Qty kosong")

    if no_pesanan.strip() == "":
        errors.append("No pesanan kosong")

    if izin == "Tidak" and alasan_izin.strip()=="":
        errors.append("Alasan perizinan wajib diisi")

    if pj == "Tidak" and alasan_pj.strip()=="":
        errors.append("Alasan PJ wajib diisi")

    if errors:
        st.error(" | ".join(errors))

    # =========================
    # SUBMIT (FIX TOTAL)
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
                surat_path
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(
                datetime.now(),pelanggan,produk,
                qty,avg,ratio,score,kategori,"Pending",

                izin,alasan_izin,
                pj,alasan_pj,

                frekuensi,
                faskes,pemukiman,
                f"{alasan_faskes} | {alasan_pemukiman}",

                jenis,no_pesanan,
                path_faskes,path_pemukiman,
                surat_path
            ))

            conn.commit()
            st.success("✅ Data berhasil disimpan & masuk approval")

# =========================
# APPROVAL
# =========================
if menu=="Approval":

    st.title("Approval")

    df=pd.read_sql("SELECT * FROM analisa ORDER BY id DESC",conn)

    for _,r in df.iterrows():
        with st.expander(f"{r['pelanggan']} ({r['status']})"):

            st.write("Qty:",r["qty_order"])
            st.write("Kategori:",r["kategori"])

            if r["status"]=="Pending":
                if st.button(f"Approve {r['id']}"):
                    conn.execute("UPDATE analisa SET status='Approved' WHERE id=?",(r["id"],))
                    conn.commit()
                    st.rerun()

                if st.button(f"Reject {r['id']}"):
                    conn.execute("UPDATE analisa SET status='Rejected' WHERE id=?",(r["id"],))
                    conn.commit()
                    st.rerun()

# =========================
# OUTPUT FORM FINAL (FIXED & FINAL)
# =========================
if menu=="Output":

    import os
    from io import BytesIO
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
    alasan = r.get("alasan", "")

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

    # 1
    tampil_sinkron(1,
    "Pelanggan memiliki Perizinan Berusaha yang masih berlaku",
    izin, alasan_izin)

    # 2
    tampil_sinkron(2,
    "Penanggung Jawab fasilitas pemesan sesuai ketentuan peraturan perundang-undangan",
    pj, alasan_pj)

    # 3
    tampil_manual(3,
    "Jumlah dan frekuensi pesanan sesuai kapasitas penyimpanan")

    # 4
    lonjakan = "Ya" if ratio <= 1.5 else "Tidak"
    cat_lonjakan = f"{qty} dari rata-rata {round(avg,2)}"

    tampil_sinkron(4,
    "Tidak terdapat lonjakan jumlah dan frekuensi pesanan yang tidak wajar berdasarkan riwayat pesanan sebelumnya",
    lonjakan,
    cat_lonjakan)

    # 5–8
    tampil_manual(5, "Jenis obat sesuai kualifikasi fasilitas")
    tampil_manual(6, "Narkotika/Psikotropika/Prekursor/OOT sesuai kebutuhan")
    tampil_manual(7, "Pesanan antibiotik rasional tidak berpotensi mendorong resistensi antimikroba")
    tampil_manual(8, "Sediaan khusus dapat ditangani oleh fasilitas / terdapat praktik tenaga kesehatan")

    # 9
    lokasi = "Ya" if (pemukiman=="Ya") else "Tidak"

    tampil_sinkron(9,
    "Lokasi dan kondisi pelayanan mendukung kewajaran pesanan",
    lokasi,
    alasan)

    # 10
    Tersedia = "Ya" if (faskes=="Ya") else "Tidak"

    tampil_sinkron(10,
    "Tersedia praktik dokter/kerja sama fasyankes jika relevan",
    lokasi,
    alasan)

    # =========================
    # KESIMPULAN
    # =========================
    st.subheader("C. Kesimpulan")

    keputusan = st.radio("Hasil Evaluasi", ["Disetujui","Ditolak"])
    catatan_akhir = st.text_area("Catatan Akhir")

    # =========================
    # PDF GENERATE (FINAL FIX)
    # =========================
    def generate_pdf():

        file_path = os.path.join(PDF_FOLDER, f"Form_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")

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

        # =========================
        # KOP SURAT
        # =========================
        elements.append(Paragraph("<b>PT. KIMIA FARMA TRADING & DISTRIBUTION</b>", header))
        elements.append(Paragraph("Kantor Cabang Mataram", header))
        elements.append(Paragraph(
            "Jl. I.G.M Jelantik Gosa No.10 X Mataram - NTB<br/>Telp (0370)624925",
            header
        ))

        elements.append(Spacer(1,6))

        garis = Table([[""]], colWidths=[500])
        garis.setStyle([("LINEABOVE",(0,0),(-1,-1),1,colors.black)])
        elements.append(garis)

        elements.append(Spacer(1,6))
        elements.append(Paragraph("<b>FORM ANALISA KEWAJARAN</b>", styles["Title"]))
        elements.append(Spacer(1,6))

        # =========================
        # INFO
        # =========================
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
            ("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ])

        elements.append(info)
        elements.append(Spacer(1,6))

        # =========================
        # CHECKLIST TABLE
        # =========================
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
            ("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
        ])

        elements.append(t)

        elements.append(Spacer(1,6))
        elements.append(Paragraph(f"Hasil: <b>{keputusan}</b>", normal))
        elements.append(Paragraph(f"Catatan: {catatan_akhir}", normal))

        elements.append(Spacer(1,20))

        # =========================
        # TTD
        # =========================
        ttd = Table([
            ["Evaluator","","Penanggung Jawab"],
            ["","",""],
            ["(______________)","","(______________)"]
        ], colWidths=[180,40,180])

        ttd.setStyle([
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("LINEABOVE",(0,2),(0,2),0.5,colors.black),
            ("LINEABOVE",(2,2),(2,2),0.5,colors.black),
        ])

        elements.append(ttd)

        # =========================
        # LAMPIRAN
        # =========================
        elements.append(PageBreak())

        def add_img(title, path):
            try:
                if path and os.path.exists(path):
                    elements.append(Paragraph(f"<b>{title}</b>", styles["Heading3"]))
                    elements.append(Spacer(1,5))
                    elements.append(Image(path, width=14*cm, height=9*cm))
                    elements.append(Spacer(1,6))
            except:
                pass

        add_img("Surat Pesanan", r.get("surat_path"))
        add_img("Faskes Terdekat", r.get("bukti_faskes"))
        add_img("Foto Pemukiman Terdekat", r.get("bukti_pemukiman"))

        doc.build(elements)

        return file_path

    if st.button("📄 Generate PDF"):
        try:
            pdf_path = generate_pdf()
            with open(pdf_path,"rb") as f:
                st.download_button("⬇️ Download PDF", f, file_name=os.path.basename(pdf_path))
        except Exception as e:
            st.error(f"Gagal generate PDF: {e}")