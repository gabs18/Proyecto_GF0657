# Carga de bibliotecas
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from PIL import Image

# URL de los datos
URL_DATOS_FELINOS = 'datos/datos_felinos.gpkg'
URL_DATOS_AREAS_CONSERVACION = 'datos/areas_conservacion.gpkg'

@st.cache_data
def cargar_gpkg_felinos():
    try:
        return gpd.read_file(URL_DATOS_FELINOS)
    except Exception as e:
        st.error(f"Error al cargar los datos de felinos: {e}")
        return None

@st.cache_data
def cargar_datos_areas():
    try:
        return gpd.read_file(URL_DATOS_AREAS_CONSERVACION)
    except Exception as e:
        st.error(f"Error al cargar los datos de áreas de conservación: {e}")
        return None

def realizar_spatial_join(felinos_gdf, areas_gdf):
    if felinos_gdf.crs != areas_gdf.crs:
        areas_gdf = areas_gdf.to_crs(felinos_gdf.crs)
    return gpd.sjoin(felinos_gdf, areas_gdf, how='inner', predicate='within')

# Cargar datos
felinos_gdf = cargar_gpkg_felinos()
areas_gdf = cargar_datos_areas()

# Configuración de la app
st.title("Avistamientos de felinos en las Áreas de Conservación de Costa Rica")

# Introducción
st.markdown("""
    ---
    ### Introducción
    Costa Rica es conocida por su rica biodiversidad, alberga varias especies de felinos que desempeñan un papel esencial en el equilibrio ecológico. Desde el jaguar hasta el ocelote, estos felinos se encuentran en diferentes ecosistemas del país. Sin embargo, enfrentan desafíos significativos debido a la pérdida de hábitat, la caza furtiva y otros factores antropogénicos.
    
    Este sitio web tiene como objetivo proporcionar una visión de los registros de observaciones de tres especies de felinos en Costa Rica en cada Área de Conservación. Se incluye una barra lateral para filtrar los registros por Área de Conservación, al interactuar con ella, la tabla, el gráfico pastel y el mapa se van a actualizar para mostrar sólo la información de dicha área de conservación.
    """)

# Ruta a la imagen (ajusta la ruta si está en una subcarpeta)
imagen_path = "datos/foto.png"  # Reemplaza con el nombre de tu archivo de imagen

# Cargar la imagen
imagen = Image.open(imagen_path)

# Mostrar la imagen con un caption
st.image(imagen, caption="Ocelote (Leopardus pardalis), Puma (Puma concolor) y Jaguar (Panthera onca)", use_container_width=True)

if felinos_gdf is not None and areas_gdf is not None:
    # Renombrar la columna `nombre_ac` en áreas de conservación
    areas_gdf = areas_gdf.rename(columns={'nombre_ac': 'Nombre'})

    # Realizar join espacial
    datos_combinados = realizar_spatial_join(felinos_gdf, areas_gdf)
    
    # Opciones de selección en barra lateral
    lista_areas = ["Todas"] + sorted(areas_gdf['Nombre'].dropna().unique().tolist())
    area_seleccionada = st.sidebar.selectbox("Seleccione un Área de Conservación", lista_areas)
    
    # Filtrar datos según selección
    if area_seleccionada != "Todas":
        datos_filtrados = datos_combinados[datos_combinados['Nombre'] == area_seleccionada]
        # Obtener geometría del área seleccionada
        geometria_seleccionada = areas_gdf[areas_gdf['Nombre'] == area_seleccionada].geometry
        if not geometria_seleccionada.empty:
            centroide = geometria_seleccionada.centroid.iloc[0]
            bounds = geometria_seleccionada.total_bounds  # MinX, MinY, MaxX, MaxY
            zoom_location = [centroide.y, centroide.x]
            zoom_level = 12 if (bounds[2] - bounds[0] < 0.1 and bounds[3] - bounds[1] < 0.1) else 10
        else:
            zoom_location = [9.75, -84]
            zoom_level = 7
    else:
        datos_filtrados = datos_combinados
        zoom_location = [9.75, -84]
        zoom_level = 7

    # Columnas relevantes del conjunto de datos
    columnas = [
        'species', 
        'eventDate',
        'locality',
        'Nombre',
        'siglas_ac',
        'regmplan',
        'area_ha'
    ]
    datos_filtrados = datos_filtrados[columnas]

    # Nombres de las columnas en español
    columnas_espaniol = {
        'species': 'Especies',
        'eventDate': 'Fecha',
        'locality': 'Localización',
        'Nombre': 'Nombre',
        'siglas_ac': 'Siglas',
        'regmplan': 'Región',
        'area_ha': 'Área(ha)'
    }
    datos_filtrados = datos_filtrados.rename(columns=columnas_espaniol)

