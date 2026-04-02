
import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="F1 Pro Telemetry & Track", layout="wide")
st.title("🏎️ F1 Interactive: Telemetry + Track Map")

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

# --- INTERFACCIA ---
if st.session_state.session_data:
    session = st.session_state.session_data
    tab1, tab2 = st.tabs(["📊 Riepilogo", "⚔️ Confronto + Mappa"])

    with tab1:
        st.header(f"Classifica: {gp_choice}")
        laps = session.laps.dropna(subset=['LapTime'])
        summary = laps.sort_values(by='LapTime').groupby('Driver').first().reset_index()
        summary = summary[['Driver', 'LapTime', 'Compound', 'TyreLife']].sort_values(by='LapTime')
        view_summary = summary.copy()
        view_summary['LapTime'] = view_summary['LapTime'].apply(format_time)
        st.table(view_summary)

    with tab2:
        st.header("Confronto Telemetria e Posizione su Mappa")
        c1, c2 = st.columns(2)
        
        for i, col in enumerate([c1, c2], 1):
            with col:
                dr = st.selectbox(f"Pilota {i}", sorted(session.laps['Driver'].unique()), key=f"d{i}")
                all_laps = session.laps.pick_driver(dr).dropna(subset=['LapTime'])
                lap_options = {f"Giro {int(row['LapNumber'])} - {format_time(row['LapTime'])}": row['LapNumber'] for _, row in all_laps.iterrows()}
                selected_label = st.selectbox(f"Giro {i}", list(lap_options.keys()), key=f"l{i}")
                if st.button(f"Fissa Slot {i}", use_container_width=True):
                    st.session_state.comp_laps[f"Slot {i}"] = all_laps[all_laps['LapNumber'] == lap_options[selected_label]].iloc[0]

        l1 = st.session_state.comp_laps["Slot 1"]
        l2 = st.session_state.comp_laps["Slot 2"]

        if l1 is not None and l2 is not None:
            # Recupero telemetria e coordinate X, Y
            t1 = l1.get_telemetry().add_distance()
            t2 = l2.get_telemetry().add_distance()

            # Creiamo i subplot: 3 per la telemetria + 1 grande per la mappa
            fig = make_subplots(
                rows=2, cols=2,
                column_widths=[0.7, 0.3],
                row_heights=[0.5, 0.5],
                specs=[[{"rowspan": 2}, {"type": "xy"}], [None, {"type": "xy"}]], # Layout custom
                subplot_titles=("Telemetria Sovrapposta", "Mappa del Tracciato"),
                vertical_spacing=0.1
            )
            
            # --- PARTE TELEMETRIA (A SINISTRA) ---
            # Nota: Per semplicità in mobile usiamo un grafico unico con più linee
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                                subplot_titles=("Velocità", "Gas", "Freno", "Mappa X-Y"),
                                row_heights=[0.25, 0.2, 0.2, 0.35])

            # Velocità
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Speed'], name=l1['Driver'], line=dict(color='cyan')), row=1, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Speed'], name=l2['Driver'], line=dict(color='magenta')), row=1, col=1)
            
            # Gas e Freno
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Throttle'], name="Gas "+l1['Driver'], line=dict(color='cyan', dash='dot'), showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Throttle'], name="Gas "+l2['Driver'], line=dict(color='magenta', dash='dot'), showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=t1['Distance'], y=t1['Brake']*100, name="Freno "+l1['Driver'], line=dict(color='cyan', width=1), showlegend=False), row=3, col=1)
            fig.add_trace(go.Scatter(x=t2['Distance'], y=t2['Brake']*100, name="Freno "+l2['Driver'], line=dict(color='magenta', width=1), showlegend=False), row=3, col=1)

            # --- MAPPA DEL TRACCIATO (A FONDO PAGINA) ---
            fig.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], name="Tracciato", line=dict(color='white', width=4), hoverinfo='skip'), row=4, col=1)
            # Puntini che si muovono sulla mappa
            fig.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], name=l1['Driver']+" Pos", mode='markers', marker=dict(color='cyan', size=8)), row=4, col=1)
            fig.add_trace(go.Scatter(x=t2['X'], y=t2['Y'], name=l2['Driver']+" Pos", mode='markers', marker=dict(color='magenta', size=8)), row=4, col=1)

            fig.update_layout(height=1000, hovermode="x unified", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Seleziona e 'Fissa' i due giri per attivare la telemetria e la mappa.")
