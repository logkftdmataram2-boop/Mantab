import pandas as pd
import streamlit as st

st.title("Monitoring Pemakaian Produk")

file = st.file_uploader("Upload Excel", type=["xlsx"])

if file:
    df = pd.read_excel(file)

    df["Tanggal"] = pd.to_datetime(df["Tanggal"])
    df["Bulan"] = df["Tanggal"].dt.to_period("M").astype(str)

    pelanggan = st.selectbox("Pilih Pelanggan", df["Nama Pelanggan"].unique())
    bulan = st.selectbox("Pilih Bulan", df["Bulan"].unique())

    data = df[(df["Nama Pelanggan"] == pelanggan) & (df["Bulan"] == bulan)]

    st.write("Data:")
    st.dataframe(data)

    st.write("Total Pemakaian:")
    st.write(data["Qty"].sum())