# ============================================================
# PERBAIKAN MENU PENOLAKAN PESANAN - VERSI MANDIRI
# ============================================================
# Konsep:
# 1. Tidak menggunakan template PDF lagi.
# 2. Surat dibuat langsung dari ReportLab.
# 3. Data penolakan disimpan pada tabel "penolakan".
# 4. Tidak mengubah tabel "analisa".
# 5. Nama sarana dapat dipilih dari tabel data atau ditulis sendiri.
# 6. Produk dapat dipilih dari database atau ditulis sendiri.
# 7. Maksimal 5 produk.
# 8. Surat yang sudah dibuat masuk Riwayat.
# 9. Riwayat dapat dilihat, download, preview, dan dihapus.
#
# CARA PEMASANGAN:
# - Tambahkan bagian DATABASE PENOLAKAN di bawah fungsi get_conn()
#   setelah "conn = get_conn()".
# - Hapus/Buang seluruh blok lama:
#       # MENU PENOLAKAN PESANAN
#   sampai akhir blok tersebut.
# - Ganti dengan blok MENU PENOLAKAN PESANAN di bawah.
#
# Library:
#   pip install reportlab
# ============================================================


# ============================================================
# DATABASE PENOLAKAN PESANAN
# Letakkan setelah:
# conn = get_conn()
# ============================================================

conn.execute("""
CREATE TABLE IF NOT EXISTS penolakan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal_dibuat TEXT,
    nama_sarana TEXT,
    nomor_sp TEXT,
    tanggal_sp TEXT,
    tanggal_surat TEXT,
    alasan TEXT,
    produk_data TEXT,
    pdf_path TEXT
)
""")
conn.commit()


# ============================================================
# MENU PENOLAKAN PESANAN - STANDALONE + RIWAYAT + AUTO MIGRATION
# ============================================================

