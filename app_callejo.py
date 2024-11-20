import streamlit as st
import pandas as pd
import gdown
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import av

# ID del archivo en Google Drive
id_archivo = "1cwcBZKZGKVrtQBBDhLfw3xy9c9O2lVeL"
url = f"https://drive.google.com/uc?id={id_archivo}"

# Descargar y cargar el archivo Excel
@st.cache_data
def cargar_datos():
    ruta_temporal = "articulos.xlsx"
    try:
        gdown.download(url, ruta_temporal, quiet=False)
    except Exception as e:
        st.error("Error al descargar el archivo: verifica la conexión o el ID del archivo.")
        return pd.DataFrame()
    datos = pd.read_excel(ruta_temporal)
    datos.columns = datos.columns.str.strip().str.upper()
    cols_precio = [col for col in datos.columns if 'PRECIO' in col or 'NETO' in col or 'OFERTA' in col]
    cols_stock_piking = [col for col in datos.columns if 'STOC' in col or 'PIKG' in col]
    datos[cols_precio] = datos[cols_precio].apply(pd.to_numeric, errors='coerce').round(2)
    datos[cols_stock_piking] = datos[cols_stock_piking].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
    return datos

# Procesador de video para decodificar el código de barras en tiempo real
class BarcodeScannerTransformer(VideoTransformerBase):
    def __init__(self):
        self.result = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded_objects = decode(img)
        for obj in decoded_objects:
            self.result = obj.data.decode("utf-8")
            break  # Procesamos solo el primer código de barras detectado
        return img

# Diccionario de colores para STOCK y PIKG
rows = ["01", "02", "03", "04", "05", "051", "052", "06", "061", "07", "08", "09", "10", "20", "30"]
colores = {k: v for k, v in zip(rows, [
    "#00008B", "#FF0000", "#FFA500", "#90EE90", "#87CEFA", "#4682B4", "#4169E1", 
    "#808080", "#696969", "#800080", "#A52A2A", "#FF69B4", "#808000", "#9370DB", "#000000"
])}

almacenes = {
    "01": "PONFE", "02": "LEON", "03": "SANTA", "04": "EXTRE",
    "05": "CANA LPGC", "051": "CANA TNF", "052": "CANA FTV", 
    "06": "GALI NOR", "061": "GALI SUR", "07": "CATAL", "08": "VALLAD",
    "09": "VALENC", "10": "EUSKA", "20": "PORT", "30": "MADR"
}

# Título de la aplicación
st.title("Consulta de Referencias")

# Cargar los datos al inicio
datos = cargar_datos()

if not datos.empty:
    # Campo de búsqueda y escaneo
    col1, col2 = st.columns([3, 1])
    referencia = None
    with col1:
        referencia = st.text_input("Ingresa la referencia exacta (ARTICULO o SINONIMO):")

    with col2:
        st.markdown("#### Escanea el código de barras:")
        webrtc_ctx = webrtc_streamer(
            key="scanner",
            video_transformer_factory=BarcodeScannerTransformer,
            media_stream_constraints={"video": True, "audio": False},
        )

        if webrtc_ctx.video_transformer:
            referencia = webrtc_ctx.video_transformer.result
            if referencia:
                st.success(f"Código escaneado: {referencia}")

    if referencia:
        referencia = referencia.strip().upper()
        resultados = datos[
            (datos['CODIGO_ARTICULO'].astype(str) == referencia) |
            (datos['CODIGO_SINONIMO'].astype(str) == referencia)
        ]

        if not resultados.empty:
            st.write("### Resultados encontrados:")

            for index, row in resultados.iterrows():
                # Mostrar los campos clave
                st.markdown("#### Información clave:")
                styled_data1 = pd.DataFrame([{
                    "FAMILIA": row['CODIGO_FAMILIA'],
                    "ARTICULO": row['CODIGO_ARTICULO'],
                    "SINONIMO": row['CODIGO_SINONIMO'],
                    "DESCRIPCIÓN": f"<span style='font-size:18px; font-weight:bold;'>{row['DESCRIP_COMERCIAL']}</span>",
                    "PESO": row['PESO_NETO']
                }])
                st.markdown(
                    styled_data1.to_html(escape=False, index=False),
                    unsafe_allow_html=True
                )

                # Mostrar la tabla de precios y descuentos
                st.markdown("#### Información de precios y descuentos:")
                styled_data2 = pd.DataFrame([{
                    "PRECIO": row['PRECIO'],
                    "DTO": row['DTO'],
                    "NETO": row['NETO'],
                    "OFERTA": row['OFERTA'],
                    "DTO_OFERTA": row['DTO_OFERTA'],
                    "OFERTA_CANA": row['OFERTA_CANA'],
                    "DTO_CANA": row['DTO_CANA'],
                    "TARIF_PORTU": row['TARIF_PORTU'],
                    "NETO10PORTU": row['NETO10PORTU']
                }])

                styled_html = styled_data2.style.format("{:.2f}").map(
                    lambda x: "background-color: #556B2F; color: white;" if x == row["NETO"] else ""
                )
                st.write(styled_html.to_html(), unsafe_allow_html=True)

                # Mostrar las tablas de stock y picking
                st.markdown("#### Información de stock y picking:")
                stock_picking_data = pd.DataFrame([
                    {
                        "ALMACÉN": almacenes[row_code],
                        "STOCK": row.get(f"STOC_{row_code}", "N/A"),
                        "PICKING": row.get(f"PIKG_{row_code}", "N/A")
                    }
                    for row_code in rows
                ]).reset_index(drop=True)

                styled_html_stock = stock_picking_data.style.format(
                    {"STOCK": "{:.0f}", "PICKING": "{:.0f}"}
                ).map(
                    lambda val: f"background-color: {colores.get(val, '#FFFFFF')}; color: white;" if val in colores else ""
                )

                st.write(styled_html_stock.to_html(), unsafe_allow_html=True)

        else:
            st.error("No se encontró la referencia.")
