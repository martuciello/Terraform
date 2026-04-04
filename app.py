
import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="F1 Energy Predictor", layout="wide")
st.title("🔋 F1 2026 Energy & Telemetry Pro")

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
    tab1, tab2, tab3 = st.tabs(["📊 Classifica", "⚔️ Telemetria & Mappa", "🔋 Simulazione Batteria"])

    # --- TAB 1: RIEPILOGO ---
    with tab1:
        laps = session.laps.dropna(subset=['LapTime'])
        summary = laps.sort_values(by='LapTime').groupby('Driver').first().reset_index()
        st.table(summary[['Driver', 'LapTime', 'Compound']].sort_values(by='LapTime'))

    # --- TAB 2: TELEMETRIA (Layout corretto) ---
    with tab2:
        c1, c2 = st.columns(2)
        for i, col in enumerate([c1, c2], 1):
            with col:
                dr = st.selectbox(f"Pilota {i}", sorted(session.laps['Driver'].unique()), key=f"d{i}")
                all_laps = session.laps.pick_driver(dr).dropna(subset=['LapTime'])
                lap_labels = {f"G {int(r['LapNumber'])} - {format_time(r['LapTime'])}": r['LapNumber'] for _, r in all_laps.iterrows()}
                sel = st.selectbox(f"Giro {i}", list(lap_labels.keys()), key=f"l{i}")
                if st.button(f"Fissa {i}", use_container_width=True):
                    st.session_state.comp_laps[f"Slot {i}"] = all_laps[all_laps['LapNumber'] == lap_labels[sel]].iloc[0]

        l1, l2 = st.session_state.comp_laps["Slot 1"], st.session_state.comp_laps["Slot 2"]
        if l1 is not None and l2 is not None:
            t1, t2 = l1.get_telemetry().add_distance(), l2.get_telemetry().add_distance()
            
            # Grafico Telemetria (Espanso)
            fig_tel = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.4, 0.3, 0.3])
            fig_tel.add_trace(go.Scatter(x=t1['Distance'], y=t1['Speed'], name=l1['Driver'], line=dict(color='cyan')), row=1, col=1)
            fig_tel.add_trace(go.Scatter(x=t2['Distance'], y=t2['Speed'], name=l2['Driver'], line=dict(color='magenta')), row=1, col=1)
            fig_tel.add_trace(go.Scatter(x=t1['Distance'], y=t1['Throttle'], name="Gas "+l1['Driver'], line=dict(color='cyan', dash='dot'), showlegend=False), row=2, col=1)
            fig_tel.add_trace(go.Scatter(x=t2['Distance'], y=t2['Throttle'], name="Gas "+l2['Driver'], line=dict(color='magenta', dash='dot'), showlegend=False), row=2, col=1)
            fig_tel.add_trace(go.Scatter(x=t1['Distance'], y=t1['Brake']*100, name="Freno", line=dict(color='white', width=1), showlegend=False), row=3, col=1)
            
            fig_tel.update_layout(height=600, hovermode="x unified", template="plotly_dark", title="Velocità / Gas / Freno")
            st.plotly_chart(fig_tel, use_container_width=True)

            # Mappa separata sotto per non comprimere i grafici
            fig_map = go.Figure()
            fig_map.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], mode='lines', line=dict(color='gray', width=2), hoverinfo='skip'))
            fig_map.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], name=l1['Driver'], mode='markers', marker=dict(color='cyan', size=6)))
            fig_map.update_layout(height=400, template="plotly_dark", title="Posizione sul Tracciato")
            st.plotly_chart(fig_map, use_container_width=True)

    # --- TAB 3: ALGORITMO BATTERIA ---
    with tab3:
        st.header("⚡ Simulazione Carica Batteria (SoC)")
        if l1 is not None:
            t = l1.get_telemetry().add_distance()
            
            # ALGORITMO: Calcolo differenziale energia
            # Recupero (Freno) - Consumo (Gas + Velocità)
            charge = t['Brake'] * 0.5  
            deploy = (t['Throttle'] / 100) * (1 + (t['Speed'] / 300))
            net_energy = charge - deploy
            
            # Integrazione del livello batteria (partendo da 90% in Qualifica)
            soc = 90 + np.cumsum(net_energy) * 0.1 
            soc = np.clip(soc, 0, 100) # Mantieni tra 0 e 100%

            fig_soc = go.Figure()
            fig_soc.add_trace(go.Scatter(x=t['Distance'], y=soc, name="Livello Batteria Estimatp", line=dict(color='yellow', width=3)))
            fig_soc.add_trace(go.Scatter(x=t['Distance'], y=t['Speed']/3.5, name="Velocità (Rapportata)", line=dict(color='gray', dash='dash')))
            
            fig_soc.update_layout(height=500, template="plotly_dark", yaxis_title="Stato di Carica (%)", title=f"Stima ERS: {l1['Driver']}")
            st.plotly_chart(fig_soc, use_container_width=True)
            st.write("🔬 **Nota tecnica:** La ricarica avviene nei picchi negativi della velocità (frenata). Il deployment è massimo in uscita di curva.")
