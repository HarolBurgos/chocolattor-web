"""
Chocolattor Web  -  Calculadora de Costos para Chocolate
Una produccion de: Ayuda en Acción Colombia y La Agencia Española de Cooperación Internacional para el Desarrollo - AECID
"""

import streamlit as st
import json, math, io
from datetime import datetime
from modelos import (MateriaPrima, InsumoMP, InsumoGeneral, CostoFijo,
                     OtroGasto, ItemFormulacion, Presentacion, calcular_tir)

# -- PDF ----------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, HRFlowable)
    RPDF = True
except ImportError:
    RPDF = False

# -- Matplotlib ---------------------------------------------------------------
try:
    import matplotlib.pyplot as plt
    MPL = True
except ImportError:
    MPL = False


# =============================================================================
#  CONFIGURACION DE PAGINA
# =============================================================================

st.set_page_config(
    page_title="Chocolattor - Calculadora de Costos",
    page_icon="images/Icono.png" if True else "🍫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS institucionales
st.markdown("""
<style>
    /* Colores institucionales ASOCACAO */
    :root {
        --naranja: #E8490F;
        --turquesa: #007A87;
        --naranja-claro: #F4A261;
        --fondo: #FFF8F2;
        --cafe: #3D1F00;
    }
    .stApp { background-color: var(--fondo); }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #3D1F00 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #FFE8D6 !important;
    }

    /* Titulos */
    h1 { color: #E8490F !important; }
    h2 { color: #007A87 !important; }
    h3 { color: #E8490F !important; }

    /* Metricas */
    [data-testid="metric-container"] {
        background-color: #FFF0E6;
        border: 1px solid #F4A261;
        border-radius: 8px;
        padding: 8px;
    }

    /* Botones */
    .stButton > button {
        background-color: #F4A261 !important;
        color: #2C1A0E !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: bold !important;
    }
    .stButton > button:hover {
        background-color: #007A87 !important;
        color: white !important;
    }

    /* Tablas */
    .stDataFrame { border: 1px solid #F4A261; border-radius: 6px; }

    /* Info box */
    .info-box {
        background-color: #FFF0E6;
        border-left: 4px solid #007A87;
        padding: 10px 14px;
        border-radius: 4px;
        margin-bottom: 12px;
        font-size: 0.9em;
        color: #007A87;
    }

    /* Pie de pagina */
    .footer {
        text-align: center;
        color: #914B2B;
        font-size: 0.8em;
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px solid #F4A261;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
#  ESTADO DE SESION
# =============================================================================

def init_state():
    if "materias_primas"   not in st.session_state:
        st.session_state.materias_primas   = []
    if "insumos_generales" not in st.session_state:
        st.session_state.insumos_generales = []
    if "presentaciones"    not in st.session_state:
        st.session_state.presentaciones    = []
    if "costos_fijos"      not in st.session_state:
        st.session_state.costos_fijos      = []
    if "pres_idx"          not in st.session_state:
        st.session_state.pres_idx          = 0
    if "mp_idx"            not in st.session_state:
        st.session_state.mp_idx            = 0

init_state()

# Atajos
MPS  = st.session_state.materias_primas
IGS  = st.session_state.insumos_generales
PRES = st.session_state.presentaciones
CFS  = st.session_state.costos_fijos

def total_cf():
    return sum(c.monto for c in CFS)


# =============================================================================
#  SIDEBAR
# =============================================================================

with st.sidebar:
    try:
        st.image("images/Logo_asociacion.png", width=140)
    except Exception:
        st.markdown("### 🍫 ASOCACAO")

    st.markdown("## Chocolattor")
    st.markdown("*Calculadora de Costos*")
    st.divider()

    pagina = st.radio("Navegacion", [
        "1. Materias Primas",
        "2. Insumos Generales",
        "3. Presentaciones",
        "4. Formulacion",
        "5. Costos Fijos",
        "6. Produccion Mensual",
        "7. Otros Gastos",
        "8. IVA y Ganancia",
        "9. Punto de Equilibrio",
        "10. TIR / VPN",
        "11. Flujo de Caja",
        "12. Graficas",
    ], label_visibility="collapsed")

    st.divider()

    # Precio actual
    if PRES and 0 <= st.session_state.pres_idx < len(PRES):
        p = PRES[st.session_state.pres_idx]
        pv = p.precio_venta(MPS, IGS, total_cf())
        st.metric("Precio de Venta", f"${pv:,.1f}",
                  delta=p.nombre, delta_color="off")

    st.divider()

    # Guardar / Cargar / PDF
    st.markdown("**Archivo**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Guardar", use_container_width=True):
            data = {
                "version": "5_web",
                "materias_primas":   [m.to_dict() for m in MPS],
                "insumos_generales": [i.to_dict() for i in IGS],
                "presentaciones":    [p.to_dict() for p in PRES],
                "costos_fijos":      [c.to_dict() for c in CFS],
            }
            st.download_button(
                "Descargar JSON",
                data=json.dumps(data, indent=4, ensure_ascii=False),
                file_name=f"chocolattor_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
            )

    with col2:
        archivo = st.file_uploader("📂 Cargar", type=["json"],
                                   label_visibility="collapsed")
        if archivo:
            try:
                data = json.load(archivo)
                st.session_state.materias_primas   = [MateriaPrima.from_dict(d)   for d in data.get("materias_primas", [])]
                st.session_state.insumos_generales = [InsumoGeneral.from_dict(d)  for d in data.get("insumos_generales", [])]
                st.session_state.presentaciones    = [Presentacion.from_dict(d)   for d in data.get("presentaciones", [])]
                st.session_state.costos_fijos      = [CostoFijo.from_dict(d)      for d in data.get("costos_fijos", [])]
                MPS  = st.session_state.materias_primas
                IGS  = st.session_state.insumos_generales
                PRES = st.session_state.presentaciones
                CFS  = st.session_state.costos_fijos
                st.success("Cargado correctamente")
                st.rerun()
            except Exception as e:
                st.error("Error al cargar: " + str(e))

    if st.button("📄 Exportar PDF", use_container_width=True):
        if RPDF:
            pdf_bytes = generar_pdf()
            st.download_button(
                "Descargar PDF",
                data=pdf_bytes,
                file_name=f"chocolattor_reporte_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
        else:
            st.error("Instala reportlab: pip install reportlab")


# =============================================================================
#  UTILIDADES UI
# =============================================================================

def info(txt):
    st.markdown(f'<div class="info-box">{txt}</div>', unsafe_allow_html=True)

def pie():
    st.markdown("""
    <div class="footer">
        Chocolattor v5 Web &nbsp;|&nbsp; Una produccion de: Ayuda en Acción y La Agencia Española de Cooperación Internacional para el Desarrollo - AECID
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
#  1. MATERIAS PRIMAS
# =============================================================================

def pagina_materias_primas():
    st.title("1. Materias Primas del Cacao")
    info("Crea cada materia prima (Licor, Manteca, Cocoa, Nibs u Otra), "
         "agrega sus insumos de batch y calcula el costo/kg. "
         "Quedaran disponibles automaticamente en Formulacion.")

    # Tabla resumen
    if MPS:
        st.subheader("Materias Primas creadas")
        filas = []
        for mp in MPS:
            filas.append({
                "Materia Prima":  mp.nombre,
                "Batch (kg)":     round(mp.batch_kg, 1),
                "Rendimiento %":  str(round(mp.rendimiento, 1)) + "%",
                "Costo/kg ($)":   f"${mp.costo_por_kg():,.1f}",
                "Costo/g ($)":    f"${mp.costo_por_gramo():,.4f}",
                "N Insumos":      len(mp.insumos),
            })
        st.dataframe(filas, use_container_width=True, hide_index=True)

        # Selector MP activa
        nombres_mp = [m.nombre for m in MPS]
        idx = st.selectbox("Seleccionar MP para ver/editar insumos:",
                           range(len(nombres_mp)),
                           format_func=lambda i: nombres_mp[i],
                           key="mp_sel")
        st.session_state.mp_idx = idx
        mp = MPS[idx]

        st.divider()
        st.subheader(f"Insumos y gastos asociados al Batch: {mp.nombre}")

        col1, col2, col3 = st.columns(3)
        with col1:
            mp.batch_kg    = st.number_input("Batch (kg):", value=mp.batch_kg,
                                              min_value=0.1, step=1.0, key="mp_bat")
        with col2:
            mp.rendimiento = st.number_input("Rendimiento (%):", value=mp.rendimiento,
                                              min_value=1.0, max_value=100.0,
                                              step=1.0, key="mp_ren")
        with col3:
            cpk = mp.costo_por_kg()
            st.metric("Costo por kg", f"${cpk:,.1f}")

        # Tabla insumos de esta MP
        if mp.insumos:
            filas_ins = []
            for ins in mp.insumos:
                filas_ins.append({
                    "Nombre":          ins.nombre,
                    "Cantidad":        ins.cantidad,
                    "Unidad":          ins.unidad,
                    "Costo Unit ($)":  f"${ins.costo_unit:,.1f}",
                    "Costo Total ($)": f"${ins.costo_total():,.1f}",
                })
            st.dataframe(filas_ins, use_container_width=True, hide_index=True)

            total_ins = sum(i.costo_total() for i in mp.insumos)
            st.info(f"Total insumos batch: **${total_ins:,.1f}**")

            # Eliminar insumo
            with st.expander("Eliminar un insumo"):
                nombres_ins = [i.nombre for i in mp.insumos]
                del_ins = st.selectbox("Insumo a eliminar:", nombres_ins, key="del_ins")
                if st.button("Eliminar insumo", key="btn_del_ins"):
                    mp.insumos = [i for i in mp.insumos if i.nombre != del_ins]
                    st.rerun()

        # Agregar insumo
        with st.expander("➕ Agregar Insumo al Batch", expanded=not mp.insumos):
            c1, c2, c3, c4 = st.columns(4)
            nom_i  = c1.text_input("Nombre:", key="ins_nom")
            cant_i = c2.number_input("Cantidad:", min_value=0.0, step=0.1, key="ins_cant")
            uni_i  = c3.text_input("Unidad:", placeholder="kg, lb, gr...", key="ins_uni")
            cu_i   = c4.number_input("Costo Unitario ($):", min_value=0.0, step=100.0, key="ins_cu")
            if st.button("Agregar Insumo", key="btn_add_ins"):
                if nom_i and cant_i > 0 and cu_i >= 0:
                    mp.insumos.append(InsumoMP(nom_i, cant_i, uni_i, cu_i))
                    st.success(f"Insumo '{nom_i}' agregado.")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos.")

        if st.button("Eliminar esta Materia Prima", type="secondary"):
            st.session_state.materias_primas.pop(idx)
            st.rerun()

    # Crear nueva MP
    st.divider()
    st.subheader("Agregar Nueva Materia Prima")
    st.caption("Referencia rendimientos: Licor 75-80% | Manteca 45-50% | Cocoa 50-55% | Nibs 80-85%")

    c1, c2, c3, c4 = st.columns(4)
    tipo_mp = c1.selectbox("Tipo:", MateriaPrima.TIPOS, key="mp_tipo")
    nom_mp  = c2.text_input("Nombre (si es Otra):", key="mp_nom")
    bat_mp  = c3.number_input("Batch (kg):", value=30.0, min_value=0.1, step=1.0, key="mp_bat_new")
    ren_mp  = c4.number_input("Rendimiento (%):", value=75.0, min_value=1.0,
                               max_value=100.0, step=1.0, key="mp_ren_new")

    if st.button("Crear Materia Prima", type="primary"):
        nombre_final = nom_mp.strip() if tipo_mp == "Otra" else tipo_mp
        if not nombre_final:
            st.error("Escribe un nombre.")
        elif any(m.nombre.lower() == nombre_final.lower() for m in MPS):
            st.error(f"Ya existe '{nombre_final}'.")
        else:
            nueva = MateriaPrima(nombre_final, bat_mp, ren_mp)
            st.session_state.materias_primas.append(nueva)
            st.success(f"'{nombre_final}' creada correctamente.")
            st.rerun()


# =============================================================================
#  2. INSUMOS GENERALES
# =============================================================================

def pagina_insumos_generales():
    st.title("2. Insumos Generales")
    info("Agrega azucar, leche, lecitina y otros ingredientes adicionales. "
         "El costo/gramo se calcula automaticamente segun la unidad de compra. "
         "Unidades aceptadas: kg, gr/g, lb, oz, ml, l/litros, unidad")

    if IGS:
        filas = []
        for ig in IGS:
            filas.append({
                "Nombre":          ig.nombre,
                "Cantidad":        ig.cantidad,
                "Unidad":          ig.unidad,
                "Costo Total ($)": f"${ig.costo_total:,.1f}",
                "$/gramo":         f"${ig.costo_por_gramo():,.4f}",
            })
        st.dataframe(filas, use_container_width=True, hide_index=True)

        with st.expander("Eliminar un insumo general"):
            nombres_ig = [i.nombre for i in IGS]
            del_ig = st.selectbox("Insumo a eliminar:", nombres_ig, key="del_ig")
            if st.button("Eliminar", key="btn_del_ig"):
                st.session_state.insumos_generales = [
                    i for i in IGS if i.nombre != del_ig]
                st.rerun()

    st.divider()
    st.subheader("Agregar Insumo General")
    c1, c2, c3, c4 = st.columns(4)
    nom_ig  = c1.text_input("Nombre:", key="ig_nom")
    cant_ig = c2.number_input("Cantidad:", min_value=0.0, step=0.1, key="ig_cant")
    uni_ig  = c3.text_input("Unidad:", placeholder="kg, gr, litros...", key="ig_uni")
    ct_ig   = c4.number_input("Costo Total ($):", min_value=0.0, step=100.0, key="ig_ct")

    if st.button("Agregar Insumo General", type="primary"):
        if not nom_ig or cant_ig <= 0 or ct_ig < 0 or not uni_ig:
            st.warning("Completa todos los campos correctamente.")
        else:
            st.session_state.insumos_generales.append(
                InsumoGeneral(nom_ig, cant_ig, uni_ig, ct_ig))
            st.success(f"'{nom_ig}' agregado.")
            st.rerun()


# =============================================================================
#  3. PRESENTACIONES
# =============================================================================

def pagina_presentaciones():
    st.title("3. Presentaciones de Producto")
    info("Cada presentacion es un producto terminado con nombre y peso. "
         "Ejemplo: 'Chocolatina Chitena 90g'.")

    tcf = total_cf()

    if PRES:
        filas = []
        for p in PRES:
            ctu = p.costo_total_unit(MPS, IGS, tcf)
            pv  = p.precio_venta(MPS, IGS, tcf)
            filas.append({
                "Presentacion":     p.nombre,
                "Peso (g)":         int(p.peso_g),
                "Costo Total ($)":  f"${ctu:,.1f}",
                "Precio Venta ($)": f"${pv:,.1f}",
                "IVA %":            f"{p.iva_pct:.1f}%",
                "Ganancia %":       f"{p.ganancia_pct:.1f}%",
            })
        st.dataframe(filas, use_container_width=True, hide_index=True)

        # Selector presentacion activa
        nombres_p = [p.nombre for p in PRES]
        idx_p = st.selectbox("Presentacion activa (para pasos siguientes):",
                             range(len(nombres_p)),
                             format_func=lambda i: nombres_p[i],
                             index=st.session_state.pres_idx,
                             key="pres_sel_main")
        st.session_state.pres_idx = idx_p

        if st.button("Eliminar presentacion seleccionada", type="secondary"):
            st.session_state.presentaciones.pop(idx_p)
            st.session_state.pres_idx = 0
            st.rerun()

    st.divider()
    st.subheader("Crear Nueva Presentacion")
    c1, c2 = st.columns(2)
    nom_p  = c1.text_input("Nombre:", placeholder="Chocolatina Chitena",  key="pnom")
    peso_p = c2.number_input("Peso (g):", min_value=1.0, value=90.0, step=5.0, key="ppeso")

    if st.button("Crear Presentacion", type="primary"):
        if not nom_p:
            st.error("El nombre es requerido.")
        elif peso_p <= 0:
            st.error("El peso debe ser > 0.")
        elif any(p.nombre.lower() == nom_p.lower() for p in PRES):
            st.error(f"Ya existe '{nom_p}'.")
        else:
            st.session_state.presentaciones.append(Presentacion(nom_p, peso_p))
            st.session_state.pres_idx = len(PRES) - 1
            st.success(f"'{nom_p}' creada.")
            st.rerun()


# =============================================================================
#  4. FORMULACION
# =============================================================================

def pagina_formulacion():
    st.title("4. Formulacion")
    if not PRES:
        st.warning("Crea una presentacion primero (Paso 3).")
        return

    idx_p = st.session_state.pres_idx
    if idx_p >= len(PRES): idx_p = 0
    p = PRES[idx_p]

    nombres_p = [pr.nombre for pr in PRES]
    nuevo_idx = st.selectbox("Presentacion:", range(len(nombres_p)),
                              format_func=lambda i: nombres_p[i],
                              index=idx_p, key="form_psel")
    if nuevo_idx != idx_p:
        st.session_state.pres_idx = nuevo_idx
        st.rerun()

    info(f"Define la proporcion de ingredientes para **{p.nombre}** "
         f"({int(p.peso_g)} g). La suma de proporciones debe ser 100%.")

    # Resumen
    suma_prop = sum(item.proporcion_pct for item in p.formulacion)
    cvi = p.costo_variable_insumos(MPS, IGS)
    col1, col2, col3 = st.columns(3)
    col1.metric("Peso", f"{int(p.peso_g)} g")
    color_suma = "normal" if 99 <= suma_prop <= 101 else "inverse"
    col2.metric("Suma proporciones", f"{suma_prop:.1f}%",
                delta="OK" if 99 <= suma_prop <= 101 else "Debe ser 100%",
                delta_color=color_suma)
    col3.metric("Costo variable insumos", f"${cvi:,.4f}")

    # Tabla formulacion actual
    if p.formulacion:
        filas_f = []
        for item in p.formulacion:
            gramos = (item.proporcion_pct / 100.0) * p.peso_g
            cpg    = p.cpg(item.nombre, MPS, IGS)
            filas_f.append({
                "Ingrediente":     item.nombre,
                "Proporcion %":    f"{item.proporcion_pct:.1f}%",
                "Cantidad (g)":    f"{gramos:.1f}",
                "$/g":             f"${cpg:.4f}",
                "Costo Total ($)": f"${gramos * cpg:.4f}",
            })
        st.dataframe(filas_f, use_container_width=True, hide_index=True)

        with st.expander("Eliminar ingrediente"):
            nombres_f = [item.nombre for item in p.formulacion]
            del_f = st.selectbox("Ingrediente:", nombres_f, key="del_form")
            if st.button("Eliminar", key="btn_del_form"):
                p.formulacion = [i for i in p.formulacion if i.nombre != del_f]
                st.rerun()

    # Agregar ingrediente
    st.divider()
    st.subheader("Agregar Ingrediente")
    opciones = [mp.nombre for mp in MPS] + [ig.nombre for ig in IGS]
    if not opciones:
        st.warning("Agrega Materias Primas e Insumos Generales primero.")
        return

    c1, c2 = st.columns(2)
    ing_sel = c1.selectbox("Ingrediente:", opciones, key="form_ing")
    prop    = c2.number_input("Proporcion (%):", min_value=0.0,
                               max_value=100.0, step=1.0, key="form_prop")

    # Mostrar costo/g en tiempo real
    cpg_preview = p.cpg(ing_sel, MPS, IGS) if ing_sel else 0.0
    gramos_prev = (prop / 100.0) * p.peso_g
    c3, c4 = st.columns(2)
    c3.metric("$/gramo", f"${cpg_preview:.4f}")
    c4.metric("Costo total ingrediente", f"${gramos_prev * cpg_preview:.4f}")

    if st.button("Agregar a Formulacion", type="primary"):
        if not ing_sel or prop <= 0:
            st.warning("Selecciona un ingrediente y define la proporcion.")
        else:
            # Reemplazar si ya existe
            p.formulacion = [i for i in p.formulacion if i.nombre != ing_sel]
            p.formulacion.append(ItemFormulacion(ing_sel, prop))
            st.success(f"'{ing_sel}' agregado con {prop:.1f}%")
            st.rerun()


# =============================================================================
#  5. COSTOS FIJOS
# =============================================================================

def pagina_costos_fijos():
    st.title("5. Costos Fijos Mensuales")
    info("Gastos que no dependen del volumen de produccion: "
         "arriendo, nomina, servicios, depreciacion...")

    tcf = total_cf()
    st.metric("Total Costos Fijos Mensuales", f"${tcf:,.1f}")

    if CFS:
        filas_cf = [{"Nombre": c.nombre, "Categoria": c.categoria,
                     "Monto ($)": f"${c.monto:,.1f}"} for c in CFS]
        st.dataframe(filas_cf, use_container_width=True, hide_index=True)

        with st.expander("Eliminar costo fijo"):
            nombres_cf = [c.nombre for c in CFS]
            del_cf = st.selectbox("Costo a eliminar:", nombres_cf, key="del_cf")
            if st.button("Eliminar", key="btn_del_cf"):
                st.session_state.costos_fijos = [c for c in CFS if c.nombre != del_cf]
                st.rerun()

    st.divider()
    st.subheader("Agregar Costo Fijo")
    c1, c2, c3 = st.columns(3)
    nom_cf  = c1.text_input("Nombre:", key="cf_nom")
    cat_cf  = c2.selectbox("Categoria:", CostoFijo.CATEGORIAS, key="cf_cat")
    mont_cf = c3.number_input("Monto Mensual ($):", min_value=0.0,
                               step=10000.0, key="cf_mont")

    if st.button("Agregar Costo Fijo", type="primary"):
        if not nom_cf or mont_cf <= 0:
            st.warning("Nombre y monto requeridos.")
        else:
            st.session_state.costos_fijos.append(CostoFijo(nom_cf, mont_cf, cat_cf))
            st.success(f"'{nom_cf}' agregado.")
            st.rerun()


# =============================================================================
#  6. PRODUCCION MENSUAL
# =============================================================================

def pagina_produccion_mensual():
    st.title("6. Produccion Mensual")
    if not PRES:
        st.warning("Crea una presentacion primero (Paso 3).")
        return

    tcf = total_cf()
    idx_p = st.session_state.pres_idx
    if idx_p >= len(PRES): idx_p = 0
    p = PRES[idx_p]

    nombres_p = [pr.nombre for pr in PRES]
    nuevo_idx = st.selectbox("Presentacion:", range(len(nombres_p)),
                              format_func=lambda i: nombres_p[i],
                              index=idx_p, key="prod_psel")
    st.session_state.pres_idx = nuevo_idx
    p = PRES[nuevo_idx]

    info(f"Define cuantas unidades de **{p.nombre}** produces al mes. "
         "Costo Fijo Unitario = Costos Fijos Totales / Unidades al mes.")

    cant_mens = st.number_input(
        "Unidades producidas por mes:",
        min_value=0.0, value=p.cantidad_mensual, step=10.0, key="prod_cant")

    p.cantidad_mensual = cant_mens
    tcf_val = tcf
    cfu = tcf_val / cant_mens if cant_mens > 0 else 0.0
    cvi = p.costo_variable_insumos(MPS, IGS)
    cog = p.costo_otros()
    cvu = cvi + cog
    ctu = cvu + cfu

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CF Totales Mensual", f"${tcf_val:,.1f}")
    c2.metric("Costo Fijo Unitario", f"${cfu:,.1f}")
    c3.metric("Costo Variable Unit.", f"${cvu:,.1f}")
    c4.metric("Costo Total Unitario", f"${ctu:,.1f}")


# =============================================================================
#  7. OTROS GASTOS
# =============================================================================

def pagina_otros_gastos():
    st.title("7. Otros Gastos Unitarios")
    if not PRES:
        st.warning("Crea una presentacion primero (Paso 3).")
        return

    idx_p = st.session_state.pres_idx
    if idx_p >= len(PRES): idx_p = 0
    p = PRES[idx_p]

    nombres_p = [pr.nombre for pr in PRES]
    nuevo_idx = st.selectbox("Presentacion:", range(len(nombres_p)),
                              format_func=lambda i: nombres_p[i],
                              index=idx_p, key="og_psel")
    st.session_state.pres_idx = nuevo_idx
    p = PRES[nuevo_idx]

    info(f"Costos adicionales por unidad de **{p.nombre}**: "
         "empaque, embalaje, etiqueta, mercadeo...")

    tcf = total_cf()
    cvi = p.costo_variable_insumos(MPS, IGS)
    cog = p.costo_otros()
    cfu = p.costo_fijo_unit(tcf)
    ctu = cvi + cog + cfu

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CV Insumos", f"${cvi:,.1f}")
    c2.metric("Otros Gastos", f"${cog:,.1f}")
    c3.metric("CF Unitario", f"${cfu:,.1f}")
    c4.metric("Costo Total Unit.", f"${ctu:,.1f}")

    if p.otros_gastos:
        filas_og = [{"Nombre": g.nombre, "Costo Unitario ($)": f"${g.costo_unit:,.1f}"}
                    for g in p.otros_gastos]
        st.dataframe(filas_og, use_container_width=True, hide_index=True)
        st.info(f"Total otros gastos: **${p.costo_otros():,.1f}**")

        with st.expander("Eliminar gasto"):
            nombres_og = [g.nombre for g in p.otros_gastos]
            del_og = st.selectbox("Gasto:", nombres_og, key="del_og")
            if st.button("Eliminar", key="btn_del_og"):
                p.otros_gastos = [g for g in p.otros_gastos if g.nombre != del_og]
                st.rerun()

    st.divider()
    st.subheader("Agregar Gasto")
    c1, c2 = st.columns(2)
    nom_og = c1.text_input("Nombre:", placeholder="Empaque, Etiqueta...", key="og_nom")
    cu_og  = c2.number_input("Costo Unitario ($):", min_value=0.0,
                              step=100.0, key="og_cu")

    if st.button("Agregar Gasto", type="primary"):
        if not nom_og or cu_og <= 0:
            st.warning("Completa todos los campos.")
        else:
            p.otros_gastos.append(OtroGasto(nom_og, cu_og))
            st.success(f"'{nom_og}' agregado.")
            st.rerun()


# =============================================================================
#  8. IVA Y GANANCIA
# =============================================================================

def pagina_iva_ganancia():
    st.title("8. IVA y Ganancia")
    if not PRES:
        st.warning("Crea una presentacion primero (Paso 3).")
        return

    idx_p = st.session_state.pres_idx
    if idx_p >= len(PRES): idx_p = 0

    nombres_p = [pr.nombre for pr in PRES]
    nuevo_idx = st.selectbox("Presentacion:", range(len(nombres_p)),
                              format_func=lambda i: nombres_p[i],
                              index=idx_p, key="iva_psel")
    st.session_state.pres_idx = nuevo_idx
    p = PRES[nuevo_idx]

    tcf = total_cf()
    ctu = p.costo_total_unit(MPS, IGS, tcf)

    info(f"Configura IVA y margen de ganancia para **{p.nombre}**.")

    c1, c2 = st.columns(2)
    iva = c1.number_input("% IVA:", min_value=0.0, max_value=100.0,
                           value=p.iva_pct, step=1.0, key="iva_val")
    gan = c2.number_input("% Ganancia:", min_value=0.0, max_value=500.0,
                           value=p.ganancia_pct, step=5.0, key="gan_val")
    p.iva_pct      = iva
    p.ganancia_pct = gan
    pv  = p.precio_venta(MPS, IGS, tcf)
    mg  = pv - ctu

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo Total Unit.", f"${ctu:,.1f}")
    c2.metric("IVA aplicado", f"${ctu * iva / 100:,.1f}")
    c3.metric("Margen ($)", f"${mg:,.1f}")
    c4.metric("PRECIO DE VENTA", f"${pv:,.1f}")


# =============================================================================
#  9. PUNTO DE EQUILIBRIO
# =============================================================================

def pagina_punto_equilibrio():
    st.title("9. Punto de Equilibrio")
    tcf = total_cf()
    info(f"PE = Costos Fijos / Margen de Contribucion  |  "
         f"Costos Fijos Mensuales: **${tcf:,.1f}**")

    if not PRES:
        st.warning("No hay presentaciones creadas.")
        return

    filas_pe = []
    for p in PRES:
        pv  = p.precio_venta(MPS, IGS, tcf)
        cvu = p.costo_variable_unit(MPS, IGS)
        mc  = pv - cvu
        if mc > 0:
            pe_u = math.ceil(tcf / mc)
            pe_i = pe_u * pv
            pe_txt = f"{pe_u:,}"
            pi_txt = f"${pe_i:,.1f}"
        else:
            pe_txt = "N/A"
            pi_txt = "N/A"
        filas_pe.append({
            "Presentacion":      p.nombre,
            "Precio ($)":        f"${pv:,.1f}",
            "CV Unitario ($)":   f"${cvu:,.1f}",
            "MC ($)":            f"${mc:,.1f}",
            "PE Unidades/mes":   pe_txt,
            "PE Ingresos ($)":   pi_txt,
        })
    st.dataframe(filas_pe, use_container_width=True, hide_index=True)

    # Grafica PE para primera presentacion con MC > 0
    if MPL:
        validos = [(p, p.precio_venta(MPS, IGS, tcf),
                    p.costo_variable_unit(MPS, IGS))
                   for p in PRES
                   if p.precio_venta(MPS, IGS, tcf) - p.costo_variable_unit(MPS, IGS) > 0]
        if validos:
            p_g, pv_g, cvu_g = validos[0]
            mc_g = pv_g - cvu_g
            pe_g = math.ceil(tcf / mc_g)
            U = list(range(0, int(pe_g * 2) + 1))
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(U, [u * pv_g for u in U],
                    color="#007A87", lw=2, label="Ingresos")
            ax.plot(U, [tcf + u * cvu_g for u in U],
                    color="#E8490F", lw=2, label="Costos Totales")
            ax.axvline(pe_g, color="#F4A261", ls="--",
                       label=f"PE = {pe_g:,} unidades")
            ax.fill_between(U,
                [u * pv_g for u in U],
                [tcf + u * cvu_g for u in U],
                where=[u * pv_g >= tcf + u * cvu_g for u in U],
                alpha=0.1, color="#007A87")
            ax.set_title(f"Punto de Equilibrio — {p_g.nombre}")
            ax.set_xlabel("Unidades / mes")
            ax.set_ylabel("$ (pesos)")
            ax.legend(); ax.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()


# =============================================================================
#  10. TIR / VPN
# =============================================================================

def pagina_tir_vpn():
    st.title("10. TIR / VPN — Evaluacion de Inversion")
    info("Evalua si el proyecto es financieramente viable.")

    tcf = total_cf()
    if not PRES:
        st.warning("No hay presentaciones creadas.")
        return

    c1, c2, c3, c4 = st.columns(4)
    inv    = c1.number_input("Inversion Inicial ($):", min_value=0.0, step=1000000.0, key="tir_inv")
    tasa_a = c2.number_input("Tasa descuento (% anual):", min_value=0.0, value=12.0, step=1.0, key="tir_tasa")
    meses  = c3.number_input("Periodos (meses):", min_value=1, value=12, step=1, key="tir_mes")
    unid   = c4.number_input("Unidades/mes:", min_value=0.0, step=10.0, key="tir_unid")

    nombres_p = [p.nombre for p in PRES]
    pres_sel  = st.selectbox("Presentacion:", nombres_p, key="tir_psel")
    p = next(x for x in PRES if x.nombre == pres_sel)

    if st.button("Calcular TIR / VPN", type="primary"):
        if inv <= 0 or unid <= 0:
            st.warning("Ingresa la inversion y unidades.")
        else:
            tasa_m = (1 + tasa_a / 100) ** (1/12) - 1
            pv_u   = p.precio_venta(MPS, IGS, tcf)
            cvu    = p.costo_variable_unit(MPS, IGS)
            fn     = unid * pv_u - unid * cvu - tcf
            flujos = [-inv] + [fn] * int(meses)

            vpn = sum(fl / (1 + tasa_m) ** t for t, fl in enumerate(flujos))
            tir = calcular_tir(flujos)
            tir_a = (1 + tir) ** 12 - 1 if tir else None

            pb = None; acc = -inv
            for i in range(1, int(meses) + 1):
                acc += fn
                if acc >= 0 and pb is None: pb = i

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Flujo Neto Mensual", f"${fn:,.1f}")
            c2.metric("VPN", f"${vpn:,.1f}",
                      delta="VIABLE" if vpn > 0 else "NO VIABLE",
                      delta_color="normal" if vpn > 0 else "inverse")
            c3.metric("TIR Anual",
                      f"{tir_a*100:.2f}%" if tir_a else "N/A")
            c4.metric("Payback",
                      f"{pb} mes(es)" if pb else f"No recupera en {meses} meses")

            if MPL:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
                colors_bar = ["#007A87" if fl >= 0 else "#E8490F" for fl in flujos]
                ax1.bar(range(len(flujos)), flujos, color=colors_bar)
                ax1.axhline(0, color="black", lw=0.8)
                ax1.set_title("Flujos por Periodo")
                ax1.grid(True, alpha=0.3)
                acc_list = []; s = 0
                for fl in flujos: s += fl; acc_list.append(s)
                ax2.plot(range(len(acc_list)), acc_list,
                         color="#F4A261", lw=2, marker="o")
                ax2.axhline(0, color="black", lw=0.8, ls="--")
                ax2.set_title("Flujo Acumulado")
                ax2.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()


# =============================================================================
#  11. FLUJO DE CAJA
# =============================================================================

def pagina_flujo_caja():
    st.title("11. Flujo de Caja Proyectado")
    tcf = total_cf()
    if not PRES:
        st.warning("No hay presentaciones creadas.")
        return

    c1, c2, c3 = st.columns(3)
    meses  = c1.number_input("Meses a proyectar:", min_value=1, value=12, step=1, key="fc_mes")
    crec   = c2.number_input("Crecimiento/mes (%):", min_value=0.0, value=0.0, step=0.5, key="fc_crec")
    saldo_i = c3.number_input("Saldo inicial ($):", min_value=0.0, value=0.0, step=100000.0, key="fc_ini")

    st.subheader("Unidades vendidas / mes por presentacion")
    v_unids = {}
    cols = st.columns(min(len(PRES), 3))
    for i, p in enumerate(PRES):
        v_unids[p.nombre] = cols[i % 3].number_input(
            p.nombre, min_value=0.0,
            value=p.cantidad_mensual, step=10.0,
            key=f"fc_u_{i}")

    if st.button("Generar Flujo de Caja", type="primary"):
        filas_fc = []
        saldo    = saldo_i
        meses_l, ing_l, fn_l, sal_l = [], [], [], []

        for mes in range(1, int(meses) + 1):
            factor = (1 + crec / 100) ** (mes - 1)
            ing = sum(
                v_unids.get(p.nombre, 0) * factor *
                p.precio_venta(MPS, IGS, tcf)
                for p in PRES)
            cv = sum(
                v_unids.get(p.nombre, 0) * factor *
                p.costo_variable_unit(MPS, IGS)
                for p in PRES)
            fn = ing - cv - tcf
            saldo += fn
            meses_l.append(mes); ing_l.append(ing)
            fn_l.append(fn); sal_l.append(saldo)
            filas_fc.append({
                "Mes":             mes,
                "Ingresos ($)":    f"${ing:,.1f}",
                "CV Total ($)":    f"${cv:,.1f}",
                "CF ($)":          f"${tcf:,.1f}",
                "Flujo Neto ($)":  f"${fn:,.1f}",
                "Saldo Acum ($)":  f"${saldo:,.1f}",
            })

        st.dataframe(filas_fc, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        c1.metric("Total Ingresos", f"${sum(ing_l):,.1f}")
        c2.metric("Total Flujo Neto", f"${sum(fn_l):,.1f}",
                  delta_color="normal" if sum(fn_l) >= 0 else "inverse")

        if MPL:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            colors_bar = ["#007A87" if f >= 0 else "#E8490F" for f in fn_l]
            ax1.bar(meses_l, fn_l, color=colors_bar)
            ax1.axhline(0, color="black", lw=0.8)
            ax1.set_title("Flujo Neto Mensual")
            ax1.grid(True, alpha=0.3)
            ax2.plot(meses_l, sal_l, color="#F4A261", lw=2, marker="o")
            ax2.axhline(0, color="black", lw=0.8, ls="--")
            ax2.fill_between(meses_l, sal_l, 0,
                             where=[s >= 0 for s in sal_l],
                             alpha=0.15, color="#007A87")
            ax2.fill_between(meses_l, sal_l, 0,
                             where=[s < 0 for s in sal_l],
                             alpha=0.15, color="#E8490F")
            ax2.set_title("Saldo Acumulado")
            ax2.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()


# =============================================================================
#  12. GRAFICAS
# =============================================================================

def pagina_graficas():
    st.title("12. Graficas y Reportes")
    tcf = total_cf()
    if not MPL:
        st.error("Instala matplotlib: pip install matplotlib")
        return
    if not PRES:
        st.warning("No hay presentaciones creadas.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Precios vs Costos",
        "Estructura Costos",
        "Margenes",
        "Costos Fijos",
        "Desglose CTU",
    ])

    with tab1:
        noms = [p.nombre for p in PRES]
        pvs  = [p.precio_venta(MPS, IGS, tcf) for p in PRES]
        ctus = [p.costo_total_unit(MPS, IGS, tcf) for p in PRES]
        cvus = [p.costo_variable_unit(MPS, IGS) for p in PRES]
        fig, ax = plt.subplots(figsize=(max(6, len(noms)*2), 5))
        x = range(len(noms))
        ax.bar([i-0.25 for i in x], pvs,  0.25, label="Precio Venta",    color="#007A87")
        ax.bar([i      for i in x], ctus, 0.25, label="Costo Total Unit.",color="#E8490F")
        ax.bar([i+0.25 for i in x], cvus, 0.25, label="Costo Variable",   color="#F4A261")
        ax.set_xticks(list(x)); ax.set_xticklabels(noms, rotation=15, ha="right")
        ax.set_title("Precio vs Costos por Presentacion")
        ax.set_ylabel("$"); ax.legend(); ax.grid(True, alpha=0.3)
        plt.tight_layout(); st.pyplot(fig); plt.close()

    with tab2:
        if not PRES:
            st.info("Sin presentaciones.")
        else:
            idx_p = st.session_state.pres_idx
            if idx_p >= len(PRES): idx_p = 0
            p = PRES[idx_p]
            etiq, vals = [], []
            for item in p.formulacion:
                gramos = (item.proporcion_pct / 100.0) * p.peso_g
                ct = gramos * p.cpg(item.nombre, MPS, IGS)
                if ct > 0: etiq.append(item.nombre); vals.append(ct)
            for g in p.otros_gastos:
                if g.costo_unit > 0: etiq.append(g.nombre); vals.append(g.costo_unit)
            if vals:
                fig, ax = plt.subplots(figsize=(7, 5))
                pal = ["#007A87","#F4A261","#E8490F","#C44A0A","#3D1F00","#888"] * 5
                ax.pie(vals, labels=etiq, autopct="%1.1f%%",
                       colors=pal[:len(vals)], startangle=90)
                ax.set_title(f"Estructura Costos — {p.nombre}")
                plt.tight_layout(); st.pyplot(fig); plt.close()
            else:
                st.info("Sin costos registrados para esta presentacion.")

    with tab3:
        mcs = [p.margen_contrib(MPS, IGS, tcf) for p in PRES]
        noms = [p.nombre for p in PRES]
        fig, ax = plt.subplots(figsize=(max(6, len(noms)*2), 5))
        ax.bar(noms, mcs,
               color=["#007A87" if m >= 0 else "#E8490F" for m in mcs])
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title("Margen de Contribucion por Presentacion")
        ax.set_ylabel("$/unidad")
        ax.set_xticklabels(noms, rotation=15, ha="right")
        ax.grid(True, alpha=0.3); plt.tight_layout()
        st.pyplot(fig); plt.close()

    with tab4:
        if not CFS:
            st.info("Sin costos fijos registrados.")
        else:
            cats = {}
            for cf in CFS:
                cats[cf.categoria] = cats.get(cf.categoria, 0) + cf.monto
            fig, ax = plt.subplots(figsize=(7, 5))
            pal = ["#007A87","#F4A261","#E8490F","#C44A0A","#3D1F00","#888"] * 4
            ax.pie(list(cats.values()), labels=list(cats.keys()),
                   autopct="%1.1f%%", colors=pal[:len(cats)], startangle=90)
            ax.set_title("Distribucion Costos Fijos Mensuales")
            plt.tight_layout(); st.pyplot(fig); plt.close()

    with tab5:
        noms = [p.nombre for p in PRES]
        cvi  = [p.costo_variable_insumos(MPS, IGS) for p in PRES]
        cog  = [p.costo_otros() for p in PRES]
        cfu  = [p.costo_fijo_unit(tcf) for p in PRES]
        fig, ax = plt.subplots(figsize=(max(6, len(noms)*2), 5))
        ax.bar(noms, cvi, label="CV Insumos",  color="#007A87")
        ax.bar(noms, cog, bottom=cvi, label="Otros Gastos", color="#F4A261")
        ax.bar(noms, cfu,
               bottom=[a+b for a,b in zip(cvi, cog)],
               label="CF Unitario", color="#E8490F")
        ax.set_title("Desglose Costo Total Unitario")
        ax.set_ylabel("$"); ax.legend()
        ax.set_xticklabels(noms, rotation=15, ha="right")
        ax.grid(True, alpha=0.3); plt.tight_layout()
        st.pyplot(fig); plt.close()


# =============================================================================
#  GENERAR PDF
# =============================================================================

def generar_pdf():
    tcf    = total_cf()
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=1.8*cm, leftMargin=1.8*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    C_NAR  = colors.HexColor("#E8490F")
    C_TURQ = colors.HexColor("#007A87")
    C_HDR  = colors.HexColor("#FFE5CC")
    C_FILA = colors.HexColor("#FFF8F2")

    st_h1 = ParagraphStyle("h1", fontSize=18, textColor=C_NAR,
                            fontName="Helvetica-Bold", spaceAfter=4)
    st_h2 = ParagraphStyle("h2", fontSize=11, textColor=C_TURQ,
                            fontName="Helvetica-Bold", spaceAfter=6)
    st_n  = ParagraphStyle("n",  fontSize=9,  fontName="Helvetica", spaceAfter=3)
    st_b  = ParagraphStyle("b",  fontSize=9,  fontName="Helvetica-Bold")
    st_ft = ParagraphStyle("ft", fontSize=7,  fontName="Helvetica",
                            textColor=colors.grey, alignment=TA_CENTER)

    def ts():
        return TableStyle([
            ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",  (0,0),(-1,-1), 8),
            ("BACKGROUND",(0,0),(-1,0), C_HDR),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_FILA, colors.white]),
            ("GRID",(0,0),(-1,-1), 0.3, colors.HexColor("#D0C8C0")),
            ("TOPPADDING",(0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("LEFTPADDING",(0,0),(-1,-1), 6),
        ])

    def sep(): return HRFlowable(width="100%", thickness=1, color=C_NAR,
                                  spaceAfter=8, spaceBefore=4)

    story = []
    story.append(Paragraph("CHOCOLATTOR", st_h1))
    story.append(Paragraph("Reporte General de Costos", st_h2))
    story.append(Paragraph(
        "Generado: " + datetime.now().strftime("%d/%m/%Y %H:%M") +
        "   |   ASOCACAO - Policarpa, Narino", st_n))
    story.append(sep())

    # 1. Materias Primas
    story.append(Paragraph("1. Materias Primas", st_h2))
    if MPS:
        d = [["Materia Prima","Batch (kg)","Rendim %","Costo/kg ($)","Costo/g ($)"]]
        for mp in MPS:
            d.append([mp.nombre, str(round(mp.batch_kg,1)),
                      str(round(mp.rendimiento,1))+"%",
                      "$"+str(round(mp.costo_por_kg(),1)),
                      "$"+str(round(mp.costo_por_gramo(),4))])
        t = Table(d, colWidths=[5*cm,2.5*cm,2.5*cm,3*cm,3*cm])
        t.setStyle(ts()); story.append(t)
    story.append(Spacer(1,8)); story.append(sep())

    # 2. Presentaciones
    story.append(Paragraph("2. Resumen de Presentaciones", st_h2))
    if PRES:
        d = [["Presentacion","Peso (g)","CV Unit ($)","CF Unit ($)",
              "Costo Total ($)","IVA %","Gan %","Precio ($)"]]
        for p in PRES:
            cvu = p.costo_variable_unit(MPS, IGS)
            cfu = p.costo_fijo_unit(tcf)
            ctu = p.costo_total_unit(MPS, IGS, tcf)
            pv  = p.precio_venta(MPS, IGS, tcf)
            d.append([p.nombre, str(int(p.peso_g)),
                      "$"+str(round(cvu,1)), "$"+str(round(cfu,1)),
                      "$"+str(round(ctu,1)),
                      str(round(p.iva_pct,1))+"%",
                      str(round(p.ganancia_pct,1))+"%",
                      "$"+str(round(pv,1))])
        t = Table(d, colWidths=[3.5*cm,1.5*cm,2*cm,2*cm,2.2*cm,1.4*cm,1.4*cm,2*cm])
        t.setStyle(ts()); story.append(t)
    story.append(Spacer(1,8)); story.append(sep())

    # 3. Formulacion
    story.append(Paragraph("3. Formulacion por Presentacion", st_h2))
    for p in PRES:
        story.append(Paragraph(p.nombre + " (" + str(int(p.peso_g)) + " g):", st_b))
        if p.formulacion:
            d = [["Ingrediente","Prop %","Cantidad (g)","$/g","Costo ($)"]]
            for item in p.formulacion:
                g   = (item.proporcion_pct/100)*p.peso_g
                cpg = p.cpg(item.nombre, MPS, IGS)
                d.append([item.nombre, str(round(item.proporcion_pct,1))+"%",
                          str(round(g,1)), "$"+str(round(cpg,4)),
                          "$"+str(round(g*cpg,4))])
            t = Table(d, colWidths=[4*cm,2*cm,2.5*cm,2.5*cm,2.5*cm])
            t.setStyle(ts()); story.append(t)
        story.append(Spacer(1,6))
    story.append(sep())

    # 4. Costos Fijos
    story.append(Paragraph("4. Costos Fijos Mensuales", st_h2))
    if CFS:
        d = [["Nombre","Categoria","Monto ($)"]]
        for cf in CFS:
            d.append([cf.nombre, cf.categoria, "$"+str(round(cf.monto,1))])
        d.append(["TOTAL","","$"+str(round(tcf,1))])
        t = Table(d, colWidths=[6*cm,4*cm,4*cm])
        sty = ts()
        sty.add("FONTNAME",(0,len(d)-1),(-1,len(d)-1),"Helvetica-Bold")
        sty.add("BACKGROUND",(0,len(d)-1),(-1,len(d)-1),C_HDR)
        t.setStyle(sty); story.append(t)
    story.append(Spacer(1,8)); story.append(sep())

    # 5. Punto de Equilibrio
    story.append(Paragraph("5. Punto de Equilibrio", st_h2))
    if PRES:
        d = [["Presentacion","Precio ($)","CV ($)","MC ($)","PE Unid","PE Ing ($)"]]
        for p in PRES:
            pv  = p.precio_venta(MPS, IGS, tcf)
            cvu = p.costo_variable_unit(MPS, IGS)
            mc  = pv - cvu
            if mc > 0:
                pe_u = math.ceil(tcf / mc)
                pi   = "$"+str(round(pe_u*pv,1))
                pu   = str(int(pe_u))
            else:
                pu = pi = "N/A"
            d.append([p.nombre,"$"+str(round(pv,1)),"$"+str(round(cvu,1)),
                      "$"+str(round(mc,1)),pu,pi])
        t = Table(d, colWidths=[3.5*cm,2*cm,2*cm,2*cm,2.5*cm,3*cm])
        t.setStyle(ts()); story.append(t)
    story.append(PageBreak())

    # 6. Flujo de Caja
    story.append(Paragraph("6. Flujo de Caja (12 meses)", st_h2))
    d = [["Mes","Ingresos ($)","CV ($)","CF ($)","Flujo Neto ($)","Saldo ($)"]]
    saldo = 0.0
    for mes in range(1, 13):
        ing = sum(p.cantidad_mensual*p.precio_venta(MPS,IGS,tcf) for p in PRES)
        cv  = sum(p.cantidad_mensual*p.costo_variable_unit(MPS,IGS) for p in PRES)
        fn  = ing - cv - tcf; saldo += fn
        d.append([str(mes),"$"+str(round(ing,1)),"$"+str(round(cv,1)),
                  "$"+str(round(tcf,1)),"$"+str(round(fn,1)),"$"+str(round(saldo,1))])
    t = Table(d, colWidths=[1.5*cm,3*cm,2.5*cm,2.5*cm,3*cm,3*cm])
    t.setStyle(ts()); story.append(t)

    # Pie
    story.append(Spacer(1,20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1,4))
    story.append(Paragraph(
        "Chocolattor v5 Web  |  ASOCACAO  |  "
        "AECID, Cooperacion Espanola y Ayuda en Accion  |  " +
        datetime.now().strftime("%d/%m/%Y %H:%M"), st_ft))

    doc.build(story)
    return buffer.getvalue()


# =============================================================================
#  ROUTER PRINCIPAL
# =============================================================================

if   pagina.startswith("1"):  pagina_materias_primas()
elif pagina.startswith("2"):  pagina_insumos_generales()
elif pagina.startswith("3"):  pagina_presentaciones()
elif pagina.startswith("4"):  pagina_formulacion()
elif pagina.startswith("5"):  pagina_costos_fijos()
elif pagina.startswith("6"):  pagina_produccion_mensual()
elif pagina.startswith("7"):  pagina_otros_gastos()
elif pagina.startswith("8"):  pagina_iva_ganancia()
elif pagina.startswith("9"):  pagina_punto_equilibrio()
elif pagina.startswith("10"): pagina_tir_vpn()
elif pagina.startswith("11"): pagina_flujo_caja()
elif pagina.startswith("12"): pagina_graficas()

pie()
