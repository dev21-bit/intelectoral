import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import folium_static
import pymysql
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Mapa Electoral Zacatecas",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------
# ESTILO MEJORADO
# ---------------------------------------------------
st.markdown("""
<style>
    /* Estilos generales */
    html, body, [class*="css"] {
        background-color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    h1 {
        color: #650021;
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    h2, h3 {
        color: #650021;
        font-weight: 600;
    }
    
    /* Mejora de inputs */
    .stTextInput input {
        border: 2px solid #650021;
        border-radius: 10px;
        padding: 10px;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus {
        border-color: #a03a5a;
        box-shadow: 0 0 0 3px rgba(165, 42, 42, 0.1);
    }
    
    /* Mejora de botones */
    .stButton button {
        background-color: #650021;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 25px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    .stButton button:hover {
        background-color: #a03a5a;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #650021;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Pestañas personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        color: #650021;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #650021 !important;
        color: white !important;
    }
    
    /* Tooltips personalizados */
    .folium-tooltip {
        background-color: #650021;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px;
        font-weight: 500;
    }
    
    /* Separadores decorativos */
    .decorative-line {
        height: 3px;
        background: linear-gradient(90deg, transparent, #650021, #a03a5a, #650021, transparent);
        margin: 30px 0;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-success {
        background-color: #28a745;
        color: white;
    }
    
    .badge-warning {
        background-color: #ffc107;
        color: #000;
    }
    
    /* Animaciones */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# LOGIN POR CLAVE
# ---------------------------------------------------
CLAVE_CORRECTA = "zac2026"

# Inicializar estado de login
if "logged_in" not in st.session_state:
    if st.query_params.get("logged_in") == ["true"]:
        st.session_state.logged_in = True
    else:
        st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### Acceso Restringido")
        clave_input = st.text_input("Ingresa la clave para acceder:", type="password")
        
        col_b1, col_b2, col_b3 = st.columns([1,2,1])
        with col_b2:
            entrar = st.button("Entrar", use_container_width=True)
        
        if entrar:
            if clave_input == CLAVE_CORRECTA:
                st.session_state.logged_in = True
                st.query_params = {"logged_in":"true"}
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Clave incorrecta. Intenta de nuevo.")
                st.stop()
        else:
            st.stop()

# ---------------------------------------------------
# HEADER CON INFORMACIÓN
# ---------------------------------------------------
col_logo, col_title, col_user = st.columns([1,3,1])

with col_title:
    st.title("🗳️ Mapa Electoral - Zacatecas")
    st.markdown("<p style='text-align: center; color: #666;'>Sistema de Visualización de Datos Electorales</p>", unsafe_allow_html=True)

with col_user:
    if st.button("🚪 Salir", use_container_width=True):
        st.session_state.logged_in = False
        st.query_params.clear()
        st.rerun()

st.markdown('<div class="decorative-line"></div>', unsafe_allow_html=True)

# ---------------------------------------------------
# INICIALIZAR FECHA DE ACTUALIZACIÓN EN SESSION STATE
# ---------------------------------------------------
if "ultima_actualizacion" not in st.session_state:
    st.session_state.ultima_actualizacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# ---------------------------------------------------
# ACTUALIZACIÓN DE DATOS MEJORADA
# ---------------------------------------------------
with st.container():
    st.markdown("### 📊 Panel de Control")
    
    col1, col2, col3, col4 = st.columns([1,1,2,2])
    
    with col1:
        actualizar = st.button("🔄 Actualizar Datos", use_container_width=True)
    
    with col2:
        if actualizar:
            with st.spinner("🔄 Actualizando datos..."):
                st.cache_data.clear()
                # Actualizar la fecha en session state
                st.session_state.ultima_actualizacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                st.success("✅ Datos actualizados correctamente")
                st.balloons()
                st.rerun()
    
    with col3:
        st.markdown(f"📅 Última actualización: {st.session_state.ultima_actualizacion}")
    
    with col4:
        st.markdown("💾 Versión 2.0")

st.markdown('<div class="decorative-line"></div>', unsafe_allow_html=True)

# ---------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------
@st.cache_data
def get_ine_data():
    connection = pymysql.connect(
        host='sql3.freesqldatabase.com',
        user='sql3817481',
        password='398j6uKWle',
        database='sql3817481',
        port=3306
    )
    query = """
    SELECT
    LPAD(CAST(seccion AS CHAR),4,'0') as seccion,
    SUBSTRING_INDEX(SUBSTRING_INDEX(domicilio,' ', -3),' ',1) as cp,
    COUNT(*) as simpatizantes
    FROM ine
    GROUP BY seccion, cp
    """
    df = pd.read_sql(query, connection)
    connection.close()
    df['cp'] = df['cp'].astype(str)
    df['seccion'] = df['seccion'].astype(str).str.zfill(4)
    return df

# ---------------------------------------------------
# EXCEL COLONIAS
# ---------------------------------------------------
@st.cache_data
def load_excel():
    xls = pd.ExcelFile("COLONIAS ZAC.xlsx")
    sheet1 = pd.read_excel(xls, xls.sheet_names[0])
    sheet2 = pd.read_excel(xls, xls.sheet_names[1])

    data = {}

    sheet1['SECCION'] = sheet1['SECCION'].astype(str).str.zfill(4)
    sheet2['Catalogo de Colonias_seccion'] = sheet2['Catalogo de Colonias_seccion'].astype(str).str.zfill(4)

    for _, row in sheet1.iterrows():
        sec = row['SECCION']
        cp = str(row['CP']).replace(".0","")
        col = row['NOMBRE DE LA COLONIA']
        if sec not in data:
            data[sec] = []
        data[sec].append({"colonia": col, "cp": cp})

    for _, row in sheet2.iterrows():
        sec = row['Catalogo de Colonias_seccion']
        cp = str(row['CP'])
        col = row['NOMBRE DE LA COLONIA']
        if sec not in data:
            data[sec] = []
        data[sec].append({"colonia": col, "cp": cp})

    return data

# ---------------------------------------------------
# RELACION SIMPATIZANTES POR COLONIA
# ---------------------------------------------------
@st.cache_data
def get_simpatizantes_colonia():
    connection = pymysql.connect(
        host='sql3.freesqldatabase.com',
        user='sql3817481',
        password='398j6uKWle',
        database='sql3817481',
        port=3306
    )
    query = """
    SELECT
    LPAD(CAST(seccion AS CHAR),4,'0') as seccion,
    domicilio
    FROM ine
    """
    df = pd.read_sql(query, connection)
    connection.close()
    df['seccion'] = df['seccion'].astype(str).str.zfill(4)
    df["cp"] = df["domicilio"].str.extract(r'(\d{5})(?!.*\d{5})')

    colonias_excel = load_excel()
    resultados = []

    for _, persona in df.iterrows():
        seccion = persona["seccion"]
        domicilio = str(persona["domicilio"]).upper()
        cp = str(persona["cp"])
        if seccion in colonias_excel:
            for col in colonias_excel[seccion]:
                nombre_col = str(col["colonia"]).upper()
                cp_col = str(col["cp"]).replace(".0","")
                if cp == cp_col and nombre_col in domicilio:
                    resultados.append({"seccion": seccion, "colonia": col["colonia"]})
                    break
                elif cp == cp_col:
                    resultados.append({"seccion": seccion, "colonia": col["colonia"]})
                    break

    conteo = pd.DataFrame(resultados)
    if len(conteo) > 0:
        conteo = conteo.groupby(["seccion","colonia"]).size().reset_index(name="simpatizantes")
    else:
        conteo = pd.DataFrame(columns=["seccion","colonia","simpatizantes"])

    return conteo

# ---------------------------------------------------
# GEOJSON
# ---------------------------------------------------
@st.cache_data
def load_geojson():
    with open("zacatecas_capital_secciones.geojson", encoding="utf-8") as f:
        geo = json.load(f)

    for feature in geo["features"]:
        if "SECCION" in feature["properties"]:
            feature["properties"]["seccion"] = str(feature["properties"]["SECCION"]).zfill(4)
        else:
            feature["properties"]["seccion"] = str(feature["properties"]["seccion"]).zfill(4)
    return geo["features"]

# ---------------------------------------------------
# CREAR MAPA
# ---------------------------------------------------
def crear_mapa(features, colonias, db, filtro):
    centro=[22.7709,-102.5832]
    zoom=13
    m=folium.Map(location=centro, zoom_start=zoom, tiles="OpenStreetMap")

    secciones = {}
    for feature in features:
        sec = feature["properties"]["seccion"]
        if sec not in secciones:
            secciones[sec] = []
        secciones[sec].append(feature)

    for seccion, lista_poligonos in secciones.items():
        if filtro and seccion != filtro:
            continue

        datos=db[db.seccion==seccion]
        total=datos.simpatizantes.sum()
        cps=datos.cp.dropna().unique()
        cp_html="<br>".join(cps)
        cols=colonias.get(seccion,[])
        colonias_html="<br>".join(f"{c['colonia']} (CP {c['cp']})" for c in cols)

        detalle = simpatizantes_colonia[simpatizantes_colonia.seccion == seccion]
        detalle_html=""
        for _, row in detalle.iterrows():
            if pd.notna(row["colonia"]):
                detalle_html += f"{row['colonia']} — {row['simpatizantes']}<br>"

        popup=f"""
        <div style='font-family: Arial, sans-serif; min-width: 250px;'>
            <h4 style='color: #650021; margin: 0 0 10px 0;'>Sección {seccion}</h4>
            <hr style='border: 1px solid #650021; margin: 5px 0;'>
            <p><strong>📍 CP registrados:</strong><br>{cp_html}</p>
            <p><strong>Colonias:</strong><br>{colonias_html}</p>
            <p><strong>Simpatizantes totales:</strong> <span style='color: #650021; font-weight: bold;'>{total}</span></p>
            <p><strong>Simpatizantes por colonia:</strong><br>{detalle_html}</p>
        </div>
        """

        if total==0:
            color="#ffffff"
        elif total<=2:
            color="#d4a5b5"
        elif total<=5:
            color="#a03a5a"
        else:
            color="#650021"

        for feature in lista_poligonos:
            folium.GeoJson(
                feature,
                style_function=lambda x,color=color: {
                    "fillColor":color,
                    "color":"#650021",
                    "weight":2,
                    "fillOpacity":0.4
                },
                tooltip=folium.Tooltip(f"Sección: {seccion}<br>Simpatizantes: {total}"),
                popup=folium.Popup(popup, max_width=350)
            ).add_to(m)

        coords = lista_poligonos[0]["geometry"]["coordinates"][0]
        lat=sum(p[1] for p in coords)/len(coords)
        lon=sum(p[0] for p in coords)/len(coords)

        if total>0:
            folium.Marker(
                [lat,lon],
                icon=folium.DivIcon(
                    html=f"""
                    <div style="
                    background:#650021;
                    color:white;
                    padding:8px 12px;
                    border-radius:20px;
                    font-weight:bold;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                    border: 2px solid white;
                    ">
                    {total}
                    </div>
                    """
                )
            ).add_to(m)

    return m

# ---------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------
with st.spinner("🔄 Cargando datos del sistema..."):
    db = get_ine_data()
    colonias = load_excel()
    geo = load_geojson()
    simpatizantes_colonia = get_simpatizantes_colonia()

# ---------------------------------------------------
# BUSCADOR MEJORADO
# ---------------------------------------------------
st.markdown("### 🔍 Búsqueda de Secciones")

col_search1, col_search2, col_search3 = st.columns([2,1,2])

with col_search1:
    st.markdown("##### Ingresa el número de sección:")
    filtro = st.text_input("", placeholder="Ej: 1234", label_visibility="collapsed")
    if filtro:
        filtro = filtro.zfill(4)
    else:
        filtro = None

with col_search2:
    st.markdown("##### &nbsp;")
    if st.button("🗺️ Ver todas", use_container_width=True):
        filtro = None
        st.rerun()

with col_search3:
    if filtro:
        if filtro in db['seccion'].values:
            st.success(f"✅ Sección {filtro} encontrada")
        else:
            st.warning(f"⚠️ Sección {filtro} no encontrada")

st.markdown('<div class="decorative-line"></div>', unsafe_allow_html=True)

# ---------------------------------------------------
# MAPA
# ---------------------------------------------------
st.markdown("### 🗺️ Visualización Geográfica")
st.caption("Haz clic en cualquier sección para ver detalles")

mapa = crear_mapa(geo, colonias, db, filtro)
folium_static(mapa, width=1600, height=600)


# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------
st.markdown('<div class="decorative-line"></div>', unsafe_allow_html=True)

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.markdown(f"**📅 Última actualización:** {st.session_state.ultima_actualizacion}")

with col_footer2:
    st.markdown("**⚙️ Versión:** 2.0.0")
