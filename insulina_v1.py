import streamlit as st
import pandas as pd
import numpy as np
import datetime

st.set_page_config(page_title="Control de Insulina", layout="wide")
st.title("📊 Monitor de Insulina Activa (IOB)")

# 1. Base de datos simulada en memoria (puedes guardarla en un archivo después)
if "dosis_log" not in st.session_state:
    st.session_state.dosis_log = pd.DataFrame(columns=["Fecha_Hora", "Tipo", "Unidades"])

# 2. Formulario de entrada de datos
st.sidebar.header("💉 Registrar Nueva Dosis")
fecha = st.sidebar.date_input("Fecha", datetime.date.today())
hora = st.sidebar.time_input("Hora", datetime.time(12, 0))
tipo_insulina = st.sidebar.selectbox("Tipo de Insulina", ["Humalog (Rápida)", "Toujeo (Basal)"])
unidades = st.sidebar.number_input("Unidades", min_value=0.5, max_value=50.0, value=2.0, step=0.5)

if st.sidebar.button("Guardar Aplicación"):
    nueva_fecha_hora = datetime.datetime.combine(fecha, hora)
    nueva_fila = pd.DataFrame([{"Fecha_Hora": nueva_fecha_hora, "Tipo": tipo_insulina, "Unidades": unidades}])
    st.session_state.dosis_log = pd.concat([st.session_state.dosis_log, nueva_fila], ignore_index=True)
    st.sidebar.success("¡Dosis registrada!")

# Mostrar historial registrado
st.sidebar.subheader("Historial de hoy")
st.sidebar.dataframe(st.session_state.dosis_log)

# 3. Modelado Matemático y Gráfico
if not st.session_state.dosis_log.empty:
    # Definir el rango del gráfico: desde la primera dosis hasta 36 horas después de la última
    inicio_grafico = st.session_state.dosis_log["Fecha_Hora"].min()
    fin_grafico = st.session_state.dosis_log["Fecha_Hora"].max() + datetime.timedelta(hours=36)
    
    # Crear línea de tiempo cada 15 minutos
    tiempo_eje = pd.date_range(start=inicio_grafico, end=fin_grafico, freq="15min")
    
    # Arrays para acumular la insulina activa en sangre
    humalog_total = np.zeros(len(tiempo_eje))
    toujeo_total = np.zeros(len(tiempo_eje))
    
    # Calcular el impacto de cada dosis insertada
    for _, fila in st.session_state.dosis_log.iterrows():
        t_aplicacion = fila["Fecha_Hora"]
        u = fila["Unidades"]
        
        # Calcular los minutos transcurridos desde esta dosis para cada punto del eje X
        minutos_transcurridos = (tiempo_eje - t_aplicacion).total_seconds() / 60.0
        
        if fila["Tipo"] == "Humalog (Rápida)":
            # Duración: 4 horas (240 mins). Inicio a los 15 mins.
            # Curva matemática suavizada (Decaimiento cuadrático)
            efecto = np.where(
                (minutos_transcurridos >= 15) & (minutos_transcurridos <= 240),
                u * (1 - ((minutos_transcurridos - 15) / 225) ** 2),
                0.0
            )
            humalog_total += efecto
            
        elif fila["Tipo"] == "Toujeo (Basal)":
            # Duración: 36 horas (2160 mins). Efecto plano constante distribuido por minuto
            efecto = np.where(
                (minutos_transcurridos >= 0) & (minutos_transcurridos <= 2160),
                u / 36.0,  # Distribuye las unidades equitativamente por hora de acción
                0.0
            )
            toujeo_total += efecto

    # 4. Crear tabla de resultados para el gráfico
    df_grafico = pd.DataFrame({
        "Tiempo": tiempo_eje,
        "Humalog Activa": humalog_total,
        "Toujeo Activa": toujeo_total,
        "Insulina Total en Sangre": humalog_total + toujeo_total
    })
    df_grafico.set_index("Tiempo", inplace=True)

    # 5. Dibujar las curvas de forma interactiva
    st.subheader("📈 Curva de Acción Combinada en Tiempo Real")
    st.line_chart(df_grafico)
    
    # Alerta visual del estado actual
    ahora = datetime.datetime.now()
    # Buscar el punto más cercano al tiempo actual para decirle cuánta insulina hay "ahora"
    idx_actual = np.abs(tiempo_eje - ahora).argmin()
    st.metric(
        label="Insulina Activa Estimada en este Momento", 
        value=f"{df_grafico['Insulina Total en Sangre'].iloc[idx_actual]:.2f} Unidades"
    )
else:
    st.info("Introduce la primera dosis en el menú de la izquierda para generar la gráfica.")
