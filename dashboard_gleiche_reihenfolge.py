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
    """Load and preprocess the matched pairs CSV dataset."""
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        return pd.DataFrame()

    dt_cols = ['SollAnkunft', 'IstAnkunft', 'SollAbfahrt', 'IstAbfahrt', 'IstZeitFinal', 'SollZeitFinal', 'DATUMist', 'DATUMsoll']
    for col in dt_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    num_cols = ['delaymin', 'SollLon', 'SollLat', 'distm', 'SollPLZ']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'verzoegerung_abfahrt_min' not in df.columns and 'delaymin' in df.columns:
        df['verzoegerung_abfahrt_min'] = df['delaymin']

    def classify(delay):
        if pd.isna(delay):
            return 'Unbekannt'
        if delay > 15:
            return 'Verspätet'
        if delay < -5:
            return 'Zu früh'
        return 'Pünktlich'

    if 'delaymin' in df.columns:
        df['status'] = df['delaymin'].apply(classify)

    if 'IstAnkunft' in df.columns:
        df['datum'] = pd.to_datetime(df['IstAnkunft'], errors='coerce').dt.normalize()
    elif 'SollAnkunft' in df.columns:
        df['datum'] = pd.to_datetime(df['SollAnkunft'], errors='coerce').dt.normalize()

    if 'datum' in df.columns:
        df['datum'] = pd.to_datetime(df['datum'], errors='coerce')

    if 'IstPosition' in df.columns:
        df['IstPosition'] = df['IstPosition'].fillna('Unbekannte Station')
    if 'SollOrt' in df.columns:
        df['SollOrt'] = df['SollOrt'].fillna('–')
    if 'SollStrasse' in df.columns:
        df['SollStrasse'] = df['SollStrasse'].fillna('–')
    if 'FAHRERNAME' in df.columns:
        df['FAHRERNAME'] = df['FAHRERNAME'].fillna('–')
    if 'IstFahrzeug' in df.columns:
        df['IstFahrzeug'] = df['IstFahrzeug'].fillna('–')

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
        "📂 CSV-Datei hochladen",
        type=["csv"],
        help="matched_pairs_best.csv hochladen"
    )
    
    st.markdown("---")
    
    df_raw = load_data(uploaded_file)
    
    if df_raw.empty:
        st.info("Bitte lade die Datei matched_pairs_best.csv hoch, um das Dashboard zu aktivieren.")
        st.markdown("""
        **Erwartete Spalten:**
        - TOURNR, FAHRERNAME, IstFahrzeug
        - SollAnkunft, IstAnkunft
        - SollAbfahrt, IstAbfahrt
        - IstPosition, SollOrt, SollStrasse
        - SollLon, SollLat
        - delaymin
        """)
        st.stop()
    
    st.markdown("### Filter")
    
    if 'datum' in df_raw.columns:
        valid_dates = pd.to_datetime(df_raw['datum'], errors='coerce').dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            date_range = st.date_input(
                "Zeitraum",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        else:
            date_range = None
    else:
        date_range = None
    
    all_tours = sorted(df_raw['TOURNR'].dropna().unique().tolist()) if 'TOURNR' in df_raw.columns else []
    selected_tours = st.multiselect("Tour-Nummer", options=all_tours, default=[])
    
    all_customers = sorted(df_raw['IstPosition'].dropna().unique().tolist()) if 'IstPosition' in df_raw.columns else []
    selected_customers = st.multiselect("Kunde / Station", options=all_customers, default=[])
    
    all_drivers = sorted(df_raw['FAHRERNAME'].dropna().unique().tolist()) if 'FAHRERNAME' in df_raw.columns else []
    selected_drivers = st.multiselect("Fahrer", options=all_drivers, default=[])
    
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
    datum_series = pd.to_datetime(df['datum'], errors='coerce').dt.date
    df = df[(datum_series >= date_range[0]) & (datum_series <= date_range[1])]

if selected_tours:
    df = df[df['TOURNR'].isin(selected_tours)]

if selected_customers:
    df = df[df['IstPosition'].isin(selected_customers)]

if selected_drivers:
    df = df[df['FAHRERNAME'].isin(selected_drivers)]

if selected_statuses and 'status' in df.columns:
    df = df[df['status'].isin(selected_statuses)]

if 'delaymin' in df.columns:
    df['status'] = df['delaymin'].apply(
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
avg_delay = df['delaymin'].mean() if 'delaymin' in df.columns else 0
max_delay = df['delaymin'].max() if 'delaymin' in df.columns else 0
n_tours = df['TOURNR'].nunique() if 'TOURNR' in df.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Stationen gesamt", f"{total_stops:,}")
with col2:
    st.metric("Touren", f"{n_tours:,}")
with col3:
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
            fig_pie = px.pie(status_counts, names='Status', values='Anzahl', color='Status', color_discrete_map=color_map, hole=0.5)
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            fig_pie.update_layout(showlegend=True, margin=dict(t=20, b=20, l=20, r=20), height=320,
                                  font=dict(family="Satoshi, sans-serif", size=13),
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_right:
        st.markdown('<div class="section-header">Verzögerungs-Verteilung (Ankunft)</div>', unsafe_allow_html=True)
        if 'verzoegerung_ankunft_min' in df.columns:
            delay_data = df['verzoegerung_ankunft_min'].dropna()
            delay_clipped = delay_data.clip(-60, 180)
            fig_hist = px.histogram(delay_clipped, x=delay_clipped, nbins=40,
                                    labels={'x': 'Verzögerung (Minuten)', 'count': 'Anzahl Stationen'},
                                    color_discrete_sequence=['#01696f'])
            fig_hist.add_vline(x=0, line_dash="dash", line_color="#7a7974", annotation_text="Planzeit")
            fig_hist.add_vline(x=delay_threshold, line_dash="dot", line_color="#a12c7b", annotation_text=f"Schwelle ({delay_threshold} Min)")
            fig_hist.update_layout(margin=dict(t=20, b=40, l=40, r=20), height=320,
                                   font=dict(family="Satoshi, sans-serif", size=12),
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                   xaxis=dict(gridcolor='rgba(0,0,0,0.06)'),
                                   yaxis=dict(gridcolor='rgba(0,0,0,0.06)'), bargap=0.05)
            st.plotly_chart(fig_hist, use_container_width=True)
    
    st.markdown('<div class="section-header">Top-10 Stationen nach durchschn. Verspätung</div>', unsafe_allow_html=True)
    if 'IstPosition' in df.columns and 'delaymin' in df.columns:
        cust_delay = df.groupby('IstPosition').agg(
            avg_delay=('delaymin', 'mean'),
            count=('delaymin', 'count'),
            n_delayed=('status', lambda x: (x == 'Verspätet').sum())
        ).reset_index()
        cust_delay['delay_rate'] = (cust_delay['n_delayed'] / cust_delay['count'] * 100).round(1)
        cust_delay = cust_delay[cust_delay['count'] >= 2].nlargest(10, 'avg_delay')
        cust_delay['avg_delay'] = cust_delay['avg_delay'].round(1)
        
        fig_bar = px.bar(cust_delay, y='IstPosition', x='avg_delay', orientation='h', text='avg_delay', color='avg_delay',
                         color_continuous_scale=[[0,'#d4dfcc'],[0.5,'#cedcd8'],[1,'#a12c7b']],
                         labels={'IstPosition': 'Station / Kunde', 'avg_delay': 'Ø Verspätung (Min.)'})
        fig_bar.update_traces(texttemplate='%{text} Min', textposition='outside')
        fig_bar.update_layout(margin=dict(t=10, b=40, l=200, r=60), height=380, yaxis={'categoryorder': 'total ascending'},
                              coloraxis_showscale=False, font=dict(family="Satoshi, sans-serif", size=12),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(gridcolor='rgba(0,0,0,0.06)'))
        st.plotly_chart(fig_bar, use_container_width=True)


with tab2:
    st.markdown('<div class="section-header">Verspätungen im Zeitverlauf</div>', unsafe_allow_html=True)
    
    if 'datum' in df.columns and 'delaymin' in df.columns:
        daily = df.groupby('datum').agg(
            avg_delay=('delaymin', 'mean'),
            n_stops=('delaymin', 'count'),
            n_delayed=('status', lambda x: (x == 'Verspätet').sum())
        ).reset_index()
        daily['pct_delayed'] = (daily['n_delayed'] / daily['n_stops'] * 100).round(1)
        daily['avg_delay'] = daily['avg_delay'].round(1)
        daily['datum'] = pd.to_datetime(daily['datum'])
        
        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(x=daily['datum'], y=daily['avg_delay'], name='Ø Verspätung (Min.)',
                                          line=dict(color='#01696f', width=2.5), mode='lines+markers', marker=dict(size=5)))
        fig_timeline.add_trace(go.Bar(x=daily['datum'], y=daily['pct_delayed'], name='Verspätungsrate (%)',
                                      marker_color='rgba(161,44,123,0.25)', yaxis='y2'))
        fig_timeline.add_hline(y=delay_threshold, line_dash="dot", line_color="#a12c7b", annotation_text=f"Schwelle {delay_threshold} Min")
        fig_timeline.update_layout(
            yaxis=dict(title='Ø Verspätung (Min.)', gridcolor='rgba(0,0,0,0.06)'),
            yaxis2=dict(title='Verspätungsrate (%)', overlaying='y', side='right', range=[0, 100], gridcolor='rgba(0,0,0,0)'),
            xaxis=dict(title='Datum', gridcolor='rgba(0,0,0,0.06)'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(t=40, b=50, l=60, r=60), height=380,
            font=dict(family="Satoshi, sans-serif", size=12), paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)', hovermode='x unified'
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        st.markdown('<div class="section-header">Verspätung nach Wochentag</div>', unsafe_allow_html=True)
        if 'IstAnkunft' in df.columns:
            df['wochentag'] = df['IstAnkunft'].dt.day_name().map({
                'Monday':'Mo', 'Tuesday':'Di', 'Wednesday':'Mi',
                'Thursday':'Do', 'Friday':'Fr', 'Saturday':'Sa', 'Sunday':'So'
            })
            day_order = ['Mo','Di','Mi','Do','Fr','Sa','So']
            wday = df.groupby('wochentag')['delaymin'].agg(['mean','count']).reset_index()
            wday.columns = ['Wochentag','Ø Verspätung','Anzahl']
            wday['Wochentag'] = pd.Categorical(wday['Wochentag'], categories=day_order, ordered=True)
            wday = wday.sort_values('Wochentag')
            wday['Ø Verspätung'] = wday['Ø Verspätung'].round(1)
            
            fig_wday = px.bar(wday, x='Wochentag', y='Ø Verspätung', text='Ø Verspätung', color='Ø Verspätung',
                              color_continuous_scale=[[0,'#cedcd8'],[1,'#a12c7b']], labels={'Ø Verspätung': 'Ø Verspätung (Min.)'})
            fig_wday.update_traces(texttemplate='%{text} Min', textposition='outside')
            fig_wday.update_layout(coloraxis_showscale=False, margin=dict(t=30, b=40, l=50, r=30), height=300,
                                   font=dict(family="Satoshi, sans-serif", size=13), paper_bgcolor='rgba(0,0,0,0)',
                                   plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='rgba(0,0,0,0)'),
                                   yaxis=dict(gridcolor='rgba(0,0,0,0.06)'))
            st.plotly_chart(fig_wday, use_container_width=True)


with tab3:
    st.markdown('<div class="section-header">Detailanalyse Stationen</div>', unsafe_allow_html=True)
    
    if 'IstPosition' in df.columns and 'delaymin' in df.columns:
        group_cols = ['IstPosition']
        if 'SollOrt' in df.columns:
            group_cols.append('SollOrt')
        if 'SollStrasse' in df.columns:
            group_cols.append('SollStrasse')

        cust_full = df.groupby(group_cols).agg(
            Besuche=('delaymin', 'count'),
            Ø_Verz_Ankunft=('delaymin', 'mean'),
            Ø_Verz_Abfahrt=('verzoegerung_abfahrt_min', 'mean'),
            Verspätet=('status', lambda x: (x == 'Verspätet').sum()),
            Max_Verz=('delaymin', 'max')
        ).reset_index()
        cust_full['Verspätungsrate'] = (cust_full['Verspätet'] / cust_full['Besuche'] * 100).round(1)
        cust_full['Ø_Verz_Ankunft'] = cust_full['Ø_Verz_Ankunft'].round(1)
        cust_full['Max_Verz'] = cust_full['Max_Verz'].round(0)
        cust_full = cust_full.sort_values('Ø_Verz_Ankunft', ascending=False)

        rename_cols = {'IstPosition': 'Name', 'SollOrt': 'Ort', 'SollStrasse': 'Straße'}
        cust_full = cust_full.rename(columns=rename_cols)
        if 'Ort' not in cust_full.columns:
            cust_full['Ort'] = '–'
        if 'Straße' not in cust_full.columns:
            cust_full['Straße'] = '–'

        cust_full = cust_full[['Name', 'Ort', 'Straße', 'Besuche', 'Ø_Verz_Ankunft', 'Ø_Verz_Abfahrt', 'Verspätet', 'Max_Verz', 'Verspätungsrate']]
        cust_full.columns = ['Name', 'Ort', 'Straße', 'Besuche', 'Ø Verz. Ankunft (Min.)', 'Ø Verz. Abfahrt (Min.)', 'Verspätet (n)', 'Max Verz. (Min.)', 'Verspätungsrate (%)']
        
        st.dataframe(
            cust_full.style.background_gradient(subset=['Ø Verz. Ankunft (Min.)'], cmap='RdYlGn_r', vmin=-30, vmax=120).format({
                'Ø Verz. Ankunft (Min.)': '{:.1f}',
                'Ø Verz. Abfahrt (Min.)': '{:.1f}',
                'Verspätungsrate (%)': '{:.1f}%'
            }),
            use_container_width=True,
            height=400
        )
        
        st.markdown('<div class="section-header">Besuchshäufigkeit vs. Verspätung</div>', unsafe_allow_html=True)
        fig_scatter = px.scatter(cust_full, x='Besuche', y='Ø Verz. Ankunft (Min.)', size='Verspätet (n)', color='Verspätungsrate (%)',
                                 hover_name='Name', color_continuous_scale=[[0,'#cedcd8'],[0.5,'#d19900'],[1,'#a12c7b']],
                                 labels={'Besuche': 'Anzahl Besuche', 'Ø Verz. Ankunft (Min.)': 'Ø Verspätung Ankunft (Min.)'})
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="#7a7974")
        fig_scatter.add_hline(y=delay_threshold, line_dash="dot", line_color="#a12c7b", annotation_text=f"Schwelle {delay_threshold} Min")
        fig_scatter.update_layout(margin=dict(t=20, b=50, l=60, r=40), height=380,
                                  font=dict(family="Satoshi, sans-serif", size=12), paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='rgba(0,0,0,0.06)'),
                                  yaxis=dict(gridcolor='rgba(0,0,0,0.06)'))
        st.plotly_chart(fig_scatter, use_container_width=True)


