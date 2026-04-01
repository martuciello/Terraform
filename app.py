
import streamlit as st
import fastf1
from fastf1 import plotting
import pandas as pd
import matplotlib.pyplot as plt

# Setup grafico F1
plotting.setup_mpl()
st.set_page_config(page_title="F1 Comparison Tool", layout="wide")
st.title("⚔️ F1 Telemetry Comparison Tool")

def format_time(td):
    if pd.isnull(td): return "N/A"
    ts = td.total_seconds()
    return f"{int(ts//60)}:{ts%60:06.3f}"

# --- SIDEBAR ---
year = st.sidebar.selectbox("Anno", [2026, 2025, 2024], index=0)

@st.cache_data
def get_calendar(year):
    schedule = fastf1.get_event_schedule(year)
    return schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()

available_gps = get_calendar(year)
gp_choice = st.sidebar.selectbox("Gran Premio", available_gps)
stype = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

# Inizializzazione Memoria
if 'session_data' not in st.session_state:
    st.session_state.session_data = None
if 'comp_laps' not in st.session_state:
    st.session_state.comp_laps = {"Slot 1": None, "Slot 2": None}

if st.sidebar.button("🚀 CARICA SESSIONE"):
    with st.spinner("Scaricando dati e telemetria..."):
        session = fastf1.get_session(year, gp_choice, stype)
        session.load()
        st.session_state.session_data = session
        st.session_state.comp_laps = {"Slot 1": None, "Slot 2": None} # Reset quando cambi GP

# --- INTERFACCIA DI CONFRONTO ---
if st.session_state.session_data:
    session = st.session_state.session_data
    
    col_sel1, col_sel2 = st.columns(2)
    
    # Selezione per i due slot
    for i, col in enumerate([col_sel1, col_sel2], 1):
        slot = f"Slot {i}"
        with col:
            st.subheader(f"Configura {slot}")
            drivers = sorted(session.laps['Driver'].unique())
            driver = st.selectbox(f"Pilota {i}", drivers, key=f"dr{i}")
            
            d_laps = session.laps.pick_driver(driver).dropna(subset=['LapTime'])
            lap_num = st.selectbox(f"Giro {i}", d_laps['LapNumber'].unique(), key=f"lp{i}")
            
            if st.button(f"Fissa in {slot}", use_container_width=True):
                st.session_state.comp_laps[slot] = d_laps[d_laps['LapNumber'] == lap_num].iloc[0]
                st.toast(f"Giro {lap_num} di {driver} caricato!")

    # --- GENERAZIONE GRAFICO ---
    st.divider()
    l1 = st.session_state.comp_laps["Slot 1"]
    l2 = st.session_state.comp_laps["Slot 2"]

    if l1 is not None and l2 is not None:
        with st.spinner("Generando i grafici..."):
            t1 = l1.get_telemetry().add_distance()
            t2 = l2.get_telemetry().add_distance()
            
            # Colori: Ciano e Magenta per contrasto massimo
            c1, c2 = 'cyan', 'magenta'
            
            fig, ax = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
            plt.subplots_adjust(hspace=0.1)

            # 1. Velocità
            ax[0].plot(t1['Distance'], t1['Speed'], color=c1, label=f"{l1['Driver']} (G{l1['LapNumber']})")
            ax[0].plot(t2['Distance'], t2['Speed'], color=c2, label=f"{l2['Driver
