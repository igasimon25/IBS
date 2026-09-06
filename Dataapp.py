import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ==========================================
# 1. KONFIGURASI HALAMAN & HEADER
# ==========================================
st.set_page_config(
    page_title="Dashboard POB IBS Building Management",
    page_icon="📊",
    layout="wide"
)

st.title("📊 DASHBOARD POB IBS BUILDING MANAGEMENT")
st.markdown("---")

# ==========================================
# 2. BACA DATA DARI GOOGLE SHEETS & DATA CLEANING
# ==========================================
# Link Google Sheets Publik yang diubah ke format CSV Export
SHEET_ID = "1g3Y6GjXUgjWFtKxC9ul8i0vZgHvamkDwT7j4-_95NMk"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=600)  # Caching selama 10 menit agar update data terdeteksi otomatis
def load_data():
    df = pd.read_csv(GSHEET_URL)
    df.columns = df.columns.astype(str).str.strip()
    
    # 🛠️ PEMBERSIHAN KOLOM AREA
    if 'Area' in df.columns:
        df['Area'] = (
            df['Area']
            .astype(str)
            .str.strip()
            .str.title()
        )
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

# Filter Area
if 'Area' in df_raw.columns:
    raw_areas = df_raw['Area'].dropna().unique().tolist()
    clean_areas = sorted([str(x) for x in raw_areas if str(x).lower() != 'nan'])
    list_area = ["(All)"] + clean_areas
    selected_area = st.sidebar.selectbox("Area Filter", options=list_area, index=0)
    
    if selected_area != "(All)":
        df_filtered = df_filtered[df_filtered['Area'] == selected_area]

# Filter Payment Month
col_month = 'Payment Month' if 'Payment Month' in df_filtered.columns else ('Month' if 'Month' in df_filtered.columns else None)
if col_month and col_month in df_filtered.columns:
    list_month = ["(All Months)"] + [str(x) for x in df_filtered[col_month].dropna().unique().tolist()]
    selected_month = st.sidebar.selectbox("Payment Month Filter", options=list_month, index=0)
    if selected_month != "(All Months)":
        df_filtered = df_filtered[df_filtered[col_month].astype(str) == selected_month]

# Filter New Regional
if 'new regional' in df_filtered.columns:
    list_reg = ["(All Regionals)"] + [str(x) for x in df_filtered['new regional'].dropna().unique().tolist()]
    selected_reg = st.sidebar.selectbox("New Regional Filter", options=list_reg, index=0)
    if selected_reg != "(All Regionals)":
        df_filtered = df_filtered[df_filtered['new regional'].astype(str) == selected_reg]

