import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(
    page_title="IPAM — Gestión de IPs",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

.stApp { background-color: #0D1117; color: #E6EDF3; }

.ipam-header {
    background: linear-gradient(135deg, #161B22 0%, #1C2128 100%);
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.ipam-header-icon { font-size: 36px; line-height: 1; }
.ipam-header-title { font-size: 26px; font-weight: 700; color: #E6EDF3; letter-spacing: -0.5px; margin: 0; }
.ipam-header-sub { font-size: 13px; color: #8B949E; margin: 2px 0 0 0; font-family: 'IBM Plex Mono', monospace; }

.stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.stat-card.total::before { background: #388BFD; }
.stat-card.usada::before { background: #F85149; }
.stat-card.libre::before { background: #3FB950; }
.stat-card:hover { border-color: #58A6FF; }
.stat-label { font-size: 11px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase; color: #8B949E; margin-bottom: 10px; font-family: 'IBM Plex Mono', monospace; }
.stat-value { font-size: 38px; font-weight: 700; line-height: 1; font-family: 'IBM Plex Mono', monospace; }
.stat-card.total .stat-value { color: #388BFD; }
.stat-card.usada .stat-value { color: #F85149; }
.stat-card.libre .stat-value { color: #3FB950; }
.stat-icon { position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 32px; opacity: 0.12; }

.stTabs [data-baseweb="tab-list"] {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 6px;
    gap: 4px;
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 7px;
    color: #8B949E;
    font-weight: 500;
    font-size: 14px;
    padding: 8px 20px;
    border: none;
    transition: all 0.2s;
}
.stTabs [data-baseweb="tab"]:hover { background: #1C2128; color: #E6EDF3; }
.stTabs [aria-selected="true"] { background: #1F6FEB !important; color: #FFFFFF !important; font-weight: 600 !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

.section-title {
    font-size: 13px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;
    color: #8B949E; margin-bottom: 16px; padding-bottom: 8px;
    border-bottom: 1px solid #21262D; font-family: 'IBM Plex Mono', monospace;
}

.stSelectbox > div > div,
.stTextInput > div > div,
.stTextArea > div > div {
    background-color: #161B22 !important;
    border: 1px solid #30363D !important;
    border-radius: 8px !important;
    color: #E6EDF3 !important;
}
label { color: #8B949E !important; font-size: 13px !important; font-weight: 500 !important; }

.stButton > button {
    background: #1F6FEB; color: white; border: none; border-radius: 8px;
    font-weight: 600; font-size: 14px; padding: 10px 24px; width: 100%;
    transition: all 0.2s; font-family: 'IBM Plex Sans', sans-serif;
}
.stButton > button:hover { background: #388BFD; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(31,111,235,0.4); }
.stFormSubmitButton > button {
    background: #1F6FEB !important; color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important; padding: 10px 24px !important; width: 100% !important;
}
.stFormSubmitButton > button:hover { background: #388BFD !important; box-shadow: 0 4px 16px rgba(31,111,235,0.4) !important; }

.stDataFrame { border: 1px solid #30363D !important; border-radius: 10px !important; overflow: hidden; }

.info-box {
    background: #161B22; border: 1px solid #30363D; border-left: 3px solid #388BFD;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;
    font-size: 13px; color: #8B949E; font-family: 'IBM Plex Mono', monospace;
}
.warn-box {
    background: rgba(210,153,34,0.1); border: 1px solid rgba(210,153,34,0.3);
    border-left: 3px solid #D29922; border-radius: 8px; padding: 14px 18px;
    margin-bottom: 16px; font-size: 13px; color: #D29922;
}
.result-count {
    font-size: 12px; color: #8B949E; font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 12px; padding: 6px 12px; background: #161B22;
    border: 1px solid #30363D; border-radius: 6px; display: inline-block;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #161B22; }
::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #8B949E; }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "IPAM_Inventario"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_client():
    import json, re
    raw = st.secrets["gcp_service_account"]["json_data"]
    info = json.loads(raw)
    pk = info["private_key"]
    pk = re.sub(r'-----BEGIN PRIVATE KEY-----', '', pk)
    pk = re.sub(r'-----END PRIVATE KEY-----', '', pk)
    pk = re.sub(r'[\s]+', '\n', pk.strip())
    info["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + pk.strip() + "\n-----END PRIVATE KEY-----\n"
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def cargar_datos():
    try:
        client = get_client()
        sh = client.open(SHEET_NAME)
        vlan_df    = pd.DataFrame(sh.worksheet("VLANs").get_all_records())
        servers_df = pd.DataFrame(sh.worksheet("Servidores").get_all_records())
        ips_df     = pd.DataFrame(sh.worksheet("IPs_VLAN").get_all_records())
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

def guardar_hoja(nombre_hoja, df):
    client = get_client()
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet(nombre_hoja)
    ws.clear()
    ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())
    cargar_datos.clear()

def marcar_ip(ips_df, vlan, ip, nuevo_estado, host="", descripcion="", observaciones="", ambiente="", cluster=""):
    vlan_df, servers_df, _, _ = cargar_datos()
    mask_ip = (ips_df["VLAN"] == int(vlan)) & (ips_df["IP"] == ip)
    ips_df.loc[mask_ip, "Estado"]      = nuevo_estado.upper()
    ips_df.loc[mask_ip, "Descripcion"] = descripcion
    guardar_hoja("IPs_VLAN", ips_df)
    mask_srv = (servers_df["VLAN"] == int(vlan)) & (servers_df["IP"] == ip)
    if nuevo_estado.upper() == "USADA":
        if mask_srv.any():
            servers_df.loc[mask_srv, "Host"]          = host
            servers_df.loc[mask_srv, "Descripcion"]   = descripcion
            servers_df.loc[mask_srv, "Observaciones"] = observaciones
            servers_df.loc[mask_srv, "Ambiente"]      = ambiente
            servers_df.loc[mask_srv, "Cluster"]       = cluster
        else:
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

vlan_df, servers_df, ips_df, data = cargar_datos()

# HEADER
st.markdown("""
<div class="ipam-header">
    <div class="ipam-header-icon">🖧</div>
    <div>
        <p class="ipam-header-title">IPAM — Gestor de Direcciones IP</p>
        <p class="ipam-header-sub">IP Address Management · Infraestructura</p>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "  📋  Consulta VLAN  ",
    "  🔍  Buscar  ",
    "  📝  Asignar IP  ",
    "  🔓  Liberar IP  "
])

# TAB 1
with tab1:
    st.markdown('<div class="section-title">Consulta por VLAN</div>', unsafe_allow_html=True)
    if data is not None:
        vlan_list = sorted(data["VLAN"].unique())
        vlan_sel  = st.selectbox("Seleccionar VLAN", vlan_list, key="vlan_sel")
        df_vlan   = data[data["VLAN"] == vlan_sel].copy()
        estados   = df_vlan["Estado"].astype(str).str.upper().str.strip()
        total = len(df_vlan)
        u     = int((estados == "USADA").sum())
        l     = int((estados == "LIBRE").sum())
        pct   = round((u / total * 100) if total > 0 else 0)
        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card total">
                <div class="stat-label">Total IPs</div>
                <div class="stat-value">{total}</div>
                <div class="stat-icon">◈</div>
            </div>
            <div class="stat-card usada">
                <div class="stat-label">Usadas</div>
                <div class="stat-value">{u}</div>
                <div class="stat-icon">●</div>
            </div>
            <div class="stat-card libre">
                <div class="stat-label">Libres</div>
                <div class="stat-value">{l}</div>
                <div class="stat-icon">○</div>
            </div>
        </div>
        <div class="info-box">
            Utilización VLAN {vlan_sel}: <strong style="color:#E6EDF3">{pct}%</strong>
            &nbsp;·&nbsp; {u} de {total} direcciones asignadas
        </div>
        """, unsafe_allow_html=True)
        cols_mostrar = ["IP", "Estado", "Host", "Cluster", "Descripcion"]
        existentes   = [c for c in cols_mostrar if c in df_vlan.columns]
        def color_estado(val):
            v = str(val).upper()
            if v == "LIBRE": return "color: #3FB950; font-weight: 600;"
            if v == "USADA": return "color: #F85149; font-weight: 600;"
            return "color: #8B949E;"
        st.dataframe(df_vlan[existentes].style.map(color_estado, subset=["Estado"]),
                     use_container_width=True, hide_index=True, height=420)

# TAB 2
with tab2:
    st.markdown('<div class="section-title">Búsqueda de Hosts y Direcciones</div>', unsafe_allow_html=True)
    if data is not None:
        c1, c2 = st.columns([1, 3])
        tipo  = c1.selectbox("Buscar por", ["IP o Host", "Solo IP", "Solo Host"])
        query = c2.text_input("Ingresá IP, hostname o parte del nombre")
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
            st.markdown(f'<div class="result-count">▸ {len(res)} resultado(s) para "{q}"</div>', unsafe_allow_html=True)
            cols_mostrar = ["VLAN", "IP", "Estado", "Host", "Ambiente", "Cluster", "Descripcion"]
            existentes   = [c for c in cols_mostrar if c in res.columns]
            def color_estado2(val):
                v = str(val).upper()
                if v == "LIBRE": return "color: #3FB950; font-weight: 600;"
                if v == "USADA": return "color: #F85149; font-weight: 600;"
                return "color: #8B949E;"
            st.dataframe(res[existentes].style.map(color_estado2, subset=["Estado"]),
                         use_container_width=True, hide_index=True, height=400)
        else:
            st.markdown('<div class="info-box">Escribí una IP o nombre de host para comenzar la búsqueda.</div>', unsafe_allow_html=True)

# TAB 3
with tab3:
    st.markdown('<div class="section-title">Asignar Dirección IP</div>', unsafe_allow_html=True)
    if data is not None and ips_df is not None:
        libres = data[data["Estado"] == "LIBRE"][["VLAN", "IP"]].drop_duplicates()
        if libres.empty:
            st.markdown('<div class="warn-box">⚠ No hay direcciones IP libres disponibles.</div>', unsafe_allow_html=True)
        else:
            c1, c2 = st.columns(2)
            with c1:
                vlan_libres = sorted(libres["VLAN"].unique())
                vlan_sel3   = st.selectbox("VLAN", vlan_libres, key="vlan_asignar")
            with c2:
                ips_libres = sorted(libres[libres["VLAN"] == vlan_sel3]["IP"].tolist())
                ip_sel     = st.selectbox("IP disponible", ips_libres)
            st.markdown(f'<div class="info-box">Asignando <strong style="color:#E6EDF3">{ip_sel}</strong> en VLAN <strong style="color:#E6EDF3">{vlan_sel3}</strong></div>', unsafe_allow_html=True)
            with st.form("form_asignar"):
                col1, col2 = st.columns(2)
                with col1:
                    host     = st.text_input("Host / Nombre del servidor *")
                    ambiente = st.selectbox("Ambiente", ["PROD", "QA", "PRE", ""])
                with col2:
                    cluster     = st.text_input("Cluster")
                    descripcion = st.text_input("Descripción")
                observ    = st.text_area("Observaciones", height=80)
                submitted = st.form_submit_button("✅  Confirmar asignación")
            if submitted:
                if not host.strip():
                    st.error("⚠ El campo Host es obligatorio.")
                else:
                    marcar_ip(ips_df.copy(), vlan_sel3, ip_sel, "USADA",
                              host=host.strip(), descripcion=descripcion,
                              observaciones=observ, ambiente=ambiente, cluster=cluster)
                    st.success(f"✓ IP **{ip_sel}** asignada correctamente a **{host}**.")
                    st.rerun()

# TAB 4
with tab4:
    st.markdown('<div class="section-title">Liberar Dirección IP</div>', unsafe_allow_html=True)
    if data is not None and ips_df is not None:
        usadas = data[data["Estado"] == "USADA"][["VLAN", "IP", "Host", "Descripcion"]].drop_duplicates()
        if usadas.empty:
            st.markdown('<div class="info-box">No hay direcciones IP en uso registradas.</div>', unsafe_allow_html=True)
        else:
            c1, c2 = st.columns(2)
            with c1:
                vlan_usadas = sorted(usadas["VLAN"].unique())
                vlan_sel4   = st.selectbox("VLAN", vlan_usadas, key="vlan_liberar")
            with c2:
                ips_usadas = usadas[usadas["VLAN"] == vlan_sel4][["IP", "Host"]].copy()
                ips_usadas["label"] = ips_usadas["IP"] + "  ·  " + ips_usadas["Host"].fillna("—")
                seleccion  = st.selectbox("IP a liberar", ips_usadas["label"].tolist())
                ip_liberar = seleccion.split("  ·  ")[0].strip()
            host_liberar = ips_usadas[ips_usadas["IP"] == ip_liberar]["Host"].values
            host_str     = host_liberar[0] if len(host_liberar) > 0 else "—"
            st.markdown(f"""
            <div class="warn-box">
                ⚠ &nbsp;Se liberará <strong>{ip_liberar}</strong> ({host_str}).
                El registro será eliminado de Servidores y la IP quedará disponible.
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔓  Confirmar liberación"):
                marcar_ip(ips_df.copy(), vlan_sel4, ip_liberar, "LIBRE")
                st.success(f"✓ IP **{ip_liberar}** liberada correctamente.")
                st.rerun()
