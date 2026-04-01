
import streamlit as st
import fastf1
from fastf1 import plotting
import pandas as pd
import matplotlib.pyplot as plt

plotting.setup_mpl()
st.set_page_config(page_title="F1 Comparison Tool", layout="wide")
st.title("⚔️ F1 Telemetry Comparison Tool")

def format_time(td):
    if pd.isnull(td): return "N/A"
    ts = td.total_seconds()
    return f"{int(ts//60)}:{ts%60:06.3f}"

# --- SIDEBAR ---
year = st.sidebar.selectbox("Anno", [2026, 2025, 2024], index=0)
available_gps = fastf1.get_event_schedule(year)[['EventName']].iloc[1:].values.flatten()
gp_choice = st.sidebar.selectbox("Gran Premio", available_gps)
stype = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

# Inizializzazione Memoria
if 'session_data' not in st.session_state:
    st.session_state.session_data = None
if 'comp_laps' not in st.session_state:
    st.session_state.comp_laps = {"Slot 1": None, "Slot 2": None}

if st.sidebar.button("🚀 CARICA SESSIONE"):
    with st.spinner("Scaricando telemetria..."):
        session = fastf1.get_session(year, gp_choice, stype)
        session.load()
        st.session_state.session_data = session

# --- MAIN ---
if st.session_state.session_data:
    session = st.session_state.session_data
    
    col_sel1, col_sel2 = st.columns(2)
    
    # Selezione per i due slot di confronto
    for i, col in enumerate([col_sel1, col_sel2], 1):
        slot = f"Slot {i}"
        with col:
            st.subheader(f"Configura {slot}")
            driver = st.selectbox(f"Pilota {i}", sorted(session.laps['Driver'].unique()), key=f"dr{i}")
            d_laps = session.laps.pick_driver(driver).dropna(subset=['LapTime'])
            lap_num = st.selectbox(f"Giro {i}", d_laps['LapNumber'].unique(), key=f"lp{i}")
            
            if st.button(f"Fissa in {slot}"):
                st.session_state.comp_laps[slot] = d_laps[d_laps['LapNumber'] == lap_num].iloc[0]
                st.success(f"{driver} Giro {lap_num} pronto!")

    # --- GRAFICO DI CONFRONTO ---
    st.divider()
    if st.session_state.comp_laps["Slot 1"] is not None and st.session_state.comp_laps["Slot 2"] is not None:
        l1 = st.session_state.comp_laps["Slot 1"]
        l2 = st.session_state.comp_laps["Slot 2"]
        
        t1 = l1.get_telemetry().add_distance()
        t2 = l2.get_telemetry().add_distance()
        
        color1, color2 = 'cyan', 'magenta'
        
        fig, ax = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        
        # 1. Velocità (Clipping e Top Speed)
        ax[0].plot(t1['Distance'], t1['Speed'], color=color1, label=f"{l1['Driver']} - G{l1['LapNumber']}")
        ax[0].plot(t2['Distance'], t2['Speed
