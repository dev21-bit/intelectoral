import sys
import geopandas as gpd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                             QWidget, QPushButton, QFileDialog, 
                             QHBoxLayout, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt
import folium
from folium import plugins
import webbrowser
import os
import tempfile

class VisorSeccionesElectorales(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gdf_original = None
        self.gdf = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("🗳️ Visor de Secciones Electorales - Zacatecas Capital")
        self.setGeometry(100, 100, 800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        
        # Barra de herramientas
        toolbar = QHBoxLayout()
        
        self.btn_cargar = QPushButton("📂 1. Cargar Shapefile")
        self.btn_cargar.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px;")
        self.btn_cargar.clicked.connect(self.cargar_shapefile)
        toolbar.addWidget(self.btn_cargar)
        
        self.btn_filtrar = QPushButton("🎯 2. FILTRAR ZACATECAS")
        self.btn_filtrar.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px; background-color: #FF6B6B; color: white;")
        self.btn_filtrar.clicked.connect(self.filtrar_zacatecas)
        self.btn_filtrar.setEnabled(False)
        toolbar.addWidget(self.btn_filtrar)
        
        self.btn_mapa = QPushButton("🗺️ 3. Abrir Mapa Interactivo")
        self.btn_mapa.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px; background-color: #4ECDC4; color: white;")
        self.btn_mapa.clicked.connect(self.abrir_mapa)
        self.btn_mapa.setEnabled(False)
        toolbar.addWidget(self.btn_mapa)
        
        self.btn_guardar = QPushButton("💾 Guardar GeoJSON")
        self.btn_guardar.setStyleSheet("font-size: 12px; padding: 8px;")
        self.btn_guardar.clicked.connect(self.guardar_geojson)
        self.btn_guardar.setEnabled(False)
        toolbar.addWidget(self.btn_guardar)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Panel de información
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(300)
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("background-color: #f8f9fa; font-family: monospace; padding: 15px; font-size: 12px;")
        layout.addWidget(self.info_text)
        
        central_widget.setLayout(layout)
        
        # Mostrar info inicial
        self.mostrar_info_inicial()
    
    def mostrar_info_inicial(self):
        info = """
        🗳️ **VISOR DE SECCIONES ELECTORALES - ZACATECAS CAPITAL**
        
        **INSTRUCCIONES:**
        1. Haz clic en "Cargar Shapefile" y selecciona tu archivo SECCION.shp
        2. Presiona "FILTRAR ZACATECAS" para extraer solo Zacatecas capital
        3. Presiona "Abrir Mapa Interactivo" para ver el mapa en tu navegador
        
        **CARACTERÍSTICAS:**
        • Mapa interactivo con OpenStreetMap
        • Haz clic en las secciones para ver sus datos
        • Zoom con rueda del mouse
        • Arrastrar para navegar
        • Exportar a GeoJSON
        
        **NOTA:** El mapa se abrirá en tu navegador web predeterminado.
        """
        self.info_text.setText(info)
    
    def cargar_shapefile(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar SECCION.shp", "", 
            "Shapefile (*.shp);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            try:
                self.gdf_original = gpd.read_file(file_path)
                self.info_text.setText(f"✅ Shapefile cargado: {os.path.basename(file_path)}")
                self.info_text.append(f"📊 Total de secciones en el archivo: {len(self.gdf_original):,}")
                self.info_text.append(f"📍 Sistema de coordenadas: {self.gdf_original.crs}")
                self.btn_filtrar.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"❌ Error al cargar: {str(e)}")
    
    def filtrar_zacatecas(self):
        if self.gdf_original is None:
            return
        
        try:
            # Identificar columnas
            cols = self.gdf_original.columns.tolist()
            col_ent = next((col for col in cols if any(x in col.upper() for x in ['CVE_ENT', 'ENTIDAD', 'CVEE', 'ENT'])), None)
            col_mun = next((col for col in cols if any(x in col.upper() for x in ['CVE_MUN', 'MUNICIPIO', 'CVEM', 'MUN'])), None)
            
            if not col_ent or not col_mun:
                QMessageBox.warning(self, "Advertencia", f"No se encontraron columnas de entidad/municipio.\nColumnas: {', '.join(cols[:10])}")
                return
            
            # FILTRAR Zacatecas capital
            self.gdf = self.gdf_original[
                (self.gdf_original[col_ent].astype(str).str.zfill(2) == '32') &
                (self.gdf_original[col_mun].astype(str).str.zfill(3) == '056')
            ].copy()
            
            if len(self.gdf) == 0:
                QMessageBox.warning(self, "Sin resultados", "No se encontraron secciones para Zacatecas capital.")
                return
            
            # Convertir a WGS84
            if self.gdf.crs and self.gdf.crs.to_string() != 'EPSG:4326':
                self.gdf = self.gdf.to_crs('EPSG:4326')
            
            # Mostrar info
            bounds = self.gdf.total_bounds
            info = f"""
            ✅ **FILTRO EXITOSO - ZACATECAS CAPITAL**
            
            📊 **SECCIONES ENCONTRADAS: {len(self.gdf):,}**
            
            📍 **UBICACIÓN:**
            • Longitud: {bounds[0]:.4f}° a {bounds[2]:.4f}°
            • Latitud:  {bounds[1]:.4f}° a {bounds[3]:.4f}°
            
            🗺️ **PRÓXIMO PASO:**
            Presiona "Abrir Mapa Interactivo" para visualizar las secciones en OpenStreetMap
            """
            
            self.info_text.setText(info)
            self.btn_mapa.setEnabled(True)
            self.btn_guardar.setEnabled(True)
            self.btn_filtrar.setText("✅ FILTRADO")
            self.btn_filtrar.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Error al filtrar: {str(e)}")
    
    def abrir_mapa(self):
        """Abrir mapa interactivo en el navegador"""
        if self.gdf is None or len(self.gdf) == 0:
            return
        
        try:
            # Calcular centro
            centro_lat = self.gdf.geometry.centroid.y.mean()
            centro_lon = self.gdf.geometry.centroid.x.mean()
            
            # Crear mapa
            m = folium.Map(
                location=[centro_lat, centro_lon],
                zoom_start=13,
                tiles='OpenStreetMap',
                control_scale=True
            )
            
            # Tooltip
            tooltip_fields = ['SECCION'] if 'SECCION' in self.gdf.columns else []
            tooltip_aliases = ['Sección:'] if tooltip_fields else []
            
            # Estilo
            style_function = lambda x: {
                'fillColor': '#FF6B6B',
                'color': '#333333',
                'weight': 1.5,
                'fillOpacity': 0.6,
            }
            
            highlight_function = lambda x: {
                'fillColor': '#4ECDC4',
                'color': '#000000',
                'weight': 3,
                'fillOpacity': 0.9,
            }
            
            # Añadir GeoJson
            folium.GeoJson(
                self.gdf,
                style_function=style_function,
                highlight_function=highlight_function,
                tooltip=folium.GeoJsonTooltip(
                    fields=tooltip_fields,
                    aliases=tooltip_aliases,
                    localize=True,
                    sticky=True,
                    labels=True
                ),
                name='Secciones Electorales'
            ).add_to(m)
            
            # Añadir controles
            plugins.Fullscreen().add_to(m)
            plugins.MousePosition().add_to(m)
            
            # Guardar archivo temporal y abrir en navegador
            temp_html = os.path.join(tempfile.gettempdir(), "zacatecas_secciones.html")
            m.save(temp_html)
            
            # Abrir en navegador
            webbrowser.open(f'file:///{temp_html}')
            
            self.info_text.append("\n✅ Mapa abierto en tu navegador")
            self.info_text.append("🗺️ Puedes hacer clic en las secciones para ver el número")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Error al crear mapa: {str(e)}")
    
    def guardar_geojson(self):
        if self.gdf is None:
            return
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar GeoJSON", 
            "zacatecas_capital_secciones.geojson",
            "GeoJSON (*.geojson);;Todos los archivos (*)",
            options=options
        )
        
        if file_path:
            try:
                self.gdf.to_file(file_path, driver='GeoJSON')
                QMessageBox.information(self, "Éxito", f"✅ GeoJSON guardado:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"❌ Error al guardar: {str(e)}")

def main():
    app = QApplication(sys.argv)
    visor = VisorSeccionesElectorales()
    visor.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()