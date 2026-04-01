
import streamlit as st
import fastf1
import pandas as pd

st.set_page_config(page_title="F1 Strategic Overview", layout="wide")
st.title("🏁 F1 Strategic Session Overview")

# Funzione per formattare i tempi (mm:ss.ms)
def format_time(td):
    if pd.isnull(td): return "N/A"
    ts = td.total_seconds()
    return f"{int(ts//60)}:{ts%60:06.3f}"

# 1. Sidebar per la selezione
year = st.sidebar.selectbox("Anno", [2026, 2025, 2024], index=0)

@st.cache_data
def get_calendar(year):
    schedule = fastf1.get_event_schedule(year)
    return schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()

available_gps = get_calendar(year)
gp_choice = st.sidebar.selectbox("Gran Premio", available_gps)
stype = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

# Inizializziamo la memoria dell'app se non esiste
if 'session_data' not in st.session_state:
    st.session_state.session_data = None

if st.sidebar.button("🚀 CARICA DATI"):
    with st.spinner("Scaricando i dati..."):
        session = fastf1.get_session(year, gp_choice, stype)
        session.load(laps=True, telemetry=False, weather=False)
        # Salviamo la sessione nella memoria dello stato
        st.session_state.session_data = session
        st.session_state.gp_name = gp_choice

# 2. Visualizzazione (avviene solo se i dati sono in memoria)
if st.session_state.session_data is not None:
    session = st.session_state.session_data
    st.header(f"Risultati: {st.session_state.gp_name} ({year})")
    
    # --- CLASSIFICA ---
    laps = session.laps.dropna(subset=['LapTime'])
    summary = laps.sort_values(by='LapTime').groupby('Driver').first().reset_index()
    summary = summary[['Driver', 'LapTime', 'Compound', 'TyreLife']].sort_values(by='LapTime')

    view_summary = summary.copy()
    view_summary['LapTime'] = view_summary['LapTime'].apply(format_time)
    
    st.subheader("Migliori Giri della Sessione")
    st.table(view_summary)

    # --- DETTAGLIO PILOTA ---
    st.divider()
    driver_list = sorted(session.laps['Driver'].unique())
    # Qui il cambio di pilota non cancellerà più tutto!
    driver_choice = st.selectbox("Seleziona un pilota per l'analisi completa:", driver_list)
    
    if driver_choice:
        driver_laps = session.laps.pick_driver(driver_choice).reset_index()
        details = driver_laps[['LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'Compound', 'TyreLife']].copy()
        
        for col in ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']:
            details[col] = details[col].apply(format_time)
        
        st.subheader(f"Tutti i giri di {driver_choice}")
        st.dataframe(details, use_container_width=True)
else:
    st.info("Configura i parametri nella sidebar e clicca 'CARICA DATI' per iniziare.")
