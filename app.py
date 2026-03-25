import pandas as pd
import streamlit as st

st.set_page_config(page_title="Monitoring Produk", layout="wide")

st.title("📊 Monitoring Pemakaian Produk")

# =========================
# DATABASE USER SEDERHANA
# =========================
users = {
    "admin": {"password": "123", "role": "admin"},
    "user1": {"password": "123", "role": "user"},
    "user2": {"password": "123", "role": "user"},
}

# =========================
# LOGIN
# =========================
st.sidebar.header("Login")

username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

role = None

if username in users and users[username]["password"] == password:
    role = users[username]["role"]
    st.sidebar.success(f"Login sebagai {role.upper()}")
else:
    st.sidebar.warning("Masukkan username & password")

# =========================
# SESSION DATA
# =========================
if "data" not in st.session_state:
    st.session_state.data = None

# =========================
# UPLOAD (HANYA ADMIN)
# =========================
if role == "admin":
    file = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)

        required_cols = ["Tanggal", "Nama Pelanggan", "Produk", "Qty"]

        if not all(col in df.columns for col in required_cols):
            st.error("Format kolom salah!")
        else:
            df["Tanggal"] = pd.to_datetime(df["Tanggal"])
            df["Bulan"] = df["Tanggal"].dt.to_period("M").astype(str)
            df["Triwulan"] = df["Tanggal"].dt.to_period("Q").astype(str)

            st.session_state.data = df
            st.success("Data berhasil diupload!")

# =========================
# TAMPILKAN DATA
# =========================
df = st.session_state.data

if df is not None and role is not None:

    st.sidebar.header("Filter")

    pelanggan = st.sidebar.selectbox(
        "Pelanggan", ["Semua"] + list(df["Nama Pelanggan"].unique())
    )

    produk = st.sidebar.selectbox(
        "Produk", ["Semua"] + list(df["Produk"].unique())
    )

    bulan = st.sidebar.selectbox(
        "Bulan", ["Semua"] + list(df["Bulan"].unique())
    )

    triwulan = st.sidebar.selectbox(
        "Triwulan", ["Semua"] + list(df["Triwulan"].unique())
    )

    filtered = df.copy()

    if pelanggan != "Semua":
        filtered = filtered[filtered["Nama Pelanggan"] == pelanggan]

    if produk != "Semua":
        filtered = filtered[filtered["Produk"] == produk]

    if bulan != "Semua":
        filtered = filtered[filtered["Bulan"] == bulan]

    if triwulan != "Semua":
        filtered = filtered[filtered["Triwulan"] == triwulan]

    st.subheader("📋 Data")
    st.dataframe(filtered, use_container_width=True)

    st.metric("Total Pemakaian", filtered["Qty"].sum())

    # Rekap Bulanan
    st.subheader("📅 Pemakaian per Bulan")
    per_bulan = filtered.groupby(["Bulan", "Produk"])["Qty"].sum().reset_index()
    st.bar_chart(per_bulan.pivot(index="Bulan", columns="Produk", values="Qty"))

    # Rekap Triwulan
    st.subheader("📆 Pemakaian per Triwulan")
    per_triwulan = filtered.groupby(["Triwulan", "Produk"])["Qty"].sum().reset_index()
    st.bar_chart(per_triwulan.pivot(index="Triwulan", columns="Produk", values="Qty"))

else:
    st.info("Silakan login terlebih dahulu atau tunggu admin upload data.")