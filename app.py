import pandas as pd
import streamlit as st
import sqlite3

st.set_page_config(page_title="Monitoring Produk", layout="wide")

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS data (
    tanggal TEXT,
    pelanggan TEXT,
    produk TEXT,
    qty INTEGER
)
''')

# =========================
# SESSION LOGIN
# =========================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = None

# =========================
# USER
# =========================
users = {
    "admin": {"password": "123", "role": "admin"},
    "user1": {"password": "123", "role": "user"},
}

# =========================
# LOGIN
# =========================
if not st.session_state.login:
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.login = True
            st.session_state.role = users[username]["role"]
            st.success("Login berhasil")
            st.rerun()
        else:
            st.error("Login gagal")

else:
    st.sidebar.success(f"Login sebagai {st.session_state.role}")

    # LOGOUT
    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    # =========================
    # ADMIN UPLOAD
    # =========================
    if st.session_state.role == "admin":
        st.sidebar.header("Admin Menu")

        file = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])

        if file:
            df_upload = pd.read_excel(file)

            if all(col in df_upload.columns for col in ["Tanggal","Nama Pelanggan","Produk","Qty"]):
                df_upload["Tanggal"] = pd.to_datetime(df_upload["Tanggal"])

                existing = pd.read_sql("SELECT * FROM data", conn)

                for _, row in df_upload.iterrows():
                    if not ((existing["tanggal"] == str(row["Tanggal"])) &
                            (existing["pelanggan"] == row["Nama Pelanggan"]) &
                            (existing["produk"] == row["Produk"])).any():

                        c.execute("INSERT INTO data VALUES (?,?,?,?)",
                                  (str(row["Tanggal"]), row["Nama Pelanggan"], row["Produk"], int(row["Qty"])))

                conn.commit()
                st.success("Data berhasil ditambahkan (tanpa duplikat)")
            else:
                st.error("Format Excel salah!")

        # HAPUS DATA
        if st.sidebar.button("Hapus Semua Data"):
            c.execute("DELETE FROM data")
            conn.commit()
            st.warning("Semua data dihapus!")

        # BACKUP
        with open("data.db", "rb") as f:
            st.sidebar.download_button("Download Backup DB", f, "backup.db")

    # =========================
    # LOAD DATA
    # =========================
    df = pd.read_sql("SELECT * FROM data", conn)

    if not df.empty:
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        df["Bulan"] = df["tanggal"].dt.to_period("M").astype(str)
        df["Triwulan"] = df["tanggal"].dt.to_period("Q").astype(str)

        st.title("📊 Dashboard Monitoring")

        # =========================
        # FILTER (HANYA 2)
        # =========================
        pelanggan = st.sidebar.selectbox("Pelanggan", ["Semua"] + list(df["pelanggan"].unique()))
        produk = st.sidebar.selectbox("Produk", ["Semua"] + list(df["produk"].unique()))

        filtered = df.copy()

        if pelanggan != "Semua":
            filtered = filtered[filtered["pelanggan"] == pelanggan]

        if produk != "Semua":
            filtered = filtered[filtered["produk"] == produk]

        # =========================
        # TOTAL
        # =========================
        st.metric("Total Pemakaian", filtered["qty"].sum())

        # =========================
        # RATA-RATA BULAN
        # =========================
        st.subheader("📅 Rata-rata Pemakaian Bulanan")

        bulanan = filtered.groupby("Bulan")["qty"].sum().reset_index()
        rata_bulanan = bulanan["qty"].mean()

        st.metric("Rata-rata Bulanan", round(rata_bulanan, 2))
        st.line_chart(bulanan.set_index("Bulan"))

        # =========================
        # RATA-RATA TRIWULAN
        # =========================
        st.subheader("📆 Rata-rata Pemakaian Triwulan")

        tri = filtered.groupby("Triwulan")["qty"].sum().reset_index()
        rata_tri = tri["qty"].mean()

        st.metric("Rata-rata Triwulan", round(rata_tri, 2))
        st.bar_chart(tri.set_index("Triwulan"))

        # =========================
        # GROWTH BULANAN
        # =========================
        st.subheader("📈 Growth Bulanan (%)")

        bulanan_sorted = bulanan.sort_values("Bulan")
        bulanan_sorted["growth"] = bulanan_sorted["qty"].pct_change() * 100

        st.metric("Rata-rata Growth (%)", round(bulanan_sorted["growth"].mean(), 2))
        st.line_chart(bulanan_sorted.set_index("Bulan")["growth"])

        # =========================
        # RATA-RATA 2 TERAKHIR
        # =========================
        st.subheader("⚡ Rata-rata 2 Transaksi Terakhir")

        last2 = filtered.sort_values("tanggal", ascending=False).head(2)
        st.metric("Rata-rata 2 Terakhir", round(last2["qty"].mean(), 2))

        # =========================
        # RATA-RATA FLEX
        # =========================
        st.subheader("⏳ Rata-rata Berdasarkan Periode")

        n = st.number_input("Jumlah transaksi terakhir", min_value=1, value=3)

        last_n = filtered.sort_values("tanggal", ascending=False).head(n)
        st.metric(f"Rata-rata {n} Transaksi", round(last_n["qty"].mean(), 2))

        # =========================
        # DATA
        # =========================
        st.subheader("📋 Data")
        st.dataframe(filtered)

    else:
        st.info("Belum ada data")