if menu == "Penolakan Pesanan":

    import os
    import base64
    import pandas as pd
    import streamlit as st
    from datetime import datetime

    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle
    )
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle
    )
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import cm


    # ========================================================
    # KONFIGURASI
    # ========================================================

    OUTPUT_FOLDER = "pdf"
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


    # ========================================================
    # DATABASE PENOLAKAN
    # TERPISAH DARI TABEL ANALISA
    # ========================================================

    def init_penolakan_database():

        # ----------------------------------------------------
        # Buat tabel jika belum ada
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS penolakan_pesanan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal_surat TEXT,
                tanggal_sp TEXT,
                nama_sarana TEXT,
                nomor_sp TEXT,
                alasan_penolakan TEXT,
                produk_data TEXT,
                file_pdf TEXT,
                dibuat_pada TEXT
            )
        """)

        conn.commit()

        # ----------------------------------------------------
        # AUTO MIGRATION
        # ----------------------------------------------------

        kolom_wajib = {
            "tanggal_surat": "TEXT",
            "tanggal_sp": "TEXT",
            "nama_sarana": "TEXT",
            "nomor_sp": "TEXT",
            "alasan_penolakan": "TEXT",
            "produk_data": "TEXT",
            "file_pdf": "TEXT",
            "dibuat_pada": "TEXT"
        }

        kolom_sekarang = [
            x[1]
            for x in conn.execute(
                "PRAGMA table_info(penolakan_pesanan)"
            ).fetchall()
        ]

        for nama_kolom, tipe in kolom_wajib.items():

            if nama_kolom not in kolom_sekarang:

                conn.execute(
                    f"""
                    ALTER TABLE penolakan_pesanan
                    ADD COLUMN {nama_kolom} {tipe}
                    """
                )

        conn.commit()


    # Jalankan database
    init_penolakan_database()


    # ========================================================
    # JUDUL
    # ========================================================

    st.title("📄 Surat Penolakan Pesanan")


    # ========================================================
    # TAB
    # ========================================================

    tab_buat, tab_riwayat = st.tabs([
        "📝 Buat Surat Penolakan",
        "📚 Riwayat Surat Penolakan"
    ])


    # ========================================================
    # TAB 1 - BUAT SURAT
    # ========================================================

    with tab_buat:

        st.subheader("A. Informasi Surat")


        # ----------------------------------------------------
        # NAMA SARANA DARI DATABASE
        # ----------------------------------------------------

        try:

            df_sarana = pd.read_sql(
                """
                SELECT DISTINCT pelanggan
                FROM data
                WHERE pelanggan IS NOT NULL
                AND TRIM(pelanggan) <> ''
                ORDER BY pelanggan
                """,
                conn
            )

            daftar_sarana = (
                df_sarana["pelanggan"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

        except Exception:

            daftar_sarana = []


        pilihan_sarana = st.selectbox(
            "Nama Sarana",
            ["-- Pilih Sarana --",
             "✍️ Tulis Sendiri"] + daftar_sarana
        )


        if pilihan_sarana == "✍️ Tulis Sendiri":

            nama_sarana = st.text_input(
                "Masukkan Nama Sarana"
            )

        elif pilihan_sarana == "-- Pilih Sarana --":

            nama_sarana = ""

        else:

            nama_sarana = pilihan_sarana


        # ----------------------------------------------------
        # NOMOR SP
        # ----------------------------------------------------

        nomor_sp = st.text_input(
            "Nomor Surat Pesanan",
            placeholder="Contoh: SP/001/IX/2026"
        )


        # ----------------------------------------------------
        # TANGGAL SP
        # ----------------------------------------------------

        tanggal_sp = st.date_input(
            "Tanggal Surat Pesanan",
            value=datetime.now().date(),
            format="DD/MM/YYYY"
        )


        # ----------------------------------------------------
        # TANGGAL SURAT
        # ----------------------------------------------------

        tanggal_surat = st.date_input(
            "Tanggal Surat Penolakan",
            value=datetime.now().date(),
            format="DD/MM/YYYY"
        )


        st.divider()


        # ====================================================
        # PRODUK
        # ====================================================

        st.subheader("B. Item Pesanan")

        st.caption(
            "Maksimal 5 produk. Nama produk dapat dipilih "
            "dari database atau ditulis sendiri."
        )


        # ----------------------------------------------------
        # AMBIL PRODUK DARI DATABASE
        # ----------------------------------------------------

        try:

            df_produk = pd.read_sql(
                """
                SELECT DISTINCT produk
                FROM data
                WHERE produk IS NOT NULL
                AND TRIM(produk) <> ''
                ORDER BY produk
                """,
                conn
            )

            daftar_produk = (
                df_produk["produk"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

        except Exception:

            daftar_produk = []


        produk_data = []


        # ----------------------------------------------------
        # 5 BARIS PRODUK
        # ----------------------------------------------------

        for i in range(1, 6):

            st.markdown(f"### Produk {i}")

            pilihan_produk = st.selectbox(
                f"Nama Produk / Barang {i}",
                [
                    "-- Kosong --",
                    "✍️ Tulis Sendiri"
                ] + daftar_produk,
                key=f"pilihan_produk_{i}"
            )


            if pilihan_produk == "✍️ Tulis Sendiri":

                nama_produk = st.text_input(
                    f"Tulis Nama Produk {i}",
                    key=f"produk_manual_{i}"
                )

            elif pilihan_produk == "-- Kosong --":

                nama_produk = ""

            else:

                nama_produk = pilihan_produk


            col1, col2 = st.columns(2)


            with col1:

                jumlah_pesanan = st.text_input(
                    f"Jumlah Pesanan {i}",
                    key=f"qty_pesanan_{i}",
                    placeholder="Contoh: 100"
                )


            with col2:

                jumlah_faktur = st.text_input(
                    f"Jumlah Difakturkan {i}",
                    key=f"qty_faktur_{i}",
                    placeholder="Contoh: 50"
                )


            produk_data.append({
                "produk": nama_produk,
                "pesanan": jumlah_pesanan,
                "faktur": jumlah_faktur
            })


        st.divider()


        # ====================================================
        # ALASAN
        # ====================================================

        st.subheader("C. Alasan Penolakan")


        alasan_ditolak = st.text_area(
            "Alasan tidak dapat melayani pesanan",
            placeholder=(
                "Contoh: Jumlah pesanan tidak sesuai "
                "dengan hasil analisa kewajaran..."
            ),
            height=120
        )


        # ====================================================
        # PREVIEW DATA
        # ====================================================

        st.subheader("D. Preview Data")


        st.write(
            f"**Sarana:** {nama_sarana or '-'}"
        )

        st.write(
            f"**Nomor SP:** {nomor_sp or '-'}"
        )

        st.write(
            f"**Tanggal SP:** "
            f"{tanggal_sp.strftime('%d/%m/%Y')}"
        )

        st.write(
            f"**Tanggal Surat:** "
            f"{tanggal_surat.strftime('%d/%m/%Y')}"
        )


        # ----------------------------------------------------
        # TABEL PREVIEW
        # ----------------------------------------------------

        preview_produk = []

        for i, item in enumerate(produk_data, start=1):

            if item["produk"].strip():

                preview_produk.append({
                    "No": i,
                    "Nama Produk": item["produk"],
                    "Jumlah Pesanan": item["pesanan"],
                    "Jumlah Difakturkan": item["faktur"]
                })


        if preview_produk:

            st.dataframe(
                pd.DataFrame(preview_produk),
                use_container_width=True,
                hide_index=True
            )


        # ====================================================
        # VALIDASI
        # ====================================================

        errors = []


        if not nama_sarana.strip():

            errors.append(
                "Nama sarana wajib diisi."
            )


        if not nomor_sp.strip():

            errors.append(
                "Nomor SP wajib diisi."
            )


        if not any(
            x["produk"].strip()
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

            st.warning(
                "\n".join(
                    [f"• {x}" for x in errors]
                )
            )


        # ====================================================
        # GENERATE PDF
        # ====================================================

        def generate_pdf_penolakan():

            waktu = datetime.now()

            nama_file = (
                "Surat_Penolakan_"
                + nomor_sp.replace("/", "_")
                .replace("\\", "_")
                .replace(" ", "_")
                + "_"
                + waktu.strftime("%Y%m%d%H%M%S")
                + ".pdf"
            )


            output_path = os.path.join(
                OUTPUT_FOLDER,
                nama_file
            )


            # ------------------------------------------------
            # PDF
            # ------------------------------------------------

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=1.5 * cm,
                leftMargin=1.5 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm
            )


            styles = getSampleStyleSheet()


            normal = ParagraphStyle(
                "NormalCustom",
                parent=styles["Normal"],
                fontSize=9,
                leading=12
            )


            center = ParagraphStyle(
                "Center",
                parent=normal,
                alignment=TA_CENTER
            )


            title = ParagraphStyle(
                "TitleCustom",
                parent=styles["Title"],
                fontSize=14,
                leading=18,
                alignment=TA_CENTER,
                spaceAfter=10
            )


            elements = []


            # =================================================
            # HEADER
            # =================================================

            header_data = [[
                Paragraph(
                    "<b>Kantor<br/>Cabang</b>",
                    ParagraphStyle(
                        "red",
                        parent=normal,
                        textColor=colors.red,
                        fontSize=9
                    )
                ),
                Paragraph(
                    "<b>PT. Kimia Farma Trading & Distribution</b>",
                    ParagraphStyle(
                        "blue",
                        parent=normal,
                        textColor=colors.HexColor("#0066CC"),
                        alignment=2,
                        fontSize=10
                    )
                )
            ]]


            header_table = Table(
                header_data,
                colWidths=[5 * cm, 12 * cm]
            )


            header_table.setStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 0),
                ("RIGHTPADDING", (0,0), (-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 0)
            ])


            elements.append(header_table)

            elements.append(
                Spacer(1, 15)
            )


            # =================================================
            # JUDUL
            # =================================================

            elements.append(
                Paragraph(
                    "<b>SURAT PENOLAKAN PESANAN</b>",
                    title
                )
            )


            elements.append(
                Spacer(1, 10)
            )


            # =================================================
            # INFORMASI
            # =================================================

            info_data = [

                [
                    Paragraph(
                        "<b>Kepada Yth.</b>",
                        normal
                    ),
                    Paragraph(
                        nama_sarana,
                        normal
                    )
                ],

                [
                    Paragraph(
                        "Surat Pesanan",
                        normal
                    ),
                    Paragraph(
                        f"Sdr. dengan nomor <b>{nomor_sp}</b>",
                        normal
                    )
                ],

                [
                    Paragraph(
                        "Tanggal SP",
                        normal
                    ),
                    Paragraph(
                        tanggal_sp.strftime("%d/%m/%Y"),
                        normal
                    )

                ]

            ]


            info_table = Table(
                info_data,
                colWidths=[4 * cm, 13 * cm]
            )


            info_table.setStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 2),
                ("RIGHTPADDING", (0,0), (-1,-1), 2),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3)
            ])


            elements.append(info_table)

            elements.append(
                Spacer(1, 8)
            )


            elements.append(
                Paragraph(
                    "Dengan ini kami menyampaikan bahwa pesanan dengan item barang sebagai berikut:",
                    normal
                )
            )


            elements.append(
                Spacer(1, 6)
            )


            # =================================================
            # TABEL PRODUK
            # =================================================

            tabel_produk = [

                [
                    Paragraph("<b>No</b>", center),
                    Paragraph("<b>Nama Produk / Barang</b>", center),
                    Paragraph("<b>Jumlah Pesanan</b>", center),
                    Paragraph("<b>Jumlah Difakturkan</b>", center)
                ]

            ]


            for i, item in enumerate(
                produk_data,
                start=1
            ):

                tabel_produk.append([

                    Paragraph(
                        f"{i}.",
                        center
                    ),

                    Paragraph(
                        item["produk"],
                        normal
                    ),

                    Paragraph(
                        item["pesanan"],
                        center
                    ),

                    Paragraph(
                        item["faktur"],
                        center
                    )

                ])


            table = Table(
                tabel_produk,
                colWidths=[
                    0.8 * cm,
                    9 * cm,
                    3.2 * cm,
                    3.2 * cm
                ],
                repeatRows=1
            )


            table.setStyle([

                ("GRID", (0,0), (-1,-1), 0.7, colors.black),

                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

                ("ALIGN", (0,0), (0,-1), "CENTER"),

                ("ALIGN", (2,0), (-1,-1), "CENTER"),

                ("BACKGROUND", (0,0), (-1,0),
                 colors.HexColor("#EAEAEA")),

                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

                ("FONTSIZE", (0,0), (-1,-1), 8),

                ("TOPPADDING", (0,0), (-1,-1), 6),

                ("BOTTOMPADDING", (0,0), (-1,-1), 6),

                ("LEFTPADDING", (0,0), (-1,-1), 4),

                ("RIGHTPADDING", (0,0), (-1,-1), 4)

            ])


            elements.append(table)

            elements.append(
                Spacer(1, 10)
            )


            # =================================================
            # ALASAN
            # =================================================

            elements.append(
                Paragraph(
                    f"<b>Tidak dapat kami layani karena:</b> "
                    f"{alasan_ditolak}",
                    normal
                )
            )


            elements.append(
                Spacer(1, 12)
            )


            elements.append(
                Paragraph(
                    "Demikian yang kami sampaikan, kiranya dapat dimaklumi.",
                    normal
                )
            )


            elements.append(
                Spacer(1, 25)
            )


            # =================================================
            # TANDA TANGAN
            # =================================================

            ttd = Table(
                [[
                    "",
                    Paragraph(
                        f"Mataram, "
                        f"{tanggal_surat.strftime('%d/%m/%Y')}<br/><br/>"
                        "Apoteker Penanggung Jawab<br/>"
                        "Kimia Farma Trading & Distribution<br/>"
                        "Cabang Mataram<br/><br/><br/>"
                        "(________________________)",
                        center
                    )
                ]],
                colWidths=[9 * cm, 8 * cm]
            )


            ttd.setStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 0),
                ("RIGHTPADDING", (0,0), (-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 0)
            ])


            elements.append(ttd)


            # =================================================
            # BUILD
            # =================================================

            doc.build(elements)


            return output_path


        # ====================================================
        # TOMBOL
        # ====================================================

        if st.button(
            "📄 Buat Surat Penolakan",
            type="primary",
            use_container_width=True
        ):

            if errors:

                st.error(
                    "Data belum lengkap:\n\n"
                    + "\n".join(
                        [f"• {x}" for x in errors]
                    )
                )

            else:

                try:

                    # ----------------------------------------
                    # BUAT PDF
                    # ----------------------------------------

                    hasil_pdf = generate_pdf_penolakan()


                    # ----------------------------------------
                    # SIMPAN PRODUK SEBAGAI TEXT
                    # ----------------------------------------

                    import json

                    produk_json = json.dumps(
                        produk_data,
                        ensure_ascii=False
                    )


                    # ----------------------------------------
                    # SIMPAN TANGGAL DALAM FORMAT ISO
                    # ----------------------------------------
                    #
                    # PENTING:
                    # SQLite menerima ini sebagai TEXT
                    # sehingga tidak ada masalah format tanggal.
                    #

                    tanggal_surat_db = tanggal_surat.strftime(
                        "%Y-%m-%d"
                    )

                    tanggal_sp_db = tanggal_sp.strftime(
                        "%Y-%m-%d"
                    )

                    dibuat_pada = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )


                    # ----------------------------------------
                    # SIMPAN KE DATABASE
                    # ----------------------------------------

                    conn.execute(
                        """
                        INSERT INTO penolakan_pesanan (
                            tanggal_surat,
                            tanggal_sp,
                            nama_sarana,
                            nomor_sp,
                            alasan_penolakan,
                            produk_data,
                            file_pdf,
                            dibuat_pada
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tanggal_surat_db,
                            tanggal_sp_db,
                            nama_sarana,
                            nomor_sp,
                            alasan_ditolak,
                            produk_json,
                            hasil_pdf,
                            dibuat_pada
                        )
                    )


                    conn.commit()


                    st.success(
                        "✅ Surat berhasil dibuat dan disimpan "
                        "ke riwayat."
                    )


                    # ----------------------------------------
                    # DOWNLOAD
                    # ----------------------------------------

                    with open(
                        hasil_pdf,
                        "rb"
                    ) as f:

                        pdf_data = f.read()


                    st.download_button(
                        "⬇️ Download Surat",
                        data=pdf_data,
                        file_name=os.path.basename(
                            hasil_pdf
                        ),
                        mime="application/pdf",
                        use_container_width=True
                    )


                    # ----------------------------------------
                    # PREVIEW
                    # ----------------------------------------

                    pdf_base64 = base64.b64encode(
                        pdf_data
                    ).decode("utf-8")


                    pdf_display = f"""
                    <iframe
                        src="data:application/pdf;base64,{pdf_base64}"
                        width="100%"
                        height="800"
                        style="
                            border:1px solid #ccc;
                            border-radius:8px;
                        ">
                    </iframe>
                    """


                    st.markdown(
                        pdf_display,
                        unsafe_allow_html=True
                    )


                except Exception as e:

                    st.error(
                        f"Gagal membuat surat: {e}"
                    )


    # ========================================================
    # TAB 2 - RIWAYAT
    # ========================================================

    with tab_riwayat:

        st.subheader(
            "📚 Riwayat Surat Penolakan"
        )


        # ====================================================
        # AMBIL DATA
        # ====================================================

        try:

            df_history = pd.read_sql(
                """
                SELECT
                    id,
                    tanggal_surat,
                    tanggal_sp,
                    nama_sarana,
                    nomor_sp,
                    alasan_penolakan,
                    file_pdf,
                    dibuat_pada
                FROM penolakan_pesanan
                ORDER BY id DESC
                """,
                conn
            )

        except Exception as e:

            st.error(
                f"Gagal membaca riwayat: {e}"
            )

            st.stop()


        # ====================================================
        # TIDAK ADA DATA
        # ====================================================

        if df_history.empty:

            st.info(
                "Belum ada surat penolakan yang dibuat."
            )

            st.stop()


        # ====================================================
        # FILTER
        # ====================================================

        col1, col2 = st.columns(2)


        with col1:

            filter_sarana = st.selectbox(
                "Filter Sarana",
                ["Semua"]
                + sorted(
                    df_history["nama_sarana"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )


        with col2:

            filter_nomor = st.text_input(
                "Cari Nomor SP"
            )


        df_tampil = df_history.copy()


        if filter_sarana != "Semua":

            df_tampil = df_tampil[
                df_tampil["nama_sarana"]
                == filter_sarana
            ]


        if filter_nomor.strip():

            df_tampil = df_tampil[
                df_tampil["nomor_sp"]
                .astype(str)
                .str.contains(
                    filter_nomor.strip(),
                    case=False,
                    na=False
                )
            ]


        # ====================================================
        # LIST RIWAYAT
        # ====================================================

        for _, row in df_tampil.iterrows():

            tanggal_tampil = "-"


            if row["tanggal_surat"]:

                try:

                    tanggal_tampil = datetime.strptime(
                        str(row["tanggal_surat"]),
                        "%Y-%m-%d"
                    ).strftime(
                        "%d/%m/%Y"
                    )

                except:

                    tanggal_tampil = str(
                        row["tanggal_surat"]
                    )


            with st.expander(
                f"📄 {row['nama_sarana']} | "
                f"{row['nomor_sp']} | "
                f"{tanggal_tampil}"
            ):


                # --------------------------------------------
                # INFORMASI
                # --------------------------------------------

                st.write(
                    "**Nama Sarana:**",
                    row["nama_sarana"]
                )

                st.write(
                    "**Nomor SP:**",
                    row["nomor_sp"]
                )

                st.write(
                    "**Tanggal SP:**",
                    (
                        datetime.strptime(
                            str(row["tanggal_sp"]),
                            "%Y-%m-%d"
                        ).strftime("%d/%m/%Y")
                        if row["tanggal_sp"]
                        else "-"
                    )
                )

                st.write(
                    "**Tanggal Surat:**",
                    tanggal_tampil
                )


                st.write(
                    "**Alasan Penolakan:**",
                    row["alasan_penolakan"]
                )


                # --------------------------------------------
                # PRODUK
                # --------------------------------------------

                try:

                    import json

                    produk_history = json.loads(
                        row["produk_data"]
                    )


                    tabel_history = []


                    for i, item in enumerate(
                        produk_history,
                        start=1
                    ):

                        if item.get("produk", "").strip():

                            tabel_history.append({

                                "No": i,

                                "Produk":
                                    item.get(
                                        "produk",
                                        ""
                                    ),

                                "Pesanan":
                                    item.get(
                                        "pesanan",
                                        ""
                                    ),

                                "Difakturkan":
                                    item.get(
                                        "faktur",
                                        ""
                                    )

                            })


                    if tabel_history:

                        st.dataframe(
                            pd.DataFrame(
                                tabel_history
                            ),
                            use_container_width=True,
                            hide_index=True
                        )


                except Exception:

                    pass


                # --------------------------------------------
                # DOWNLOAD PDF
                # --------------------------------------------

                file_pdf = row["file_pdf"]


                if file_pdf and os.path.exists(
                    file_pdf
                ):

                    with open(
                        file_pdf,
                        "rb"
                    ) as f:

                        pdf_data = f.read()


                    st.download_button(
                        "⬇️ Download Surat",
                        data=pdf_data,
                        file_name=os.path.basename(
                            file_pdf
                        ),
                        mime="application/pdf",
                        key=f"download_{row['id']}"
                    )


                    # ----------------------------------------
                    # PREVIEW PDF
                    # ----------------------------------------

                    pdf_base64 = base64.b64encode(
                        pdf_data
                    ).decode("utf-8")


                    st.markdown(
                        f"""
                        <iframe
                            src="data:application/pdf;base64,{pdf_base64}"
                            width="100%"
                            height="600"
                            style="border:1px solid #ccc;">
                        </iframe>
                        """,
                        unsafe_allow_html=True
                    )


                else:

                    st.warning(
                        "File PDF tidak ditemukan."
                    )


                # --------------------------------------------
                # HAPUS
                # --------------------------------------------

                st.divider()


                if st.button(
                    "🗑️ Hapus Surat Ini",
                    key=f"hapus_penolakan_{row['id']}"
                ):

                    # Hapus file PDF
                    if file_pdf and os.path.exists(
                        file_pdf
                    ):

                        try:

                            os.remove(file_pdf)

                        except Exception:

                            pass


                    # Hapus database
                    conn.execute(
                        """
                        DELETE FROM penolakan_pesanan
                        WHERE id=?
                        """,
                        (int(row["id"]),)
                    )

                    conn.commit()


                    st.success(
                        "Surat berhasil dihapus."
                    )

                    st.rerun()
