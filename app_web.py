import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------
st.set_page_config(page_title="IPAM - Gestor de IPs", layout="wide")

st.markdown("""
    <style>
    .stat-card {
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
    }
    .total-card { background-color: #0066CC; }
    .usada-card { background-color: #DC3545; }
    .libre-card { background-color: #28A745; }
    .stat-label { font-size: 16px; font-weight: bold; opacity: 0.9; }
    .stat-value { font-size: 32px; font-weight: bold; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------
# NOMBRE DE TU GOOGLE SHEET
# Cambiá este valor por el nombre exacto de tu Sheet
# -----------------------------------------------
SHEET_NAME = "IPAM_Inventario"

# -----------------------------------------------
# CONEXIÓN A GOOGLE SHEETS
# -----------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
#def get_client():
#    """Crea el cliente de Google Sheets usando las credenciales del secret."""
#    import json
#    info = json.loads(st.secrets["gcp_service_account"]["json_data"])
#   creds = Credentials.from_service_account_info(info, scopes=SCOPES)
#    return gspread.authorize(creds)

def get_client():
    import json
    raw = st.secrets["gcp_service_account"]["json_data"]
    st.write("Tipo:", type(raw))
    st.write("Primeros 100 chars:", str(raw)[:100])
    info = json.loads(raw)
    st.write("Keys encontradas:", list(info.keys()))
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def cargar_datos():
    """Lee las 3 hojas del Google Sheet y devuelve los DataFrames."""
    try:
        client = get_client()
        sh = client.open(SHEET_NAME)

        vlan_df     = pd.DataFrame(sh.worksheet("VLANs").get_all_records())
        servers_df  = pd.DataFrame(sh.worksheet("Servidores").get_all_records())
        ips_df      = pd.DataFrame(sh.worksheet("IPs_VLAN").get_all_records())

        for df in [vlan_df, servers_df, ips_df]:
            df.columns = df.columns.str.strip()

        ips_df["VLAN"]     = pd.to_numeric(ips_df["VLAN"],     errors="coerce").fillna(0).astype(int)
        servers_df["VLAN"] = pd.to_numeric(servers_df["VLAN"], errors="coerce").fillna(0).astype(int)

        data = ips_df.merge(
            servers_df[["IP", "VLAN", "Host", "Ambiente", "Cluster", "Observaciones", "Descripcion"]],
            on=["IP", "VLAN"], how="left", suffixes=("_ip", "_srv")
        )

        if "Descripcion_srv" in data.columns:
            data["Descripcion"] = data["Descripcion_srv"].fillna(data.get("Descripcion_ip", ""))

        if "Estado" in data.columns:
            data["Estado"] = data["Estado"].astype(str).str.strip().str.upper()

        return vlan_df, servers_df, ips_df, data

    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None, None, None, None

def guardar_hoja(nombre_hoja: str, df: pd.DataFrame):
    """Sobreescribe una hoja completa con el DataFrame recibido."""
    client = get_client()
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet(nombre_hoja)
    ws.clear()
    ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())
    # Invalida el cache para que la próxima lectura traiga datos frescos
    cargar_datos.clear()

def marcar_ip(ips_df, vlan, ip, nuevo_estado, host="", descripcion="", observaciones="", ambiente="", cluster=""):
    """Actualiza el estado de una IP en IPs_VLAN y sincroniza Servidores."""
    vlan_df, servers_df, _, _ = cargar_datos()

    # --- Actualizar IPs_VLAN ---
    mask_ip = (ips_df["VLAN"] == int(vlan)) & (ips_df["IP"] == ip)
    ips_df.loc[mask_ip, "Estado"]      = nuevo_estado.upper()
    ips_df.loc[mask_ip, "Descripcion"] = descripcion
    guardar_hoja("IPs_VLAN", ips_df)

    # --- Actualizar Servidores ---
    mask_srv = (servers_df["VLAN"] == int(vlan)) & (servers_df["IP"] == ip)

    if nuevo_estado.upper() == "USADA":
        if mask_srv.any():
            servers_df.loc[mask_srv, "Host"]         = host
            servers_df.loc[mask_srv, "Descripcion"]  = descripcion
            servers_df.loc[mask_srv, "Observaciones"]= observaciones
            servers_df.loc[mask_srv, "Ambiente"]     = ambiente
            servers_df.loc[mask_srv, "Cluster"]      = cluster
        else:
            # Buscar datos de red desde VLANs
            vlan_info = vlan_df[vlan_df["VLAN"] == int(vlan)]
            subnet  = vlan_info["Subnet"].values[0]  if len(vlan_info) else ""
            gateway = vlan_info["Gateway"].values[0] if len(vlan_info) else ""
            mascara = vlan_info["Mascara"].values[0] if len(vlan_info) else ""

            nueva_fila = pd.DataFrame([{
                "Host": host, "Descripcion": descripcion, "Ambiente": ambiente,
                "Cluster": cluster, "IP": ip, "VLAN": int(vlan),
                "Subnet": subnet, "Gateway": gateway, "Mascara": mascara,
                "Observaciones": observaciones,
            }])
            servers_df = pd.concat([servers_df, nueva_fila], ignore_index=True)

    elif nuevo_estado.upper() == "LIBRE":
        servers_df = servers_df[~mask_srv]

    guardar_hoja("Servidores", servers_df)

# -----------------------------------------------
# CARGA INICIAL
# -----------------------------------------------
vlan_df, servers_df, ips_df, data = cargar_datos()

# -----------------------------------------------
# INTERFAZ
# -----------------------------------------------
st.title("🖧 Gestor de IPs — IPAM")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Consulta VLAN", "🔍 Buscar", "📝 Asignar IP", "🔓 Liberar IP"])

# -----------------------------------------------
# TAB 1 — CONSULTA POR VLAN
# -----------------------------------------------
with tab1:
    st.subheader("Consulta por VLAN")
    if data is not None:
        vlan_list = sorted(data["VLAN"].unique())
        vlan_sel  = st.selectbox("Seleccionar VLAN:", vlan_list, key="vlan_sel")

        df_vlan = data[data["VLAN"] == vlan_sel].copy()
        estados = df_vlan["Estado"].astype(str).str.upper().str.strip()

        total = len(df_vlan)
        u     = (estados == "USADA").sum()
        l     = (estados == "LIBRE").sum()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="stat-card total-card"><div class="stat-label">Total IPs</div><div class="stat-value">{total}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-card usada-card"><div class="stat-label">Usadas</div><div class="stat-value">{u}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-card libre-card"><div class="stat-label">Libres</div><div class="stat-value">{l}</div></div>', unsafe_allow_html=True)

        cols_mostrar = ["IP", "Estado", "Host", "Cluster", "Descripcion"]
        existentes   = [c for c in cols_mostrar if c in df_vlan.columns]

        def color_estado(val):
            if str(val).upper() == "LIBRE": return "color: #28A745; font-weight: bold;"
            if str(val).upper() == "USADA": return "color: #DC3545; font-weight: bold;"
            return ""

        st.dataframe(
            df_vlan[existentes].style.map(color_estado, subset=["Estado"]),
            use_container_width=True, hide_index=True
        )

# -----------------------------------------------
# TAB 2 — BUSCAR
# -----------------------------------------------
with tab2:
    st.subheader("Buscar Host / IP")
    if data is not None:
        c1, c2 = st.columns([1, 2])
        tipo  = c1.selectbox("Buscar por:", ["IP o Host", "Solo IP", "Solo Host"])
        query = c2.text_input("Texto a buscar:")

        if query:
            q = query.strip()
            if tipo == "Solo IP":
                res = data[data["IP"].astype(str).str.contains(q, case=False, na=False)]
            elif tipo == "Solo Host":
                res = data[data["Host"].astype(str).str.contains(q, case=False, na=False)]
            else:
                res = data[
                    data["IP"].astype(str).str.contains(q, case=False, na=False) |
                    data["Host"].astype(str).str.contains(q, case=False, na=False)
                ]

            st.write(f"**{len(res)} resultado(s) encontrado(s)**")
            cols_mostrar = ["VLAN", "IP", "Estado", "Host", "Ambiente", "Cluster", "Descripcion"]
            existentes   = [c for c in cols_mostrar if c in res.columns]
            st.dataframe(res[existentes], use_container_width=True, hide_index=True)

# -----------------------------------------------
# TAB 3 — ASIGNAR IP
# -----------------------------------------------
with tab3:
    st.subheader("Asignar IP a un servidor")
    if data is not None and ips_df is not None:
        libres = data[data["Estado"] == "LIBRE"][["VLAN", "IP"]].drop_duplicates()

        if libres.empty:
            st.warning("No hay IPs libres disponibles.")
        else:
            vlan_libres = sorted(libres["VLAN"].unique())
            vlan_sel3   = st.selectbox("VLAN:", vlan_libres, key="vlan_asignar")

            ips_libres  = sorted(libres[libres["VLAN"] == vlan_sel3]["IP"].tolist())
            ip_sel      = st.selectbox("IP libre:", ips_libres)

            with st.form("form_asignar"):
                host        = st.text_input("Host / Nombre del servidor *")
                descripcion = st.text_input("Descripción")
                ambiente    = st.selectbox("Ambiente", ["PROD", "QA", "PRE", ""])
                cluster     = st.text_input("Cluster")
                observ      = st.text_area("Observaciones")
                submitted   = st.form_submit_button("✅ Asignar IP")

            if submitted:
                if not host.strip():
                    st.error("El campo Host es obligatorio.")
                else:
                    marcar_ip(ips_df.copy(), vlan_sel3, ip_sel, "USADA",
                              host=host.strip(), descripcion=descripcion,
                              observaciones=observ, ambiente=ambiente, cluster=cluster)
                    st.success(f"IP **{ip_sel}** asignada a **{host}** correctamente.")
                    st.rerun()

# -----------------------------------------------
# TAB 4 — LIBERAR IP
# -----------------------------------------------
with tab4:
    st.subheader("Liberar IP")
    if data is not None and ips_df is not None:
        usadas = data[data["Estado"] == "USADA"][["VLAN", "IP", "Host", "Descripcion"]].drop_duplicates()

        if usadas.empty:
            st.info("No hay IPs usadas registradas.")
        else:
            vlan_usadas = sorted(usadas["VLAN"].unique())
            vlan_sel4   = st.selectbox("VLAN:", vlan_usadas, key="vlan_liberar")

            ips_usadas  = usadas[usadas["VLAN"] == vlan_sel4][["IP", "Host"]].copy()
            ips_usadas["label"] = ips_usadas["IP"] + "  —  " + ips_usadas["Host"].fillna("")
            opciones    = ips_usadas["label"].tolist()

            seleccion   = st.selectbox("IP a liberar:", opciones)
            ip_liberar  = seleccion.split("  —  ")[0].strip()

            st.warning(f"Se eliminará **{ip_liberar}** de la hoja Servidores y quedará como LIBRE.")

            if st.button("🔓 Confirmar liberación"):
                marcar_ip(ips_df.copy(), vlan_sel4, ip_liberar, "LIBRE")
                st.success(f"IP **{ip_liberar}** liberada correctamente.")
                st.rerun()
