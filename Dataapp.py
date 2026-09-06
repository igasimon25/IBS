# ==========================================
# STATUS TRACKING INV BM (WITH STICKY HEADER)
# ==========================================
st.markdown("---")
st.subheader("📊 Status Tracking Invoice BM")

# 1. MENDAPATKAN DATAFRAME DARI SCRIPT UTAMA
df_source = None
for var_name in ['df', 'data', 'df_filtered']:
    if var_name in locals():
        df_source = locals()[var_name]
        break
    elif var_name in globals():
        df_source = globals()[var_name]
        break
    elif hasattr(st, 'session_state') and var_name in st.session_state:
        df_source = st.session_state[var_name]
        break

if df_source is None or not isinstance(df_source, pd.DataFrame) or df_source.empty:
    dummy_data = {
        'Area': ['Area 1', 'Area 1', 'Area 1', 'Area 2'],
        'Year': [2024, 2024, 2024, 2024],
        'PIC Site': ['Alex', 'Alex', 'Budi', 'Cici'],
        'new regional': ['RO3_Jakarta Banten', 'RO3_Jakarta Banten', 'RO3_Jakarta Banten', 'RO3_Jakarta Banten'],
        'Supplier Name': ['PT. Batara Tabaraka', 'PT. POS PROPERTI INDO', 'Apartamen Oasis Mitra', 'ASURANSI KREDIT INDON'],
        'Site ID': ['JKP187', 'JKP020', 'JKP652', 'JKP692'],
        'Invoice No.': ['INV-01', 'INV-02', 'INV-03', 'INV-04'],
        'Month': ['Jan', 'Feb', 'Mar', 'Apr']
    }
    df_source = pd.DataFrame(dummy_data)

# Pembersihan awal nama kolom & duplikasi dataframe utama
df_source = df_source.loc[:, ~df_source.columns.duplicated()].copy()
for col in df_source.columns:
    if isinstance(df_source[col], pd.DataFrame):
        df_source[col] = df_source[col].iloc[:, 0]

# ------------------------------------------
# 2. FILTER DATA (AREA, YEAR, PIC SITE, NEW REGIONAL)
# ------------------------------------------
col_area = next((c for c in ['Area (Khusus SAP)', 'Area', 'Region'] if c in df_source.columns), None)
col_year = next((c for c in ['Year', 'Tahun', 'Payment Year'] if c in df_source.columns), None)
col_pic = next((c for c in ['PIC Site (Khusus SAP)', 'PIC Site', 'PIC', 'pic_site'] if c in df_source.columns), None)
col_reg = next((c for c in ['new regional', 'Regional', 'regional'] if c in df_source.columns), None)

st.markdown("#### 🔍 Filter Data Tracking")
f_col1, f_col2, f_col3, f_col4 = st.columns(4)

with f_col1:
    opts_area = ["All"] + sorted(list(df_source[col_area].dropna().astype(str).unique())) if col_area else ["All"]
    sel_area = st.selectbox("Select Area", opts_area, key="trk_area_github_v5")

with f_col2:
    opts_year = ["All"] + sorted(list(df_source[col_year].dropna().astype(str).unique())) if col_year else ["All"]
    sel_year = st.selectbox("Select Year", opts_year, key="trk_year_github_v5")

with f_col3:
    opts_pic = ["All"] + sorted(list(df_source[col_pic].dropna().astype(str).unique())) if col_pic else ["All"]
    sel_pic = st.selectbox("Select PIC Site", opts_pic, key="trk_pic_github_v5")

with f_col4:
    opts_reg = ["All"] + sorted(list(df_source[col_reg].dropna().astype(str).unique())) if col_reg else ["All"]
    sel_reg = st.selectbox("Select New Regional", opts_reg, key="trk_reg_github_v5")

# Logika Filtering Bertingkat
df_trk_filtered = df_source.copy()
if sel_area != "All" and col_area:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_area].astype(str) == sel_area]
if sel_year != "All" and col_year:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_year].astype(str) == sel_year]
if sel_pic != "All" and col_pic:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_pic].astype(str) == sel_pic]
if sel_reg != "All" and col_reg:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_reg].astype(str) == sel_reg]


