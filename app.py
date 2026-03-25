import pandas as pd
import streamlit as st

st.set_page_config(page_title="Monitoring Produk", layout="wide")

st.title("📊 Monitoring Pemakaian Produk")

# =========================
# LOGIN SEDERHANA
# =========================
st.sidebar.header("Login")

user = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

# akun sederhana
ADMIN_USER = "admin"
ADMIN_PASS = "123"

is_admin = (user == ADMIN_USER and password == ADMIN_PASS)

# =========================
# SESSION DATA (biar bisa dilihat user lain)
# =========================
if "data" not in st.session_state:
    st.session_state.data = None

# =========================
# UPLOAD (HANYA ADMIN)
# =========================
if is_admin:
    st.sidebar.success("Login sebagai ADMIN")

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

else:
    st.sidebar.warning("Login sebagai USER (hanya lihat data)")

# =========================
# TAMPILKAN DATA
# =========================
df = st.session_state.data

if df is not None:

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

    # =========================
    # DATA
    # =========================
    st.subheader("📋 Data")
    st.dataframe(filtered, use_container_width=True)

    # =========================
    # TOTAL
    # =========================
    st.metric("Total Pemakaian", filtered["Qty"].sum())

    # =========================
    # PEMAKAIAN PER BULAN
    # =========================
    st.subheader("📅 Pemakaian per Bulan")

    per_bulan = filtered.groupby(["Bulan", "Produk"])["Qty"].sum().reset_index()

    st.dataframe(per_bulan, use_container_width=True)
    st.bar_chart(per_bulan.pivot(index="Bulan", columns="Produk", values="Qty"))

    # =========================
    # PEMAKAIAN PER TRIWULAN
    # =========================
    st.subheader("📆 Pemakaian per Triwulan")

    per_triwulan = filtered.groupby(["Triwulan", "Produk"])["Qty"].sum().reset_index()

    st.dataframe(per_triwulan, use_container_width=True)
    st.bar_chart(per_triwulan.pivot(index="Triwulan", columns="Produk", values="Qty"))

    # =========================
    # DOWNLOAD
    # =========================
    st.subheader("⬇️ Download Data")

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "data.csv", "text/csv")

else:
    st.info("Belum ada data. Silakan admin upload file.")