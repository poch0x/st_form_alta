import streamlit as st
from streamlit_option_menu import option_menu
from google_sheets import GoogleSheets
from dotenv import load_dotenv
import os
import requests
import json
import time
import re

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


# Función para obtener un nuevo token de API
def obtener_nuevo_token():
    url = "https://api.saed.digital/token"
    payload = {
        "UserName": os.getenv("SAED_USERNAME"),
        "Password": os.getenv("SAED_PASSWORD"),
        "grant_type": os.getenv("SAED_GRANT_TYPE"),
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers)

        if response.status_code == 200:
            token_data = response.json()
            new_token = token_data["access_token"]

            # Actualizar el token en las variables de entorno y en la sesión de Streamlit
            os.environ["API_TOKEN"] = new_token
            st.secrets["API_TOKEN"] = new_token

            return new_token
        else:
            st.error(f"Error al obtener el nuevo token: {response.status_code}")
            st.error(response.text)
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión: {str(e)}")
        return None


# Obtener el token de la API desde las variables de entorno
api_token = os.getenv("API_TOKEN")
if not api_token:
    st.error("No se ha encontrado el token de API. Obteniendo nuevo token...")
    api_token = obtener_nuevo_token()

    if not api_token:
        st.error("No se pudo obtener un nuevo token. Verifica tus credenciales.")
    else:
        st.success("Token obtenido correctamente. Continuando...")


# VARIABLES
page_title = "Formulario de alta SAED"
page_icon = "📅"
layout = "centered"

situacion_revista = ["Titular", "Suplente"]
document = "form-alta-saedpf"  # Reemplazar con el ID de tu documento de Google Sheets
sheet = "Altas"

# Credenciales cargadas desde secrets
credentials_json = st.secrets["sheets"]["credentials_google"]
credentials = json.loads(credentials_json, strict=False)

# Configurar la página de Streamlit
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
st.title(page_title)

# Inicializar el estado de la sesión para entradas y mensaje de éxito
if "success" not in st.session_state:
    st.session_state.success = False
if "cuil" not in st.session_state:
    st.session_state.cuil = ""
if "apellido" not in st.session_state:
    st.session_state.apellido = ""
if "nombre" not in st.session_state:
    st.session_state.nombre = ""
if "nivel_ens" not in st.session_state:
    st.session_state.nivel_ens = ""
if "cargo" not in st.session_state:
    st.session_state.cargo = ""
if "cant_horas" not in st.session_state:
    st.session_state.cant_horas = ""
if "sit_rev" not in st.session_state:
    st.session_state.sit_rev = situacion_revista[0]


# Función para obtener niveles de enseñanza desde la API con almacenamiento en caché
@st.cache_data
def get_niveles_ensenanza(api_token):
    headers = {"Authorization": f"Bearer {api_token}"}
    url = "https://alumnos.api.saed.digital/NivelEnse%C3%B1anza/GetLista?limit=500&unidadAdministrativa_Id=1"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()["rows"]
        item_dict = {
            f"{item['Establecimiento']['Nombre']} - {item['NombreNivel']}": item
            for item in data
        }
        return list(item_dict.keys())
    else:
        st.error(f"Error al obtener datos de la API: {response.status_code}")
        st.error(response.text)
        return []


# Función para obtener cargos desde la API con almacenamiento en caché
@st.cache_data
def get_cargos(api_token):
    headers = {"Authorization": f"Bearer {api_token}"}
    url = "https://api.saed.digital/Cargo/GetLista/{Id}?listParams.limit=100"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()["rows"]
        item_dict = {f"{item['Nombre']}": item for item in data}
        return list(item_dict.keys())
    else:
        st.error(f"Error al obtener datos de la API: {response.status_code}")
        st.error(response.text)
        return []


# Obtener los niveles de enseñanza y cargos si el token de API está disponible
if not api_token:
    st.error("No se ha encontrado el token de API. Verifica tu archivo .env.")
else:
    nivel_ensenanza = get_niveles_ensenanza(api_token)
    cargos = get_cargos(api_token)

# Formulario de entrada
c1, c2, c3 = st.columns(3)
cuil = c1.text_input("CUIL*", st.session_state.cuil)
apellido = c2.text_input("Apellido*", st.session_state.apellido)
nombre = c3.text_input("Nombre*", st.session_state.nombre)

# Validar el formato del CUIL con una expresión regular
cuil_pattern = re.compile(r"^\d{2}-\d{8}-\d{1}$")

# Validar el CUIL solo si se ha ingresado texto y si no coincide con el formato esperado
if cuil and (not cuil_pattern.match(cuil) or len(cuil) > 13):
    st.warning(
        "Por favor, ingresa un CUIL válido (XX-XXXXXXXX-X) y con un máximo de 13 caracteres"
    )

# Mostrar el selectbox de nivel de enseñanza si hay opciones disponibles
if nivel_ensenanza:
    nivel_ens = c1.selectbox("Nivel de Enseñanza*", [""] + nivel_ensenanza)
else:
    nivel_ens = c1.selectbox("Nivel de Enseñanza*", [""])

# Mostrar el selectbox de cargo si hay opciones disponibles
if cargos:
    cargo = c2.selectbox("Cargo*", [""] + cargos)
else:
    cargo = c2.selectbox("Cargo*", [""])

cant_horas = c1.text_input("Cantidad de horas", st.session_state.cant_horas)

sit_rev = c3.selectbox(
    "Situacion de Revista",
    situacion_revista,
    index=situacion_revista.index(st.session_state.sit_rev),
)

enviar = st.button("Guardar")

if enviar:
    # Validar que los campos no estén vacíos y que el CUIL tenga el formato correcto
    if cuil == "":
        st.warning("El campo CUIL es obligatorio")
    elif not cuil_pattern.match(cuil) or len(cuil) > 13:
        st.warning(
            "Por favor, ingresa un CUIL válido (XX-XXXXXXXX-X) y con un máximo de 13 caracteres"
        )
    elif apellido == "":
        st.warning("El campo apellido es obligatorio")
    elif nombre == "":
        st.warning("El campo nombre es obligatorio")
    elif nivel_ens == "":
        st.warning("El campo nivel de enseñanza es obligatorio")
    elif cargo == "":
        st.warning("El campo cargo es obligatorio")
    # elif cant_horas == "":
    #     st.warning("El campo cantidad horas es obligatorio")
    elif sit_rev == "":
        st.warning("El campo situación de revista es obligatorio")
    else:
        # Valor por defecto para la columna "authorization"
        authorization = False

        # Crear un registro en Google Sheets
        data = [
            [
                cuil,
                apellido,
                nombre,
                nivel_ens,
                cargo,
                cant_horas,
                sit_rev,
                authorization,
            ]
        ]

        gs = GoogleSheets(credentials, document, sheet)
        range_ = gs.get_last_row_range()
        gs.write_data(range_, data)

        st.session_state.success = True
        st.session_state.cuil = ""
        st.session_state.apellido = ""
        st.session_state.nombre = ""
        st.session_state.nivel_ens = ""
        st.session_state.cargo = ""
        st.session_state.cant_horas = ""
        st.session_state.sit_rev = situacion_revista[0]

        st.experimental_rerun()

if st.session_state.success:
    st.success("Datos guardados correctamente")
    time.sleep(2)  # Delay for 2 seconds before rerunning
    st.session_state.success = False
    st.markdown("<meta http-equiv='refresh' content='2'>", unsafe_allow_html=True)