# ------------------------------------------
# 3. PROSES PIVOT TABLE & FORMULA
# ------------------------------------------
def generate_tracking_invoice_table(df_input):
    df_trk = df_input.copy()
    df_trk = df_trk.loc[:, ~df_trk.columns.duplicated()].copy()

    col_reg_t = next((c for c in ['new regional', 'Regional', 'regional'] if c in df_trk.columns), 'Regional')
    col_supp_t = next((c for c in ['Supplier Name', 'Supplier', 'supplier_name'] if c in df_trk.columns), 'Supplier Name')
    col_site_t = next((c for c in ['Site ID', 'SiteID', 'site_id'] if c in df_trk.columns), 'Site ID')
    col_inv_no = next((c for c in ['Invoice No.', 'Invoice No', 'Invoice Number'] if c in df_trk.columns), 'Invoice No.')
    col_m_t = next((c for c in ['Month', 'Payment Month', 'Month Name'] if c in df_trk.columns), 'Month')

    for col_req in [col_reg_t, col_supp_t, col_site_t]:
        if col_req not in df_trk.columns:
            df_trk[col_req] = "-"
        elif isinstance(df_trk[col_req], pd.DataFrame):
            df_trk[col_req] = df_trk[col_req].iloc[:, 0]

    if col_inv_no not in df_trk.columns:
        df_trk[col_inv_no] = 1
    elif isinstance(df_trk[col_inv_no], pd.DataFrame):
        df_trk[col_inv_no] = df_trk[col_inv_no].iloc[:, 0]

    months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    month_mapping = {
        '1': 'Jan', '01': 'Jan', 'january': 'Jan', 'jan': 'Jan',
        '2': 'Feb', '02': 'Feb', 'february': 'Feb', 'feb': 'Feb',
        '3': 'Mar', '03': 'Mar', 'march': 'Mar', 'mar': 'Mar',
        '4': 'Apr', '04': 'Apr', 'april': 'Apr', 'apr': 'Apr',
        '5': 'May', '05': 'May', 'may': 'May',
        '6': 'Jun', '06': 'Jun', 'june': 'Jun', 'jun': 'Jun',
        '7': 'Jul', '07': 'Jul', 'july': 'Jul', 'jul': 'Jul',
        '8': 'Aug', '08': 'Aug', 'august': 'Aug', 'aug': 'Aug',
        '9': 'Sep', '09': 'Sep', 'september': 'Sep', 'sep': 'Sep',
        '10': 'Oct', 'october': 'Oct', 'oct': 'Oct',
        '11': 'Nov', 'november': 'Nov', 'nov': 'Nov',
        '12': 'Dec', 'december': 'Dec', 'dec': 'Dec'
    }

    if col_m_t in df_trk.columns:
        s_m = df_trk[col_m_t]
        if isinstance(s_m, pd.DataFrame):
            s_m = s_m.iloc[:, 0]
        df_trk['month_clean'] = s_m.astype(str).str.lower().str.strip().map(month_mapping).fillna(s_m.astype(str).str.slice(0, 3).str.title())
    else:
        df_trk['month_clean'] = 'Jan'

    df_trk = df_trk[df_trk['month_clean'].isin(months_order)]

    if df_trk.empty:
        return pd.DataFrame(), col_reg_t, col_supp_t, col_site_t

    index_cols = [col_reg_t, col_supp_t, col_site_t]

    pivot_df = df_trk.pivot_table(
        index=index_cols,
        columns='month_clean',
        values=col_inv_no,
        aggfunc='count',
        fill_value=0,
        observed=True
    ).reset_index()

    for m in months_order:
        if m not in pivot_df.columns:
            pivot_df[m] = 0

    pivot_df = pivot_df[index_cols + months_order]

    for m in months_order:
        pivot_df[m] = pivot_df[m].map(lambda x: 1 if x > 0 else 0)

    pivot_df['Grand Total'] = pivot_df[months_order].sum(axis=1)
    pivot_df['Progress'] = (pivot_df['Grand Total'] / 12.0 * 100).round(0)
    pivot_df['Invoice NY Received'] = pivot_df['Grand Total'].apply(lambda x: max(0, 12 - int(x)))

    return pivot_df, col_reg_t, col_supp_t, col_site_t


df_trk_res, c_reg, c_supp, c_site = generate_tracking_invoice_table(df_trk_filtered)

