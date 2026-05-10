import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="CIS Touren-Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    @import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Satoshi', sans-serif; }
    
    .metric-card {
        background: #f9f8f5;
        border: 1px solid rgba(40,37,29,0.10);
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 4px rgba(40,37,29,0.06);
    }
    .metric-card .label { font-size: 0.78rem; color: #7a7974; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500; }
    .metric-card .value { font-size: 2rem; font-weight: 700; color: #28251d; line-height: 1.2; }
    .metric-card .delta { font-size: 0.82rem; margin-top: 0.2rem; }
    .metric-card .delta.pos { color: #437a22; }
    .metric-card .delta.neg { color: #a12c7b; }
    
    .status-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-on-time { background: #d4dfcc; color: #1e3f0a; }
    .badge-delay { background: #e0ced7; color: #561740; }
    .badge-early { background: #c6d8e4; color: #0b3751; }
    
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #28251d;
        margin-bottom: 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #01696f;
        display: inline-block;
    }
    
    [data-testid="stSidebar"] { background: #1c1b19; }
    [data-testid="stSidebar"] * { color: #cdccca !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stDateInput label { color: #cdccca !important; }
    
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    
    div[data-testid="stMetric"] {
        background: #f9f8f5;
        border: 1px solid rgba(40,37,29,0.10);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 4px rgba(40,37,29,0.06);
    }
</style>
""", unsafe_allow_html=True)


# ── DATA LOADING ──────────────────────────────────────────────────────────────

@st.cache_data
def load_data(uploaded_file=None):
    """Load and preprocess the CIS dataset."""
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    else:
        return pd.DataFrame()

    # lower the case of column names
    df.columns = df.columns.str.lower()
    
    df = df[['lkwnr','fahrername','tournr','tourstation_id','name1',
              'ankunft','tats_ankunft','abfahrt','tats_abfahrt',
              'plz','ort','strasse','geox','geoy']]
    
    # Parse datetime columns
    dt_cols = ['ankunft','tats_ankunft','abfahrt','tats_abfahrt']
    for col in dt_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col]
                .astype(str)
                .str.replace("\xa0", " ", regex=False)
                .str.strip(),
                format="%d.%m.%Y %H:%M",
                errors="coerce"
            )
            # Also try date-only format
            mask = df[col].isna()
            if mask.any():
                df.loc[mask, col] = pd.to_datetime(df.loc[mask, col], errors='coerce')

    # only keep rows that make sense in time
    # df = df[df.tats_ankunft <= df.tats_abfahrt]

    # Compute delay metrics (in minutes)
    if 'ankunft' in df.columns and 'tats_ankunft' in df.columns:
        df['verzoegerung_ankunft_min'] = (
            (df['tats_ankunft'] - df['ankunft']).dt.total_seconds() / 60
        ).round(1)
    
    if 'abfahrt' in df.columns and 'tats_abfahrt' in df.columns:
        df['verzoegerung_abfahrt_min'] = (
            (df['tats_abfahrt'] - df['abfahrt']).dt.total_seconds() / 60
        ).round(1)

    # Status classification
    def classify(delay):
        if pd.isna(delay): return 'Unbekannt'
        if delay > 15: return 'Verspätet'
        if delay < -5: return 'Zu früh'
        return 'Pünktlich'
    
    if 'verzoegerung_ankunft_min' in df.columns:
        df['status'] = df['verzoegerung_ankunft_min'].apply(classify)

    # Extract date for filtering
    if 'tats_ankunft' in df.columns:
        df['datum'] = df['tats_ankunft'].dt.date

    return df


def format_delay(minutes):
    if pd.isna(minutes): return "–"
    sign = "+" if minutes > 0 else ""
    return f"{sign}{minutes:.0f} Min"


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## CIS Dashboard")
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        "📂 Excel-Datei hochladen",
        type=["xlsx", "xls"],
        help="CIS-Daten.xlsx hochladen"
    )
    
    st.markdown("---")
    
    df_raw = load_data(uploaded_file)
    
    if df_raw.empty:
        st.info("Bitte lade eine CIS Excel-Datei hoch, um das Dashboard zu aktivieren.")
        st.markdown("""
        **Erwartete Spalten:**
        - LKWNR, FAHRERNAME, TOURNR
        - ANKUNFT, TATS_ANKUNFT
        - ABFAHRT, TATS_ABFAHRT
        - NAME1, PLZ, ORT, STRASSE
        - GEOX, GEOY
        """)
        st.stop()
    
    # Filters
    st.markdown("### Filter")
    
    # Date range
    if 'datum' in df_raw.columns:
        min_date = df_raw['datum'].min()
        max_date = df_raw['datum'].max()
        date_range = st.date_input(
            "Zeitraum",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    else:
        date_range = None
    
    # Tour filter
    all_tours = sorted(df_raw['tournr'].dropna().unique().tolist()) if 'tournr' in df_raw.columns else []
    selected_tours = st.multiselect("Tour-Nummer", options=all_tours, default=[])
    
    # Customer filter
    all_customers = sorted(df_raw['name1'].dropna().unique().tolist()) if 'name1' in df_raw.columns else []
    selected_customers = st.multiselect("Kunde / Station", options=all_customers, default=[])
    
    # Driver filter
    all_drivers = sorted(df_raw['fahrername'].dropna().unique().tolist()) if 'fahrername' in df_raw.columns else []
    selected_drivers = st.multiselect("Fahrer", options=all_drivers, default=[])
    
    # Status filter
    if 'status' in df_raw.columns:
        all_statuses = df_raw['status'].unique().tolist()
        selected_statuses = st.multiselect("Status", options=all_statuses, default=all_statuses)
    else:
        selected_statuses = []

    st.markdown("---")
    st.markdown("#### Verzögerungs-Schwelle")
    delay_threshold = st.slider("Verspätet ab (Min.)", min_value=0, max_value=120, value=15, step=5)


# ── DATA FILTERING ────────────────────────────────────────────────────────────

df = df_raw.copy()

if date_range and 'datum' in df.columns and len(date_range) == 2:
    df = df[(df['datum'] >= date_range[0]) & (df['datum'] <= date_range[1])]

if selected_tours:
    df = df[df['tournr'].isin(selected_tours)]

if selected_customers:
    df = df[df['name1'].isin(selected_customers)]

if selected_drivers:
    df = df[df['fahrername'].isin(selected_drivers)]

if selected_statuses and 'status' in df.columns:
    df = df[df['status'].isin(selected_statuses)]

# Recompute status with custom threshold
if 'verzoegerung_ankunft_min' in df.columns:
    df['status'] = df['verzoegerung_ankunft_min'].apply(
        lambda x: 'Verspätet' if x > delay_threshold else ('Zu früh' if x < -5 else 'Pünktlich') if not pd.isna(x) else 'Unbekannt'
    )


# ── HEADER ────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;">
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
        <rect width="36" height="36" rx="8" fill="#01696f"/>
        <path d="M6 24h4l2-8h12l2 8h4M8 24v2M28 24v2" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <circle cx="11" cy="27" r="2" fill="white"/>
        <circle cx="25" cy="27" r="2" fill="white"/>
        <path d="M10 16h16M14 16v-4h8v4" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    <div>
        <h1 style="margin:0;font-size:1.6rem;color:#28251d;font-weight:700;">CIS Touren-Dashboard</h1>
        <p style="margin:0;color:#7a7974;font-size:0.85rem;">Plan-Ist-Vergleich & Verzögerungsanalyse</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── KPI METRICS ───────────────────────────────────────────────────────────────

total_stops = len(df)
n_delayed = (df['status'] == 'Verspätet').sum() if 'status' in df.columns else 0
n_ontime = (df['status'] == 'Pünktlich').sum() if 'status' in df.columns else 0
n_early = (df['status'] == 'Zu früh').sum() if 'status' in df.columns else 0
pct_ontime = (n_ontime / total_stops * 100) if total_stops > 0 else 0
avg_delay = df['verzoegerung_ankunft_min'].mean() if 'verzoegerung_ankunft_min' in df.columns else 0
max_delay = df['verzoegerung_ankunft_min'].max() if 'verzoegerung_ankunft_min' in df.columns else 0
n_tours = df['tournr'].nunique() if 'tournr' in df.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Stationen gesamt", f"{total_stops:,}")
with col2:
    st.metric("Touren", f"{n_tours:,}")
with col3:
    delta_color = "normal" if pct_ontime >= 80 else "inverse"
    st.metric("Pünktlichkeitsrate", f"{pct_ontime:.1f}%", f"{n_ontime} pünktlich")
with col4:
    st.metric("Verspätungen", f"{n_delayed:,}", f"{n_delayed/total_stops*100:.1f}%" if total_stops > 0 else "")
with col5:
    st.metric("Ø Verspätung", f"{avg_delay:.0f} Min", f"Max: {max_delay:.0f} Min")

st.markdown("<br>", unsafe_allow_html=True)


# ── TABS ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Übersicht",
    "Zeitverlauf",
    "Kunden & Stationen",
    "Tourverlauf",
    "Rohdaten"
])


# ─── TAB 1: OVERVIEW ─────────────────────────────────────────────────────────

with tab1:
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown('<div class="section-header">Status-Verteilung</div>', unsafe_allow_html=True)
        if 'status' in df.columns and total_stops > 0:
            status_counts = df['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Anzahl']
            color_map = {
                'Pünktlich': '#437a22',
                'Verspätet': '#a12c7b',
                'Zu früh': '#006494',
                'Unbekannt': '#7a7974'
            }
            fig_pie = px.pie(
                status_counts, names='Status', values='Anzahl',
                color='Status', color_discrete_map=color_map,
                hole=0.5
            )
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            fig_pie.update_layout(
                showlegend=True,
                margin=dict(t=20, b=20, l=20, r=20),
                height=320,
                font=dict(family="Satoshi, sans-serif", size=13),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_right:
        st.markdown('<div class="section-header">Verzögerungs-Verteilung (Ankunft)</div>', unsafe_allow_html=True)
        if 'verzoegerung_ankunft_min' in df.columns:
            delay_data = df['verzoegerung_ankunft_min'].dropna()
            delay_clipped = delay_data.clip(-60, 180)
            fig_hist = px.histogram(
                delay_clipped, x=delay_clipped,
                nbins=40,
                labels={'x': 'Verzögerung (Minuten)', 'count': 'Anzahl Stationen'},
                color_discrete_sequence=['#01696f']
            )
            fig_hist.add_vline(x=0, line_dash="dash", line_color="#7a7974", annotation_text="Planzeit")
            fig_hist.add_vline(x=delay_threshold, line_dash="dot", line_color="#a12c7b",
                               annotation_text=f"Schwelle ({delay_threshold} Min)")
            fig_hist.update_layout(
                margin=dict(t=20, b=40, l=40, r=20),
                height=320,
                font=dict(family="Satoshi, sans-serif", size=12),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='rgba(0,0,0,0.06)'),
                yaxis=dict(gridcolor='rgba(0,0,0,0.06)'),
                bargap=0.05
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    
    # Top delayed customers
    st.markdown('<div class="section-header">Top-10 Stationen nach durchschn. Verspätung</div>', unsafe_allow_html=True)
    if 'name1' in df.columns and 'verzoegerung_ankunft_min' in df.columns:
        cust_delay = df.groupby('name1').agg(
            avg_delay=('verzoegerung_ankunft_min', 'mean'),
            count=('verzoegerung_ankunft_min', 'count'),
            n_delayed=('status', lambda x: (x == 'Verspätet').sum())
        ).reset_index()
        cust_delay['delay_rate'] = (cust_delay['n_delayed'] / cust_delay['count'] * 100).round(1)
        cust_delay = cust_delay[cust_delay['count'] >= 2].nlargest(10, 'avg_delay')
        cust_delay['avg_delay'] = cust_delay['avg_delay'].round(1)
        
        fig_bar = px.bar(
            cust_delay, y='name1', x='avg_delay',
            orientation='h',
            text='avg_delay',
            color='avg_delay',
            color_continuous_scale=[[0,'#d4dfcc'],[0.5,'#cedcd8'],[1,'#a12c7b']],
            labels={'name1': 'Station / Kunde', 'avg_delay': 'Ø Verspätung (Min.)'}
        )
        fig_bar.update_traces(texttemplate='%{text} Min', textposition='outside')
        fig_bar.update_layout(
            margin=dict(t=10, b=40, l=200, r=60),
            height=380,
            yaxis={'categoryorder': 'total ascending'},
            coloraxis_showscale=False,
            font=dict(family="Satoshi, sans-serif", size=12),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='rgba(0,0,0,0.06)')
        )
        st.plotly_chart(fig_bar, use_container_width=True)


# ─── TAB 2: ZEITVERLAUF ───────────────────────────────────────────────────────

with tab2:
    st.markdown('<div class="section-header">Verspätungen im Zeitverlauf</div>', unsafe_allow_html=True)
    
    if 'datum' in df.columns and 'verzoegerung_ankunft_min' in df.columns:
        daily = df.groupby('datum').agg(
            avg_delay=('verzoegerung_ankunft_min', 'mean'),
            n_stops=('verzoegerung_ankunft_min', 'count'),
            n_delayed=('status', lambda x: (x == 'Verspätet').sum())
        ).reset_index()
        daily['pct_delayed'] = (daily['n_delayed'] / daily['n_stops'] * 100).round(1)
        daily['avg_delay'] = daily['avg_delay'].round(1)
        daily['datum'] = pd.to_datetime(daily['datum'])
        
        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(
            x=daily['datum'], y=daily['avg_delay'],
            name='Ø Verspätung (Min.)',
            line=dict(color='#01696f', width=2.5),
            mode='lines+markers',
            marker=dict(size=5)
        ))
        fig_timeline.add_trace(go.Bar(
            x=daily['datum'], y=daily['pct_delayed'],
            name='Verspätungsrate (%)',
            marker_color='rgba(161,44,123,0.25)',
            yaxis='y2'
        ))
        fig_timeline.add_hline(y=delay_threshold, line_dash="dot", line_color="#a12c7b",
                               annotation_text=f"Schwelle {delay_threshold} Min")
        fig_timeline.update_layout(
            yaxis=dict(title='Ø Verspätung (Min.)', gridcolor='rgba(0,0,0,0.06)'),
            yaxis2=dict(title='Verspätungsrate (%)', overlaying='y', side='right',
                       range=[0, 100], gridcolor='rgba(0,0,0,0)'),
            xaxis=dict(title='Datum', gridcolor='rgba(0,0,0,0.06)'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(t=40, b=50, l=60, r=60),
            height=380,
            font=dict(family="Satoshi, sans-serif", size=12),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified'
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Wochentag-Analyse
        st.markdown('<div class="section-header">Verspätung nach Wochentag</div>', unsafe_allow_html=True)
        if 'tats_ankunft' in df.columns:
            df['wochentag'] = df['tats_ankunft'].dt.day_name().map({
                'Monday':'Mo', 'Tuesday':'Di', 'Wednesday':'Mi',
                'Thursday':'Do', 'Friday':'Fr', 'Saturday':'Sa', 'Sunday':'So'
            })
            day_order = ['Mo','Di','Mi','Do','Fr','Sa','So']
            wday = df.groupby('wochentag')['verzoegerung_ankunft_min'].agg(['mean','count']).reset_index()
            wday.columns = ['Wochentag','Ø Verspätung','Anzahl']
            wday['Wochentag'] = pd.Categorical(wday['Wochentag'], categories=day_order, ordered=True)
            wday = wday.sort_values('Wochentag')
            wday['Ø Verspätung'] = wday['Ø Verspätung'].round(1)
            
            fig_wday = px.bar(
                wday, x='Wochentag', y='Ø Verspätung',
                text='Ø Verspätung',
                color='Ø Verspätung',
                color_continuous_scale=[[0,'#cedcd8'],[1,'#a12c7b']],
                labels={'Ø Verspätung': 'Ø Verspätung (Min.)'}
            )
            fig_wday.update_traces(texttemplate='%{text} Min', textposition='outside')
            fig_wday.update_layout(
                coloraxis_showscale=False,
                margin=dict(t=30, b=40, l=50, r=30),
                height=300,
                font=dict(family="Satoshi, sans-serif", size=13),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='rgba(0,0,0,0)'),
                yaxis=dict(gridcolor='rgba(0,0,0,0.06)')
            )
            st.plotly_chart(fig_wday, use_container_width=True)


# ─── TAB 3: KUNDEN & STATIONEN ───────────────────────────────────────────────

with tab3:
    st.markdown('<div class="section-header">Detailanalyse Stationen</div>', unsafe_allow_html=True)
    
    if 'name1' in df.columns and 'verzoegerung_ankunft_min' in df.columns:
        cust_full = df.groupby(['name1','ort','strasse']).agg(
            Besuche=('verzoegerung_ankunft_min', 'count'),
            Ø_Verz_Ankunft=('verzoegerung_ankunft_min', 'mean'),
            Ø_Verz_Abfahrt=('verzoegerung_abfahrt_min', 'mean') if 'verzoegerung_abfahrt_min' in df.columns else ('verzoegerung_ankunft_min', 'mean'),
            Verspätet=('status', lambda x: (x == 'Verspätet').sum()),
            Max_Verz=('verzoegerung_ankunft_min', 'max')
        ).reset_index()
        cust_full['Verspätungsrate'] = (cust_full['Verspätet'] / cust_full['Besuche'] * 100).round(1)
        cust_full['Ø_Verz_Ankunft'] = cust_full['Ø_Verz_Ankunft'].round(1)
        cust_full['Max_Verz'] = cust_full['Max_Verz'].round(0).astype(int)
        cust_full = cust_full.sort_values('Ø_Verz_Ankunft', ascending=False)
        cust_full.columns = ['Name', 'Ort', 'Straße', 'Besuche', 'Ø Verz. Ankunft (Min.)', 'Ø Verz. Abfahrt (Min.)', 'Verspätet (n)', 'Max Verz. (Min.)', 'Verspätungsrate (%)']
        
        st.dataframe(
            cust_full.style.background_gradient(
                subset=['Ø Verz. Ankunft (Min.)'],
                cmap='RdYlGn_r',
                vmin=-30, vmax=120
            ).format({
                'Ø Verz. Ankunft (Min.)': '{:.1f}',
                'Ø Verz. Abfahrt (Min.)': '{:.1f}',
                'Verspätungsrate (%)': '{:.1f}%'
            }),
            use_container_width=True,
            height=400
        )
        
        # Scatter: Besuchsfrequenz vs Verspätung
        st.markdown('<div class="section-header">Besuchshäufigkeit vs. Verspätung</div>', unsafe_allow_html=True)
        fig_scatter = px.scatter(
            cust_full,
            x='Besuche', y='Ø Verz. Ankunft (Min.)',
            size='Verspätet (n)', color='Verspätungsrate (%)',
            hover_name='Name',
            color_continuous_scale=[[0,'#cedcd8'],[0.5,'#d19900'],[1,'#a12c7b']],
            labels={'Besuche': 'Anzahl Besuche', 'Ø Verz. Ankunft (Min.)': 'Ø Verspätung Ankunft (Min.)'}
        )
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="#7a7974")
        fig_scatter.add_hline(y=delay_threshold, line_dash="dot", line_color="#a12c7b",
                              annotation_text=f"Schwelle {delay_threshold} Min")
        fig_scatter.update_layout(
            margin=dict(t=20, b=50, l=60, r=40),
            height=380,
            font=dict(family="Satoshi, sans-serif", size=12),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='rgba(0,0,0,0.06)'),
            yaxis=dict(gridcolor='rgba(0,0,0,0.06)')
        )
        st.plotly_chart(fig_scatter, use_container_width=True)


# ─── TAB 4: TOURVERLAUF ───────────────────────────────────────────────────────

with tab4:
    st.markdown('<div class="section-header">Interaktiver Tourverlauf</div>', unsafe_allow_html=True)
    
    if 'tournr' in df.columns:
        all_tours_tab = sorted(df['tournr'].dropna().unique().tolist())
        
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            selected_tour = st.selectbox("Tour auswählen", options=all_tours_tab)
        
        if selected_tour:
            tour_df = df[df['tournr'] == selected_tour].copy()
            if 'tats_ankunft' in tour_df.columns:
                tour_df = tour_df.sort_values('tats_ankunft')
            
            with col_info:
                driver = tour_df['fahrername'].iloc[0] if 'fahrername' in tour_df.columns and len(tour_df) > 0 else '–'
                lkw = tour_df['lkwnr'].iloc[0] if 'lkwnr' in tour_df.columns and len(tour_df) > 0 else '–'
                st.info(f"**Fahrer:** {driver} | **LKW:** {lkw} | **Stationen:** {len(tour_df)}")
            
            if 'geox' in tour_df.columns and 'geoy' in tour_df.columns:
                map_df = tour_df.dropna(subset=['geox','geoy']).copy()
                map_df['lon'] = pd.to_numeric(map_df['geox'], errors='coerce')
                map_df['lat'] = pd.to_numeric(map_df['geoy'], errors='coerce')
                map_df = map_df.dropna(subset=['lon','lat'])
                
                if not map_df.empty:
                    map_df['delay_label'] = map_df['verzoegerung_ankunft_min'].apply(format_delay) if 'verzoegerung_ankunft_min' in map_df.columns else '–'
                    map_df['color'] = map_df['status'].map({
                        'Pünktlich': '#437a22',
                        'Verspätet': '#a12c7b',
                        'Zu früh': '#006494',
                        'Unbekannt': '#7a7974'
                    }).fillna('#7a7974') if 'status' in map_df.columns else '#01696f'
                    
                    fig_map = go.Figure()
                    
                    # Route line
                    fig_map.add_trace(go.Scattermapbox(
                        lon=map_df['lon'], lat=map_df['lat'],
                        mode='lines',
                        line=dict(width=2, color='#01696f'),
                        opacity=0.5,
                        name='Route',
                        hoverinfo='skip'
                    ))
                    
                    # Points per status
                    for status, color in [('Pünktlich','#437a22'),('Verspätet','#a12c7b'),('Zu früh','#006494'),('Unbekannt','#7a7974')]:
                        sub = map_df[map_df['color'] == color] if 'color' in map_df.columns else map_df
                        if status == 'Pünktlich': sub = map_df[map_df['status'] == 'Pünktlich'] if 'status' in map_df.columns else map_df
                        elif status == 'Verspätet': sub = map_df[map_df['status'] == 'Verspätet'] if 'status' in map_df.columns else pd.DataFrame()
                        elif status == 'Zu früh': sub = map_df[map_df['status'] == 'Zu früh'] if 'status' in map_df.columns else pd.DataFrame()
                        else: sub = map_df[map_df['status'] == 'Unbekannt'] if 'status' in map_df.columns else pd.DataFrame()
                        
                        if len(sub) > 0:
                            fig_map.add_trace(go.Scattermapbox(
                                lon=sub['lon'], lat=sub['lat'],
                                mode='markers+text',
                                marker=dict(size=14, color=color, opacity=0.9),
                                text=sub.get('name1', sub.index).astype(str),
                                textposition='top right',
                                textfont=dict(size=10),
                                name=status,
                                customdata=sub[['delay_label']].values if 'delay_label' in sub.columns else None,
                                hovertemplate=(
                                    "<b>%{text}</b><br>"
                                    "Verspätung: %{customdata[0]}<br>"
                                    "<extra></extra>"
                                ) if 'delay_label' in sub.columns else None
                            ))
                    
                    fig_map.update_layout(
                        mapbox_style="open-street-map",
                        mapbox=dict(
                            center=dict(lon=map_df['lon'].mean(), lat=map_df['lat'].mean()),
                            zoom=10
                        ),
                        margin=dict(t=0, b=0, l=0, r=0),
                        height=480,
                        legend=dict(orientation='h', yanchor='bottom', y=0, xanchor='left', x=0,
                                   bgcolor='rgba(255,255,255,0.85)', bordercolor='#dcd9d5', borderwidth=1)
                    )
                    st.plotly_chart(fig_map, use_container_width=True)
            
            # Gantt / Timeline
            st.markdown('<div class="section-header">Plan vs. Ist – Zeitstrahl</div>', unsafe_allow_html=True)
            if 'ankunft' in tour_df.columns and 'tats_ankunft' in tour_df.columns:
                gantt_rows = []
                for _, row in tour_df.iterrows():
                    name = str(row.get('name1', row.get('tourstation_id', '?')))
                    if pd.notna(row.get('ankunft')) and pd.notna(row.get('abfahrt')):
                        gantt_rows.append(dict(
                            Task=name, Start=row['ankunft'], Finish=row['abfahrt'],
                            Type='Plan', Verzögerung=format_delay(row.get('verzoegerung_ankunft_min', np.nan))
                        ))
                    if pd.notna(row.get('tats_ankunft')) and pd.notna(row.get('tats_abfahrt')):
                        gantt_rows.append(dict(
                            Task=name, Start=row['tats_ankunft'], Finish=row['tats_abfahrt'],
                            Type='Ist', Verzögerung=format_delay(row.get('verzoegerung_ankunft_min', np.nan))
                        ))
                
                if gantt_rows:
                    gantt_df = pd.DataFrame(gantt_rows)
                    fig_gantt = px.timeline(
                        gantt_df, x_start='Start', x_end='Finish', y='Task', color='Type',
                        color_discrete_map={'Plan': '#cedcd8', 'Ist': '#01696f'},
                        hover_data=['Verzögerung'],
                        labels={'Task': 'Station'}
                    )
                    fig_gantt.update_yaxes(autorange='reversed')
                    fig_gantt.update_layout(
                        margin=dict(t=20, b=40, l=180, r=40),
                        height=max(300, len(tour_df) * 50 + 100),
                        font=dict(family="Satoshi, sans-serif", size=12),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(gridcolor='rgba(0,0,0,0.06)')
                    )
                    st.plotly_chart(fig_gantt, use_container_width=True)
            
            # Stop detail table
            st.markdown('<div class="section-header">Stationen-Details</div>', unsafe_allow_html=True)
            detail_cols = ['name1','ort','strasse','ankunft','tats_ankunft','verzoegerung_ankunft_min','abfahrt','tats_abfahrt','status']
            detail_cols = [c for c in detail_cols if c in tour_df.columns]
            detail_show = tour_df[detail_cols].copy()
            rename = {
                'name1': 'Station', 'ort': 'Ort', 'strasse': 'Straße',
                'ankunft': 'Soll-Ankunft', 'tats_ankunft': 'Ist-Ankunft',
                'verzoegerung_ankunft_min': 'Verz. (Min.)',
                'abfahrt': 'Soll-Abfahrt', 'tats_abfahrt': 'Ist-Abfahrt',
                'status': 'Status'
            }
            detail_show.rename(columns=rename, inplace=True)
            
            def color_status(val):
                if val == 'Verspätet': return 'background-color: #f8eef5; color: #561740'
                if val == 'Pünktlich': return 'background-color: #eef4ea; color: #1e3f0a'
                if val == 'Zu früh': return 'background-color: #e8f0f7; color: #0b3751'
                return ''
            
            def color_delay(val):
                if pd.isna(val): return ''
                if val > delay_threshold: return 'color: #a12c7b; font-weight: 600'
                if val < -5: return 'color: #006494; font-weight: 600'
                return 'color: #437a22; font-weight: 600'
            
            styled = detail_show.style
            if 'Status' in detail_show.columns:
                styled = styled.applymap(color_status, subset=['Status'])
            if 'Verz. (Min.)' in detail_show.columns:
                styled = styled.applymap(color_delay, subset=['Verz. (Min.)'])
                styled = styled.format({'Verz. (Min.)': lambda x: format_delay(x)})
            
            st.dataframe(styled, use_container_width=True)


# ─── TAB 5: ROHDATEN ─────────────────────────────────────────────────────────

with tab5:
    st.markdown('<div class="section-header">Rohdaten-Explorer</div>', unsafe_allow_html=True)
    
    col_dl, col_info2 = st.columns([1, 3])
    with col_dl:
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 CSV exportieren",
            data=csv_data,
            file_name="cis_gefiltert.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_info2:
        st.caption(f"{len(df):,} Zeilen nach aktiven Filtern")
    
    display_cols = ['tournr','fahrername','lkwnr','name1','ort','ankunft','tats_ankunft',
                    'verzoegerung_ankunft_min','abfahrt','tats_abfahrt','status']
    display_cols = [c for c in display_cols if c in df.columns]
    
    rename_map = {
        'tournr': 'Tour-Nr.', 'fahrername': 'Fahrer', 'lkwnr': 'LKW',
        'name1': 'Station', 'ort': 'Ort', 'ankunft': 'Soll-Ankunft',
        'tats_ankunft': 'Ist-Ankunft', 'verzoegerung_ankunft_min': 'Verz. Ankunft (Min.)',
        'abfahrt': 'Soll-Abfahrt', 'tats_abfahrt': 'Ist-Abfahrt', 'status': 'Status'
    }
    
    show_df = df[display_cols].rename(columns=rename_map).copy()
    if 'Verz. Ankunft (Min.)' in show_df.columns:
        show_df['Verz. Ankunft (Min.)'] = show_df['Verz. Ankunft (Min.)'].apply(format_delay)
    
    st.dataframe(show_df, use_container_width=True, height=500)


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("CIS Touren-Dashboard · Prototyp · Plan-Ist-Analyse · Datenstand: gefilterte CIS-Daten")
