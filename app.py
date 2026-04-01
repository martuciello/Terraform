import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="F1 Pro Analyzer", layout="wide")
st.title("🏎️ F1 Strategic & Interactive Telemetry")

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

if 'session_data' not in st.session_state:
    st.session_state.session_data = None
if 'comp_laps' not in st.session_state:
    st.session_state.comp_laps = {"Slot 1": None, "Slot 2": None}

if st.sidebar.button("🚀 CARICA/AGGIORNA SESSIONE"):
    with st.spinner("Scaricando dati completi..."):
        session = fastf1.get_session(year, gp_choice, stype)
        session.load()
        st.session_state.session_data = session

# --- MAIN INTERFACE CON TAB ---
if st.session_state.session_data:
    session = st.session_state.session_data
    tab1, tab2 = st.tabs(["📊 Riepilogo Sessione", "⚔️ Confronto Telemetria"])

    with tab1:
        st.header(f"Classifica Sessione: {gp_choice}")
        laps = session.laps.dropna(subset=['LapTime'])
        
        # Riepilogo Migliori Giri
        summary = laps.sort_values(by='LapTime').groupby('Driver').first().reset_index()
        summary = summary[['Driver', 'LapTime', 'Compound', 'TyreLife']].sort_values(by='LapTime')
        view_summary = summary.copy()
        view_summary['LapTime'] = view_summary['LapTime'].apply(format_time)
        st.table(view_summary)

        st.divider()
        # Dettaglio Singolo Pilota
        driver_list = sorted(session.laps['Driver'].unique())
        d_choice = st.selectbox("Dettaglio Giri Pilota:", driver_list)
        if d_choice:
            d_laps = session.laps.pick_driver(d_choice).reset_index()
            details = d_laps[['LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'Compound', 'TyreLife']].copy()
            for col in ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']:
                details[col] = details[col].apply(format_time)
            st.dataframe(details, use_container_width=True)

    with tab2:
        st.header("Confronto Telemetria Interattivo")
        c1, c2 = st.columns(2)
        
        for i, col in enumerate([c1, c2], 1):
            with col:
                dr = st.selectbox(f"Pilota {i}", sorted(session.laps['Driver'].unique()), key=f"d{i}")
                # Creiamo una lista di stringhe "Giro X - Tempo" per il selettore
                all_laps = session.laps.pick_driver(dr).dropna(subset=['LapTime'])
                lap_options = {f"Giro {int(row['LapNumber'])} - {format_time(row['LapTime'])}": row['LapNumber'] for _, row in all_laps.iterrows()}
                
                selected_label = st.selectbox(f"Seleziona Giro {i}", list(lap_options.keys()), key=f"l{i}")
                if st.button(f"Fissa {dr} in Slot {i}", use_container_width=True):
                    st.session_state.comp_laps[f"Slot {i}"] = all_laps[all_laps['LapNumber'] == lap_options[selected_label]].iloc[0]

        # --- GRAFICO PLOTLY ---
        l1 = st.session_state.comp_laps["Slot 1"]
        l2 = st.session_state.comp_laps["Slot 2"]

        if l1 is not None and l2 is not None:
            t1 = l1.get_telemetry().add_distance()
            t2 = l2.get_telemetry().add_distance()

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                                subplot_titles=("Velocità (km/h)", "Acceleratore (%)", "Freno (%)"))

            # Velocità
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Speed'], name=f"{l1['Driver']}", line=dict(color='cyan')), row=1, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Speed'], name=f"{l2['Driver']}", line=dict(color='magenta')), row=1, col=1)

            # Gas
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Throttle'], name=f"{l1['Driver']} Gas", line=dict(color='cyan'), showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Throttle'], name=f"{l2['Driver']} Gas", line=dict(color='magenta'), showlegend=False), row=2, col=1)

            # Freno
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Brake']*100, name=f"{l1['Driver']} Freno", line=dict(color='cyan'), showlegend=False), row=3, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Brake']*100, name=f"{l2['Driver']} Freno", line=dict(color='magenta'), showlegend=False), row=3, col=1)

            fig.update_layout(height=800, hovermode="x unified", template="plotly_dark",
                              title=f"Confronto: {l1['Driver']} vs {l2['Driver']}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Scegli due piloti e i rispettivi giri, poi clicca 'Fissa' per vedere il confronto.")
else:
    st.info("Configura la sessione nella sidebar e clicca 'CARICA DATI'.")
