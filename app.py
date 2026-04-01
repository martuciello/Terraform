import streamlit as st
import fastf1
import pandas as pd

st.set_page_config(page_title="F1 Session Analyzer", layout="wide")
st.title("🏁 F1 Strategic Session Overview")

# Sidebar per la selezione
st.sidebar.header("Parametri Ricerca")
year = st.sidebar.selectbox("Anno", [2026, 2025, 2024], index=0)
gp = st.sidebar.text_input("Nome GP o Numero (es. 1)", value="1")
stype = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

if st.sidebar.button("Carica Sessione"):
    with st.spinner("Caricamento in corso..."):
        session = fastf1.get_session(year, gp, stype)
        session.load(laps=True, telemetry=False, weather=False)
        
        # --- SEZIONE 1: RIEPILOGO MIGLIORI GIRI ---
        st.header(f"Migliori Tempi: {session.event['EventName']}")
        
        # Estraiamo il miglior giro per ogni pilota
        best_laps = session.laps.pick_quickest_per_driver().reset_index()
        summary = best_laps[['Driver', 'LapTime', 'Compound', 'TyreLife']].sort_values(by='LapTime')
        
        # Formattazione tempi per renderli leggibili
        summary['LapTime'] = summary['LapTime'].dt.total_seconds().apply(lambda x: f"{int(x//60)}:{x%60:06.3f}")
        
        st.table(summary)

        # --- SEZIONE 2: DETTAGLIO PILOTA ---
        st.divider()
        driver_choice = st.selectbox("Seleziona un pilota per vedere tutti i suoi giri:", session.laps['Driver'].unique())
        
        if driver_choice:
            st.subheader(f"Analisi Completa: {driver_choice}")
            driver_laps = session.laps.pick_driver(driver_choice).reset_index()
            
            # Selezione colonne per i parziali
            details = driver_laps[['LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'Compound', 'TyreLife']]
            
            # Convertiamo i tempi in formato leggibile (mm:ss.ms)
            for col in ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']:
                details[col] = details[col].dt.total_seconds()
            
            st.dataframe(details.style.highlight_min(subset=['Sector1Time', 'Sector2Time', 'Sector3Time'], color='lightgreen'))

st.info("Ricorda: Il file 'requirements.txt' deve contenere: fastf1, streamlit, pandas")

