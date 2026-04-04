

import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="F1 Energy Analytics", layout="wide")
st.title("⚡ F1 2026: Battery & Clipping Analyzer")

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
    tab1, tab2 = st.tabs(["📊 Classifica & Tempi", "🔋 Analisi Batteria & Clipping"])

    # --- TAB 1: CLASSIFICA (CORRETTA) ---
    with tab1:
        st.subheader("Migliori Tempi della Sessione")
        laps = session.laps.dropna(subset=['LapTime'])
        # Metodo ultra-sicuro per la classifica
        drivers = laps['Driver'].unique()
        best_laps_list = []
        for d in drivers:
            best_laps_list.append(laps.pick_driver(d).pick_fastest())
        
        summary = pd.DataFrame(best_laps_list).sort_values(by='LapTime')
        summary['Tempo'] = summary['LapTime'].apply(format_time)
        st.dataframe(summary[['Driver', 'Tempo', 'Compound', 'TyreLife']], use_container_width=True)

    # --- TAB 2: BATTERIA & CLIPPING ---
    with tab2:
        dr = st.selectbox("Seleziona Pilota per analisi ERS:", sorted(session.laps['Driver'].unique()))
        all_laps = session.laps.pick_driver(dr).dropna(subset=['LapTime'])
        lap_labels = {f"G {int(r['LapNumber'])} - {format_time(r['LapTime'])}": r['LapNumber'] for _, r in all_laps.iterrows()}
        sel_lap = st.selectbox("Seleziona Giro:", list(lap_labels.keys()))
        
        lap_data = all_laps[all_laps['LapNumber'] == lap_labels[sel_lap]].iloc[0]
        t = lap_data.get_telemetry().add_distance()

        # ALGORITMO BATTERIA MIGLIORATO
        # Ricarica (MGU-K) = Forza frenante + Velocità
        # Consumo (Deployment) = Throttle + Resistenza Aria (V^2)
        recovery = (t['Brake'] * 1.5) * (t['Speed'] / 200) 
        deployment = (t['Throttle'] / 100) * (0.8 + (t['Speed'] / 350)**2)
        
        # Flusso Energetico Netto
        energy_flow = recovery - deployment

        # Calcolo Clipping (Velocità piatta con Gas 100%)
        # Se la variazione di velocità è minima (< 1km/h) ma il gas è > 95%
        v_diff = np.gradient(t['Speed'])
        clipping = np.where((t['Throttle'] > 95) & (v_diff < 0.2), 1, 0)

        # Grafici
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                            subplot_titles=("Velocità e Zone di Clipping", "Flusso Energetico (Verde=Carica, Rosso=Spinta)", "Livello Batteria Stimato (%)"))

        # 1. Velocità + Evidenza Clipping
        fig.add_trace(go.Scatter(x=t['Distance'], y=t['Speed'], name="Velocità", line=dict(color='white')), row=1, col=1)
        fig.add_trace(go.Scatter(x=t['Distance'], y=clipping * t['Speed'], name="Clipping", mode='markers', marker=dict(color='orange', size=4)), row=1, col=1)

        # 2. Energy Flow (Deployment vs Recovery)
        fig.add_trace(go.Scatter(x=t['Distance'], y=energy_flow, fill='tozeroy', name="Flusso Energia", line=dict(color='yellow')), row=2, col=1)

        # 3. Stato di Carica (SoC) - Simulazione più realistica
        soc = 85 + np.cumsum(energy_flow) * 0.05
        soc = np.clip(soc, 10, 100)
        fig.add_trace(go.Scatter(x=t['Distance'], y=soc, name="Livello Batteria", fill='tozeroy', line=dict(color='green')), row=3, col=1)

        fig.update_layout(height=800, hovermode="x unified", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        **Guida all'analisi:**
        - **Puntini Arancioni:** Indicano il **Clipping**. La macchina ha finito l'energia elettrica e non riesce più ad accelerare.
        - **Grafico Centrale:** Quando la linea è sopra lo zero, l'MGU-K sta ricaricando. Sotto lo zero, stai usando il boost.
        - **Livello Batteria:** Se scende troppo velocemente, il pilota dovrà fare 'Lift and Coast' nel giro successivo.
        """)
