import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
import re

# ==========================================
# 1. KONFIGURASI HALAMAN & HEADER RESPONSIF
# ==========================================
st.set_page_config(
    page_title="Dashboard POB IBS Building Management",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# CSS Global untuk Responsivitas Mobile & Web
st.markdown("""
    <style>
    /* Memastikan elemen utama responsif terhadap ukuran layar */
    .main {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    /* Responsif untuk tabel dan kontainer kustom */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column !important;
        }
        h1 {
            font-size: 20px !important;
        }
        h2 {
            font-size: 18px !important;
        }
        h3 {
            font-size: 16px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 DASHBOARD POB IBS BUILDING MANAGEMENT")
st.markdown("---")

# ==========================================
# 2. BACA DATA GOOGLE SHEETS & DATA CLEANING
# ==========================================
SHEET_ID = "1g3Y6GjXUgjWFtKxC9ul8i0vZgHvamkDwT7j4-_95NMk"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def clean_currency_advanced(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', '-', '#value!', '#n/a']:
        return 0.0
    
    is_negative = False
    if val_str.startswith('(') and val_str.endswith(')'):
        is_negative = True
        val_str = val_str[1:-1]
        
    cleaned = re.sub(r'[^0-9.-]', '', val_str)
    try:
        num = float(cleaned) if cleaned != '' else 0.0
        return -num if is_negative else num
    except ValueError:
        return 0.0

@st.cache_data(ttl=10)
def load_data():
    df = pd.read_csv(GSHEET_URL, low_memory=False)
    df.columns = [str(col).strip() for col in df.columns]
    
    mapping = {}
    for col in df.columns:
        c_upper = col.upper().replace('_', ' ').strip()
        if c_upper == 'NET AMOUNT':
            mapping[col] = 'NET AMOUNT'
        elif c_upper == 'INVOICE AMOUNT':
            mapping[col] = 'Invoice Amount'
        elif 'STATUS REIMBURSE' in c_upper:
            mapping[col] = 'Status Reimburse Actual'
        elif c_upper == 'INVOICE AGENT':
            mapping[col] = 'Invoice Agent'
        elif c_upper == 'STATUS':
            mapping[col] = 'Status'
        elif c_upper in ['STATUS SAP', 'STATUSSAP', 'STATUS_SAP']:
            mapping[col] = 'StatusSAP'
        elif c_upper == 'AREA':
            mapping[col] = 'Area'
        elif c_upper == 'NEW REGIONAL':
            mapping[col] = 'new regional'

    df = df.rename(columns=mapping)
    df = df.loc[:, ~df.columns.duplicated(keep='first')].copy()

    if 'Area' in df.columns:
        df['Area'] = df['Area'].astype(str).str.strip().str.title()

    numeric_cols = [
        'Invoice Amount', 'NET AMOUNT', 'Amount SAP', 
        'Amount Paid Based on Setoff Data', 'Amount Actual Paid', 
        'Amount Paid'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_currency_advanced)

    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"❌ Gagal membaca data dari Google Sheets. Detail: {e}")
    st.stop()

df_filtered = df_raw.copy()

# ==========================================
# 3. SIDEBAR CONTROL & GLOBAL FILTERS
# ==========================================
st.sidebar.header("🔍 Global Filters")

if 'Area' in df_raw.columns:
    raw_areas = df_raw['Area'].dropna().unique().tolist()
    clean_areas = sorted([str(x) for x in raw_areas if str(x).lower() not in ['nan', 'none', '']])
    list_area = ["(All)"] + clean_areas
    selected_area = st.sidebar.selectbox("Area Filter", options=list_area, index=0)
    if selected_area != "(All)":
        df_filtered = df_filtered[df_filtered['Area'] == selected_area]

col_month = 'Payment Month' if 'Payment Month' in df_filtered.columns else ('Month' if 'Month' in df_filtered.columns else None)
if col_month and col_month in df_filtered.columns:
    list_month = ["(All Months)"] + [str(x) for x in df_filtered[col_month].dropna().unique().tolist() if str(x).lower() not in ['nan', 'none', '']]
    selected_month = st.sidebar.selectbox("Payment Month Filter", options=list_month, index=0)
    if selected_month != "(All Months)":
        df_filtered = df_filtered[df_filtered[col_month].astype(str) == selected_month]

if 'new regional' in df_filtered.columns:
    list_reg = ["(All Regionals)"] + [str(x) for x in df_filtered['new regional'].dropna().unique().tolist() if str(x).lower() not in ['nan', 'none', '']]
    selected_reg = st.sidebar.selectbox("New Regional Filter", options=list_reg, index=0)
    if selected_reg != "(All Regionals)":
        df_filtered = df_filtered[df_filtered['new regional'].astype(str) == selected_reg]

# ==========================================
# FUNGSI HELPER: COMPACT DONUT CHART (KPI)
# ==========================================
def create_compact_donut_card(title, paid_val, ny_val, color_done='#558B2F', color_ny='#E53935', key=None):
    total_val = paid_val + ny_val
    pct_done = (paid_val / total_val * 100) if total_val > 0 else 0.0

    paid_m = paid_val / 1_000_000_000
    ny_m = ny_val / 1_000_000_000
    total_m = total_val / 1_000_000_000

    st.markdown(f"<div style='text-align: center; font-weight: bold; font-size: 13px; min-height: 38px;'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; color: #1E88E5; font-weight: bold; font-size: 16px; margin-bottom: 5px;'>Rp {total_m:,.2f} M</div>", unsafe_allow_html=True)

    fig = go.Figure(data=[go.Pie(
        labels=['Done', 'Not Yet Paid'],
        values=[paid_m, ny_m],
        hole=0.65,
        marker=dict(colors=[color_done, color_ny]),
        textinfo='none',
        hovertemplate="<b>%{label}</b><br>Nominal: Rp %{value:,.2f} M<br>Proporsi: %{percent}<extra></extra>"
    )])

    fig.update_layout(
        annotations=[dict(
            text=f"<b>{pct_done:.1f}%</b>",
            x=0.5, y=0.5, font_size=15, showarrow=False, font_color="#000000"
        )],
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=5, r=5, t=5, b=5),
        height=180
    )

    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown(f"<div style='font-size: 11px; text-align: center; color: #555;'>Done: <b>Rp {paid_m:,.2f}M</b><br>NY: <b>Rp {ny_m:,.2f}M</b></div>", unsafe_allow_html=True)

# ==========================================
# 4. KPI SEJAJAR (RESPONSIF KOLOM OTOMATIS)
# ==========================================
st.subheader("📌 Key Performance Indicators (KPI Overview)")

cols_kpi = st.columns(5)

# 1. Payout to BM
df_c1 = df_filtered.copy()
if 'Status' in df_c1.columns and 'Invoice Amount' in df_c1.columns:
    m_paid = df_c1['Status'].astype(str).str.upper().str.strip() == 'PAID'
    val_payout_bm = df_c1[m_paid]['Invoice Amount'].sum()
    ny_val = df_c1[~m_paid]['Invoice Amount'].sum()
    with cols_kpi[0]:
        create_compact_donut_card("Total Payout to BM", val_payout_bm, ny_val, key="kpi_1")

# 2. Huawei To Agent
df_c2 = df_filtered.copy()
if 'Status' in df_c2.columns and 'NET AMOUNT' in df_c2.columns:
    m_paid = df_c2['Status'].astype(str).str.upper().str.strip() == 'PAID'
    val_huawei_agent = df_c2[m_paid]['NET AMOUNT'].sum()
    ny_val = df_c2[~m_paid]['NET AMOUNT'].sum()
    with cols_kpi[1]:
        create_compact_donut_card("Huawei To Agent", val_huawei_agent, ny_val, key="kpi_2")

# 3. Agent To Telkomsel
df_c3 = df_filtered.copy()
if 'Invoice Agent' in df_c3.columns:
    df_c3 = df_c3[df_c3['Invoice Agent'].astype(str).str.upper().str.strip() == 'INVOICE DONE']
if 'Status' in df_c3.columns and 'NET AMOUNT' in df_c3.columns:
    m_paid = df_c3['Status'].astype(str).str.upper().str.strip() == 'PAID'
    val_agent_tsel = df_c3[m_paid]['NET AMOUNT'].sum()
    ny_val = df_c3[~m_paid]['NET AMOUNT'].sum()
    with cols_kpi[2]:
        create_compact_donut_card("Agent To Telkomsel", val_agent_tsel, ny_val, key="kpi_3")

# 4. DN Issued
df_c4 = df_filtered.copy()
if 'Status Reimburse Actual' in df_c4.columns and 'NET AMOUNT' in df_c4.columns:
    status_clean = df_c4['Status Reimburse Actual'].astype(str).str.upper().str.strip()
    m_done = status_clean.isin(['PAID', 'DN ISSUED'])
    val_dn_issued = df_c4[m_done]['NET AMOUNT'].sum()
    ny_val = df_c4[~m_done]['NET AMOUNT'].sum()
    with cols_kpi[3]:
        create_compact_donut_card("DN Issued", val_dn_issued, ny_val, key="kpi_4")

# 5. Total Pay In To Huawei
df_c5 = df_filtered.copy()
if 'Status Reimburse Actual' in df_c5.columns and 'NET AMOUNT' in df_c5.columns:
    status_clean = df_c5['Status Reimburse Actual'].astype(str).str.upper().str.strip()
    m_paid = status_clean == 'PAID'
    val_payin_huawei = df_c5[m_paid]['NET AMOUNT'].sum()
    m_ny = status_clean.isin(['DN ISSUED', 'NY ISSUE DN'])
    ny_val = df_c5[m_ny]['NET AMOUNT'].sum()
    with cols_kpi[4]:
        create_compact_donut_card("Total Pay In To Huawei", val_payin_huawei, ny_val, key="kpi_5")

st.markdown("---")

# ==========================================
# 5. STATUS PAY OUT
# ==========================================
st.subheader("📋 Status Pay Out")

col_status, col_amount = 'Status', 'Invoice Amount'
if col_status in df_filtered.columns and col_amount in df_filtered.columns:
    df_status_calc = df_filtered.copy()
    target_statuses = [
        "MODIFY REQUEST", "PAID", "Wait for Cashier",
        "WAITING FOR APW PROCESS", "Waiting for Accounting",
        "WAITING MGR APPROVAL", "WAITING PAYMENT APPROVAL"
    ]

    grouped = df_status_calc.groupby(df_status_calc[col_status].astype(str).str.strip(), as_index=False)[col_amount].sum()
    status_dict = {str(k).upper().strip(): v for k, v in zip(grouped[col_status], grouped[col_amount])}

    st.markdown("""
        <style>
        .status-box { background-color: #f0f0f0; border: 1px solid #cccccc; border-radius: 4px; padding: 8px 12px; text-align: center; font-size: 13px; font-weight: 500; color: #333333; margin-bottom: 6px; height: 38px; display: flex; align-items: center; justify-content: center; }
        .amount-box { background-color: #8faadc; border: 1px solid #6c8ebf; border-radius: 8px; padding: 8px 12px; text-align: center; font-size: 14px; font-weight: bold; color: #111111; margin-bottom: 6px; height: 38px; display: flex; align-items: center; justify-content: center; }
        </style>
    """, unsafe_allow_html=True)

    col_layout, _ = st.columns([2, 3])
    with col_layout:
        for status_item in target_statuses:
            amount_val = status_dict.get(status_item.upper().strip(), 0)
            amount_str = f"Rp{amount_val:,.0f}".replace(",", ".") if amount_val > 0 else ("Rp0" if amount_val == 0 else "Rp-")
            c1, c2 = st.columns([1.2, 2])
            with c1:
                st.markdown(f"<div class='status-box'>{status_item}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='amount-box'>{amount_str}</div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 6. END-TO-END PROCESS WORKFLOW & SLA (RESPONSIF MOBILE/WEB)
# ==========================================
st.subheader("🔄 End-to-End Process Workflow & SLA")

str_payout_bm = f"Rp{val_payout_bm:,.0f}".replace(",", ".") if val_payout_bm > 0 else "Rp0"
str_huawei_agent = f"Rp{val_huawei_agent:,.0f}".replace(",", ".") if val_huawei_agent > 0 else "Rp0"
str_agent_tsel = f"Rp{val_agent_tsel:,.0f}".replace(",", ".") if val_agent_tsel > 0 else "Rp0"
str_dn_issued = f"Rp{val_dn_issued:,.0f}".replace(",", ".") if val_dn_issued > 0 else "Rp0"
str_payin_huawei = f"Rp{val_payin_huawei:,.0f}".replace(",", ".") if val_payin_huawei > 0 else "Rp0"

html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: transparent; margin: 0; padding: 5px; }}
    .flow-container {{ display: flex; flex-direction: column; gap: 15px; width: 100%; }}
    .flow-row {{ display: flex; align-items: stretch; justify-content: space-between; gap: 8px; flex-wrap: wrap; }}
    .flow-card-wrapper {{ display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 140px; }}
    .amount-badge {{ background: linear-gradient(180deg, #1f497d 0%, #0d284a 100%); color: white; font-weight: bold; font-size: 11px; padding: 5px 8px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); margin-bottom: -12px; z-index: 10; width: 85%; text-align: center; white-space: nowrap; }}
    .flow-card {{ border-radius: 8px; padding: 18px 8px 10px 8px; width: 100%; min-height: 95px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; font-size: 11px; font-weight: 600; box-shadow: 0 2px 5px rgba(0,0,0,0.08); border: 1px solid #ccc; box-sizing: border-box; }}
    .card-huawei {{ background-color: #dce6f1; border-color: #b8cce4; color: #1f497d; }}
    .card-rpj {{ background-color: #fce4d6; border-color: #f8c2a6; color: #c65911; }}
    .card-telkomsel {{ background-color: #fff2cc; border-color: #ffe599; color: #806000; }}
    .sla-label {{ font-size: 10px; font-weight: bold; color: #555; margin-top: 6px; }}
    .arrow-right {{ font-size: 18px; color: #1f497d; font-weight: bold; display: flex; align-items: center; justify-content: center; }}
    .arrow-down {{ font-size: 20px; color: #1f497d; font-weight: bold; text-align: center; width: 100%; }}
    
    /* Responsif untuk Layar Handphone */
    @media (max-width: 768px) {{
        .flow-row {{ flex-direction: column; align-items: center; }}
        .flow-card-wrapper {{ width: 100%; max-width: 100%; }}
        .arrow-right {{ transform: rotate(90deg); margin: 5px 0; }}
    }}
</style>
</head>
<body>
<div class="flow-container">
    <div class="flow-row">
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_payout_bm}</div>
            <div class="flow-card card-huawei">Huawei Release Payment to Supplier</div>
            <div class="sla-label">SLA 5 WD</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_huawei_agent}</div>
            <div class="flow-card card-huawei"><b>Huawei Submit Reimbursement Data to Agent</b></div>
            <div class="sla-label">SLA 2-3 WD</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">-</div>
            <div class="flow-card card-rpj">Agent Received, Process BAST & DN to Telkomsel</div>
            <div class="sla-label">SLA 1-2 D</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_agent_tsel}</div>
            <div class="flow-card card-rpj">Agent Submit Doc Reimbursement</div>
            <div class="sla-label">SLA 1 D</div>
        </div>
    </div>
    <div class="arrow-down">↓</div>
    <div class="flow-row">
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_payin_huawei}</div>
            <div class="flow-card card-rpj">Agent Paid to Huawei</div>
            <div class="sla-label">SLA 30 Days</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_agent_tsel}</div>
            <div class="flow-card card-telkomsel">Telkomsel Paid to Agent</div>
            <div class="sla-label">SLA 2-4 Weeks</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_dn_issued}</div>
            <div class="flow-card card-huawei">Huawei Send DN to Agent</div>
            <div class="sla-label">SLA 2-3 Days</div>
        </div>
        <div class="arrow-right">➔</div>
        <div class="flow-card-wrapper">
            <div class="amount-badge">{str_agent_tsel}</div>
            <div class="flow-card card-telkomsel">Received, Review and Submit in SAP by Telkomsel NOS</div>
            <div class="sla-label">SLA 1 Days</div>
        </div>
    </div>
</div>
</body>
</html>
"""

components.html(html_content, height=650, scrolling=True)

st.markdown("---")

# ==========================================
# 7. PAYOUT & PAYIN BY AREA
# ==========================================
st.subheader("📊 Payout (Bn IDR) & Payin (Bn IDR)")

if 'Area' in df_filtered.columns:
    raw_unique_areas = df_filtered['Area'].dropna().unique().tolist()
    unique_areas = sorted([str(x) for x in raw_unique_areas if str(x).lower() not in ['nan', 'none', '']])
    
    def draw_area_donut(title, done_bn, ny_bn, color_main, key=None):
        total_bn = done_bn + ny_bn
        pct_done = (done_bn / total_bn * 100) if total_bn > 0 else 0.0
        
        st.markdown(f"<div style='background-color: #f0f0f0; padding: 4px 10px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 13px; color: #111;'>{title}</div>", unsafe_allow_html=True)
        
        fig = go.Figure(data=[go.Pie(
            labels=['Done', 'Not Yet Paid'],
            values=[done_bn, ny_bn],
            hole=0.68,
            marker=dict(colors=[color_main, '#FFC000']),
            textinfo='none',
            hovertemplate="<b>%{label}</b><br>Nominal: %{value:.2f} Bn IDR<extra></extra>"
        )])
        
        fig.update_layout(
            annotations=[dict(text=f"<b>{pct_done:.1f}%</b>", x=0.5, y=0.5, font_size=14, showarrow=False, font_color="#000000")],
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=160
        )
        st.plotly_chart(fig, use_container_width=True, key=key)
        st.markdown(f"<div style='text-align: center; font-size: 11px; font-weight: bold; color: #222; margin-top: -10px;'><span style='color: #888;'>NY: {ny_bn:,.2f}</span> | <span>Done: {done_bn:,.2f}</span></div>", unsafe_allow_html=True)

    for idx, area_name in enumerate(unique_areas):
        df_area = df_filtered[df_filtered['Area'] == area_name]
        
        col_amt_payout = 'Invoice Amount' if 'Invoice Amount' in df_area.columns else 'NET AMOUNT'
        if 'Status' in df_area.columns and col_amt_payout in df_area.columns:
            payout_series = df_area[col_amt_payout]
            mask_payout_done = df_area['Status'].astype(str).str.upper().str.strip() == 'PAID'
            payout_done_bn = payout_series[mask_payout_done].sum() / 1_000_000_000
            payout_ny_bn = payout_series[~mask_payout_done].sum() / 1_000_000_000
        else:
            payout_done_bn, payout_ny_bn = 0.0, 0.0

        col_amt_payin = 'NET AMOUNT'
        if 'Status Reimburse Actual' in df_area.columns and col_amt_payin in df_area.columns:
            payin_series = df_area[col_amt_payin]
            status_area_clean = df_area['Status Reimburse Actual'].astype(str).str.upper().str.strip()
            mask_payin_done = status_area_clean == 'PAID'
            mask_payin_ny = status_area_clean.isin(['DN ISSUED', 'NY ISSUE DN'])
            payin_done_bn = payin_series[mask_payin_done].sum() / 1_000_000_000
            payin_ny_bn = payin_series[mask_payin_ny].sum() / 1_000_000_000
        else:
            payin_done_bn, payin_ny_bn = 0.0, 0.0

        c_payout, c_payin = st.columns(2)
        with c_payout:
            draw_area_donut(f"Progress Payout {area_name}", payout_done_bn, payout_ny_bn, color_main='#70AD47', key=f"payout_{idx}")
        with c_payin:
            draw_area_donut(f"Progress Payin {area_name}", payin_done_bn, payin_ny_bn, color_main='#ED7D31', key=f"payin_{idx}")

st.markdown("---")

# ==========================================
# 8. INVOICE REGIONAL
# ==========================================
st.subheader("📊 Invoice Process (Invoice Regional)")

df_inv_reg = df_filtered.copy()
col_inv_agent = 'Invoice Agent'
if col_inv_agent in df_raw.columns:
    raw_agents = [str(x) for x in df_raw[col_inv_agent].dropna().unique().tolist()]
    list_inv_agent = ["INVOICE DONE", "(All)"] + [x for x in raw_agents if x != "INVOICE DONE"]
    selected_inv_agent = st.selectbox("Filter Invoice Agent", options=list_inv_agent, index=0)
    if selected_inv_agent != "(All)":
        df_inv_reg = df_inv_reg[df_inv_reg[col_inv_agent].astype(str).str.upper().str.strip() == selected_inv_agent.upper().strip()]

col_reg, col_status_sap, col_net_amt = 'new regional', 'StatusSAP', 'NET AMOUNT'

if col_reg in df_inv_reg.columns and col_status_sap in df_inv_reg.columns and col_net_amt in df_inv_reg.columns:
    available_regionals = df_inv_reg[col_reg].dropna().unique().tolist()
    num_cols = 3
    cols = st.columns(num_cols)
    
    for idx, reg_name in enumerate(available_regionals):
        col_target = cols[idx % num_cols]
        df_reg = df_inv_reg[df_inv_reg[col_reg].astype(str) == reg_name]
        status_sap_clean = df_reg[col_status_sap].astype(str).str.upper().str.strip()
        
        mask_done = status_sap_clean.isin(['CLEARED', 'PAID', 'CLEARED/PAID'])
        done_m = df_reg[mask_done][col_net_amt].sum() / 1_000_000_000
        ny_m = df_reg[~mask_done][col_net_amt].sum() / 1_000_000_000
        total_m = done_m + ny_m
        pct_done = (done_m / total_m * 100) if total_m > 0 else 0.0

        with col_target:
            st.markdown(f"<div style='text-align: center; font-weight: bold; padding: 5px; text-decoration: underline;'>{reg_name}</div>", unsafe_allow_html=True)
            fig = go.Figure(data=[go.Pie(
                labels=['Cleared/Paid', 'Not Yet Paid'],
                values=[done_m, ny_m],
                hole=0.65,
                marker=dict(colors=['#2F5597', '#A6A6A6']),
                textinfo='none'
            )])
            fig.update_layout(
                annotations=[dict(text=f"<b>{pct_done:.1f}%</b>", x=0.5, y=0.5, font_size=14, showarrow=False)],
                showlegend=False,
                margin=dict(l=5, r=5, t=5, b=5),
                height=160
            )
            st.plotly_chart(fig, use_container_width=True, key=f"chart_reg_{idx}")

st.markdown("---")

# ==========================================
# 9. PROCESS REIMBURSEMENT SUMMARY TABLE
# ==========================================
st.subheader("📊 Process Reimbursement Summary")

def generate_reimbursement_summary_table(df):
    df_calc = df.copy()
    num_cols = ['NET AMOUNT', 'Amount SAP', 'Amount Paid Based on Setoff Data', 'Amount Paid']
    for col in num_cols:
        if col == 'Amount Paid' and col not in df_calc.columns and 'Amount Actual Paid' in df_calc.columns:
            df_calc['Amount Paid'] = df_calc['Amount Actual Paid']
        elif col not in df_calc.columns:
            df_calc[col] = 0

    col_status_sap = 'StatusSAP' if 'StatusSAP' in df_calc.columns else 'Status SAP'
    if col_status_sap in df_calc.columns:
        sap_status_clean = df_calc[col_status_sap].astype(str).str.upper().str.strip()
        mask_sap_cleared = sap_status_clean.isin(['CLEARED', 'PAID', 'CLEARED/PAID'])
        df_calc['Amount SAP Filtered'] = np.where(mask_sap_cleared, df_calc['Amount SAP'], 0)
    else:
        df_calc['Amount SAP Filtered'] = df_calc['Amount SAP']

    col_m = 'Payment Month' if 'Payment Month' in df_calc.columns else ('Month' if 'Month' in df_calc.columns else 'Periode Month')
    if col_m not in df_calc.columns:
        return pd.DataFrame(), col_m

    summary = df_calc.groupby(col_m, as_index=False, dropna=False).agg({
        'NET AMOUNT': 'sum',
        'Amount SAP Filtered': 'sum',
        'Amount Paid Based on Setoff Data': 'sum',
        'Amount Paid': 'sum'
    })

    summary['GAP'] = summary['NET AMOUNT'] - summary['Amount Paid Based on Setoff Data']

    grand_total = pd.DataFrame([{
        col_m: 'Grand Total',
        'NET AMOUNT': summary['NET AMOUNT'].sum(),
        'Amount SAP Filtered': summary['Amount SAP Filtered'].sum(),
        'Amount Paid Based on Setoff Data': summary['Amount Paid Based on Setoff Data'].sum(),
        'Amount Paid': summary['Amount Paid'].sum(),
        'GAP': summary['GAP'].sum()
    }])

    return pd.concat([summary, grand_total], ignore_index=True), col_m

df_summary_raw, col_month_name = generate_reimbursement_summary_table(df_filtered)

if not df_summary_raw.empty:
    def fmt_rp(val):
        if abs(val) < 1e-9:
            return "Rp -"
        elif val < 0:
            return f"-Rp {abs(val):,.0f}".replace(",", ".")
        else:
            return f"Rp {val:,.0f}".replace(",", ".")

    rows_html = ""
    for idx, row in df_summary_raw.iterrows():
        val_m = row[col_month_name]
        is_total = (val_m == 'Grand Total')
        if pd.isna(val_m) or str(val_m).strip().lower() in ['nan', 'none', '']:
            val_m = "(blank)"

        row_style = "background-color: #b4c6e7; font-weight: bold;" if is_total else ("background-color: #ffffff;" if idx % 2 == 0 else "background-color: #f2f2f2;")

        rows_html += f"""
        <tr style="{row_style}">
            <td style="text-align: center; border: 1px solid #7f7f7f; padding: 5px;">{val_m}</td>
            <td style="text-align: right; font-weight: bold; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp(row['NET AMOUNT'])}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp(row['Amount SAP Filtered'])}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp(row['Amount Paid Based on Setoff Data'])}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp(row['Amount Paid'])}</td>
            <td style="text-align: right; font-weight: bold; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp(row['GAP'])}</td>
        </tr>
        """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background-color: transparent; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000; }}
        th {{ border: 1px solid #7f7f7f; padding: 6px; text-align: center; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th style="background-color: #d9e1f2; width: 12%;">Payment Month</th>
                    <th style="background-color: #b4c6e7;">NET AMOUNT</th>
                    <th style="background-color: #b4c6e7;">Amount SAP</th>
                    <th style="background-color: #b4c6e7;">Amount Paid Setoff</th>
                    <th style="background-color: #b4c6e7;">Amount Paid</th>
                    <th style="background-color: #b4c6e7;">GAP</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    components.html(full_html, height=450, scrolling=True)

# ==========================================
# 10. REIMBURSEMENT SUMMARY TO TSEL & AGENT
# ==========================================
st.markdown("---")
st.subheader("📊 Reimbursement Summary to TSEL & Agent")

def generate_tsel_agent_summary(df):
    df_calc = df.copy()
    col_m = 'Payment Month' if 'Payment Month' in df_calc.columns else ('Month' if 'Month' in df_calc.columns else 'Periode Month')
    if col_m not in df_calc.columns or 'NET AMOUNT' not in df_calc.columns:
        return pd.DataFrame(), col_m

    col_inv = 'Invoice Agent' if 'Invoice Agent' in df_calc.columns else 'Invoice Agent Status'
    col_dn = 'Status Reimburse Actual' if 'Status Reimburse Actual' in df_calc.columns else ('DN HW' if 'DN HW' in df_calc.columns else 'Status Reimburse')

    inv_series = df_calc[col_inv].astype(str).str.upper().str.strip() if col_inv in df_calc.columns else pd.Series('', index=df_calc.index)
    dn_series = df_calc[col_dn].astype(str).str.upper().str.strip() if col_dn in df_calc.columns else pd.Series('', index=df_calc.index)

    df_calc['INV_DONE'] = np.where(inv_series == 'INVOICE DONE', df_calc['NET AMOUNT'], 0)
    df_calc['INV_NY'] = np.where(inv_series != 'INVOICE DONE', df_calc['NET AMOUNT'], 0)

    df_calc['DN_DONE'] = np.where(dn_series.isin(['PAID', 'DN ISSUED']), df_calc['NET AMOUNT'], 0)
    df_calc['DN_NY'] = np.where(~dn_series.isin(['PAID', 'DN ISSUED']), df_calc['NET AMOUNT'], 0)

    summary = df_calc.groupby(col_m, as_index=False, dropna=False).agg({
        'NET AMOUNT': 'sum',
        'INV_DONE': 'sum',
        'INV_NY': 'sum',
        'DN_DONE': 'sum',
        'DN_NY': 'sum'
    })

    grand_total = pd.DataFrame([{
        col_m: 'Grand Total',
        'NET AMOUNT': summary['NET AMOUNT'].sum(),
        'INV_DONE': summary['INV_DONE'].sum(),
        'INV_NY': summary['INV_NY'].sum(),
        'DN_DONE': summary['DN_DONE'].sum(),
        'DN_NY': summary['DN_NY'].sum()
    }])

    full_summary = pd.concat([summary, grand_total], ignore_index=True)
    full_summary['PCT_TSEL'] = np.where(full_summary['NET AMOUNT'] > 0, (full_summary['INV_DONE'] / full_summary['NET AMOUNT']) * 100, 0.0)
    full_summary['PCT_AGENT'] = np.where(full_summary['NET AMOUNT'] > 0, (full_summary['DN_DONE'] / full_summary['NET AMOUNT']) * 100, 0.0)

    return full_summary, col_m

df_tsel_agent, col_m_name = generate_tsel_agent_summary(df_filtered)

if not df_tsel_agent.empty:
    def fmt_rp_tsel(val):
        if abs(val) < 1e-9:
            return "Rp -"
        elif val < 0:
            return f"-Rp {abs(val):,.0f}".replace(",", ".")
        else:
            return f"Rp {val:,.0f}".replace(",", ".")

    rows_html_tsel = ""
    for idx, row in df_tsel_agent.iterrows():
        val_m = row[col_m_name]
        is_total = (val_m == 'Grand Total')
        if pd.isna(val_m) or str(val_m).strip().lower() in ['nan', 'none', '']:
            val_m = "(blank)"

        row_style = "background-color: #f2f2f2; font-weight: bold;" if is_total else ("background-color: #ffffff;" if idx % 2 == 0 else "background-color: #fafafa;")

        rows_html_tsel += f"""
        <tr style="{row_style}">
            <td style="text-align: center; border: 1px solid #d9d9d9; padding: 5px;">{val_m}</td>
            <td style="text-align: right; font-weight: bold; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_tsel(row['NET AMOUNT'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_tsel(row['INV_DONE'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_tsel(row['INV_NY'])}</td>
            <td style="text-align: center; font-weight: bold; background-color: #fce4d6; border: 1px solid #d9d9d9; padding: 5px;">{row['PCT_TSEL']:.2f}%</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_tsel(row['DN_DONE'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_tsel(row['DN_NY'])}</td>
            <td style="text-align: center; font-weight: bold; background-color: #e2efda; border: 1px solid #d9d9d9; padding: 5px;">{row['PCT_AGENT']:.2f}%</td>
        </tr>
        """

    full_html_tsel = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background-color: transparent; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000; }}
        th {{ border: 1px solid #b0b0b0; padding: 6px; text-align: center; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th rowspan="2" style="background-color: #d9d9d9; width: 10%;">Periode Month</th>
                    <th rowspan="2" style="background-color: #d9d9d9; width: 13%;">NET AMOUNT</th>
                    <th colspan="3" style="background-color: #f8c2a6; color: #000;">Reimbursement to TSEL</th>
                    <th colspan="3" style="background-color: #a9d08e; color: #000;">Reimbursement to Agent</th>
                </tr>
                <tr>
                    <th style="background-color: #fce4d6; width: 13%;">INV. DONE</th>
                    <th style="background-color: #fce4d6; width: 13%;">INV. NY</th>
                    <th style="background-color: #f8c2a6; width: 8%;">% Done</th>
                    <th style="background-color: #e2efda; width: 13%;">DebitNote DONE</th>
                    <th style="background-color: #e2efda; width: 13%;">DebitNote NY</th>
                    <th style="background-color: #a9d08e; width: 8%;">% Done</th>
                </tr>
            </thead>
            <tbody>
                {rows_html_tsel}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    components.html(full_html_tsel, height=450, scrolling=True)

# ==========================================
# 11. RISK VAT HUAWEI SUMMARY
# ==========================================
st.markdown("---")
st.subheader("⚠️ Risk VAT Huawei Summary")

def generate_risk_vat_summary(df):
    df_calc = df.copy()
    col_m = 'Payment Month' if 'Payment Month' in df_calc.columns else ('Month' if 'Month' in df_calc.columns else 'Periode Month')
    if col_m not in df_calc.columns or 'NET AMOUNT' not in df_calc.columns:
        return pd.DataFrame(), col_m

    if 'PPN' not in df_calc.columns:
        if 'VAT Amount' in df_calc.columns:
            df_calc['PPN'] = df_calc['VAT Amount']
        else:
            df_calc['PPN'] = 0.0

    for col in ['NET AMOUNT', 'PPN']:
        if col in df_calc.columns:
            df_calc[col] = (
                df_calc[col]
                .astype(str)
                .str.replace(r'[^\d.-]', '', regex=True)
                .replace('', '0')
            )
            df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0.0)

    col_fp = 'Status FP' if 'Status FP' in df_calc.columns else 'Status_FP'
    fp_series = df_calc[col_fp].astype(str).str.upper().str.strip() if col_fp in df_calc.columns else pd.Series('', index=df_calc.index)

    df_calc['NET_NORMAL'] = np.where(fp_series == 'NORMAL', df_calc['NET AMOUNT'], 0.0)
    df_calc['NET_POTENTIAL'] = np.where(fp_series.isin(['POTENTIAL EXPIRED', 'POTENTIAL EXPIRED ']), df_calc['NET AMOUNT'], 0.0)
    df_calc['NET_EXPIRED'] = np.where(fp_series == 'FP EXPIRED', df_calc['NET AMOUNT'], 0.0)

    mask_expired = (fp_series == 'FP EXPIRED')
    df_calc['FP_EXP_NET_MINUS_VAT'] = np.where(mask_expired, df_calc['NET AMOUNT'] - df_calc['PPN'], 0.0)
    df_calc['VAT_LOSS'] = np.where(mask_expired, df_calc['PPN'], 0.0)

    summary = df_calc.groupby(col_m, as_index=False, dropna=False).agg({
        'NET_NORMAL': 'sum',
        'NET_POTENTIAL': 'sum',
        'NET_EXPIRED': 'sum',
        'NET AMOUNT': 'sum',
        'FP_EXP_NET_MINUS_VAT': 'sum',
        'VAT_LOSS': 'sum'
    })

    grand_total = pd.DataFrame([{
        col_m: 'Grand Total',
        'NET_NORMAL': summary['NET_NORMAL'].sum(),
        'NET_POTENTIAL': summary['NET_POTENTIAL'].sum(),
        'NET_EXPIRED': summary['NET_EXPIRED'].sum(),
        'NET AMOUNT': summary['NET AMOUNT'].sum(),
        'FP_EXP_NET_MINUS_VAT': summary['FP_EXP_NET_MINUS_VAT'].sum(),
        'VAT_LOSS': summary['VAT_LOSS'].sum()
    }])

    return pd.concat([summary, grand_total], ignore_index=True), col_m

df_risk_vat, col_m_vat = generate_risk_vat_summary(df_filtered)

if not df_risk_vat.empty:
    def fmt_rp_vat(val):
        if abs(val) < 1e-9:
            return "Rp -"
        elif val < 0:
            return f"-Rp {abs(val):,.0f}".replace(",", ".")
        else:
            return f"Rp {val:,.0f}".replace(",", ".")

    rows_html_vat = ""
    for idx, row in df_risk_vat.iterrows():
        val_m = row[col_m_vat]
        is_total = (val_m == 'Grand Total')
        if pd.isna(val_m) or str(val_m).strip().lower() in ['nan', 'none', '']:
            val_m = "(blank)"

        row_style = "background-color: #b4c6e7; font-weight: bold;" if is_total else ("background-color: #ffffff;" if idx % 2 == 0 else "background-color: #f2f2f2;")

        rows_html_vat += f"""
        <tr style="{row_style}">
            <td style="text-align: center; border: 1px solid #7f7f7f; padding: 5px;">{val_m}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp_vat(row['NET_NORMAL'])}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp_vat(row['NET_POTENTIAL'])}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp_vat(row['NET_EXPIRED'])}</td>
            <td style="text-align: right; font-weight: bold; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp_vat(row['NET AMOUNT'])}</td>
            <td style="text-align: right; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp_vat(row['FP_EXP_NET_MINUS_VAT'])}</td>
            <td style="text-align: right; font-weight: bold; border: 1px solid #7f7f7f; padding: 5px;">{fmt_rp_vat(row['VAT_LOSS'])}</td>
        </tr>
        """

    full_html_vat = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background-color: transparent; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000; }}
        th {{ border: 1px solid #7f7f7f; padding: 6px; text-align: center; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th rowspan="2" style="background-color: #d9e1f2; width: 12%;">Periode Month</th>
                    <th colspan="4" style="background-color: #ffc000; color: #000;">Net Amount</th>
                    <th rowspan="2" style="background-color: #ffff00; width: 16%;">FP Exp Net Amount-VAT(ppn)</th>
                    <th rowspan="2" style="background-color: #ffff00; width: 14%;">VAT Loss</th>
                </tr>
                <tr>
                    <th style="background-color: #ffc000; width: 14%;">Normal</th>
                    <th style="background-color: #ffc000; width: 14%;">Potential Expired</th>
                    <th style="background-color: #ffc000; width: 14%;">FP Expired</th>
                    <th style="background-color: #ffc000; width: 16%;">Total Net Amount</th>
                </tr>
            </thead>
            <tbody>
                {rows_html_vat}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    components.html(full_html_vat, height=450, scrolling=True)

# ==========================================
# 12. MANAGEMENT FEE PROCESS SUMMARY
# ==========================================
st.markdown("---")
st.subheader("📊 Management Fee Process")

def generate_manfee_summary(df):
    df_calc = df.copy()
    col_m = 'Payment Month' if 'Payment Month' in df_calc.columns else ('Month' if 'Month' in df_calc.columns else 'Periode Month')
    if col_m not in df_calc.columns:
        return pd.DataFrame(), col_m

    manfee_cols = ['Total Manfee', 'Agent Share', 'Huawei Share']
    for col in manfee_cols:
        if col not in df_calc.columns:
            col_match = [c for c in df_calc.columns if col.lower() in c.lower()]
            if col_match:
                df_calc[col] = df_calc[col_match[0]]
            else:
                df_calc[col] = 0.0

    for col in manfee_cols:
        df_calc[col] = (
            df_calc[col]
            .astype(str)
            .str.replace(r'[^\d.-]', '', regex=True)
            .replace('', '0')
        )
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0.0)

    col_status = 'Progress PR Status (RPJ to HTI)'
    if col_status not in df_calc.columns:
        match_st = [c for c in df_calc.columns if 'progress' in c.lower() or 'rpj' in c.lower()]
        col_status = match_st[0] if match_st else 'Status'

    status_series = df_calc[col_status].astype(str).str.upper().str.strip() if col_status in df_calc.columns else pd.Series('', index=df_calc.index)
    is_paid = status_series == 'PAID'

    df_calc['MANFEE_NY'] = np.where(~is_paid, df_calc['Total Manfee'], 0.0)
    df_calc['MANFEE_PAID'] = np.where(is_paid, df_calc['Total Manfee'], 0.0)
    df_calc['AGENT_NY'] = np.where(~is_paid, df_calc['Agent Share'], 0.0)
    df_calc['AGENT_PAID'] = np.where(is_paid, df_calc['Agent Share'], 0.0)
    df_calc['HUAWEI_NY'] = np.where(~is_paid, df_calc['Huawei Share'], 0.0)
    df_calc['HUAWEI_PAID'] = np.where(is_paid, df_calc['Huawei Share'], 0.0)

    summary = df_calc.groupby(col_m, as_index=False, dropna=False).agg({
        'MANFEE_NY': 'sum',
        'MANFEE_PAID': 'sum',
        'AGENT_NY': 'sum',
        'AGENT_PAID': 'sum',
        'HUAWEI_NY': 'sum',
        'HUAWEI_PAID': 'sum'
    })

    grand_total = pd.DataFrame([{
        col_m: '(blank)',
        'MANFEE_NY': summary['MANFEE_NY'].sum(),
        'MANFEE_PAID': summary['MANFEE_PAID'].sum(),
        'AGENT_NY': summary['AGENT_NY'].sum(),
        'AGENT_PAID': summary['AGENT_PAID'].sum(),
        'HUAWEI_NY': summary['HUAWEI_NY'].sum(),
        'HUAWEI_PAID': summary['HUAWEI_PAID'].sum()
    }])

    return pd.concat([summary, grand_total], ignore_index=True), col_m

df_manfee, col_m_mf = generate_manfee_summary(df_filtered)

if not df_manfee.empty:
    def fmt_rp_mf(val):
        if abs(val) < 1e-9:
            return "Rp -"
        elif val < 0:
            return f"-Rp {abs(val):,.0f}".replace(",", ".")
        else:
            return f"Rp {val:,.0f}".replace(",", ".")

    rows_html_mf = ""
    for idx, row in df_manfee.iterrows():
        val_m = row[col_m_mf]
        is_total = (val_m == '(blank)' or val_m == 'Grand Total')
        if pd.isna(val_m) or str(val_m).strip().lower() in ['nan', 'none', '']:
            val_m = "(blank)"

        row_style = "background-color: #ffffff; font-weight: bold;" if is_total else ("background-color: #ffffff;" if idx % 2 == 0 else "background-color: #f9f9f9;")

        rows_html_mf += f"""
        <tr style="{row_style}">
            <td style="text-align: center; border: 1px solid #d9d9d9; padding: 5px;">{val_m}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_mf(row['MANFEE_NY'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_mf(row['MANFEE_PAID'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_mf(row['AGENT_NY'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_mf(row['AGENT_PAID'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_mf(row['HUAWEI_NY'])}</td>
            <td style="text-align: right; border: 1px solid #d9d9d9; padding: 5px;">{fmt_rp_mf(row['HUAWEI_PAID'])}</td>
        </tr>
        """

    full_html_mf = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background-color: transparent; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000; }}
        th {{ border: 1px solid #b0b0b0; padding: 6px; text-align: center; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th rowspan="3" style="background-color: #f2f2f2; width: 10%;">Periode Month</th>
                    <th colspan="6" style="background-color: #e6e6e6; color: #000;">Management Fee</th>
                </tr>
                <tr>
                    <th colspan="2" style="background-color: #fff2cc; width: 30%;">Sum of Total Manfee</th>
                    <th colspan="2" style="background-color: #d9e1f2; width: 30%;">Sum of AGENT Share</th>
                    <th colspan="2" style="background-color: #fce4d6; width: 30%;">Sum of Huawei Share</th>
                </tr>
                <tr>
                    <th style="background-color: #fff2cc; width: 15%;">Not Yet</th>
                    <th style="background-color: #fff2cc; width: 15%;">Paid</th>
                    <th style="background-color: #d9e1f2; width: 15%;">Not Yet</th>
                    <th style="background-color: #d9e1f2; width: 15%;">Paid</th>
                    <th style="background-color: #fce4d6; width: 15%;">Not Yet</th>
                    <th style="background-color: #fce4d6; width: 15%;">Paid</th>
                </tr>
            </thead>
            <tbody>
                {rows_html_mf}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    components.html(full_html_mf, height=450, scrolling=True)

# ==========================================
# 13. STATUS REJECTION SAP SUMMARY
# ==========================================
st.markdown("---")
st.subheader("❌ Status Rejection SAP")

col_area_candidates = ['Area (Khusus SAP)', 'Area', 'Region']
col_pic_candidates = ['PIC Site (Khusus SAP)', 'PIC Site', 'PIC']

col_area = next((c for c in col_area_candidates if c in df_filtered.columns), None)
col_pic = next((c for c in col_pic_candidates if c in df_filtered.columns), None)

df_rej_filtered = df_filtered.copy()

st.markdown("**Filter Rejection SAP**")
f_col1, f_col2 = st.columns(2)

with f_col1:
    if col_area:
        unique_areas = sorted(df_filtered[col_area].dropna().astype(str).unique())
        selected_areas = st.multiselect("Area (Khusus SAP)", options=unique_areas, default=unique_areas, key="rej_area_multiselect")
        if selected_areas:
            df_rej_filtered = df_rej_filtered[df_rej_filtered[col_area].astype(str).isin(selected_areas)]
        else:
            df_rej_filtered = df_rej_filtered.iloc[0:0]

with f_col2:
    if col_pic:
        unique_pics = sorted(df_filtered[col_pic].dropna().astype(str).unique())
        selected_pics = st.multiselect("PIC Site (Khusus SAP)", options=unique_pics, default=unique_pics, key="rej_pic_multiselect")
        if selected_pics:
            df_rej_filtered = df_rej_filtered[df_rej_filtered[col_pic].astype(str).isin(selected_pics)]
        else:
            df_rej_filtered = df_rej_filtered.iloc[0:0]

def generate_rejection_sap_summary(df):
    df_calc = df.copy()
    col_reg = 'new regional' if 'new regional' in df_calc.columns else ('Regional' if 'Regional' in df_calc.columns else None)
    col_inv_type = 'IBS Invoice Type' if 'IBS Invoice Type' in df_calc.columns else ('Invoice Type' if 'Invoice Type' in df_calc.columns else None)
    col_inv_no = 'Invoice No' if 'Invoice No' in df_calc.columns else ('No Invoice' if 'No Invoice' in df_calc.columns else None)
    col_sap = 'StatusSAP' if 'StatusSAP' in df_calc.columns else ('Status SAP' if 'Status SAP' in df_calc.columns else None)

    if not col_reg or not col_inv_type or not col_sap:
        return pd.DataFrame(), None, None, 0, 0.0

    if 'NET AMOUNT' in df_calc.columns:
        df_calc['NET AMOUNT'] = (
            df_calc['NET AMOUNT']
            .astype(str)
            .str.replace(r'[^\d.-]', '', regex=True)
            .replace('', '0')
        )
        df_calc['NET AMOUNT'] = pd.to_numeric(df_calc['NET AMOUNT'], errors='coerce').fillna(0.0)
    else:
        df_calc['NET AMOUNT'] = 0.0

    sap_series = df_calc[col_sap].astype(str).str.upper().str.strip()
    df_rejected = df_calc[sap_series == 'REJECTED'].copy()

    if df_rejected.empty:
        return pd.DataFrame(), col_reg, col_inv_type, 0, 0.0

    summary = df_rejected.groupby([col_reg, col_inv_type], as_index=False, dropna=False).agg(
        Count_of_Invoice_No=(col_inv_no, 'count') if col_inv_no else (col_reg, 'count'),
        Sum_of_NET_AMOUNT=('NET AMOUNT', 'sum')
    )

    summary = summary.sort_values(by=[col_reg, col_inv_type]).reset_index(drop=True)
    total_count = int(summary['Count_of_Invoice_No'].sum())
    total_net = float(summary['Sum_of_NET_AMOUNT'].sum())

    return summary, col_reg, col_inv_type, total_count, total_net

df_reject_summary, col_reg_name, col_type_name, total_inv_count, total_net_amt = generate_rejection_sap_summary(df_rej_filtered)

if not df_reject_summary.empty and col_reg_name:
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; border-radius: 5px;">
            <p style="margin: 0; font-size: 12px; color: #6c757d; font-weight: bold;">Total Count of Invoice No</p>
            <h3 style="margin: 0; color: #212529;">{total_inv_count:,}</h3>
        </div>
        """, unsafe_allow_html=True)
        
    with col_m2:
        formatted_total_net = f"Rp {total_net_amt:,.0f}".replace(",", ".")
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; border-radius: 5px;">
            <p style="margin: 0; font-size: 12px; color: #6c757d; font-weight: bold;">Total NET AMOUNT</p>
            <h3 style="margin: 0; color: #212529;">{formatted_total_net}</h3>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    rows_html_reject = ""
    for idx, row in df_reject_summary.iterrows():
        reg_val = row[col_reg_name]
        type_val = row[col_type_name]
        cnt_val = row['Count_of_Invoice_No']
        net_val = row['Sum_of_NET_AMOUNT']
        
        formatted_net = f"Rp {net_val:,.0f}".replace(",", ".")
        row_bg = "#ffffff" if idx % 2 == 0 else "#f9f9f9"

        rows_html_reject += f"""
        <tr style="background-color: {row_bg};">
            <td style="border: 1px solid #d9d9d9; padding: 6px; text-align: left;">{reg_val}</td>
            <td style="border: 1px solid #d9d9d9; padding: 6px; text-align: center;">{type_val}</td>
            <td style="border: 1px solid #d9d9d9; padding: 6px; text-align: center;">{cnt_val:,}</td>
            <td style="border: 1px solid #d9d9d9; padding: 6px; text-align: right;">{formatted_net}</td>
        </tr>
        """

    full_html_reject = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background-color: transparent; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000; }}
        th {{ border: 1px solid #b0b0b0; padding: 8px; text-align: center; background-color: #f2f2f2; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th style="width: 35%;">new regional</th>
                    <th style="width: 15%;">IBS Invoice Type</th>
                    <th style="width: 20%;">Count of Invoice No</th>
                    <th style="width: 30%;">Sum of NET AMOUNT</th>
                </tr>
            </thead>
            <tbody>
                {rows_html_reject}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    components.html(full_html_reject, height=350, scrolling=True)
else:
    st.info("Tidak ada data dengan Status SAP 'Rejected' yang sesuai dengan pilihan filter saat ini.")


# ==========================================
# STATUS TRACKING INV BM
# ==========================================
st.markdown("---")
st.subheader("📊 Status Tracking Invoice BM")

df_source = df_filtered.copy()
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

df_trk_filtered = df_source.copy()
if sel_area != "All" and col_area:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_area].astype(str) == sel_area]
if sel_year != "All" and col_year:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_year].astype(str) == sel_year]
if sel_pic != "All" and col_pic:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_pic].astype(str) == sel_pic]
if sel_reg != "All" and col_reg:
    df_trk_filtered = df_trk_filtered[df_trk_filtered[col_reg].astype(str) == sel_reg]

def generate_tracking_invoice_table(df_input):
    df_trk = df_input.copy()
    col_reg_t = next((c for c in ['new regional', 'Regional', 'regional'] if c in df_trk.columns), 'Regional')
    col_supp_t = next((c for c in ['Supplier Name', 'Supplier', 'supplier_name'] if c in df_trk.columns), 'Supplier Name')
    col_site_t = next((c for c in ['Site ID', 'SiteID', 'site_id'] if c in df_trk.columns), 'Site ID')
    col_inv_no = next((c for c in ['Invoice No.', 'Invoice No', 'Invoice Number'] if c in df_trk.columns), 'Invoice No.')
    col_m_t = next((c for c in ['Month', 'Payment Month', 'Month Name'] if c in df_trk.columns), 'Month')

    for col_req in [col_reg_t, col_supp_t, col_site_t]:
        if col_req not in df_trk.columns:
            df_trk[col_req] = "-"

    if col_inv_no not in df_trk.columns:
        df_trk[col_inv_no] = 1

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    components.html(full_trk_html, height=480, scrolling=False)
else:
    st.warning("Data Tracking Invoice tidak ditemukan berdasarkan filter yang dipilih.")
