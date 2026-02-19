import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import folium_static
import pymysql

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Mapa Electoral Zacatecas",
    layout="wide"
)


# ---------------------------------------------------
# ESTILO
# ---------------------------------------------------

st.markdown("""
<style>

html, body, [class*="css"] {
background-color:white;
}

h1 {
color:#650021;
text-align:center;
}

.stTextInput input {
border:2px solid #650021;
border-radius:8px;
}

</style>
""", unsafe_allow_html=True)


st.title("Mapa Electoral - Zacatecas")

st.markdown("### Actualización de datos")

col1, col2, col3 = st.columns([1,1,4])

with col1:

    actualizar = st.button(
        "🔄 Actualizar",
        use_container_width=True
    )


with col2:

    if actualizar:

        with st.spinner("Actualizando datos..."):

            st.cache_data.clear()

            st.success("Datos actualizados correctamente")

            st.rerun()
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

    SUBSTRING_INDEX(
        SUBSTRING_INDEX(domicilio,' ', -3),
    ' ',1) as cp,

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

        data[sec].append({

            "colonia": col,
            "cp": cp

        })


    for _, row in sheet2.iterrows():

        sec = row['Catalogo de Colonias_seccion']
        cp = str(row['CP'])
        col = row['NOMBRE DE LA COLONIA']

        if sec not in data:

            data[sec] = []

        data[sec].append({

            "colonia": col,
            "cp": cp

        })


    return data



# ---------------------------------------------------
# RELACION SIMPATIZANTES POR COLONIA EXACTA
# ---------------------------------------------------

@st.cache_data
def get_simpatizantes_colonia():

    connection = pymysql.connect(
        host='sql3.freesqldatabase.com',
        user='sql3816861',
        password='Xvkw87Sknd',
        database='sql3816861',
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

    # extraer cp correctamente
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

                # coincidencia perfecta
                if cp == cp_col and nombre_col in domicilio:

                    resultados.append({

                        "seccion": seccion,
                        "colonia": col["colonia"]

                    })

                    break


                # si no contiene nombre colonia, asignar por CP
                elif cp == cp_col:

                    resultados.append({

                        "seccion": seccion,
                        "colonia": col["colonia"]

                    })

                    break


                    resultados.append({

                        "seccion": seccion,
                        "colonia": col["colonia"]

                    })

                    break


    conteo = pd.DataFrame(resultados)

    if len(conteo) > 0:

        conteo = conteo.groupby(
            ["seccion","colonia"]
        ).size().reset_index(name="simpatizantes")

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

            feature["properties"]["seccion"] = str(
                feature["properties"]["SECCION"]
            ).zfill(4)

        else:

            feature["properties"]["seccion"] = str(
                feature["properties"]["seccion"]
            ).zfill(4)


    return geo["features"]



# ---------------------------------------------------
# CREAR MAPA
# ---------------------------------------------------

def crear_mapa(features, colonias, db, filtro):

    centro=[22.7709,-102.5832]
    zoom=13

    m=folium.Map(
        location=centro,
        zoom_start=zoom,
        tiles="OpenStreetMap"
    )

    # agrupar
    secciones = {}

    for feature in features:

        sec = feature["properties"]["seccion"]

        if sec not in secciones:
            secciones[sec] = []

        secciones[sec].append(feature)


    # recorrer secciones
    for seccion, lista_poligonos in secciones.items():

        if filtro and seccion != filtro:
            continue


        datos=db[db.seccion==seccion]

        total=datos.simpatizantes.sum()


        cps=datos.cp.dropna().unique()

        cp_html="<br>".join(cps)


        cols=colonias.get(seccion,[])

        colonias_html="<br>".join(
            f"{c['colonia']} (CP {c['cp']})"
            for c in cols
        )


        # SIMPATIZANTES POR COLONIA

        detalle = simpatizantes_colonia[
            simpatizantes_colonia.seccion == seccion
        ]

        detalle_html=""

        for _, row in detalle.iterrows():

            if pd.notna(row["colonia"]):

                detalle_html += f"""
                {row['colonia']} — {row['simpatizantes']}<br>
                """


        popup=f"""

        <b>Sección:</b> {seccion}

        <br><br>

        <b>CP registrados:</b><br>

        {cp_html}

        <br><br>

        <b>Colonias:</b><br>

        {colonias_html}

        <br><br>

        <b>Simpatizantes totales:</b>

        {total}

        <br><br>

        <b>Simpatizantes por colonia:</b><br>

        {detalle_html}

        """


        # color

        if total==0:
            color="#ffffff"

        elif total<=2:
            color="#d4a5b5"

        elif total<=5:
            color="#a03a5a"

        else:
            color="#650021"



        # dibujar

        for feature in lista_poligonos:

            folium.GeoJson(

                feature,

                style_function=lambda x,color=color:{

                    "fillColor":color,
                    "color":"#650021",
                    "weight":2,
                    "fillOpacity":0.4

                },

                tooltip=folium.Tooltip(

                    f"""
                    Sección: {seccion}
                    <br>
                    Simpatizantes: {total}
                    """

                ),

                popup=folium.Popup(popup,max_width=350)

            ).add_to(m)



        # marcador

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
                    padding:6px;
                    border-radius:6px;
                    font-weight:bold;
                    ">

                    {total}

                    </div>

                    """

                )

            ).add_to(m)



    return m





# ---------------------------------------------------
# CARGA
# ---------------------------------------------------

db = get_ine_data()

colonias = load_excel()

geo = load_geojson()

simpatizantes_colonia = get_simpatizantes_colonia()


# ---------------------------------------------------
# BUSCADOR
# ---------------------------------------------------

st.subheader("Buscar Seccion")

filtro=st.text_input("Escribe seccion")

if filtro:

    filtro=filtro.zfill(4)

else:

    filtro=None


# ---------------------------------------------------
# MAPA
# ---------------------------------------------------

mapa=crear_mapa(

geo,
colonias,
db,
filtro

)


folium_static(mapa,width=1600,height=800)


# ---------------------------------------------------
# DEBUG OPCIONAL
# ---------------------------------------------------

st.subheader("Datos INE")

st.dataframe(db)
