import streamlit as st
import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt

# Configurazione pagina per Mobile
st.set_page_config(page_title="F1 Energy Analyzer", layout="wide")
plotting.setup_mpl()

st.title("⚡ F1 2026 Energy & Clipping Analyzer")
st.write("Analizza chi gestisce meglio la batteria confrontando la telemetria.")

# Sidebar per i controlli
st.sidebar.header("Impostazioni Sessione")
year = st.sidebar.number_input("Anno", min_value=2024, max_value=2026, value=2026)
gp = st.sidebar.text_input("Gran Premio (es. Bahrain o 1)", value="1")
session_type = st.sidebar.selectbox("Sessione", ["R", "Q", "FP1", "FP2", "FP3"])

d1 = st.sidebar.text_input("Pilota 1 (Sigla)", value="VER").upper()
d2 = st.sidebar.text_input("Pilota 2 (Sigla)", value="HAM").upper()

if st.button("Analizza Dati"):
    with st.spinner("Scaricando i dati dalla telemetria..."):
        try:
            # Caricamento dati
            session = fastf1.get_session(year, gp, session_type)
            session.load()
            
            l1 = session.laps.pick_driver(d1).pick_fastest()
            l2 = session.laps.pick_driver(d2).pick_fastest()
            
            t1 = l1.get_telemetry().add_distance()
            t2 = l2.get_telemetry().add_distance()
            
            # Creazione Grafico
            fig, ax = plt.subplots(3, 1, figsize=(10, 12))
            
            # 1. Velocità e Clipping
            ax[0].plot(t1['Distance'], t1['Speed'], label=d1, color='cyan')
            ax[0].plot(t2['Distance'], t2['Speed'], label=d2, color='magenta')
            ax[0].set_ylabel("Velocità (km/h)")
            ax[0].set_title("Analisi Clipping (Fine Rettilineo)")
            ax[0].legend()
            
            # 2. Gas (Ricarica forzata o Lift & Coast)
            ax[1].plot(t1['Distance'], t1['Throttle'], color='cyan')
            ax[1].plot(t2['Distance'], t2['Throttle'], color='magenta')
            ax[1].set_ylabel("Gas %")
            
            # 3. Freno (Recupero MGU-K)
            ax[2].plot(t1['Distance'], t1['Brake'], color='cyan')
            ax[2].plot(t2['Distance'], t2['Brake'], color='magenta')
            ax[2].set_ylabel("Freno")
            ax[2].set_xlabel("Distanza (m)")

            st.pyplot(fig)
            
            st.success("Analisi completata! Se vedi la velocità piatta col gas al 100%, la batteria è vuota.")
            
        except Exception as e:
            st.error(f"Errore nel caricamento: {e}")
