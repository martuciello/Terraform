
import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="F1 Telemetry Pro", layout="wide")
st.title("🏎️ F1 2026: Analisi Telemetria, ERS & Clipping")

def format_time(td):
    if pd.isnull(td): return "N/A"
    ts = td.total_seconds()
    return f"{int(ts//60)}:{ts%60:06.3f}"

# --- SIDEBAR ---
year = st.sidebar.selectbox("Anno", [2026, 2025, 2024], index=0)
@st.cache_data
def get_calendar(year):
    return fastf1.get_event_schedule(year)['EventName'].tolist()

available_gps = get_calendar(year)
gp_choice = st.sidebar.selectbox("Gran Premio", available_gps)
stype = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

if 'session_data' not in st.session_state:
    st.session_state.session_data = None
if 'comp_laps' not in st.session_state:
    st.session_state.comp_laps = {"Slot 1": None, "Slot 2": None}

if st.sidebar.button("🚀 CARICA SESSIONE"):
    with st.spinner("Download dati..."):
        session = fastf1.get_session(year, gp_choice, stype)
        session.load()
        st.session_state.session_data = session

if st.session_state.session_data:
    session = st.session_state.session_data
    tab1, tab2 = st.tabs(["📊 Classifica Sessione", "⚔️ Confronto Telemetria & Batteria"])

    # --- TAB 1: CLASSIFICA ---
    with tab1:
        laps = session.laps.dropna(subset=['LapTime'])
        drivers = laps['Driver'].unique()
        best_laps_list = [laps.pick_driver(d).pick_fastest() for d in drivers]
        summary = pd.DataFrame(best_laps_list).sort_values(by='LapTime')
        summary['Tempo'] = summary['LapTime'].apply(format_time)
        st.subheader("Leaderboard")
        st.table(summary[['Driver', 'Tempo', 'Compound', 'TyreLife']])

    # --- TAB 2: CONFRONTO PRO ---
    with tab2:
        c1, c2 = st.columns(2)
        for i, col in enumerate([c1, c2], 1):
            with col:
                dr = st.selectbox(f"Pilota {i}", sorted(session.laps['Driver'].unique()), key=f"d{i}")
                all_laps = session.laps.pick_driver(dr).dropna(subset=['LapTime'])
                lap_labels = {f"G {int(r['LapNumber'])} - {format_time(r['LapTime'])}": r['LapNumber'] for _, r in all_laps.iterrows()}
                sel = st.selectbox(f"Giro {i}", list(lap_labels.keys()), key=f"l{i}")
                if st.button(f"Fissa Slot {i}", use_container_width=True):
                    st.session_state.comp_laps[f"Slot {i}"] = all_laps[all_laps['LapNumber'] == lap_labels[sel]].iloc[0]

        l1, l2 = st.session_state.comp_laps["Slot 1"], st.session_state.comp_laps["Slot 2"]

        if l1 is not None and l2 is not None:
            t1 = l1.get_telemetry().add_distance()
            t2 = l2.get_telemetry().add_distance()

            # --- CALCOLO ERS & CLIPPING ---
            def get_ers_data(t):
                # Flusso: Verde (Recupero) se > 0, Rosso (Uso) se < 0
                flow = (t['Brake'] * 2) - (t['Throttle'] / 100 * (1 + t['Speed']/300))
                # Clipping: gas 100% e accelerazione piatta
                accel = np.gradient(t['Speed'])
                clip = np.where((t['Throttle'] > 98) & (accel < 0.1), t['Speed'], np.nan)
                # Simulazione Batteria (partenza 90%)
                soc = 90 + np.cumsum(flow) * 0.05
                return np.clip(soc, 5, 100), flow, clip

            soc1, flow1, clip1 = get_ers_data(t1)
            soc2, flow2, clip2 = get_ers_data(t2)

            # --- GRAFICI SOVRAPPOSTI ---
            fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                                row_heights=[0.3, 0.15, 0.15, 0.15, 0.25],
                                subplot_titles=("Velocità e Clipping", "Gas %", "Freno %", "Stato Batteria (SoC %)", "Mappa Tracciato (Sincronizzata)"))

            # 1. Velocità + Clipping (Puntini Arancioni)
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Speed'], name=l1['Driver'], line=dict(color='cyan')), row=1, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Speed'], name=l2['Driver'], line=dict(color='magenta')), row=1, col=1)
            fig.add_trace(go.Scatter(x=t1['Distance'], y=clip1, name="Clipping "+l1['Driver'], mode='markers', marker=dict(color='orange', size=5)), row=1, col=1)

            # 2. Gas
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Throttle'], name="Gas "+l1['Driver'], line=dict(color='cyan'), showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Throttle'], name="Gas "+l2['Driver'], line=dict(color='magenta'), showlegend=False), row=2, col=1)

            # 3. Freno
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Brake']*100, name="Freno "+l1['Driver'], line=dict(color='cyan'), showlegend=False), row=3, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Brake']*100, name="Freno "+l2['Driver'], line=dict(color='magenta'), showlegend=False), row=3, col=1)

            # 4. Batteria (Il tuo "Verde e Rosso" ora è visibile nel livello)
            fig.add_trace(go.Scatter(x=t1['Distance'], y=soc1, name="SoC "+l1['Driver'], line=dict(color='cyan', width=3), fill='tozeroy'), row=4, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=soc2, name="SoC "+l2['Driver'], line=dict(color='magenta', width=3)), row=4, col=1)

            # 5. MAPPA SINCRONIZZATA
            fig.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], name="Tracciato", line=dict(color='gray'), hoverinfo='skip'), row=5, col=1)
            # Puntini posizione (Sincronizzati con l'asse X della distanza)
            fig.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], name=l1['Driver']+" Pos", mode='markers', marker=dict(color='cyan', size=10)), row=5, col=1)
            fig.add_trace(go.Scatter(x=t2['X'], y=t2['Y'], name=l2['Driver']+" Pos", mode='markers', marker=dict(color='magenta', size=10)), row=5, col=1)

            fig.update_layout(height=1100, hovermode="x unified", template="plotly_dark", title=f"Battle: {l1['Driver']} vs {l2['Driver']}")
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 Trascina il cursore sul grafico: i puntini sulla mappa in fondo si muoveranno seguendo la posizione esatta in quel momento!")
