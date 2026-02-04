import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import statsmodels.api as sm
from scipy.spatial import distance

# ==============================================================================
# 0. CONFIGURACIÓN VISUAL (MODO ALTO CONTRASTE CORREGIDO)
# ==============================================================================
st.set_page_config(page_title="ALBORÁN ANALYTICS", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
    /* FONDO Y TEXTO GENERAL */
    .stApp { background-color: #050505; color: #FFFFFF !important; font-family: 'Verdana', sans-serif; }
    p, h1, h2, h3, h4, li, div, label, span { color: #FFFFFF !important; }
    
    /* CAJAS EXPLICATIVAS (VERDES) */
    .didactic-box {
        background-color: #101010; 
        border-left: 5px solid #00E676; 
        padding: 20px; 
        margin-bottom: 20px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* TARJETAS DE DATOS (KPIs) */
    .kpi-card {
        background-color: #1E1E1E; 
        border: 1px solid #333; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center;
        margin-bottom: 10px;
    }
    .kpi-value { font-size: 2.2em; font-weight: bold; color: #00E676 !important; }
    .kpi-label { font-size: 0.9em; font-weight: bold; text-transform: uppercase; color: #AAAAAA !important; letter-spacing: 1px;}
    
    /* COLORES DE ÉNFASIS */
    .text-red { color: #FF5252 !important; }
    .text-blue { color: #448AFF !important; }

    /* AJUSTES DE MAPA */
    iframe { border-radius: 10px; border: 2px solid #333; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE DATOS (ESTÁTICO - SIN PARPADEOS)
# ==============================================================================
@st.cache_data
def get_malaga_data():
    """Generación de datos estática usando semilla fija."""
    np.random.seed(42) # CLAVE: Esto evita que el mapa cambie al recargar
    
    CENTER_LAT, CENTER_LON = 36.7213, -4.4214
    
    districts = {
        "Centro Histórico": {"lat": 36.7213, "lon": -4.4214, "price": 1400, "airbnb_rate": 0.80},
        "La Malagueta":     {"lat": 36.7196, "lon": -4.4100, "price": 1800, "airbnb_rate": 0.65},
        "Soho / Puerto":    {"lat": 36.7160, "lon": -4.4230, "price": 1600, "airbnb_rate": 0.70},
        "Teatinos (Univ)":  {"lat": 36.7170, "lon": -4.4750, "price": 900,  "airbnb_rate": 0.10},
        "Huelin / Oeste":   {"lat": 36.7050, "lon": -4.4450, "price": 850,  "airbnb_rate": 0.30},
        "Pedregalejo":      {"lat": 36.7220, "lon": -4.3800, "price": 1500, "airbnb_rate": 0.55},
        "Ciudad Jardín":    {"lat": 36.7450, "lon": -4.4250, "price": 700,  "airbnb_rate": 0.05},
    }
    
    all_data = []
    
    # Generamos 4.000 viviendas
    for _ in range(4000):
        dist_name = np.random.choice(list(districts.keys()), p=[0.15, 0.10, 0.10, 0.20, 0.20, 0.10, 0.15])
        d = districts[dist_name]
        
        lat = np.random.normal(d["lat"], 0.007)
        lon = np.random.normal(d["lon"], 0.007)
        
        dist_center = distance.euclidean((lat, lon), (CENTER_LAT, CENTER_LON)) * 100 
        is_airbnb = 1 if np.random.random() < d["airbnb_rate"] else 0
        sqm = int(np.random.normal(80, 25))
        
        # Fórmula de Precio
        price_noise = np.random.normal(0, 100)
        final_price = d["price"] + (is_airbnb * 450) - (dist_center * 80) + (sqm * 3) + price_noise
        
        all_data.append({
            "lat": lat, "lon": lon, "district": dist_name,
            "price": int(max(final_price, 400)),
            "is_airbnb": is_airbnb,
            "type": "Piso Turístico" if is_airbnb else "Residencial",
            "sqm": sqm,
            "dist_center": dist_center
        })
        
    return pd.DataFrame(all_data)

df = get_malaga_data()

# ==============================================================================
# 2. ENCABEZADO
# ==============================================================================
st.title("🏛️ PROJECT ALBORÁN: Análisis de Gentrificación")
st.markdown("""
Sistema de inteligencia urbana para analizar el impacto del turismo en el mercado residencial de Málaga.
""")

# ==============================================================================
# 3. NAVEGACIÓN (2 PESTAÑAS)
# ==============================================================================
tab1, tab2 = st.tabs(["🗺️ MAPA DE CALOR", "🧮 EVIDENCIA MATEMÁTICA"])

# ------------------------------------------------------------------------------
# PESTAÑA 1: EL MAPA VISUAL
# ------------------------------------------------------------------------------
with tab1:
    st.header("📍 Diagnóstico Espacial")
    
    col_map, col_info = st.columns([3, 1])
    
    with col_map:
        m = folium.Map(location=[36.7213, -4.4214], zoom_start=13, tiles="CartoDB dark_matter")
        
        # HEATMAP (Airbnbs)
        heat_data = df[df["is_airbnb"] == 1][['lat', 'lon']].values.tolist()
        HeatMap(heat_data, radius=14, blur=8, 
                gradient={0.4: '#2962FF', 0.7: '#FFEB3B', 1: '#FF1744'}, 
                name="Densidad Turística").add_to(m)
        
        # CLUSTERS (Residencial) - Muestreo para rendimiento
        residential_group = MarkerCluster(name="Viviendas Vecinos").add_to(m)
        sample_res = df[df["is_airbnb"] == 0].sample(300)
        
        for _, row in sample_res.iterrows():
            color = "#00E676" 
            if row['price'] > 1200: color = "orange"
            if row['price'] > 1800: color = "red"
            
            folium.CircleMarker(
                [row['lat'], row['lon']], radius=5, color=color, fill=True, fill_opacity=0.8,
                popup=f"Alquiler: {row['price']}€"
            ).add_to(residential_group)
        
        folium.LayerControl().add_to(m)
        
        # FIX PARPADEO: returned_objects=[] evita el bucle de recarga
        st_folium(m, width="100%", height=600, returned_objects=[])

    with col_info:
        total_p = len(df)
        total_airbnb = df["is_airbnb"].sum()
        turist_saturation = (total_airbnb / total_p) * 100
        avg_price = df[df["is_airbnb"] == 0]["price"].mean()
        
        st.subheader("Métricas Clave")
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Saturación Turística</div>
            <div class="kpi-value text-red">{turist_saturation:.1f}%</div>
            <p>Porcentaje del parque de viviendas dedicado a uso turístico.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Alquiler Medio</div>
            <div class="kpi-value">{avg_price:.0f} €</div>
            <p>Precio medio soportado por los residentes locales.</p>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PESTAÑA 2: MATEMÁTICAS
# ------------------------------------------------------------------------------
with tab2:
    st.header("🧮 Análisis Econométrico (Regresión Hedónica)")
    
    st.markdown("""
    <div class="didactic-box">
        <h4>📘 Aislamiento de Variables</h4>
        <p>Utilizamos un modelo de <strong>Mínimos Cuadrados Ordinarios (OLS)</strong> para determinar científicamente cuánto valor añade el factor "Turismo" a una vivienda, aislando otras variables como el tamaño o la ubicación.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("EJECUTAR MODELO OLS"):
        with st.spinner("Calculando coeficientes beta..."):
            X = df[["is_airbnb", "dist_center", "sqm"]]
            X = sm.add_constant(X)
            Y = df["price"]
            
            model = sm.OLS(Y, X).fit()
            
            premium_airbnb = model.params["is_airbnb"]
            saving_dist = model.params["dist_center"]
            r2 = model.rsquared
            
            # --- KPIs ---
            c1, c2, c3 = st.columns(3)
            
            c1.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">PREMIUM TURÍSTICO</div>
                <div class="kpi-value text-red">+{premium_airbnb:.0f} €</div>
                <p>Incremento de precio puro por convertir a uso turístico.</p>
            </div>""", unsafe_allow_html=True)
            
            c2.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">FACTOR UBICACIÓN</div>
                <div class="kpi-value text-blue">{saving_dist:.0f} €</div>
                <p>Reducción de precio por cada Km de distancia al centro.</p>
            </div>""", unsafe_allow_html=True)
            
            c3.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">R² (FIABILIDAD)</div>
                <div class="kpi-value">{r2:.2f}</div>
                <p>El modelo explica el {r2*100:.0f}% de la varianza de precios.</p>
            </div>""", unsafe_allow_html=True)
            
            st.success("Análisis econométrico completado.")
            
            # --- FIX VISIBILIDAD REPORTE TÉCNICO ---
            st.markdown("### Resumen Técnico del Modelo")
            
            # Usamos HTML directo para forzar fondo oscuro y letra blanca en el reporte
            summary_html = f"""
            <div style="
                background-color: #0d1117; 
                color: #c9d1d9; 
                padding: 15px; 
                border-radius: 6px; 
                border: 1px solid #30363d; 
                font-family: 'Courier New', monospace; 
                white-space: pre; 
                overflow-x: auto;
                font-size: 0.85em;">
{model.summary().as_text()}
            </div>
            """
            st.markdown(summary_html, unsafe_allow_html=True)

# ==============================================================================
# PIE DE PÁGINA
# ==============================================================================
st.markdown("---")
st.caption("Proyecto Académico | Modelado con Python, Statsmodels & Folium")