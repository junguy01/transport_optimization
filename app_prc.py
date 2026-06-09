"""
HTS Cargo – Soll-Ist-Dashboard

Liest die drei im Notebook exportierten Tabellen aus data/processed/ und stellt sie dar.
Das Dashboard rechnet die Kennzahlen nicht neu, es zeigt die fertigen Tabellen und
verdichtet sie nur fürs Zeichnen (Gruppieren, Zählen).

Start:   streamlit run app.py
Bedarf:  pip install streamlit folium streamlit-folium altair pandas
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import altair as alt
import folium
from streamlit_folium import st_folium

DATA = Path("data/processed")

# ── Farb-Identität ────────────────────────────────────────────────────────────
# Plan = Blau, Ist = Rot (durchgängig, an die HTS-Marke angelehnt).
# Die übrigen Farben sind semantisch: Grün pünktlich, Bernstein leicht daneben,
# Grau neutral/Basis. Farbe trägt hier Bedeutung, sie dekoriert nicht.
PLAN   = "#2C5FA8"   # Soll / Plan
IST    = "#C0392B"   # Ist / gefahren
GRUEN  = "#1E9E6A"   # pünktlich, im Plan
AMBER  = "#E8A317"   # leichte Abweichung
SLATE  = "#5B6B7F"   # neutral
INK    = "#1A2331"   # Text
PAPER  = "#F5F7FA"   # Flächen

STATUS_FARBEN = {"Treffer": PLAN, "nur geplant": SLATE, "nicht zuordenbar": IST}
QUELLE_FARBEN = {"EMR": GRUEN, "PRC": PLAN, "Basis": SLATE, "fehlt": "#C9D2DD", "unplausibel": IST}

st.set_page_config(page_title="HTS Cargo – Soll-Ist", page_icon="🚚", layout="wide")

# ── CSS: Typografie, Kennzahl-Karten, Abschnitts-Köpfe ────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {INK}; }}
h1, h2, h3, .hts-display {{ font-family: 'Barlow Semi Condensed', sans-serif; letter-spacing: .2px; }}

.hts-band {{
    background: linear-gradient(100deg, {PLAN} 0%, #21487f 55%, {IST} 150%);
    padding: 22px 28px; border-radius: 14px; color: #fff; margin-bottom: 6px;
}}
.hts-band h1 {{ color:#fff; margin:0; font-size: 30px; font-weight:700; }}
.hts-band p  {{ color:#dce6f5; margin:.35rem 0 0; font-size:14px; }}

.hts-eyebrow {{
    font-family:'Barlow Semi Condensed',sans-serif; text-transform:uppercase;
    letter-spacing:1.4px; font-size:12px; color:{SLATE}; font-weight:600; margin-bottom:-6px;
}}
.hts-card {{
    background:#fff; border:1px solid #e6eaf0; border-left:5px solid {PLAN};
    border-radius:10px; padding:14px 16px; box-shadow:0 1px 3px rgba(20,35,49,.05);
    height:100%;
}}
.hts-card .v {{ font-family:'Barlow Semi Condensed',sans-serif; font-size:30px; font-weight:700; line-height:1.05; }}
.hts-card .l {{ font-size:12.5px; color:{SLATE}; margin-top:2px; }}
.hts-card .h {{ font-size:11px; color:#9aa6b4; margin-top:6px; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def lade_daten():
    stops = pd.read_pickle(DATA / "dash_stops.pkl")
    touren = pd.read_pickle(DATA / "dash_touren.pkl")
    spur = pd.read_pickle(DATA / "dash_spur.pkl")
    for sp in ["zeit_abw_min", "standzeit_min", "standzeit_abw_min", "soll_standzeit_min"]:
        stops[sp] = pd.to_numeric(stops[sp], errors="coerce")
    return stops, touren, spur


def karte(value, label, hint="", accent=PLAN):
    st.markdown(
        f"<div class='hts-card' style='border-left-color:{accent}'>"
        f"<div class='v' style='color:{accent}'>{value}</div>"
        f"<div class='l'>{label}</div>"
        f"{f'<div class=\"h\">{hint}</div>' if hint else ''}</div>",
        unsafe_allow_html=True)


def kopf(eyebrow, titel):
    st.markdown(f"<div class='hts-eyebrow'>{eyebrow}</div>", unsafe_allow_html=True)
    st.markdown(f"### {titel}")


def basis_chart(c):
    return c.configure_view(strokeWidth=0).configure_axis(
        labelFont="Inter", titleFont="Barlow Semi Condensed", titleColor=SLATE,
        grid=True, gridColor="#eef1f5").configure_legend(labelFont="Inter", titleFont="Inter")

def _hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient_line(fmap, coords, hex_start, hex_end, weight=4, opacity=0.85, dash=None, tooltip=None):
    """Zeichnet eine Linie, die sich entlang der chronologischen Punktfolge von
    hex_start nach hex_end verfärbt (hell = früh, dunkel = spät)."""
    pts = [list(p) for p in coords]
    n = len(pts)
    if n < 2:
        return
    c1, c2 = _hex2rgb(hex_start), _hex2rgb(hex_end)
    mitte = n // 2
    for i in range(n - 1):
        t = i / (n - 2) if n > 2 else 0.0
        r, g, b = (int(round(a + (bb - a) * t)) for a, bb in zip(c1, c2))
        folium.PolyLine(pts[i:i + 2], color=f"#{r:02x}{g:02x}{b:02x}",
                        weight=weight, opacity=opacity, dash_array=dash,
                        tooltip=tooltip if i == mitte else None).add_to(fmap)
        
stops, touren, spur = lade_daten()
kunden = stops[~stops["ist_basis"].fillna(False) & stops["soll_nummer"].notna()]

# ── Kopfband ──────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='hts-band'><h1>🚚 HTS Cargo – Soll-Ist-Vergleich der Touren</h1>"
    "<p>Geplante Touren (TMS) gegen tatsächlich gefahrene (GPS/Telematik) · März 2026, KW 10–14 · "
    "Plan in Blau, Ist in Rot</p></div>", unsafe_allow_html=True)

# ============================================================ Überblick
st.write("")
kopf("Überblick", "Die Kennzahlen auf einen Blick")

a, b, c, d = st.columns(4)
with a: karte(len(touren), "Touren geplant", accent=PLAN)
with b: karte(int((touren["n_gefahren"] == 0).sum()), "ohne PRC-Erfassung",
              "Keine PRC-Stationsmeldung – laut EMR-Spur aber gefahren", accent=AMBER)
with c: karte(int(touren["reihenfolge_abw"].sum()), "Reihenfolge geändert",
              "Gefahrene Folge weicht vom Soll-Plan ab", accent=IST)
with d: karte(int(touren["redisponiert"].sum()), "re-disponiert",
              "Tour nach Planung noch umgeplant", accent=SLATE)

st.write("")
e, f, g = st.columns(3)
with e: karte(f"{kunden['zeit_abw_min'].median():.0f} min", "Median Zeitabweichung",
              "Ist- minus Soll-Ankunft je Kundenstopp", accent=PLAN)
with f: karte(f"{kunden['standzeit_abw_min'].median():.0f} min", "Median Standzeit-Abweichung",
              "Nur verwertbare Stopps (≥ 5 min)", accent=IST)
with g: karte(int((kunden["standzeit_min"] >= 5).sum()), "Kundenstopps mit Standzeit",
              "verwertbar gemessen (≥ 5 min)", accent=GRUEN)

st.divider()

# ============================================================ Datengüte / zwei Quellen
kopf("Datengüte", "Wie gut passen Plan und Ist zusammen?")
links, rechts = st.columns(2)

with links:
    st.markdown("**Zuordnung der Stopps**")
    av = stops["ausfuehrung"].value_counts().rename_axis("Ausführung").reset_index(name="Anzahl")
    ring = alt.Chart(av).mark_arc(innerRadius=62, stroke="#fff", strokeWidth=2).encode(
        theta=alt.Theta("Anzahl:Q"),
        color=alt.Color("Ausführung:N",
                        scale=alt.Scale(domain=list(STATUS_FARBEN), range=list(STATUS_FARBEN.values())),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Ausführung:N", "Anzahl:Q"]).properties(height=300)
    st.altair_chart(basis_chart(ring), use_container_width=True)
    st.caption("Jeder geplante und jeder gefahrene Stopp landet in genau einer Gruppe: geografisch "
               "zugeordnet (Treffer), nur im Plan vorhanden oder gefahren, aber keinem Plan-Stopp "
               "zuzuordnen. Die Aufteilung zeigt, wie viel der Verbund trägt.")

with rechts:
    st.markdown("**Woher die Standzeit stammt**")
    qv = stops["standzeit_quelle"].value_counts().rename_axis("Quelle").reset_index(name="Anzahl")
    ring2 = alt.Chart(qv).mark_arc(innerRadius=62, stroke="#fff", strokeWidth=2).encode(
        theta=alt.Theta("Anzahl:Q"),
        color=alt.Color("Quelle:N",
                        scale=alt.Scale(domain=list(QUELLE_FARBEN), range=list(QUELLE_FARBEN.values())),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Quelle:N", "Anzahl:Q"]).properties(height=300)
    st.altair_chart(basis_chart(ring2), use_container_width=True)
    st.caption("Die Standzeit kommt bevorzugt aus der dichten EMR-Spur, ersatzweise aus dem "
               "PRC-Stationsstatus. Basis-Stopps bleiben ausgenommen, weil dort Parken und Beladen "
               "verschmelzen. Wo keine Quelle einen verwertbaren Wert hat, steht „fehlt“.")

st.divider()

# ============================================================ Zeitabweichung
kopf("Pünktlichkeit", "Wie stark weicht die Ankunft vom Plan ab?")
li, re = st.columns([3, 2])

with li:
    zd = kunden.dropna(subset=["zeit_abw_min"]).copy()
    zd["clip"] = zd["zeit_abw_min"].clip(-180, 180)
    hist = alt.Chart(zd).mark_bar().encode(
        x=alt.X("clip:Q", bin=alt.Bin(maxbins=40), title="Zeitabweichung (min)  ·  negativ = zu früh"),
        y=alt.Y("count():Q", title="Kundenstopps"),
        color=alt.value(PLAN),
        tooltip=[alt.Tooltip("count():Q", title="Stopps")]).properties(height=320)
    regel = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK, strokeDash=[4, 3]).encode(x="x:Q")
    st.altair_chart(basis_chart(hist + regel), use_container_width=True)
    st.caption("Verteilung über alle Kundenstopps, für die Darstellung auf ±180 min begrenzt. "
               "Die gestrichelte Linie ist der Plan; rechts davon liegt Verspätung, links Verfrühung.")

with re:
    if "tag" in touren.columns:
        wd = touren.dropna(subset=["zeit_abw_median_min"]).copy()
        wd["tag"] = pd.to_datetime(wd["tag"], errors="coerce")
        namen = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}
        wd["wt"] = wd["tag"].dt.weekday.map(namen)
        agg = wd.groupby("wt")["zeit_abw_median_min"].median().reindex(list(namen.values())).reset_index()
        bar = alt.Chart(agg.dropna()).mark_bar().encode(
            x=alt.X("wt:N", sort=list(namen.values()), title=None),
            y=alt.Y("zeit_abw_median_min:Q", title="Median Zeitabw. (min)"),
            color=alt.condition(alt.datum.zeit_abw_median_min > 0, alt.value(IST), alt.value(GRUEN)),
            tooltip=[alt.Tooltip("wt:N", title="Tag"),
                     alt.Tooltip("zeit_abw_median_min:Q", format=".0f", title="Median (min)")]
        ).properties(height=320)
        st.altair_chart(basis_chart(bar), use_container_width=True)
        st.caption("Mediane Zeitabweichung je Wochentag. Rot = im Schnitt verspätet, Grün = im Schnitt früh.")

st.divider()

# ============================================================ Standzeit
kopf("Standzeit", "Wo bleibt die Zeit stehen?")
links, rechts = st.columns(2)

with links:
    st.markdown("**Top-Touren nach Standzeit-Summe**")
    tt = touren.reset_index().nlargest(15, "standzeit_summe_min")
    chart_t = alt.Chart(tt).mark_bar(color=IST).encode(
        x=alt.X("standzeit_summe_min:Q", title="Standzeit-Summe (min)"),
        y=alt.Y("tour_nr:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("tour_nr:N", title="Tour"),
                 alt.Tooltip("standzeit_summe_min:Q", format=".0f", title="Standzeit (min)"),
                 alt.Tooltip("zeit_abw_median_min:Q", format=".0f", title="Zeit-Abw. Median (min)")],
    ).properties(height=380)
    st.altair_chart(basis_chart(chart_t), use_container_width=True)
    st.caption("Touren mit der höchsten summierten Standzeit an Kunden – hier steckt das meiste "
               "Verzögerungspotenzial.")

with rechts:
    st.markdown("**Top-Kunden nach Standzeit-Überschreitung**")
    ks = kunden[(kunden["standzeit_min"] >= 5) & kunden["standzeit_abw_min"].notna()]
    kc = (ks.groupby("NAME1").agg(mittel=("standzeit_abw_min", "mean"), n=("standzeit_abw_min", "size"))
            .reset_index())
    kc = kc[kc["n"] >= 3].sort_values("mittel", ascending=False).head(15)
    chart_k = alt.Chart(kc).mark_bar(color=AMBER).encode(
        x=alt.X("mittel:Q", title="Ø Standzeit-Überschreitung (min)"),
        y=alt.Y("NAME1:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("NAME1:N", title="Kunde"),
                 alt.Tooltip("mittel:Q", format=".0f", title="Ø Überschreitung (min)"),
                 alt.Tooltip("n:Q", title="Stopps")],
    ).properties(height=380)
    st.altair_chart(basis_chart(chart_k), use_container_width=True)
    st.caption("Kunden, an denen die Standzeit im Schnitt am stärksten über dem Plan liegt "
               "(positiv = länger als geplant). Nur Kunden mit mindestens 3 gemessenen Stopps.")

st.divider()

# ============================================================ Touren im Vergleich
kopf("Touren", "Größe, Verspätung und Umplanung je Tour")
tv = touren.reset_index().copy()
tv["Re-Disposition"] = tv["redisponiert"].map({True: "re-disponiert", False: "unverändert"})
scatter = alt.Chart(tv.dropna(subset=["zeit_abw_median_min"])).mark_circle(opacity=.75).encode(
    x=alt.X("n_geplant:Q", title="Stopps geplant"),
    y=alt.Y("zeit_abw_median_min:Q", title="Median Zeitabweichung (min)"),
    size=alt.Size("standzeit_summe_min:Q", title="Standzeit-Summe (min)", scale=alt.Scale(range=[20, 600])),
    color=alt.Color("Re-Disposition:N",
                    scale=alt.Scale(domain=["unverändert", "re-disponiert"], range=[PLAN, IST]),
                    legend=alt.Legend(orient="top", title=None)),
    tooltip=[alt.Tooltip("tour_nr:N", title="Tour"),
             alt.Tooltip("n_geplant:Q", title="Stopps geplant"),
             alt.Tooltip("n_gefahren:Q", title="in PRC erfasst"),
             alt.Tooltip("zeit_abw_median_min:Q", format=".0f", title="Zeit-Abw. (min)"),
             alt.Tooltip("standzeit_summe_min:Q", format=".0f", title="Standzeit (min)")]
).properties(height=380)
regel0 = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=INK, strokeDash=[4, 3]).encode(y="y:Q")
st.altair_chart(basis_chart(scatter + regel0), use_container_width=True)
st.caption("Jeder Punkt ist eine Tour. Größere Punkte stehen für mehr summierte Standzeit, rote für "
           "re-disponierte Touren. Die gestrichelte Linie ist der Plan (keine Zeitabweichung).")

st.write("")
st.markdown("**Alle Touren**")
tour_anzeige = touren.reset_index().rename(columns={
    "tour_nr": "Tour", "n_geplant": "Geplant", "n_gefahren": "In PRC erfasst",
    "zeit_abw_median_min": "Zeit-Abw. Median (min)", "standzeit_summe_min": "Standzeit-Summe (min)",
    "n_standzeit_verwertbar": "Stopps mit Standzeit", "reihenfolge_abw": "Reihenfolge geändert",
    "redisponiert": "Re-disponiert"})
st.dataframe(
    tour_anzeige[["Tour", "Geplant", "In PRC erfasst", "Zeit-Abw. Median (min)", "Standzeit-Summe (min)",
                  "Stopps mit Standzeit", "Reihenfolge geändert", "Re-disponiert"]],
    use_container_width=True, hide_index=True, height=300)

st.divider()

# ============================================================ Tour-Detail
kopf("Detailansicht", "Eine Tour Stopp für Stopp")

tour_nr = st.selectbox("Tour wählen", touren.index.tolist())
t = touren.loc[tour_nr]
s = stops[stops["tour_nr"] == tour_nr].sort_values("soll_nummer")

d1, d2, d3, d4 = st.columns(4)
with d1: karte(f"{int(t['n_geplant'])} / {int(t['n_gefahren'])}", "Stopps geplant / in PRC erfasst", accent=PLAN)
zeit_med = t["zeit_abw_median_min"]
with d2: karte("—" if pd.isna(zeit_med) else f"{zeit_med:.0f} min", "Zeit-Abw. Median",
               accent=IST if (not pd.isna(zeit_med) and zeit_med > 0) else GRUEN)
with d3: karte(f"{t['standzeit_summe_min']:.0f} min", "Standzeit-Summe", accent=AMBER)
with d4: karte(f"{'ja' if t['reihenfolge_abw'] else 'nein'} / {'ja' if t['redisponiert'] else 'nein'}",
               "Reihenfolge / Re-disp.", accent=SLATE)

st.write("")
karte_stops = s.dropna(subset=["GEOY", "GEOX"]).copy()
trace = spur[(spur["LKW_KENNZ"] == t["lkw_kennz"]) & (spur["tag"] == t["tag"])].sort_values("Meldungszeit")

if karte_stops.empty:
    st.info("Für diese Tour liegen keine zuordenbaren Stopp-Koordinaten vor.")
else:
    mitte = [karte_stops["GEOY"].mean(), karte_stops["GEOX"].mean()]
    m = folium.Map(location=mitte, zoom_start=10, tiles="cartodbpositron")

    if len(trace) >= 2:
        gradient_line(m, trace[["Breitengrad", "Längengrad"]].values.tolist(),
                      "#E8907F", "#8E1F14", weight=4, opacity=0.85,
                      tooltip="Ist – gefahrene Spur (EMR), hell → dunkel = früh → spät")

    gradient_line(m, karte_stops[["GEOY", "GEOX"]].values.tolist(),
                  "#9DBCE6", "#1B3A66", weight=2, opacity=0.85, dash="8",
                  tooltip="Plan – Soll-Reihenfolge (schematisch), hell → dunkel = früh → spät")

    for _, r in karte_stops.iterrows():
        ist_ank = "—" if pd.isna(r["ist_ankunft"]) else pd.Timestamp(r["ist_ankunft"]).strftime("%H:%M")
        soll_ank = "—" if pd.isna(r["soll_ankunft"]) else pd.Timestamp(r["soll_ankunft"]).strftime("%H:%M")
        zeit = "—" if pd.isna(r["zeit_abw_min"]) else f"{r['zeit_abw_min']:+.0f} min"
        sz = "—" if pd.isna(r["standzeit_min"]) else f"{r['standzeit_min']:.0f} min ({r['standzeit_quelle']})"
        popup = folium.Popup(
            f"<b>Stopp {int(r['soll_nummer'])}: {r['NAME1']}</b><br>"
            f"Ausführung: {r['ausfuehrung']}<br>"
            f"Soll-Ankunft: {soll_ank} &nbsp; Ist: {ist_ank} ({zeit})<br>"
            f"Standzeit: {sz}", max_width=300)
        if r["ist_basis"]:
            farbe, symbol = "gray", "home"
        elif r["ausfuehrung"] == "nur geplant":
            farbe, symbol = "lightgray", "remove"
        else:
            farbe, symbol = "blue", "info-sign"
        folium.Marker([r["GEOY"], r["GEOX"]], popup=popup,
                      icon=folium.Icon(color=farbe, icon=symbol)).add_to(m)

    st.markdown(
        f"<span style='color:{PLAN}'>●</span> Plan (Soll-Reihenfolge, schematisch) &nbsp;&nbsp; "
        f"<span style='color:{IST}'>●</span> Ist (gefahrene Spur) &nbsp;&nbsp; "
        "je heller, desto früher · je dunkler, desto später im Tourverlauf &nbsp;&nbsp; "
        "graue Marker = Basis · hellgrau = nur geplant", unsafe_allow_html=True)
    st_folium(m, use_container_width=True, height=520, returned_objects=[])

st.markdown("**Stopps dieser Tour**")
tab = s[["soll_nummer", "NAME1", "ausfuehrung", "soll_ankunft", "ist_ankunft",
         "zeit_abw_min", "soll_standzeit_min", "standzeit_min", "standzeit_quelle"]].rename(columns={
    "soll_nummer": "Nr", "NAME1": "Stopp", "ausfuehrung": "Ausführung", "soll_ankunft": "Soll-Ankunft",
    "ist_ankunft": "Ist-Ankunft", "zeit_abw_min": "Zeit-Abw. (min)",
    "soll_standzeit_min": "Soll-Standzeit (min)", "standzeit_min": "Ist-Standzeit (min)",
    "standzeit_quelle": "Quelle"})
st.dataframe(tab, use_container_width=True, hide_index=True)
