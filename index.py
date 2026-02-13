import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import folium_static
import pymysql

st.set_page_config(
    page_title="Mapa Zacatecas - Electores",
    page_icon="🗺️",
    layout="wide"
)

# ---------------------------------------------------
# ESTILO VISUAL PERSONALIZADO
# ---------------------------------------------------
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            background-color: white !important;
        }

        h1 {
            text-align: center;
            font-weight: 700;
            color: #650021;
        }

        .stTextInput>div>div>input {
            border: 2px solid #650021;
            border-radius: 8px;
        }

        .stTextInput>label {
            color: #650021;
            font-weight: 600;
        }

        .stSubheader {
            color: #650021;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Mapa Electoral - Zacatecas")

# ---------------------------------------------------
# LEER EXCEL
# ---------------------------------------------------
@st.cache_data
def load_excel(path='COLONIAS ZAC.xlsx'):
    xls = pd.ExcelFile(path)
    sheet1 = pd.read_excel(xls, xls.sheet_names[0])
    sheet2 = pd.read_excel(xls, xls.sheet_names[1])

    sheet1['SECCION'] = sheet1['SECCION'].astype(str).str.strip().str.zfill(4)
    sheet2['Catalogo de Colonias_seccion'] = sheet2['Catalogo de Colonias_seccion'].astype(str).str.strip().str.zfill(4)

    seccion_colonia = {}

    for _, row in sheet1.iterrows():
        seccion_colonia[row['SECCION']] = row['NOMBRE DE LA COLONIA']

    for _, row in sheet2.iterrows():
        sec = row['Catalogo de Colonias_seccion']
        if sec not in seccion_colonia:
            seccion_colonia[sec] = row['NOMBRE DE LA COLONIA']

    return seccion_colonia

# ---------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------
@st.cache_data
def get_ine_data():
    connection = pymysql.connect(
        host='sql3.freesqldatabase.com',
        user='sql3816861',
        password='Xvkw87Sknd',
        database='sql3816861',
        port=3306
    )

    query = "SELECT seccion, COUNT(*) as total_votantes FROM ine GROUP BY seccion"
    df = pd.read_sql(query, connection)
    connection.close()

    df['seccion'] = df['seccion'].astype(str).str.strip().str.zfill(4)
    return df

# ---------------------------------------------------
# GEOJSON
# ---------------------------------------------------
@st.cache_data
def load_geojson(path='zacatecas_capital_secciones.geojson'):
    with open(path) as f:
        geojson_data = json.load(f)

    for feature in geojson_data['features']:
        feature['properties']['seccion'] = str(
            feature['properties']['seccion']
        ).strip().zfill(4)

    return geojson_data['features']

# ---------------------------------------------------
# MAPA
# ---------------------------------------------------
def create_map(features, seccion_colonia, db_data, filtro_seccion=None):

    db_dict = {row['seccion']: row['total_votantes'] for _, row in db_data.iterrows()}

    m = folium.Map(
        location=[22.7709, -102.5832],
        zoom_start=13,
        tiles=None
    )

    # Vialidad
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="🛣️ Vialidad",
        control=True
    ).add_to(m)

    # Satélite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="🛰️ Satélite",
        control=True
    ).add_to(m)

    # DIBUJAR SECCIONES
    for feature in features:
        seccion = feature['properties']['seccion']

        if filtro_seccion and seccion != filtro_seccion:
            continue

        colonia = seccion_colonia.get(seccion, "Sin nombre")
        total = db_dict.get(seccion, 0)

        popup_text = f"""
        <div style="font-size:14px">
        <b>Sección:</b> {seccion}<br>
        <b>Colonia:</b> {colonia}<br>
        <b>Total electores:</b> {total}
        </div>
        """

        if total == 0:
            fill_color = "#f5f5f5"
        elif total <= 2:
            fill_color = "#d4a5b5"
        elif total <= 5:
            fill_color = "#a03a5a"
        else:
            fill_color = "#650021"

        folium.GeoJson(
            feature,
            control=False,
            style_function=lambda f, fill_color=fill_color: {
                'fillColor': fill_color,
                'color': '#650021',
                'weight': 1.5,
                'fillOpacity': 0.3
            },
            highlight_function=lambda f: {
                'weight': 3,
                'color': '#650021'
            },
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    return m

# ---------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------
seccion_colonia = load_excel()
geo_features = load_geojson()
db_data = get_ine_data()

st.subheader("Buscar sección")

filtro = st.text_input("Escribe la sección que deseas filtrar").strip()

if filtro != "":
    filtro = filtro.zfill(4)
else:
    filtro = None

if geo_features and seccion_colonia:
    mapa = create_map(geo_features, seccion_colonia, db_data, filtro)
    folium_static(mapa, width=1600, height=750)
else:
    st.error("No se pudieron cargar los datos.")

st.subheader("🗺️ Mapa de Zacatecas - Colonias y Electores")
