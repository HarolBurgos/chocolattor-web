import streamlit as st
import json
import math
import io
import os
from datetime import datetime
import matplotlib.pyplot as plt

# Importación de clases y funciones del modelo local
from modelos import (
    MateriaPrima,
    InsumoMP,
    InsumoGeneral,
    CostoFijo,
    OtroGasto,
    ItemFormulacion,
    Presentacion,
    calcular_tir
)

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# -----------------------------------------------------------------------------
ICONO_PATH = "images/Icono.png"
page_icon = ICONO_PATH if os.path.exists(ICONO_PATH) else "🍫"

st.set_page_config(
    page_title="Chocolattor - Calculadora de Costos",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inyección de CSS personalizado para la interfaz
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #6c757d;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    .metric-card-primary { border-left-color: #0d6efd; }
    .metric-card-success { border-left-color: #198754; }
    .metric-card-warning { border-left-color: #ffc107; }
    .metric-card-danger  { border-left-color: #dc3545; }
    .metric-title {
        font-size: 0.85rem;
        color: #6c757d;
        text-transform: uppercase;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: bold;
        color: #212529;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. INICIALIZACIÓN DEL ESTADO DE SESIÓN (SESSION STATE)
# -----------------------------------------------------------------------------
if 'materias_primas' not in st.session_state:
    st.session_state.materias_primas = [
        MateriaPrima("Grano Cacao Seco", 12000.0, "kg", 80.0),
        MateriaPrima("Azúcar Orgánica", 4500.0, "kg", 100.0),
        MateriaPrima("Manteca de Cacao", 25000.0, "kg", 100.0),
        MateriaPrima("Leche en Polvo", 18000.0, "kg", 100.0),
    ]

# Asignar rendimiento si el objeto lo soporta
    for mp, rend in zip(st.session_state.materias_primas, [80.0, 100.0, 100.0, 100.0]):
        if hasattr(mp, 'rendimiento'):
            mp.rendimiento = rend

if 'insumos_generales' not in st.session_state:
    st.session_state.insumos_generales = [
        InsumoGeneral("Caja de Cartón Exportación", 1200.0, "unidad"),
        InsumoGeneral("Cinta Adhesiva", 3500.0, "rollo"),
    ]

if 'costos_fijos' not in st.session_state:
    st.session_state.costos_fijos = [
        CostoFijo("Arriendo Planta", 1500000.0),
        CostoFijo("Servicios Públicos", 450000.0),
        CostoFijo("Nómina Operativa", 2200000.0),
    ]

if 'otros_gastos' not in st.session_state:
    st.session_state.otros_gastos = [
        OtroGasto("Mantenimiento Equipos", 250000.0),
        OtroGasto("Imprevistos", 150000.0),
    ]

if 'presentaciones' not in st.session_state:
    st.session_state.presentaciones = []

# -----------------------------------------------------------------------------
# 3. FUNCIONES HELPER Y DE CÁLCULO
# -----------------------------------------------------------------------------
def fmt_cop(monto):
    """Formatea valores numéricos como pesos colombianos (COP)."""
    if monto is None:
        return "$0"
    return f"${monto:,.0f}".replace(",", ".")

def total_cf():
    """Calcula el total de costos fijos mensuales."""
    return sum(cf.monto for cf in st.session_state.costos_fijos)

def total_og():
    """Calcula el total de otros gastos."""
    return sum(og.monto for og in st.session_state.otros_gastos)

def info(texto):
    """Muestra una caja informativa estilizada."""
    st.info(texto)

# -----------------------------------------------------------------------------
# 4. VISTAS / PÁGINAS DE LA APLICACIÓN
# -----------------------------------------------------------------------------

def pagina_materias_primas():
    st.title("1. Materias Primas")
    info("Defina las materias primas base, su costo por unidad y el rendimiento en proceso.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Agregar / Editar")
        with st.form("form_mp", clear_on_submit=True):
            nombre = st.text_input("Nombre de la Materia Prima:")
            costo = st.number_input("Costo Total ($):", min_value=0.0, step=100.0)
            unidad = st.selectbox("Unidad de Medida:", ["kg", "g", "litro", "ml", "unidad"])
            rendimiento = st.number_input("Rendimiento (%):", min_value=1.0, max_value=100.0, value=100.0, step=1.0)
            submit = st.form_submit_button("Guardar Materia Prima")

            if submit and nombre:
                # Actualizar si existe, o añadir nueva
                existente = next((mp for mp in st.session_state.materias_primas if mp.nombre.lower() == nombre.lower()), None)
                if existente:
                    existente.costo = costo
                    existente.unidad = unidad
                    existente.rendimiento = rendimiento
                    st.success(f"Materia prima '{nombre}' actualizada.")
                else:
                    st.session_state.materias_primas.append(MateriaPrima(nombre, costo, unidad, rendimiento))
                    st.success(f"Materia prima '{nombre}' agregada.")

    with col2:
        st.subheader("Listado Registrado")
        if not st.session_state.materias_primas:
            st.warning("No hay materias primas registradas.")
        else:
            datos = []
            for idx, mp in enumerate(st.session_state.materias_primas):
                costo_real = mp.costo_real_unitario()
                datos.append({
                    "Índice": idx + 1,
                    "Nombre": mp.nombre,
                    "Costo Nom.": fmt_cop(mp.costo),
                    "Unidad": mp.unidad,
                    "Rend. (%)": f"{mp.rendimiento:.1f}%",
                    "Costo Real Unit.": fmt_cop(costo_real)
                })
            st.dataframe(datos, use_container_width=True)

            # Opción de eliminación
            nombres_mp = [mp.nombre for mp in st.session_state.materias_primas]
            elim = st.selectbox("Seleccione para eliminar:", ["---"] + nombres_mp)
            if st.button("Eliminar Materia Prima") and elim != "---":
                st.session_state.materias_primas = [mp for mp in st.session_state.materias_primas if mp.nombre != elim]
                st.rerun()


def pagina_insumos_generales():
    st.title("2. Insumos Generales")
    info("Registre empaques, embalajes y materiales consumibles indirectos.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Agregar Insumo")
        with st.form("form_ig", clear_on_submit=True):
            nombre = st.text_input("Nombre del Insumo:")
            costo = st.number_input("Costo Unitario ($):", min_value=0.0, step=50.0)
            unidad = st.selectbox("Unidad:", ["unidad", "rollo", "caja", "metro", "paquete"])
            submit = st.form_submit_button("Guardar Insumo")

            if submit and nombre:
                st.session_state.insumos_generales.append(InsumoGeneral(nombre, costo, unidad))
                st.success(f"Insumo '{nombre}' guardado.")

    with col2:
        st.subheader("Listado de Insumos")
        if not st.session_state.insumos_generales:
            st.warning("No hay insumos generales registrados.")
        else:
            datos = [{
                "Nombre": ig.nombre,
                "Costo Unitario": fmt_cop(ig.costo),
                "Unidad": ig.unidad
            } for ig in st.session_state.insumos_generales]
            st.dataframe(datos, use_container_width=True)

            nombres_ig = [ig.nombre for ig in st.session_state.insumos_generales]
            elim = st.selectbox("Seleccione para eliminar insumo:", ["---"] + nombres_ig)
            if st.button("Eliminar Insumo") and elim != "---":
                st.session_state.insumos_generales = [ig for ig in st.session_state.insumos_generales if ig.nombre != elim]
                st.rerun()


def pagina_costos_fijos():
    st.title("3. Costos Fijos Mensuales")
    info("Costos operativos recurrentes e independientes del volumen de producción.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Agregar Costo Fijo")
        with st.form("form_cf", clear_on_submit=True):
            nombre = st.text_input("Concepto / Nombre:")
            monto = st.number_input("Monto Mensual ($):", min_value=0.0, step=10000.0)
            submit = st.form_submit_button("Guardar Costo Fijo")

            if submit and nombre:
                st.session_state.costos_fijos.append(CostoFijo(nombre, monto))
                st.success(f"Costo fijo '{nombre}' registrado.")

    with col2:
        st.subheader("Resumen Costos Fijos")
        if not st.session_state.costos_fijos:
            st.warning("No hay costos fijos registrados.")
        else:
            datos = [{"Concepto": cf.nombre, "Monto Mensual": fmt_cop(cf.monto)} for cf in st.session_state.costos_fijos]
            st.dataframe(datos, use_container_width=True)
            st.metric("TOTAL COSTOS FIJOS", fmt_cop(total_cf()))

            nombres_cf = [cf.nombre for cf in st.session_state.costos_fijos]
            elim = st.selectbox("Seleccione para eliminar costo fijo:", ["---"] + nombres_cf)
            if st.button("Eliminar Costo Fijo") and elim != "---":
                st.session_state.costos_fijos = [cf for cf in st.session_state.costos_fijos if cf.nombre != elim]
                st.rerun()


def pagina_otros_gastos():
    st.title("4. Otros Gastos")
    info("Gastos adicionales, imprevistos o rubros eventuales.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Agregar Otro Gasto")
        with st.form("form_og", clear_on_submit=True):
            nombre = st.text_input("Concepto:")
            monto = st.number_input("Monto ($):", min_value=0.0, step=5000.0)
            submit = st.form_submit_button("Guardar Gasto")

            if submit and nombre:
                st.session_state.otros_gastos.append(OtroGasto(nombre, monto))
                st.success(f"Gasto '{nombre}' guardado.")

    with col2:
        st.subheader("Resumen de Otros Gastos")
        if not st.session_state.otros_gastos:
            st.warning("No hay otros gastos registrados.")
        else:
            datos = [{"Concepto": og.nombre, "Monto": fmt_cop(og.monto)} for og in st.session_state.otros_gastos]
            st.dataframe(datos, use_container_width=True)
            st.metric("TOTAL OTROS GASTOS", fmt_cop(total_og()))

            nombres_og = [og.nombre for og in st.session_state.otros_gastos]
            elim = st.selectbox("Seleccione para eliminar gasto:", ["---"] + nombres_og)
            if st.button("Eliminar Gasto") and elim != "---":
                st.session_state.otros_gastos = [og for og in st.session_state.otros_gastos if og.nombre != elim]
                st.rerun()


def pagina_presentaciones():
    st.title("5. Presentaciones y Formulación de Producto")
    info("Defina las recetas/formulaciones por producto final e insumos específicos asociados.")

    if not st.session_state.materias_primas:
        st.error("Primero debe registrar al menos una Materia Prima.")
        return

    st.subheader("Crear Nueva Presentación")
    nombre_p = st.text_input("Nombre del Producto / Presentación (ej. Barra 70% Cacao 80g):")
    peso_g = st.number_input("Peso Neto Total por Unidad (gramos):", min_value=1.0, value=80.0, step=5.0)
    margen_deseado = st.number_input("Margen de Ganancia Deseado (%):", min_value=0.0, max_value=500.0, value=30.0, step=5.0)

    st.markdown("---")
    st.markdown("#### Formulación (Proporción de Materias Primas)")

    items_form = []
    col_mp, col_pct = st.columns([2, 1])

    # Construcción dinámica de la formulación
    total_pct = 0.0
    for mp in st.session_state.materias_primas:
        pct = col_pct.number_input(f"% de {mp.nombre}:", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"pct_{mp.nombre}")
        if pct > 0:
            items_form.append(ItemFormulacion(mp, pct))
            total_pct += pct

    st.write(f"**Suma total de porcentaje:** `{total_pct:.1f}%`")
    if abs(total_pct - 100.0) > 0.01 and total_pct > 0:
        st.warning("Atención: La formulación no suma exactamente 100%.")

    st.markdown("---")
    st.markdown("#### Insumos Específicos de la Presentación")
    insumos_p = []
    
    if st.session_state.insumos_generales:
        st.caption("Seleccione los insumos que utiliza esta presentación:")
        for ig in st.session_state.insumos_generales:
            usar = st.checkbox(f"Usar {ig.nombre} ({fmt_cop(ig.costo)}/{ig.unidad})", key=f"ig_check_{ig.nombre}")
            if usar:
                cant = st.number_input(f"Cantidad de {ig.nombre} por unidad:", min_value=0.01, value=1.0, step=1.0, key=f"ig_cant_{ig.nombre}")
                insumos_p.append(InsumoMP(ig, cant))

    if st.button("Guardar Presentación", type="primary"):
        if not nombre_p:
            st.error("Debe ingresar un nombre para la presentación.")
        elif not items_form:
            st.error("Debe asignar al menos una materia prima con porcentaje mayor a 0.")
        else:
            nueva_p = Presentacion(nombre_p, peso_g, items_form, insumos_p, margen_deseado)
            st.session_state.presentaciones.append(nueva_p)
            st.success(f"Presentación '{nombre_p}' guardada exitosamente.")

    st.markdown("---")
    st.subheader("Presentaciones Creadas")
    if st.session_state.presentaciones:
        for p in st.session_state.presentaciones:
            with st.expander(f"📦 {p.nombre} ({p.peso_g}g) - Margen: {p.margen_deseado}%"):
                st.write(f"**Costo Variable Unitario (CVU):** {fmt_cop(p.calcular_cvu())}")
                st.write(f"**Precio Sugerido de Venta:** {fmt_cop(p.precio_sugerido())}")
                st.markdown("**Formulación:**")
                for item in p.items_formulacion:
                    st.write(f"- {item.materia_prima.nombre}: {item.porcentaje}%")
                if p.insumos:
                    st.markdown("**Insumos Específicos:**")
                    for ins in p.insumos:
                        st.write(f"- {ins.insumo.nombre}: {ins.cantidad} {ins.insumo.unidad}")

        nombres_pres = [p.nombre for p in st.session_state.presentaciones]
        elim_p = st.selectbox("Eliminar presentación:", ["---"] + nombres_pres)
        if st.button("Eliminar Presentación") and elim_p != "---":
            st.session_state.presentaciones = [p for p in st.session_state.presentaciones if p.nombre != elim_p]
            st.rerun()


def pagina_resumen_costos():
    st.title("6. Resumen General de Costos")
    info("Visualice la estructura completa de costos de la operación.")

    t_cf = total_cf()
    t_og = total_og()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Costos Fijos", fmt_cop(t_cf))
    c2.metric("Total Otros Gastos", fmt_cop(t_og))
    c3.metric("Presentaciones Configuradas", len(st.session_state.presentaciones))

    st.markdown("---")
    st.subheader("Matriz Comparativa de Productos")

    if not st.session_state.presentaciones:
        st.info("Registre presentaciones para ver el resumen detallado.")
        return

    tabla = []
    for p in st.session_state.presentaciones:
        cvu = p.calcular_cvu()
        pv = p.precio_sugerido()
        ganancia = pv - cvu
        tabla.append({
            "Presentación": p.nombre,
            "Peso (g)": p.peso_g,
            "CVU ($)": fmt_cop(cvu),
            "Margen (%)": f"{p.margen_deseado}%",
            "Precio Sugerido ($)": fmt_cop(pv),
            "Ganancia Unit. ($)": fmt_cop(ganancia)
        })

    st.dataframe(tabla, use_container_width=True)


def pagina_simulador_precios():
    st.title("7. Simulador de Precios y Márgenes")
    info("Evalúe el impacto de modificar el precio de venta final sobre la rentabilidad.")

    if not st.session_state.presentaciones:
        st.warning("Debe registrar al menos una presentación.")
        return

    nombres_p = [p.nombre for p in st.session_state.presentaciones]
    pres_sel = st.selectbox("Seleccione Presentación a Simular:", nombres_p)
    p = next((x for x in st.session_state.presentaciones if x.nombre == pres_sel), None)

    if p:
        cvu = p.calcular_cvu()
        pv_sugerido = p.precio_sugerido()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Costo Variable Unitario (CVU):** `{fmt_cop(cvu)}`")
            st.markdown(f"**Precio Sugerido ({p.margen_deseado}%):** `{fmt_cop(pv_sugerido)}`")
            pv_simulado = st.number_input("Precio de Venta Simulado ($):", min_value=0.0, value=pv_sugerido, step=500.0)

        with col2:
            if pv_simulado > 0:
                margen_real = ((pv_simulado - cvu) / pv_simulado) * 100
                utilidad_unit = pv_simulado - cvu

                st.metric("Margen Bruto Real", f"{margen_real:.2f}%")
                st.metric("Utilidad Bruta por Unidad", fmt_cop(utilidad_unit))

                if utilidad_unit < 0:
                    st.error("¡Atención! El precio simulado genera pérdidas por unidad.")
                elif margen_real < p.margen_deseado:
                    st.warning("El margen simulado es menor al margen objetivo deseado.")
                else:
                    st.success("El margen simula una operación rentable.")


def pagina_punto_equilibrio():
    st.title("8. Punto de Equilibrio")
    info("Determina la cantidad de unidades necesarias a vender para cubrir los costos fijos totales.")

    if not st.session_state.presentaciones:
        st.warning("Debe configurar al menos una presentación.")
        return

    tcf = total_cf() + total_og()
    nombres_p = [p.nombre for p in st.session_state.presentaciones]
    pres_sel = st.selectbox("Seleccione Presentación para el Cálculo:", nombres_p)
    p = next((x for x in st.session_state.presentaciones if x.nombre == pres_sel), None)

    if p:
        cvu = p.calcular_cvu()
        pv = st.number_input("Precio de Venta a Considerar ($):", min_value=0.0, value=p.precio_sugerido(), step=500.0)

        mc = pv - cvu
        st.write(f"**Margen de Contribución Unitario (MC):** {fmt_cop(mc)}")

        if mc <= 0:
            st.error("El precio de venta debe ser mayor al Costo Variable Unitario para calcular el punto de equilibrio.")
        else:
            pe_unidades = math.ceil(tcf / mc)
            pe_ventas = pe_unidades * pv

            col1, col2 = st.columns(2)
            col1.metric("Punto de Equilibrio (Unidades)", f"{pe_unidades:,} unidades".replace(",", "."))
            col2.metric("Punto de Equilibrio (Ventas Totales)", fmt_cop(pe_ventas))

            # Gráfica simple de Punto de Equilibrio
            fig, ax = plt.subplots(figsize=(8, 4))
            unidades_x = [0, pe_unidades * 2]
            costos_fijos_y = [tcf, tcf]
            costos_totales_y = [tcf, tcf + (cvu * pe_unidades * 2)]
            ventas_totales_y = [0, pv * pe_unidades * 2]

            ax.plot(unidades_x, costos_fijos_y, label="Costos Fijos", color="red", linestyle="--")
            ax.plot(unidades_x, costos_totales_y, label="Costos Totales", color="orange")
            ax.plot(unidades_x, ventas_totales_y, label="Ventas Totales", color="green")
            ax.axvline(x=pe_unidades, color="blue", linestyle=":", label=f"Equilibrio: {pe_unidades} unid.")

            ax.set_xlabel("Unidades")
            ax.set_ylabel("Valor ($ COP)")
            ax.set_title("Gráfico de Punto de Equilibrio")
            ax.legend()
            ax.grid(True, alpha=0.3)

            st.pyplot(fig)
            plt.close(fig)


def pagina_flujo_caja():
    st.title("9. Proyección de Flujo de Caja")
    info("Proyección estimada de ingresos, egresos y flujo neto mensual.")

    if not st.session_state.presentaciones:
        st.warning("Registre presentaciones para proyectar el flujo de caja.")
        return

    nombres_p = [p.nombre for p in st.session_state.presentaciones]
    pres_sel = st.selectbox("Seleccione Presentación Principal:", nombres_p, key="fc_pres")
    p = next((x for x in st.session_state.presentaciones if x.nombre == pres_sel), None)

    if p:
        col1, col2, col3 = st.columns(3)
        ventas_mes = col1.number_input("Unidades proyectadas por mes:", min_value=0, value=1000, step=100)
        pv = col2.number_input("Precio Venta ($):", min_value=0.0, value=p.precio_sugerido(), step=500.0)
        meses = col3.number_input("Horizonte (Meses):", min_value=1, max_value=36, value=12)

        cvu = p.calcular_cvu()
        tcf = total_cf() + total_og()

        ingresos_m = ventas_mes * pv
        egresos_v_m = ventas_mes * cvu
        egresos_t_m = egresos_v_m + tcf
        flujo_neto_m = ingresos_m - egresos_t_m

        st.markdown("### Resumen Proyectado Mensual")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingresos / Mes", fmt_cop(ingresos_m))
        c2.metric("Egresos Var. / Mes", fmt_cop(egresos_v_m))
        c3.metric("Egresos Fijos / Mes", fmt_cop(tcf))
        c4.metric("Flujo Neto / Mes", fmt_cop(flujo_neto_m))

        # Tabla acumulada
        proyeccion = []
        acumulado = 0.0
        for m in range(1, meses + 1):
            acumulado += flujo_neto_m
            proyeccion.append({
                "Mes": f"Mes {m}",
                "Ingresos": fmt_cop(ingresos_m),
                "Egresos Totales": fmt_cop(egresos_t_m),
                "Flujo Neto": fmt_cop(flujo_neto_m),
                "Flujo Acumulado": fmt_cop(acumulado)
            })

        st.dataframe(proyeccion, use_container_width=True)


def pagina_tir_vpn():
    st.title("10. TIR / VPN — Evaluación de Inversión")
    info("Evaluación financiera del proyecto considerando inversión inicial y tasa de descuento.")

    if not st.session_state.presentaciones:
        st.warning("No hay presentaciones registradas para evaluar.")
        return

    c1, c2, c3, c4 = st.columns(4)
    inv = c1.number_input("Inversión Inicial ($):", min_value=0.0, value=10000000.0, step=1000000.0, key="tir_inv")
    tasa_a = c2.number_input("Tasa Descuento Anual (%):", min_value=0.0, value=12.0, step=1.0, key="tir_tasa")
    meses = c3.number_input("Periodos (Meses):", min_value=1, value=12, step=1, key="tir_mes")
    unid = c4.number_input("Unidades/Mes:", min_value=0, value=500, step=50, key="tir_unid")

    nombres_p = [p.nombre for p in st.session_state.presentaciones]
    pres_sel = st.selectbox("Presentación a Evaluar:", nombres_p, key="tir_psel")
    p = next((x for x in st.session_state.presentaciones if x.nombre == pres_sel), None)

    if p:
        cvu = p.calcular_cvu()
        pv = p.precio_sugerido()
        tcf = total_cf() + total_og()

        flujo_neto_mensual = (unid * (pv - cvu)) - tcf

        # Construcción de la serie de flujos (Flujo 0 = -Inversión)
        flujos = [-inv] + [flujo_neto_mensual] * meses

        tasa_m = (1 + (tasa_a / 100)) ** (1/12) - 1

        # Cálculo de VPN
        vpn = -inv
        for t in range(1, meses + 1):
            vpn += flujo_neto_mensual / ((1 + tasa_m) ** t)

        tir_m = calcular_tir(flujos)
        tir_a = ((1 + tir_m) ** 12 - 1) * 100 if tir_m is not None else None

        col_a, col_b = st.columns(2)
        col_a.metric("Valor Presente Neto (VPN)", fmt_cop(vpn))
        if tir_a is not None:
            col_b.metric("Tasa Interna de Retorno (TIR Anual)", f"{tir_a:.2f}%")
        else:
            col_b.metric("Tasa Interna de Retorno (TIR Anual)", "N/A")

        if vpn > 0:
            st.success("El proyecto es viable financieramente (VPN > 0).")
        else:
            st.error("El proyecto no alcanza la rentabilidad mínima exigida (VPN < 0).")


def pagina_exportar_importar():
    st.title("11. Exportar / Importar Datos")
    info("Respalde la información registrada en formato JSON o cargue configuraciones previas.")

    st.subheader("Exportar Datos")
    estado = {
        "materias_primas": [mp.to_dict() for mp in st.session_state.materias_primas],
        "insumos_generales": [ig.to_dict() for ig in st.session_state.insumos_generales],
        "costos_fijos": [cf.to_dict() for cf in st.session_state.costos_fijos],
        "otros_gastos": [og.to_dict() for og in st.session_state.otros_gastos],
        "presentaciones": [p.to_dict() for p in st.session_state.presentaciones],
    }

    json_str = json.dumps(estado, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 Descargar Respaldo JSON",
        data=json_str,
        file_name=f"chocolattor_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

    st.markdown("---")
    st.subheader("Importar Datos")
    archivo = st.file_uploader("Seleccione archivo JSON de respaldo:", type=["json"])

    if archivo is not None:
        try:
            datos = json.load(archivo)
            if st.button("Restaurar Datos desde Archivo", type="primary"):
                st.session_state.materias_primas = [MateriaPrima.from_dict(d) for d in datos.get("materias_primas", [])]
                st.session_state.insumos_generales = [InsumoGeneral.from_dict(d) for d in datos.get("insumos_generales", [])]
                st.session_state.costos_fijos = [CostoFijo.from_dict(d) for d in datos.get("costos_fijos", [])]
                st.session_state.otros_gastos = [OtroGasto.from_dict(d) for d in datos.get("otros_gastos", [])]

                # Reconstrucción de Presentaciones con referencias a objetos
                presentaciones_cargadas = []
                for dp in datos.get("presentaciones", []):
                    presentaciones_cargadas.append(Presentacion.from_dict(dp, st.session_state.materias_primas, st.session_state.insumos_generales))

                st.session_state.presentaciones = presentaciones_cargadas
                st.success("¡Datos restaurados con éxito!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo JSON: {e}")

# -----------------------------------------------------------------------------
# 5. NAVEGACIÓN PRINCIPAL (SIDEBAR)
# -----------------------------------------------------------------------------
def main():
    st.sidebar.title("🍫 Chocolattor")
    st.sidebar.caption("Calculadora de Costos de Chocolatería")

    paginas = {
        "1. Materias Primas": pagina_materias_primas,
        "2. Insumos Generales": pagina_insumos_generales,
        "3. Costos Fijos": pagina_costos_fijos,
        "4. Otros Gastos": pagina_otros_gastos,
        "5. Presentaciones y Receta": pagina_presentaciones,
        "6. Resumen de Costos": pagina_resumen_costos,
        "7. Simulador de Precios": pagina_simulador_precios,
        "8. Punto de Equilibrio": pagina_punto_equilibrio,
        "9. Flujo de Caja": pagina_flujo_caja,
        "10. TIR / VPN": pagina_tir_vpn,
        "11. Exportar / Importar": pagina_exportar_importar,
    }

    seleccion = st.sidebar.radio("Ir a:", list(paginas.keys()))
    
    # Ejecución de la página seleccionada
    paginas[seleccion]()

if __name__ == "__main__":
    main()
