import streamlit as st
import fastf1
import pandas as pd

st.set_page_config(page_title="F1 Strategic Overview", layout="wide")
st.title("🏁 F1 Strategic Session Overview")

# 1. Selezione Anno (Prima di tutto, per caricare il calendario giusto)
year = st.sidebar.selectbox("Seleziona Anno", [2026, 2025, 2024], index=0)

@st.cache_data # Memorizza il calendario per non scaricarlo ogni volta
def get_calendar(year):
    schedule = fastf1.get_event_schedule(year)
    # Filtriamo solo gli eventi che sono veri GP (escludiamo i Test se vuoi)
    return schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()

try:
    available_gps = get_calendar(year)
    
    # 2. Sidebar con i GP disponibili presi da FastF1
    gp_choice = st.sidebar.selectbox("Seleziona Gran Premio", available_gps)
    stype = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

    if st.sidebar.button("🚀 CARICA DATI", use_container_width=True):
        with st.spinner(f"Scaricando i dati di {gp_choice}..."):
            session = fastf1.get_session(year, gp_choice, stype)
            session.load()
            
            if len(session.laps) == 0:
                st.warning("Sessione non ancora disponibile o senza dati.")
            else:
                st.header(f"Risultati: {gp_choice} ({year})")
                
                # --- CLASSIFICA MIGLIORI GIRI ---
                best_laps = session.laps.pick_quickest_per_driver()
                summary = best_laps[['Driver', 'LapTime', 'Compound', 'TyreLife']].copy()
                summary = summary.sort_values(by='LapTime').reset_index(drop=True)
                
                def format_time(td):
                    if pd.isnull(td): return "N/A"
                    ts = td.total_seconds()
                    return f"{int(ts//60)}:{ts%60:06.3f}"

                summary['LapTime'] = summary['LapTime'].apply(format_time)
                st.subheader("Tabella Tempi e Mescole")
                st.table(summary)

                # --- DETTAGLIO PILOTA ---
                st.divider()
                driver_list = sorted(session.laps['Driver'].unique())
                driver_choice = st.selectbox("Analisi dettagliata Pilota:", driver_list)
                
                if driver_choice:
                    driver_laps = session.laps.pick_driver(driver_choice).reset_index()
                    details = driver_laps[['LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'Compound', 'TyreLife']].copy()
                    
                    for col in ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']:
                        details[col] = details[col].apply(format_time)
                    
                    st.dataframe(details, use_container_width=True)

except Exception as e:
    st.error(f"Errore nel caricamento del calendario: {e}")
