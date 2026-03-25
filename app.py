import pandas as pd
import streamlit as st

st.set_page_config(page_title="Monitoring Produk", layout="wide")

st.title("📊 Monitoring Pemakaian Produk")

# Upload file
file = st.file_uploader("Upload File Excel", type=["xlsx"])

if file:
    df = pd.read_excel(file)

    # Validasi kolom
    required_cols = ["Tanggal", "Nama Pelanggan", "Produk", "Qty"]
    if not all(col in df.columns for col in required_cols):
        st.error("Format kolom tidak sesuai!")
    else:
        # Format data
        df["Tanggal"] = pd.to_datetime(df["Tanggal"])
        df["Bulan"] = df["Tanggal"].dt.to_period("M").astype(str)

        # Sidebar filter
        st.sidebar.header("Filter")

        pelanggan = st.sidebar.selectbox(
            "Pilih Pelanggan", ["Semua"] + list(df["Nama Pelanggan"].unique())
        )

        bulan = st.sidebar.selectbox(
            "Pilih Bulan", ["Semua"] + list(df["Bulan"].unique())
        )

        produk = st.sidebar.selectbox(
            "Pilih Produk", ["Semua"] + list(df["Produk"].unique())
        )

        # Filter data
        filtered = df.copy()

        if pelanggan != "Semua":
            filtered = filtered[filtered["Nama Pelanggan"] == pelanggan]

        if bulan != "Semua":
            filtered = filtered[filtered["Bulan"] == bulan]

        if produk != "Semua":
            filtered = filtered[filtered["Produk"] == produk]

        # Tampilkan data
        st.subheader("📋 Data Pemakaian")
        st.dataframe(filtered, use_container_width=True)

        # Total
        total = filtered["Qty"].sum()
        st.metric("Total Pemakaian", total)

        # Rekap per produk
        st.subheader("📦 Rekap per Produk")
        rekap = filtered.groupby("Produk")["Qty"].sum().reset_index()
        st.dataframe(rekap, use_container_width=True)

        # Grafik
        st.subheader("📈 Grafik Pemakaian")
        st.bar_chart(rekap.set_index("Produk"))

        # Download hasil
        st.subheader("⬇️ Download Data")
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            csv,
            "data_pemakaian.csv",
            "text/csv"
        )