# ------------------------------------------
# 4. VISUALISASI CHART & RENDER HTML
# ------------------------------------------
if not df_trk_res.empty:
    st.markdown("### 📈 Visualisasi Progress Tracking (%)")
    
    total_sites = len(df_trk_res)
    avg_progress = round(df_trk_res['Progress'].mean(), 1)
    total_ny_rec = int(df_trk_res['Invoice NY Received'].sum())
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Site", f"{total_sites} Sites")
    m2.metric("Rata-Rata Progress", f"{avg_progress}%")
    m3.metric("Total Invoice NY Received", f"{total_ny_rec} Inv", delta_color="inverse")

    chart_data = df_trk_res[[c_site, 'Progress']].set_index(c_site)
    st.bar_chart(chart_data)

    st.markdown("---")

    months_headers = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    rows_trk_html = ""
    
    for idx, row in df_trk_res.iterrows():
        m_cells = ""
        for m in months_headers:
            val_m = int(row[m])
            cell_bg = "background-color: #fce4d6; color: #c00000; font-weight: bold;" if val_m == 0 else "text-align: center;"
            m_cells += f'<td style="{cell_bg}">{val_m}</td>'

        grand_tot = int(row['Grand Total'])
        prog_pct = int(row['Progress'])
        ny_rec = int(row['Invoice NY Received'])

        ny_bg = "background-color: #ff0000; color: #ffffff; font-weight: bold;" if ny_rec > 0 else "text-align: center;"

        rows_trk_html += f"""
        <tr>
            <td style="text-align: left;">{row[c_reg]}</td>
            <td style="text-align: left;">{row[c_supp]}</td>
            <td style="text-align: center;">{row[c_site]}</td>
            {m_cells}
            <td style="text-align: center; font-weight: bold;">{grand_tot}</td>
            <td style="text-align: center; background-color: #e2efda; font-weight: bold; color: #375623;">{prog_pct}%</td>
            <td style="{ny_bg}">{ny_rec}</td>
        </tr>
        """

    full_trk_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: transparent; }}
        .scroll-container {{
            max-height: 450px; 
            overflow-y: auto; 
            overflow-x: auto;
            border: 1px solid #d9d9d9;
        }}
        .trk-table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000000; }}
        .trk-table th, .trk-table td {{ border: 1px solid #d9d9d9; padding: 4px 6px; white-space: nowrap; }}
        .trk-hdr {{ 
            background-color: #ffffff; 
            color: #000000; 
            font-weight: bold; 
            text-align: center; 
            vertical-align: middle; 
            border: 1px solid #000000 !important; 
            position: sticky; 
            top: 0; 
            z-index: 10;
        }}
        .trk-hdr-title {{ font-size: 16px; font-weight: bold; text-decoration: underline; padding: 8px 0; border: none; text-align: left; color: #000000; }}
    </style>
    </head>
    <body>
    <div class="trk-hdr-title">Tracking invoice</div>
    <div class="scroll-container">
        <table class="trk-table">
            <thead>
                <tr>
                    <th class="trk-hdr">Regional</th>
                    <th class="trk-hdr">Supplier Name</th>
                    <th class="trk-hdr">Site ID</th>
                    <th class="trk-hdr">Jan</th>
                    <th class="trk-hdr">Feb</th>
                    <th class="trk-hdr">Mar</th>
                    <th class="trk-hdr">Apr</th>
                    <th class="trk-hdr">May</th>
                    <th class="trk-hdr">Jun</th>
                    <th class="trk-hdr">Jul</th>
                    <th class="trk-hdr">Aug</th>
                    <th class="trk-hdr">Sep</th>
                    <th class="trk-hdr">Oct</th>
                    <th class="trk-hdr">Nov</th>
                    <th class="trk-hdr">Dec</th>
                    <th class="trk-hdr">Grand Total</th>
                    <th class="trk-hdr">Progress</th>
                    <th class="trk-hdr">Invoice NY Received</th>
                </tr>
            </thead>
            <tbody>
                {rows_trk_html}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    components.html(full_trk_html, height=520, scrolling=False)
else:
    st.warning("Data Tracking Invoice tidak ditemukan berdasarkan filter yang dipilih.")
