import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Pengu 3D - Gestor Web", layout="centered")

# --- ESTILOS CSS PERSONALIZADOS (Para que se vea bonito) ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #fc9d03;
        color: white;
        font-weight: bold;
    }
    .total-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        color: #fc9d03;
        border: 2px solid #fc9d03;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATOS INICIALES Y ESTADO ---
# Usamos session_state para guardar datos mientras el usuario navega
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# Base de datos simulada (En web es mejor tenerlos así o conectar a Google Sheets)
MATERIALES = {
    "PLA Estándar": 15000, "PLA+ / Silk": 19000, "PETG": 17000,
    "ABS": 16000, "TPU (Flexible)": 28000, "Resina Estándar": 40000,
    "ASA": 22000, "Nylon": 45000, "PC": 35000
}

# --- BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/299/299901.png", width=100) # Icono genérico
    st.title("Configuración")
    
    st.markdown("### ⚙️ Costos Globales")
    costo_minuto = st.number_input("Costo Máquina ($/min)", value=3.0, step=0.5)
    valor_hora_mo = st.number_input("Valor Hora Hombre ($)", value=3000.0, step=500.0)
    
    st.markdown("---")
    st.info("Pengu 3D Web App v1.0")

# --- TÍTULO PRINCIPAL ---
st.title("🐧 Pengu 3D | Calculadora y Presupuestos")

# --- PESTAÑAS ---
tab_calc, tab_presu = st.tabs(["🖨️ Calculadora 3D", "📄 Presupuesto Final"])

# ==========================================
# PESTAÑA 1: CALCULADORA
# ==========================================
with tab_calc:
    st.subheader("Calcular Costo de Impresión")
    
    col1, col2 = st.columns(2)
    
    with col1:
        material_sel = st.selectbox("Material", list(MATERIALES.keys()))
        precio_kg_default = MATERIALES[material_sel]
        costo_rollo = st.number_input("Precio Rollo (1kg)", value=float(precio_kg_default))
        peso = st.number_input("Peso de la pieza (gramos)", min_value=1, value=50)

    with col2:
        c1, c2 = st.columns(2)
        horas = c1.number_input("Horas", min_value=0, value=2)
        mins = c2.number_input("Minutos", min_value=0, max_value=59, value=30)
        
        # Lógica de Horas Hombre
        horas_mo = st.number_input("Mano de Obra (Horas dedicadas)", value=0.5, step=0.1, help="Tiempo de post-procesado, laminado, limpieza.")
        st.caption(f"Valor MO: ${horas_mo * valor_hora_mo:,.0f}")

    margen = st.slider("Margen de Ganancia (%)", 0, 300, 100)

    # --- CÁLCULOS ---
    if st.button("CALCULAR PRECIO"):
        tiempo_total_mins = (horas * 60) + mins
        costo_material = (costo_rollo / 1000) * peso
        costo_tiempo = costo_minuto * tiempo_total_mins
        costo_mo_total = horas_mo * valor_hora_mo
        
        costo_base = costo_material + costo_tiempo + costo_mo_total
        precio_final = costo_base * (1 + (margen/100))
        
        # Guardar resultado temporalmente
        st.session_state.resultado_temp = {
            "desc": f"Impresión {material_sel} ({peso}g - {horas}h {mins}m)",
            "precio": precio_final,
            "detalle": f"Mat: ${costo_material:.0f} | Máq: ${costo_tiempo:.0f} | MO: ${costo_mo_total:.0f}"
        }

    # Mostrar Resultado si existe
    if 'resultado_temp' in st.session_state:
        res = st.session_state.resultado_temp
        st.success(f"✅ Precio Sugerido: ${res['precio']:,.0f}")
        st.caption(res['detalle'])
        
        if st.button("Añadir al Presupuesto ➡️"):
            st.session_state.carrito.append({
                "cant": 1,
                "descripcion": res['desc'],
                "unitario": res['precio'],
                "total": res['precio']
            })
            st.toast("¡Agregado al carrito!")
            del st.session_state.resultado_temp # Limpiar temp

# ==========================================
# PESTAÑA 2: PRESUPUESTO
# ==========================================
with tab_presu:
    st.subheader("Generar PDF")
    
    cliente = st.text_input("Nombre del Cliente", "Cliente General")
    
    # Agregar Item Manual
    with st.expander("Agregar Item Manual (Extra)"):
        c_man1, c_man2, c_man3 = st.columns([3, 1, 1])
        desc_man = c_man1.text_input("Descripción")
        cant_man = c_man2.number_input("Cant", 1, 100, 1)
        prec_man = c_man3.number_input("Precio Unit", 0.0)
        if st.button("Agregar Item Manual"):
            st.session_state.carrito.append({
                "cant": cant_man,
                "descripcion": desc_man,
                "unitario": prec_man,
                "total": prec_man * cant_man
            })
            st.rerun()

    # Tabla de Items
    if st.session_state.carrito:
        df_carrito = pd.DataFrame(st.session_state.carrito)
        
        # Mostrar tabla bonita
        st.dataframe(df_carrito, use_container_width=True, hide_index=True)
        
        # Botón para borrar todo
        if st.button("Vaciar Carrito 🗑️"):
            st.session_state.carrito = []
            st.rerun()

        total_presupuesto = sum(item['total'] for item in st.session_state.carrito)

        st.markdown(f'<div class="total-box">TOTAL: $ {total_presupuesto:,.0f}</div>', unsafe_allow_html=True
                   )
