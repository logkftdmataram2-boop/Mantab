import pandas as pd
import streamlit as st
import sqlite3

st.set_page_config(page_title="Monitoring Produk", layout="wide")

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

# buat tabel jika belum ada
c.execute('''
CREATE TABLE IF NOT EXISTS data (
    tanggal TEXT,
    pelanggan TEXT,
    produk TEXT,
    qty INTEGER
)
''')

# =========================
# USER LOGIN
# =========================
users = {
    "admin": {"password": "123", "role": "admin"},
    "user1": {"password": "123", "role": "user"},
    "user2": {"password": "123", "role": "user"},
}

st.sidebar.header("Login")

username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

role = None
if username in users and users[username]["password"] == password:
    role = users[username]["role"]
    st.sidebar.success(f"Login sebagai {role}")
else:
    st.sidebar.warning("Masukkan username & password")

# =========================
# UPLOAD EXCEL (ADMIN)
# =========================
if role == "admin":
    file = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)

        if all(col in df.columns for col in ["Tanggal","Nama Pelanggan","Produk","Qty"]):
            df["Tanggal"] = pd.to_datetime(df["Tanggal"])

            # simpan ke database
            for _, row in df.iterrows():
                c.execute("INSERT INTO data VALUES (?,?,?,?)",
                          (str(row["Tanggal"]), row["Nama Pelanggan"], row["Produk"], int(row["Qty"])))
            conn.commit()

            st.success("Data berhasil disimpan ke database!")
        else:
            st.error("Format Excel salah!")

# =========================
# AMBIL DATA DARI DATABASE
# =========================
df = pd.read_sql("SELECT * FROM data", conn)

if not df.empty and role is not None:

    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["Bulan"] = df["tanggal"].dt.to_period("M").astype(str)
    df["Triwulan"] = df["tanggal"].dt.to_period("Q").astype(str)

    st.title("📊 Monitoring Pemakaian Produk")

    # FILTER
    st.sidebar.header("Filter")

    pelanggan = st.sidebar.selectbox("Pelanggan", ["Semua"] + list(df["pelanggan"].unique()))
    produk = st.sidebar.selectbox("Produk", ["Semua"] + list(df["produk"].unique()))
    bulan = st.sidebar.selectbox("Bulan", ["Semua"] + list(df["Bulan"].unique()))
    triwulan = st.sidebar.selectbox("Triwulan", ["Semua"] + list(df["Triwulan"].unique()))

    filtered = df.copy()

    if pelanggan != "Semua":
        filtered = filtered[filtered["pelanggan"] == pelanggan]

    if produk != "Semua":
        filtered = filtered[filtered["produk"] == produk]

    if bulan != "Semua":
        filtered = filtered[filtered["Bulan"] == bulan]

    if triwulan != "Semua":
        filtered = filtered[filtered["Triwulan"] == triwulan]

    # DATA
    st.subheader("📋 Data")
    st.dataframe(filtered)

    # TOTAL
    st.metric("Total Pemakaian", filtered["qty"].sum())

    # BULAN
    st.subheader("📅 Pemakaian per Bulan")
    per_bulan = filtered.groupby(["Bulan","produk"])["qty"].sum().reset_index()
    st.bar_chart(per_bulan.pivot(index="Bulan", columns="produk", values="qty"))

    # TRIWULAN
    st.subheader("📆 Pemakaian per Triwulan")
    per_tri = filtered.groupby(["Triwulan","produk"])["qty"].sum().reset_index()
    st.bar_chart(per_tri.pivot(index="Triwulan", columns="produk", values="qty"))

else:
    st.info("Belum ada data / silakan login")