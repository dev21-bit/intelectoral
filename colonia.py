import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import folium_static
import pymysql
import geopandas as gpd
import plotly.express as px
from datetime import datetime

# ---------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------

st.set_page_config(
    page_title="Mapa Electoral - Zacatecas",
    page_icon="🗳️",
    layout="wide"
)

# Estilo minimalista
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    h1 {
        color: #1e3c72;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1e3c72;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1e3c72;
    }
    .metric-label {
        color: #6c757d;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# TÍTULO
# ---------------------------------------------------

st.title("🗳️ Mapa Electoral - Zacatecas")
st.markdown("### Visualización Integrada: Secciones y Colonias")

# Sidebar - Solo filtros esenciales
with st.sidebar:
    st.markdown("## 🔍 Filtros")
    
    # Filtro por sección
    seccion_input = st.text_input("Número de sección:", placeholder="Ej: 1804")
    if seccion_input:
        seccion_input = seccion_input.zfill(4)
    
    # Filtro por colonia
    colonia_input = st.text_input("Nombre de colonia:", placeholder="Ej: LIBERTADORES")
    
    st.markdown("---")
    
    # Control de capas
    st.markdown("## 🗺️ Capas")
    mostrar_secciones = st.checkbox("Mostrar secciones", value=True)
    mostrar_colonias = st.checkbox("Mostrar colonias", value=True)
    
    st.markdown("---")
    
    # Botón actualizar
    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------
# FUNCIONES DE CARGA
# ---------------------------------------------------

@st.cache_data
def get_ine_data():
    """Carga datos de simpatizantes"""
    try:
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
            SUBSTRING_INDEX(SUBSTRING_INDEX(domicilio,' ', -3), ' ',1) as cp,
            COUNT(*) as simpatizantes
        FROM ine
        GROUP BY seccion, cp
        """
        df = pd.read_sql(query, connection)
        connection.close()
        df['cp'] = df['cp'].astype(str)
        df['seccion'] = df['seccion'].astype(str).str.zfill(4)
        return df
    except Exception as e:
        st.error(f"Error cargando datos INE: {str(e)}")
        return pd.DataFrame(columns=['seccion', 'cp', 'simpatizantes'])

@st.cache_data
def load_colonias_excel():
    """Carga catálogo de colonias"""
    try:
        xls = pd.ExcelFile("COLONIAS ZAC.xlsx")
        data = {}
        
        # Hoja 1
        sheet1 = pd.read_excel(xls, xls.sheet_names[0])
        sheet1['SECCION'] = sheet1['SECCION'].astype(str).str.zfill(4)
        for _, row in sheet1.iterrows():
            sec = row['SECCION']
            cp = str(row['CP']).replace(".0", "")
            col = row['NOMBRE DE LA COLONIA']
            if sec not in data:
                data[sec] = []
            data[sec].append({"colonia": col, "cp": cp})
        
        # Hoja 2
        if len(xls.sheet_names) > 1:
            sheet2 = pd.read_excel(xls, xls.sheet_names[1])
            if 'Catalogo de Colonias_seccion' in sheet2.columns:
                sheet2['Catalogo de Colonias_seccion'] = sheet2['Catalogo de Colonias_seccion'].astype(str).str.zfill(4)
                for _, row in sheet2.iterrows():
                    sec = row['Catalogo de Colonias_seccion']
                    cp = str(row['CP'])
                    col = row['NOMBRE DE LA COLONIA']
                    if sec not in data:
                        data[sec] = []
                    data[sec].append({"colonia": col, "cp": cp})
        
        return data
    except Exception as e:
        st.warning(f"Error cargando colonias: {str(e)}")
        return {}

@st.cache_data
def load_colonias_geojson():
    """Carga GeoJSON de colonias"""
    try:
        gdf = gpd.read_file('zacatecas_capital_colonias.geojson')
        return gdf
    except Exception as e:
        st.warning(f"Error cargando GeoJSON de colonias: {str(e)}")
        return None

@st.cache_data
def load_secciones_geojson():
    """Carga GeoJSON de secciones electorales - Versión específica para tu archivo"""
    try:
        # Cargar el archivo directamente
        with open('zacatecas_capital_secciones.geojson', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = []
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            
            # Extraer el número de sección (en tu archivo viene como 'seccion': 1804)
            seccion_raw = props.get('seccion', None)
            
            if seccion_raw is not None:
                # Convertir a string y rellenar con ceros a la izquierda
                seccion = str(int(float(seccion_raw))).zfill(4)
            else:
                seccion = "0000"
            
            # Crear nuevo feature con la propiedad estandarizada
            new_feature = {
                "type": "Feature",
                "properties": {
                    "seccion": seccion,
                    "id": props.get('id', ''),
                    "entidad": props.get('entidad', ''),
                    "municipio": props.get('municipio', ''),
                    "distrito_f": props.get('distrito_f', ''),
                    "distrito_l": props.get('distrito_l', ''),
                    "tipo": props.get('tipo', '')
                },
                "geometry": feature.get('geometry', {})
            }
            features.append(new_feature)
        
        return features
    except Exception as e:
        st.error(f"Error cargando secciones: {str(e)}")
        return []

@st.cache_data
def get_simpatizantes_por_colonia():
    """Calcula simpatizantes por colonia"""
    try:
        connection = pymysql.connect(
            host='sql3.freesqldatabase.com',
            user='sql3817481',
            password='398j6uKWle',
            database='sql3817481',
            port=3306
        )
        query = "SELECT LPAD(CAST(seccion AS CHAR),4,'0') as seccion, domicilio FROM ine"
        df = pd.read_sql(query, connection)
        connection.close()

        df['seccion'] = df['seccion'].astype(str).str.zfill(4)
        df["cp"] = df["domicilio"].str.extract(r'(\d{5})(?!.*\d{5})')

        colonias_excel = load_colonias_excel()
        resultados = []

        for _, persona in df.iterrows():
            seccion = persona["seccion"]
            domicilio = str(persona["domicilio"]).upper()
            cp = str(persona["cp"])

            if seccion in colonias_excel:
                for col in colonias_excel[seccion]:
                    nombre_col = str(col["colonia"]).upper()
                    cp_col = str(col["cp"]).replace(".0", "")
                    if cp == cp_col and nombre_col in domicilio:
                        resultados.append({"seccion": seccion, "colonia": col["colonia"]})
                        break
                    elif cp == cp_col:
                        resultados.append({"seccion": seccion, "colonia": col["colonia"]})
                        break

        conteo = pd.DataFrame(resultados)
        if len(conteo) > 0:
            conteo = conteo.groupby(["seccion", "colonia"]).size().reset_index(name="simpatizantes")
        return conteo
    except Exception as e:
        st.warning(f"Error calculando simpatizantes: {str(e)}")
        return pd.DataFrame(columns=["seccion", "colonia", "simpatizantes"])

# ---------------------------------------------------
# FUNCIÓN DEL MAPA INTEGRADO
# ---------------------------------------------------

def crear_mapa(features_secciones, gdf_colonias, colonias_data, df_ine, df_colonias_simps, 
               filtro_seccion=None, filtro_colonia=None, mostrar_sec=True, mostrar_col=True):
    
    centro = [22.7709, -102.5832]
    m = folium.Map(location=centro, zoom_start=13, tiles="CartoDB positron", control_scale=True)

    # CAPA SECCIONES
    if mostrar_sec and features_secciones:
        secciones_group = folium.FeatureGroup(name="🏛️ Secciones Electorales")
        
        for feature in features_secciones:
            # Obtener número de sección (ya viene formateado)
            props = feature.get('properties', {})
            seccion = props.get('seccion', '0000')
            
            # Aplicar filtro
            if filtro_seccion and seccion != filtro_seccion:
                continue
            
            # Datos de simpatizantes para esta sección
            datos_sec = df_ine[df_ine['seccion'] == seccion]
            total_simps = datos_sec['simpatizantes'].sum() if not datos_sec.empty else 0
            
            # Colonias en esta sección (del Excel)
            colonias_sec = colonias_data.get(seccion, [])
            
            # Color según simpatizantes
            if total_simps == 0:
                color = "#ffffff"
                border = "#cccccc"
            elif total_simps <= 5:
                color = "#ffd1dc"
                border = "#ff9eb5"
            elif total_simps <= 15:
                color = "#ff9eb5"
                border = "#ff6b8b"
            elif total_simps <= 30:
                color = "#ff6b8b"
                border = "#ff3860"
            else:
                color = "#ff3860"
                border = "#cc0000"

            # Crear popup
            popup_html = f"""
            <div style="min-width: 250px; max-height: 300px; overflow-y: auto;">
                <b style="color: #1e3c72; font-size: 16px;">🏛️ Sección {seccion}</b><br>
                <hr style="margin: 5px 0;">
                <b>👥 Simpatizantes:</b> {total_simps}<br>
                <b>📍 CPs:</b> {', '.join(datos_sec['cp'].unique()) if not datos_sec.empty else 'N/A'}<br>
                <b>🏘️ Colonias en catálogo:</b> {len(colonias_sec)}<br>
                <hr style="margin: 5px 0;">
                <b>Colonias en esta sección:</b><br>
            """
            
            for col in colonias_sec[:8]:
                # Buscar si esta colonia tiene simpatizantes
                simps_col = df_colonias_simps[(df_colonias_simps['seccion'] == seccion) & 
                                              (df_colonias_simps['colonia'] == col['colonia'])]
                simps = simps_col['simpatizantes'].sum() if not simps_col.empty else 0
                popup_html += f"• {col['colonia']} (CP {col['cp']}) - <b>{simps} simps</b><br>"
            
            if len(colonias_sec) > 8:
                popup_html += f"• ... y {len(colonias_sec)-8} más<br>"
            
            popup_html += "</div>"
            
            # Añadir al mapa
            folium.GeoJson(
                feature,
                style_function=lambda x, c=color, b=border: {
                    "fillColor": c,
                    "color": b,
                    "weight": 2,
                    "fillOpacity": 0.6,
                    "dashArray": None
                },
                tooltip=f"🏛️ Sección {seccion} | {total_simps} simpatizantes",
                popup=folium.Popup(popup_html, max_width=350)
            ).add_to(secciones_group)
        
        secciones_group.add_to(m)

    # CAPA COLONIAS
    if mostrar_col and gdf_colonias is not None:
        colonias_group = folium.FeatureGroup(name="🏘️ Colonias")
        
        # Mapa de simpatizantes por colonia
        simps_dict = {}
        for _, row in df_colonias_simps.iterrows():
            simps_dict[row['colonia']] = simps_dict.get(row['colonia'], 0) + row['simpatizantes']
        
        # Filtrar por nombre si es necesario
        gdf_filtrado = gdf_colonias.copy()
        if filtro_colonia:
            gdf_filtrado = gdf_filtrado[gdf_filtrado['NOMBRE'].str.contains(filtro_colonia, case=False, na=False)]
        
        for _, row in gdf_filtrado.iterrows():
            nombre = row.get('NOMBRE', '')
            cp = str(row.get('CP', 'N/A')).replace('.0', '')
            simps = simps_dict.get(nombre, 0)
            
            # Color según tenga simpatizantes
            color = "#1e3c72" if simps > 0 else "#95a5a6"
            
            # Buscar secciones relacionadas por CP
            secciones_rel = df_ine[df_ine['cp'] == cp]['seccion'].unique()
            secciones_text = ', '.join(secciones_rel) if len(secciones_rel) > 0 else 'No determinado'
            
            popup_html = f"""
            <div style="min-width: 200px;">
                <b style="color: #1e3c72;">🏘️ {nombre}</b><br>
                <hr style="margin: 5px 0;">
                <b>📍 CP:</b> {cp}<br>
                <b>👥 Simpatizantes:</b> {simps}<br>
                <b>🏛️ Secciones:</b> {secciones_text}<br>
            </div>
            """
            
            folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda x, c=color: {
                    "fillColor": c,
                    "color": "#2c3e50",
                    "weight": 1,
                    "fillOpacity": 0.3,
                    "dashArray": "5, 5"
                },
                tooltip=f"🏘️ {nombre} | {simps} simpatizantes",
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(colonias_group)
        
        colonias_group.add_to(m)

    # Control de capas
    folium.LayerControl().add_to(m)
    
    return m

# ---------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------

with st.spinner("🔄 Cargando datos..."):
    df_ine = get_ine_data()
    colonias_data = load_colonias_excel()
    features_secciones = load_secciones_geojson()
    df_colonias_simps = get_simpatizantes_por_colonia()
    gdf_colonias = load_colonias_geojson()

# ---------------------------------------------------
# VERIFICACIÓN DE CARGA
# ---------------------------------------------------

col1, col2 = st.columns(2)
with col1:
    if features_secciones:
        st.success(f"✅ {len(features_secciones)} secciones cargadas")
        # Mostrar ejemplo
        if len(features_secciones) > 0:
            ejemplo = features_secciones[0]['properties']['seccion']
            st.info(f"Ejemplo: Sección {ejemplo}")
    else:
        st.error("❌ No se cargaron secciones")

with col2:
    if gdf_colonias is not None:
        st.success(f"✅ {len(gdf_colonias)} colonias cargadas")
    else:
        st.error("❌ No se cargaron colonias")

# ---------------------------------------------------
# MÉTRICAS CLAVE
# ---------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{df_ine['simpatizantes'].sum():,}</div>
        <div class="metric-label">Total Simpatizantes</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{df_ine['seccion'].nunique()}</div>
        <div class="metric-label">Secciones con datos</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(colonias_data)}</div>
        <div class="metric-label">Secciones con colonias</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    col_datos = df_colonias_simps['colonia'].nunique() if not df_colonias_simps.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{col_datos}</div>
        <div class="metric-label">Colonias con datos</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------
# MAPA PRINCIPAL
# ---------------------------------------------------

if features_secciones or gdf_colonias is not None:
    mapa = crear_mapa(
        features_secciones,
        gdf_colonias,
        colonias_data,
        df_ine,
        df_colonias_simps,
        seccion_input if seccion_input else None,
        colonia_input if colonia_input else None,
        mostrar_secciones,
        mostrar_colonias
    )
    
    folium_static(mapa, width=1600, height=700)
else:
    st.error("No hay datos cartográficos para mostrar")

# ---------------------------------------------------
# TABLAS DE REFERENCIA
# ---------------------------------------------------

with st.expander("📋 Ver datos por sección y colonia"):
    tab1, tab2 = st.tabs(["Resumen por Sección", "Detalle por Colonia"])
    
    with tab1:
        # Resumen por sección
        resumen = []
        for seccion in sorted(df_ine['seccion'].unique()):
            datos = df_ine[df_ine['seccion'] == seccion]
            total = datos['simpatizantes'].sum()
            cps = ', '.join(datos['cp'].unique())
            num_cols = len(colonias_data.get(seccion, []))
            resumen.append({
                'Sección': seccion,
                'Simpatizantes': total,
                'CPs': cps,
                'Colonias en catálogo': num_cols
            })
        df_resumen = pd.DataFrame(resumen)
        st.dataframe(df_resumen, use_container_width=True)
    
    with tab2:
        # Detalle por colonia
        if not df_colonias_simps.empty:
            detalle = df_colonias_simps.groupby(['colonia', 'seccion'])['simpatizantes'].sum().reset_index()
            detalle = detalle.sort_values('simpatizantes', ascending=False)
            st.dataframe(detalle, use_container_width=True)
        else:
            st.info("No hay datos de simpatizantes por colonia")

# ---------------------------------------------------
# PIE
# ---------------------------------------------------

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: #6c757d;">
        <p>🗳️ Mapa Electoral Zacatecas | Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    </div>
    """,
    unsafe_allow_html=True
)