# ---------------- Mostrar tabla filtrada ----------------------------------
    st.subheader("Datos de felinos por Área de Conservación")
    st.dataframe(datos_filtrados[['Especies', 'Fecha', 'Localización', 'Nombre', 'Siglas', 'Región', 'Área(ha)']], hide_index=True)
    
# ----------------  Gráfico de distribución de especies ------------------------
    st.subheader("Porcentaje de felinos por Área de Conservación")
    conteo_especies = datos_filtrados['Especies'].value_counts().reset_index()
    conteo_especies.columns = ['Especie', 'Cantidad']

     # Definir colores personalizados (tres colores de la paleta YlOrBr)
    colores_personalizados = px.colors.sequential.YlOrBr[3:6]

    fig_especies = px.pie(
       conteo_especies,
       names='Especie',
       values='Cantidad',
       title="Distribución de especies por Área de Conservación",
       color_discrete_sequence=colores_personalizados
    )
    st.plotly_chart(fig_especies)


 # -------------  Mapa interactivo -------------------------
# Mapa interactivo
st.subheader("Mapa de registros de felinos")
if not datos_filtrados.empty:
    # Contar los registros por área
    conteo_por_area = datos_filtrados.groupby('Nombre').size().reset_index(name='Registros')
    
    # Asegurarse de que todas las áreas tengan un valor de "Registros" (incluso aquellas sin registros)
    areas_gdf = areas_gdf.merge(conteo_por_area, on='Nombre', how='left')  # Usar left join
    areas_gdf['Registros'] = areas_gdf['Registros'].fillna(0)  # Rellenar NaN con 0 para las áreas sin registros

    # Si se selecciona un área, obtén el centroide
    if area_seleccionada != "Todas":
        # Filtrar el GeoDataFrame para obtener la geometría del área seleccionada
        geometria_seleccionada = areas_gdf[areas_gdf['Nombre'] == area_seleccionada].geometry
        if not geometria_seleccionada.empty:
            # Asegurarse de que la geometría esté en el CRS adecuado para folium (WGS 84)
            geometria_seleccionada = geometria_seleccionada.to_crs("EPSG:4326")
            
            # Obtener el centroide de la geometría del área
            centroide = geometria_seleccionada.centroid.iloc[0]
            zoom_location = [centroide.y, centroide.x]  # Centroide en formato [latitud, longitud]
            zoom_level = 9  # Ajusta según el área seleccionada
        else:
            # Valores por defecto si no se encuentra el área
            zoom_location = [9.75, -84]  # Coordenadas de Costa Rica
            zoom_level = 7
    else:
        # Si no se selecciona un área específica, usar Costa Rica como centro
        zoom_location = [9.75, -84]  # Coordenadas de Costa Rica
        zoom_level = 7

    # Crear el mapa base con estilo gris
    mapa = folium.Map(location=zoom_location, zoom_start=zoom_level, tiles="CartoDB positron", control_scale=True)

    # Crear la capa Choropleth sin usar clasificación Jenks ni bins
    coropleta = folium.Choropleth(
        geo_data=areas_gdf,
        data=areas_gdf,
        columns=['Nombre', 'Registros'],
        key_on='feature.properties.Nombre',
        fill_color='YlOrBr',  # Usar la paleta de colores YlOrBr
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Registros por Área de Conservación',
        name="Registros por Área de Conservación",  # Nombre para el control de capas
        reset=True  # Resetear el estado para una nueva creación
    )
    coropleta.add_to(mapa)

    # Añadir `hoverdata` directamente a la capa de coropletas
    folium.GeoJson(
        areas_gdf,
        style_function=lambda x: {
            'fillColor': 'transparent',
            'color': 'black',
            'weight': 0.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['Nombre', 'Registros'],
            aliases=['Área de Conservación:', 'Registros:'],
            localize=True
        )
    ).add_to(coropleta.geojson)  # Asocia el tooltip directamente al GeoJson del Choropleth

    # Añadir control de capas
    folium.LayerControl().add_to(mapa)

    # Mostrar el mapa
    st_folium(mapa, width=700, height=500)
else:
    st.warning("No hay registros para el área seleccionada.")



# Autoría de la página
st.markdown("""
    ---
    ### Créditos
    **Autoría**: Esta aplicación fue desarrollada por Gabriela Becerra y Maikol Fallas.
    
    **Curso:** Programación en SIG (GF0657)
    
    **Fuente de los datos:** 
    - Registros de felinos: API de GBIF 
    - Áreas de Conservación de Costa Rica: SINAC
    """)