# ==========================================
# FUNGSI HELPER: COMPACT DONUT CHART (KPI)
# ==========================================
def create_compact_donut_card(title, paid_val, ny_val, color_done='#558B2F', color_ny='#E53935', element_key=None):
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
            x=0.5, y=0.5,
            font_size=15,
            showarrow=False,
            font_color="#000000"
        )],
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(l=5, r=5, t=5, b=5),
        height=180
    )

    # Tambahkan parameter key unik
    st.plotly_chart(fig, use_container_width=True, key=element_key)

    st.markdown(f"""
    <div style='font-size: 11px; text-align: center; color: #555;'>
        Done: <b>Rp {paid_m:,.2f}M</b><br>
        NY: <b>Rp {ny_m:,.2f}M</b>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# 4. 5 CHART KPI SEJAJAR HORIZONTAL
# ==========================================
st.subheader("📌 Key Performance Indicators (KPI Overview)")

col1, col2, col3, col4, col5 = st.columns(5)

val_payout_bm = 0
val_huawei_agent = 0
val_agent_tsel = 0
val_dn_issued = 0
val_payin_huawei = 0

# 1. Total Payout to BM
with col1:
    df_c1 = df_filtered.copy()
    col_status, col_amt = 'Status', 'Invoice Amount'
    if col_status in df_c1.columns and col_amt in df_c1.columns:
        df_c1[col_amt] = pd.to_numeric(df_c1[col_amt], errors='coerce').fillna(0)
        mask_paid = df_c1[col_status].astype(str).str.upper().str.strip() == 'PAID'
        val_payout_bm = df_c1[mask_paid][col_amt].sum()
        ny_val = df_c1[~mask_paid][col_amt].sum()
        create_compact_donut_card("Total Payout to BM", val_payout_bm, ny_val, element_key="kpi_payout_bm")
    else:
        st.warning("Kolom N/A")

# 2. Huawei To Agent
with col2:
    df_c2 = df_filtered.copy()
    col_status, col_amt = 'Status', 'NET AMOUNT'
    if col_status in df_c2.columns and col_amt in df_c2.columns:
        df_c2[col_amt] = pd.to_numeric(df_c2[col_amt], errors='coerce').fillna(0)
        mask_paid = df_c2[col_status].astype(str).str.upper().str.strip() == 'PAID'
        val_huawei_agent = df_c2[mask_paid][col_amt].sum()
        ny_val = df_c2[~mask_paid][col_amt].sum()
        create_compact_donut_card("Huawei To Agent", val_huawei_agent, ny_val, element_key="kpi_huawei_agent")
    else:
        st.warning("Kolom N/A")

# 3. Agent To Telkomsel
with col3:
    df_c3 = df_filtered.copy()
    col_status, col_amt, col_inv = 'Status', 'NET AMOUNT', 'Invoice Agent'
    if col_inv in df_c3.columns:
        df_c3 = df_c3[df_c3[col_inv].astype(str).str.upper().str.strip() == 'INVOICE DONE']
    if col_status in df_c3.columns and col_amt in df_c3.columns:
        df_c3[col_amt] = pd.to_numeric(df_c3[col_amt], errors='coerce').fillna(0)
        mask_paid = df_c3[col_status].astype(str).str.upper().str.strip() == 'PAID'
        val_agent_tsel = df_c3[mask_paid][col_amt].sum()
        ny_val = df_c3[~mask_paid][col_amt].sum()
        create_compact_donut_card("Agent To Telkomsel", val_agent_tsel, ny_val, element_key="kpi_agent_tsel")
    else:
        st.warning("Kolom N/A")

# 4. DN Issued
with col4:
    df_c4 = df_filtered.copy()
    col_status, col_amt = 'Status Reimburse Actual', 'NET AMOUNT'
    if col_status in df_c4.columns and col_amt in df_c4.columns:
        df_c4[col_amt] = pd.to_numeric(df_c4[col_amt], errors='coerce').fillna(0)
        status_clean = df_c4[col_status].astype(str).str.upper().str.strip()
        mask_done = status_clean.isin(['PAID', 'DN ISSUED'])
        val_dn_issued = df_c4[mask_done][col_amt].sum()
        ny_val = df_c4[~mask_done][col_amt].sum()
        create_compact_donut_card("DN Issued", val_dn_issued, ny_val, element_key="kpi_dn_issued")
    else:
        st.warning("Kolom N/A")

# 5. Total Pay In To Huawei
with col5:
    df_c5 = df_filtered.copy()
    col_status = 'Status Reimburse Actual'
    col_amt = 'NET AMOUNT'
    
    if col_status in df_c5.columns and col_amt in df_c5.columns:
        df_c5[col_amt] = pd.to_numeric(df_c5[col_amt], errors='coerce').fillna(0)
        status_clean = df_c5[col_status].astype(str).str.upper().str.strip()
        
        mask_paid = status_clean == 'PAID'
        val_payin_huawei = df_c5[mask_paid][col_amt].sum()
        
        mask_ny = status_clean.isin(['DN ISSUED', 'NY ISSUE DN'])
        ny_val = df_c5[mask_ny][col_amt].sum()
        
        create_compact_donut_card("Total Pay In To Huawei", val_payin_huawei, ny_val, element_key="kpi_payin_huawei")
    else:
        st.warning("Kolom Status Reimburse Actual / NET AMOUNT N/A")

st.markdown("---")

# ==========================================
# 5. STATUS PAY OUT (TABLE MAPPING)
# ==========================================
st.subheader("📋 Status Pay Out")

col_status = 'Status'
col_amount = 'Invoice Amount'

if col_status in df_filtered.columns and col_amount in df_filtered.columns:
    df_status_calc = df_filtered.copy()
    df_status_calc[col_amount] = pd.to_numeric(df_status_calc[col_amount], errors='coerce').fillna(0)

    target_statuses = [
        "MODIFY REQUEST",
        "PAID",
        "Wait for Cashier",
        "WAITING FOR APW PROCESS",
        "Waiting for Accounting",
        "WAITING MGR APPROVAL",
        "WAITING PAYMENT APPROVAL"
    ]

    grouped = df_status_calc.groupby(df_status_calc[col_status].astype(str).str.strip(), as_index=False)[col_amount].sum()
    status_dict = {str(k).upper().strip(): v for k, v in zip(grouped[col_status], grouped[col_amount])}

    st.markdown("""
        <style>
        .status-box {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 8px 12px;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            color: #333333;
            margin-bottom: 6px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .amount-box {
            background-color: #8faadc;
            border: 1px solid #6c8ebf;
            border-radius: 8px;
            padding: 8px 12px;
            text-align: center;
            font-size: 14px;
            font-weight: bold;
            color: #111111;
            margin-bottom: 6px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
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
# 6. END-TO-END PROCESS WORKFLOW & SLA
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
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: transparent; margin: 0; padding: 5px; }}
    .flow-container {{ display: flex; flex-direction: column; gap: 20px; width: 100%; }}
    .flow-row {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }}
    .flow-card-wrapper {{ display: flex; flex-direction: column; align-items: center; flex: 1; }}
    .amount-badge {{ background: linear-gradient(180deg, #1f497d 0%, #0d284a 100%); color: white; font-weight: bold; font-size: 11px; padding: 5px 8px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); margin-bottom: -12px; z-index: 10; width: 85%; text-align: center; white-space: nowrap; }}
    .flow-card {{ border-radius: 8px; padding: 18px 8px 10px 8px; width: 100%; min-height: 95px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; font-size: 11px; font-weight: 600; box-shadow: 0 2px 5px rgba(0,0,0,0.08); border: 1px solid #ccc; box-sizing: border-box; }}
    .card-huawei {{ background-color: #dce6f1; border-color: #b8cce4; color: #1f497d; }}
    .card-rpj {{ background-color: #fce4d6; border-color: #f8c2a6; color: #c65911; }}
    .card-telkomsel {{ background-color: #fff2cc; border-color: #ffe599; color: #806000; }}
    .sla-label {{ font-size: 10px; font-weight: bold; color: #555; margin-top: 6px; }}
    .arrow-right {{ font-size: 20px; color: #1f497d; font-weight: bold; margin-top: 45px; }}
    .arrow-down {{ font-size: 22px; color: #1f497d; font-weight: bold; text-align: right; padding-right: 40px; margin-top: -10px; margin-bottom: -10px; }}
    .legend-container {{ display: flex; justify-content: flex-end; gap: 15px; margin-top: 20px; }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: bold; color: #333; }}
    .legend-box {{ width: 30px; height: 14px; border-radius: 3px; border: 1px solid #ccc; }}
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
            <div class="flow-card card-huawei">
                <b>Huawei Submit Reimbursement Data to Agent</b>
                <span style="font-size: 8.5px; font-weight: normal; margin-top: 4px; line-height: 1.2;">
                    1. Summary Cover | 4. Tax Invoice (FP)<br>
                    2. Invoice BM | 5. Stand meter (kWh)<br>
                    3. Pay Slip | 6. XLX detail Calculation
                </span>
            </div>
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
            <div style="font-size: 14px; margin-bottom: -6px; z-index: 11;">🏅</div>
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
<div class="legend-container">
    <div class="legend-item"><div class="legend-box" style="background-color: #dce6f1; border-color: #b8cce4;"></div> Huawei</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #fff2cc; border-color: #ffe599;"></div> Telkomsel</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #fce4d6; border-color: #f8c2a6;"></div> RPJ (Agent)</div>
</div>
</body>
</html>
"""

components.html(html_content, height=440, scrolling=False)

st.markdown("---")

# ==========================================
# 7. PAYOUT & PAYIN BY AREA
# ==========================================
st.subheader("📊 Payout (Bn IDR) & Payin (Bn IDR)")

if 'Area' in df_filtered.columns:
    raw_unique_areas = df_filtered['Area'].dropna().unique().tolist()
    unique_areas = sorted([str(x) for x in raw_unique_areas if str(x).lower() != 'nan'])
    
    def draw_area_donut(title, done_bn, ny_bn, color_main, element_key=None):
        total_bn = done_bn + ny_bn
        pct_done = (done_bn / total_bn * 100) if total_bn > 0 else 0.0
        
        st.markdown(f"""
            <div style='background-color: #f0f0f0; padding: 4px 10px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 13px; color: #111;'>
                {title}
            </div>
        """, unsafe_allow_html=True)
        
        fig = go.Figure(data=[go.Pie(
            labels=['Done', 'Not Yet Paid'],
            values=[done_bn, ny_bn],
            hole=0.68,
            marker=dict(colors=[color_main, '#FFC000']),
            textinfo='none',
            hovertemplate="<b>%{label}</b><br>Nominal: %{value:.2f} Bn IDR<extra></extra>"
        )])
        
        fig.update_layout(
            annotations=[dict(
                text=f"<b>{pct_done:.1f}%</b>",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False,
                font_color="#000000"
            )],
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=160,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, key=element_key)
        
        st.markdown(f"""
            <div style='text-align: center; font-size: 11px; font-weight: bold; color: #222; margin-top: -10px;'>
                <span style='color: #888;'>NY: {ny_bn:,.2f}</span> | <span>Done: {done_bn:,.2f}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        .area-container {
            background-color: #a6a6a6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='area-container'>", unsafe_allow_html=True)
        
        for area_name in unique_areas:
            df_area = df_filtered[df_filtered['Area'] == area_name]
            
            col_amt_payout = 'Invoice Amount' if 'Invoice Amount' in df_area.columns else 'NET AMOUNT'
            if 'Status' in df_area.columns and col_amt_payout in df_area.columns:
                payout_series = pd.to_numeric(df_area[col_amt_payout], errors='coerce').fillna(0)
                mask_payout_done = df_area['Status'].astype(str).str.upper().str.strip() == 'PAID'
                payout_done_bn = payout_series[mask_payout_done].sum() / 1_000_000_000
                payout_ny_bn = payout_series[~mask_payout_done].sum() / 1_000_000_000
            else:
                payout_done_bn, payout_ny_bn = 0.0, 0.0

            col_amt_payin = 'NET AMOUNT'
            if 'Status Reimburse Actual' in df_area.columns and col_amt_payin in df_area.columns:
                payin_series = pd.to_numeric(df_area[col_amt_payin], errors='coerce').fillna(0)
                status_area_clean = df_area['Status Reimburse Actual'].astype(str).str.upper().str.strip()
                
                mask_payin_done = status_area_clean == 'PAID'
                mask_payin_ny = status_area_clean.isin(['DN ISSUED', 'NY ISSUE DN'])
                
                payin_done_bn = payin_series[mask_payin_done].sum() / 1_000_000_000
                payin_ny_bn = payin_series[mask_payin_ny].sum() / 1_000_000_000
            else:
                payin_done_bn, payin_ny_bn = 0.0, 0.0

            c_payout, c_payin = st.columns(2)
            clean_area_key = str(area_name).replace(" ", "_").lower()
            with c_payout:
                draw_area_donut(f"Progress Payout {area_name}", payout_done_bn, payout_ny_bn, color_main='#70AD47', element_key=f"area_payout_{clean_area_key}")
            with c_payin:
                draw_area_donut(f"Progress Payin {area_name}", payin_done_bn, payin_ny_bn, color_main='#ED7D31', element_key=f"area_payin_{clean_area_key}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("Kolom 'Area' tidak ditemukan pada dataset.")

st.markdown("---")

# ==========================================
# 8. INVOICE REGIONAL (INVOICE PROCESS)
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

col_reg = 'new regional'
col_status_sap = 'StatusSAP'
col_net_amt = 'NET AMOUNT'

if col_reg in df_inv_reg.columns and col_status_sap in df_inv_reg.columns and col_net_amt in df_inv_reg.columns:
    df_inv_reg[col_net_amt] = pd.to_numeric(df_inv_reg[col_net_amt], errors='coerce').fillna(0)
    
    target_order = [
        "R03_Jakarta Banten",
        "R12_Eastern Jabotabek",
        "R04_Jawa Barat",
        "R08_Kalimantan",
        "R09_Sulawesi",
        "R11_Maluku dan Papua"
    ]
    
    available_regionals = df_inv_reg[col_reg].dropna().unique().tolist()
    ordered_regionals = [r for r in target_order if r in available_regionals]
    for r in available_regionals:
        if r not in ordered_regionals and str(r).lower() != 'nan':
            ordered_regionals.append(r)
    
    st.markdown("""
        <style>
        .regional-container {
            background-color: #a6a6a6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .regional-card-title {
            background-color: #ffffff;
            color: #000000;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
            padding: 6px;
            border-radius: 4px;
            margin-bottom: 10px;
            text-decoration: underline;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='regional-container'>", unsafe_allow_html=True)
        
        num_cols = 3
        cols = st.columns(num_cols)
        
        for idx, reg_name in enumerate(ordered_regionals):
            col_target = cols[idx % num_cols]
            
            df_reg = df_inv_reg[df_inv_reg[col_reg].astype(str) == reg_name]
            status_sap_clean = df_reg[col_status_sap].astype(str).str.upper().str.strip()
            
            mask_done = status_sap_clean.isin(['CLEARED', 'PAID', 'CLEARED/PAID'])
            done_val = df_reg[mask_done][col_net_amt].sum()
            done_m = done_val / 1_000_000_000
            
            ny_val = df_reg[~mask_done][col_net_amt].sum()
            ny_m = ny_val / 1_000_000_000
            
            total_m = done_m + ny_m
            pct_done = (done_m / total_m * 100) if total_m > 0 else 0.0
            
            text_done = f"{done_m:.2f}".replace('.', ',')
            text_ny = f"{ny_m:.2f}".replace('.', ',')
            
            with col_target:
                st.markdown(f"<div class='regional-card-title'>{reg_name}</div>", unsafe_allow_html=True)
                
                color_ny = '#E67E22' if idx >= 3 else '#A6A6A6'
                
                fig = go.Figure(data=[go.Pie(
                    labels=['Cleared/Paid', 'Not Yet Paid'],
                    values=[done_m, ny_m],
                    text=[text_done, text_ny],
                    textinfo='text',
                    textposition='inside',
                    hole=0.65,
                    marker=dict(colors=['#2F5597', color_ny]),
                    hovertemplate="<b>%{label}</b><br>Nominal: Rp %{value:.2f} M<extra></extra>"
                )])
                
                fig.update_layout(
                    annotations=[dict(
                        text=f"<b>{pct_done:.2f}%</b>".replace('.', ','),
                        x=0.5, y=0.5,
                        font_size=15,
                        showarrow=False,
                        font_color="#000000"
                    )],
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=200,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                clean_reg_key = str(reg_name).replace(" ", "_").replace("-", "_").lower()
                st.plotly_chart(fig, use_container_width=True, key=f"regional_chart_{clean_reg_key}_{idx}")
                st.markdown("<br>", unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("Kolom 'new regional', 'StatusSAP', atau 'NET AMOUNT' tidak ditemukan dalam dataset.")

st.markdown("---")

# ==========================================
# 9. PROCESS REIMBURSEMENT SUMMARY TABLE (BERWARNA)
# ==========================================
st.subheader("📊 Process Reimbursement Summary")

def generate_reimbursement_summary_table(df):
    df_calc = df.copy()

    # 1. Bersihkan & Petakan Kolom Numerik (Logika & Formula Asli)
    num_cols = ['NET AMOUNT', 'Amount SAP', 'Amount Paid Based on Setoff Data', 'Amount Paid']
    for col in num_cols:
        if col == 'Amount Paid' and col not in df_calc.columns and 'Amount Actual Paid' in df_calc.columns:
            df_calc['Amount Paid'] = pd.to_numeric(df_calc['Amount Actual Paid'], errors='coerce').fillna(0)
        elif col in df_calc.columns:
            df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)
        else:
            df_calc[col] = 0

    # 2. Filter Khusus Kolom Amount SAP berdasarkan Status SAP ("CLEARED" atau "PAID")
    col_status_sap = 'StatusSAP' if 'StatusSAP' in df_calc.columns else ('Status SAP' if 'Status SAP' in df_calc.columns else None)
    if col_status_sap:
        sap_status_clean = df_calc[col_status_sap].astype(str).str.upper().str.strip()
        mask_sap_cleared = sap_status_clean.isin(['CLEARED', 'PAID', 'CLEARED/PAID'])
        df_calc['Amount SAP Filtered'] = np.where(mask_sap_cleared, df_calc['Amount SAP'], 0)
    else:
        df_calc['Amount SAP Filtered'] = df_calc['Amount SAP']

    # 3. Identifikasi Kolom Payment Month
    col_m = 'Payment Month' if 'Payment Month' in df_calc.columns else ('Month' if 'Month' in df_calc.columns else 'Periode Month')
    if col_m not in df_calc.columns:
        st.warning("Kolom Payment Month tidak ditemukan.")
        return pd.DataFrame(), col_m

    # 4. GroupBy berdasarkan Rows: Payment Month & Values: Sum of Kolom
    summary = df_calc.groupby(col_m, as_index=False, dropna=False).agg({
        'NET AMOUNT': 'sum',
        'Amount SAP Filtered': 'sum',
        'Amount Paid Based on Setoff Data': 'sum',
        'Amount Paid': 'sum'
    })

    # 5. Pengurutan Kronologis Payment Month (Lama -> Baru)
    summary['date_parsed'] = pd.to_datetime(summary[col_m].astype(str), format='%b-%y', errors='coerce')
    valid_dates = summary[summary['date_parsed'].notna()].sort_values('date_parsed', ascending=True)
    invalid_dates = summary[summary['date_parsed'].isna()]
    
    summary = pd.concat([valid_dates, invalid_dates], ignore_index=True)
    summary = summary.drop(columns=['date_parsed'])

    # 6. Formulas: Hitung GAP = Sum of NET AMOUNT - Sum of Amount Paid Based on Setoff Data
    summary['GAP'] = summary['NET AMOUNT'] - summary['Amount Paid Based on Setoff Data']

    # 7. Baris Grand Total
    grand_total = pd.DataFrame([{
        col_m: 'Grand Total',
        'NET AMOUNT': summary['NET AMOUNT'].sum(),
        'Amount SAP Filtered': summary['Amount SAP Filtered'].sum(),
        'Amount Paid Based on Setoff Data': summary['Amount Paid Based on Setoff Data'].sum(),
        'Amount Paid': summary['Amount Paid'].sum(),
        'GAP': summary['GAP'].sum()
    }])

    summary_final = pd.concat([summary, grand_total], ignore_index=True)

    return summary_final, col_m

# Menghasilkan Dataframe Raw (Angka Murni)
df_summary_raw, col_month_name = generate_reimbursement_summary_table(df_filtered)

if not df_summary_raw.empty:
    # Helper Format Rupiah Sesuai Excel/Gambar
    def fmt_rp(val):
        if abs(val) < 1e-9:
            return "Rp -"
        elif val < 0:
            return f"-Rp {abs(val):,.0f}".replace(",", ".")
        else:
            return f"Rp {val:,.0f}".replace(",", ".")

    # Render Tabel HTML Berwarna
    rows_html = ""
    for idx, row in df_summary_raw.iterrows():
        val_m = row[col_month_name]
        is_total = (val_m == 'Grand Total')
        
        # Penanganan Label Kosong/None
        if pd.isna(val_m) or str(val_m).strip().lower() in ['nan', 'none', '']:
            val_m = "(blank)"

        row_class = "row-total" if is_total else ("row-even" if idx % 2 == 0 else "row-odd")

        rows_html += f"""
        <tr class="{row_class}">
            <td class="align-center">{val_m}</td>
            <td class="align-right col-bold">{fmt_rp(row['NET AMOUNT'])}</td>
            <td class="align-right">{fmt_rp(row['Amount SAP Filtered'])}</td>
            <td class="align-right">{fmt_rp(row['Amount Paid Based on Setoff Data'])}</td>
            <td class="align-right">{fmt_rp(row['Amount Paid'])}</td>
            <td class="align-right col-bold">{fmt_rp(row['GAP'])}</td>
        </tr>
        """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: transparent; }}
        .process-table {{ width: 100%; border-collapse: collapse; font-size: 11px; color: #000000; }}
        .process-table th, .process-table td {{ border: 1px solid #7f7f7f; padding: 5px 8px; white-space: nowrap; }}
        
        /* Stylings & Colors Sesuai Excel */
        .hdr-month {{ background-color: #d9e1f2; font-weight: bold; text-align: center; vertical-align: middle; }}
        .hdr-blue {{ background-color: #b4c6e7; font-weight: bold; text-align: center; vertical-align: middle; }}
        
        .row-total {{ font-weight: bold; background-color: #b4c6e7; }}
        .row-even {{ background-color: #ffffff; }}
        .row-odd {{ background-color: #f2f2f2; }}
        
        .align-center {{ text-align: center; }}
        .align-right {{ text-align: right; }}
        .col-bold {{ font-weight: bold; }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto;">
        <table class="process-table">
            <thead>
                <tr>
                    <th class="hdr-month" style="width: 12%;">Payment Month</th>
                    <th class="hdr-blue" style="width: 18%;">Sum of NET AMOUNT</th>
                    <th class="hdr-blue" style="width: 20%;">Sum of Amount SAP (Cleared/Paid)</th>
                    <th class="hdr-blue" style="width: 20%;">Sum of Amount Paid Based on Setoff Data</th>
                    <th class="hdr-blue" style="width: 15%;">Sum of Amount Paid</th>
                    <th class="hdr-blue" style="width: 15%;">Sum of GAP</th>
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

    components.html(full_html, height=400, scrolling=True)