with tab4:
    st.markdown('<div class="section-header">Interaktiver Tourverlauf</div>', unsafe_allow_html=True)
    
    if 'TOURNR' in df.columns:
        all_tours_tab = sorted(df['TOURNR'].dropna().unique().tolist())
        
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            selected_tour = st.selectbox("Tour auswählen", options=all_tours_tab)
        
        if selected_tour:
            tour_df = df[df['TOURNR'] == selected_tour].copy()
            if 'IstAnkunft' in tour_df.columns:
                tour_df = tour_df.sort_values('IstAnkunft')
            elif 'SollAnkunft' in tour_df.columns:
                tour_df = tour_df.sort_values('SollAnkunft')
            
            with col_info:
                driver = tour_df['FAHRERNAME'].iloc[0] if 'FAHRERNAME' in tour_df.columns and len(tour_df) > 0 else '–'
                lkw = tour_df['IstFahrzeug'].iloc[0] if 'IstFahrzeug' in tour_df.columns and len(tour_df) > 0 else '–'
                st.info(f"**Fahrer:** {driver} | **LKW:** {lkw} | **Stationen:** {len(tour_df)}")
            
            if 'SollLon' in tour_df.columns and 'SollLat' in tour_df.columns:
                map_df = tour_df.dropna(subset=['SollLon','SollLat']).copy()
                map_df['lon'] = pd.to_numeric(map_df['SollLon'], errors='coerce')
                map_df['lat'] = pd.to_numeric(map_df['SollLat'], errors='coerce')
                map_df = map_df.dropna(subset=['lon','lat'])
                
                if not map_df.empty:
                    map_df['delay_label'] = map_df['delaymin'].apply(format_delay) if 'delaymin' in map_df.columns else '–'
                    map_df['color'] = map_df['status'].map({
                        'Pünktlich': '#437a22',
                        'Verspätet': '#a12c7b',
                        'Zu früh': '#006494',
                        'Unbekannt': '#7a7974'
                    }).fillna('#7a7974') if 'status' in map_df.columns else '#01696f'
                    
                    fig_map = go.Figure()
                    fig_map.add_trace(go.Scattermapbox(lon=map_df['lon'], lat=map_df['lat'], mode='lines',
                                                       line=dict(width=2, color='#01696f'), opacity=0.5,
                                                       name='Route', hoverinfo='skip'))
                    
                    for status, color in [('Pünktlich','#437a22'),('Verspätet','#a12c7b'),('Zu früh','#006494'),('Unbekannt','#7a7974')]:
                        if 'status' in map_df.columns:
                            sub = map_df[map_df['status'] == status]
                        else:
                            sub = map_df
                        if len(sub) > 0:
                            fig_map.add_trace(go.Scattermapbox(
                                lon=sub['lon'], lat=sub['lat'], mode='markers+text',
                                marker=dict(size=14, color=color, opacity=0.9),
                                text=sub.get('IstPosition', sub.index).astype(str), textposition='top right',
                                textfont=dict(size=10), name=status,
                                customdata=sub[['delay_label']].values if 'delay_label' in sub.columns else None,
                                hovertemplate=("<b>%{text}</b><br>Verspätung: %{customdata[0]}<br><extra></extra>") if 'delay_label' in sub.columns else None
                            ))
                    
                    fig_map.update_layout(
                        mapbox_style="open-street-map",
                        mapbox=dict(center=dict(lon=map_df['lon'].mean(), lat=map_df['lat'].mean()), zoom=10),
                        margin=dict(t=0, b=0, l=0, r=0), height=480,
                        legend=dict(orientation='h', yanchor='bottom', y=0, xanchor='left', x=0,
                                    bgcolor='rgba(255,255,255,0.85)', bordercolor='#dcd9d5', borderwidth=1)
                    )
                    st.plotly_chart(fig_map, use_container_width=True)
            
            st.markdown('<div class="section-header">Plan vs. Ist – Zeitstrahl</div>', unsafe_allow_html=True)
            if 'SollAnkunft' in tour_df.columns and 'IstAnkunft' in tour_df.columns:
                gantt_rows = []
                for _, row in tour_df.iterrows():
                    name = str(row.get('IstPosition', row.get('istidx', '?')))
                    if pd.notna(row.get('SollAnkunft')) and pd.notna(row.get('SollAbfahrt')):
                        gantt_rows.append(dict(Task=name, Start=row['SollAnkunft'], Finish=row['SollAbfahrt'], Type='Plan', Verzögerung=format_delay(row.get('delaymin', np.nan))))
                    if pd.notna(row.get('IstAnkunft')) and pd.notna(row.get('IstAbfahrt')):
                        gantt_rows.append(dict(Task=name, Start=row['IstAnkunft'], Finish=row['IstAbfahrt'], Type='Ist', Verzögerung=format_delay(row.get('delaymin', np.nan))))
                
                if gantt_rows:
                    gantt_df = pd.DataFrame(gantt_rows)
                    fig_gantt = px.timeline(gantt_df, x_start='Start', x_end='Finish', y='Task', color='Type',
                                            color_discrete_map={'Plan': '#cedcd8', 'Ist': '#01696f'}, hover_data=['Verzögerung'], labels={'Task': 'Station'})
                    fig_gantt.update_yaxes(autorange='reversed')
                    fig_gantt.update_layout(margin=dict(t=20, b=40, l=180, r=40), height=max(300, len(tour_df) * 50 + 100),
                                            font=dict(family="Satoshi, sans-serif", size=12), paper_bgcolor='rgba(0,0,0,0)',
                                            plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='rgba(0,0,0,0.06)'))
                    st.plotly_chart(fig_gantt, use_container_width=True)
            
            st.markdown('<div class="section-header">Stationen-Details</div>', unsafe_allow_html=True)
            detail_cols = ['IstPosition','SollOrt','SollStrasse','SollAnkunft','IstAnkunft','delaymin','SollAbfahrt','IstAbfahrt','status']
            detail_cols = [c for c in detail_cols if c in tour_df.columns]
            detail_show = tour_df[detail_cols].copy()
            rename = {
                'IstPosition': 'Station', 'SollOrt': 'Ort', 'SollStrasse': 'Straße',
                'SollAnkunft': 'Soll-Ankunft', 'IstAnkunft': 'Ist-Ankunft',
                'delaymin': 'Verz. (Min.)',
                'SollAbfahrt': 'Soll-Abfahrt', 'IstAbfahrt': 'Ist-Abfahrt',
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


with tab5:
    st.markdown('<div class="section-header">Rohdaten-Explorer</div>', unsafe_allow_html=True)
    
    col_dl, col_info2 = st.columns([1, 3])
    with col_dl:
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 CSV exportieren", data=csv_data, file_name="cis_gefiltert.csv", mime="text/csv", use_container_width=True)
    with col_info2:
        st.caption(f"{len(df):,} Zeilen nach aktiven Filtern")
    
    display_cols = ['TOURNR','FAHRERNAME','IstFahrzeug','IstPosition','SollOrt','SollAnkunft','IstAnkunft', 'delaymin','SollAbfahrt','IstAbfahrt','status']
    display_cols = [c for c in display_cols if c in df.columns]
    
    rename_map = {
        'TOURNR': 'Tour-Nr.', 'FAHRERNAME': 'Fahrer', 'IstFahrzeug': 'LKW',
        'IstPosition': 'Station', 'SollOrt': 'Ort', 'SollAnkunft': 'Soll-Ankunft',
        'IstAnkunft': 'Ist-Ankunft', 'delaymin': 'Verz. Ankunft (Min.)',
        'SollAbfahrt': 'Soll-Abfahrt', 'IstAbfahrt': 'Ist-Abfahrt', 'status': 'Status'
    }
    
    show_df = df[display_cols].rename(columns=rename_map).copy()
    if 'Verz. Ankunft (Min.)' in show_df.columns:
        show_df['Verz. Ankunft (Min.)'] = show_df['Verz. Ankunft (Min.)'].apply(format_delay)
    
    st.dataframe(show_df, use_container_width=True, height=500)


st.markdown("---")
st.caption("CIS Touren-Dashboard · Prototyp · Plan-Ist-Analyse · Datenstand: matched_pairs_best.csv")
