import pandas as pd
import streamlit as st
import sqlite3

st.set_page_config(page_title="Monitoring Produk", layout="wide")

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

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
    # FILTER (HANYA PELANGGAN & PRODUK)
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
    # RATA-RATA PER BULAN
    # =========================
    st.subheader("📅 Rata-rata Pemakaian per Bulan")

    bulanan = filtered.groupby("Bulan")["qty"].sum().reset_index()
    rata_bulanan = bulanan["qty"].mean()

    st.metric("Rata-rata per Bulan", round(rata_bulanan, 2))
    st.line_chart(bulanan.set_index("Bulan"))

    # =========================
    # RATA-RATA PER TRIWULAN
    # =========================
    st.subheader("📆 Rata-rata Pemakaian per Triwulan")

    tri = filtered.groupby("Triwulan")["qty"].sum().reset_index()
    rata_tri = tri["qty"].mean()

    st.metric("Rata-rata per Triwulan", round(rata_tri, 2))
    st.bar_chart(tri.set_index("Triwulan"))

    # =========================
    # PERKEMBANGAN BULAN KE BULAN
    # =========================
    st.subheader("📈 Rata-rata Perkembangan Bulanan")

    bulanan_sorted = bulanan.sort_values("Bulan")
    bulanan_sorted["growth"] = bulanan_sorted["qty"].pct_change() * 100

    avg_growth = bulanan_sorted["growth"].mean()

    st.metric("Rata-rata Growth (%)", round(avg_growth, 2))
    st.line_chart(bulanan_sorted.set_index("Bulan")["growth"])

    # =========================
    # RATA-RATA 2 TRANSAKSI TERAKHIR
    # =========================
    st.subheader("⚡ Rata-rata 2 Pengambilan Terakhir")

    last2 = filtered.sort_values("tanggal", ascending=False).head(2)
    avg_last2 = last2["qty"].mean()

    st.metric("Rata-rata 2 Transaksi Terakhir", round(avg_last2, 2))

    # =========================
    # RATA-RATA PERIODE (CUSTOM)
    # =========================
    st.subheader("⏳ Rata-rata Berdasarkan Periode")

    n = st.number_input("Jumlah transaksi terakhir", min_value=1, value=3)

    last_n = filtered.sort_values("tanggal", ascending=False).head(n)
    avg_n = last_n["qty"].mean()

    st.metric(f"Rata-rata {n} Transaksi Terakhir", round(avg_n, 2))

    # =========================
    # DATA
    # =========================
    st.subheader("📋 Data")
    st.dataframe(filtered)

else:
    st.info("Belum ada data")