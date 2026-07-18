import pandas as pd
import graphs_manager
import calendar
from shiny.express import ui, render, input
from shiny import ui as ui_core
from shiny import reactive
# from anthropic_client import AnthropicMCPClient
from ollama_client import LocalMCPClient
from shinywidgets import render_plotly
from sales_summary import sales_summary_by_date, sales_summary_by_period, product_analysis, data_graphs_by_date, data_graphs_for_predictions
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ui.page_opts(
    title=ui.div(
        ui.span("MAGIK", style="font-weight: 900; letter-spacing: -0.05em; color: #111827;"),
        ui.span("SHOES", style="font-weight: 300; letter-spacing: 0.2em; color: #6B7280; margin-left: 4px;"),
        ui.span("BI", style="""
            background-color: #4F46E5; 
            color: white; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 0.5em; 
            vertical-align: middle; 
            margin-left: 10px; 
            font-weight: 700;
            letter-spacing: 0.05em;
        """),
        style="display: flex; align-items: center;"
    ),
    window_title="Magik BI",
    fillable_mobile=True,
    fillable=True
)

# cliente mcp
# client = AnthropicMCPClient()
client = LocalMCPClient()

# estilos css responsive
ui.head_content(
    ui.tags.style(
        """
        @media (min-width: 768px) {
            .fila-responsiva {
                min-height: 130px;
            }
            .columna-scroll {
                height: 600px;
                overflow-y: auto;
                padding: 5px;
            }
        }

        @media (max-width: 767px) {
            .fila-responsiva, .fila-responsiva2 {
                min-height: auto !important;
                display: block !important;
            }
            
            .columna-scroll {
                height: auto !important;
                overflow-y: visible !important;
            }

            .fila-responsiva > *, .fila-responsiva2 > * {
                margin-bottom: 20px !important; 
            }

            .fila-responsiva > *:last-child, .fila-responsiva2 > *:last-child {
                margin-bottom: 0 !important;
            }
        }

        .navbar {
            position: sticky !important;
            top: 0;
            z-index: 1050;
            
            /* 1. Fondo base con transparencia para el efecto cristal */
            background-color: rgba(255, 255, 255, 0.7) !important;
            
            /* 2. El "Toque Mágico": Un gradiente de malla sutil que no necesita imágenes */
            background-image: 
                radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.07) 0px, transparent 50%), 
                radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.05) 0px, transparent 50%) !important;
            
            /* 3. Desenfoque de fondo (Efecto iOS/Apple) */
            backdrop-filter: blur(12px) saturate(180%);
            -webkit-backdrop-filter: blur(12px) saturate(180%);
            
            /* 4. Bordes y sombras ultra finas */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border-bottom: 1px solid rgba(229, 231, 235, 0.5);
            
            /* Espaciado para que respire el logo */
            padding: 0.75rem 1.5rem !important;
            transition: all 0.3s ease;
        }

        /* Ajuste opcional: para que el texto del navbar sea más nítido sobre el blur */
        .navbar-brand, .nav-link {
            text-shadow: 0 1px 1px rgba(255,255,255,0.5);
        }

        /* Esto quita el margen inferior de los contenedores de inputs */
        .form-group {
            margin-bottom: 0 !important;
        }
        """
    )
)

# título de secciones
def section_title(title: str):
    return ui.div(
        title, # El texto va directo aquí para controlar el padding
        style="""
            /* 1. Fondo y Bordes (Sin espacios entre ellos) */
            background-color: #F9FAFB; /* Un gris muy sutil (Slate 50) */
            border-top: 1px solid #E5E7EB; /* Línea superior */
            border-bottom: 1px solid #E5E7EB; /* Línea inferior */
            
            /* 2. Espaciado Interno (Padding) */
            padding: 10px 20px; 
            
            /* 3. Tipografía */
            font-size: 12px; 
            font-weight: 700; 
            color: #4B5563; /* Slate 600 */
            text-transform: uppercase; 
            letter-spacing: 0.15em;
            
            /* 4. Espaciado Externo (Márgenes) */
            margin-top: 50px;    /* Espacio antes de la sección */
            margin-bottom: 25px; /* Espacio antes de las columnas de abajo */
            
            /* 5. Ajuste de bordes para que ocupen todo el ancho si es necesario */
            margin-left: -15px;
            margin-right: -15px;
        """
    )

# ==================================================
# >>> VARIABLES REACTIVAS
# ==================================================

processed_data = reactive.Value((None, None, None, None)) # donde se guardará los resultados reactivos
dates = reactive.Value((None, None))
selected_product_memory = reactive.Value("")
processed_data_for_product = reactive.Value((None))

@reactive.effect
@reactive.event(input.period, input.establishment) # se activa con los dos 'select'
def _handle_auto_filter():
    p = input.period()
    if p not in ["dia", "rango", "mes", "ano"]:
        result = {}
        result_for_graphs = {}
        result_for_product = {}
        establishment_reactive = input.establishment()
        fecha_actual = obtener_fecha_actual()
        fecha_inicio = ""
        fecha_fin = ""    


        if p == "Hoy":
            hoy = fecha_actual.isoformat()

            result = sales_summary_by_date(hoy, input.establishment())
            result_for_graphs = data_graphs_by_date(hoy, hoy, input.establishment())
            result_for_product = product_analysis(selected_product_memory(), hoy, hoy, input.establishment())
            date_reactive = f"Hoy, {hoy}"
            fecha_inicio = hoy
            fecha_fin = hoy
        if p == "Esta semana":
            hace_7_dias = fecha_actual - timedelta(days=7)
            start_date = hace_7_dias.isoformat()
            finish_date = fecha_actual.isoformat()

            result = sales_summary_by_period(start_date, finish_date, input.establishment())
            result_for_graphs = data_graphs_by_date(start_date, finish_date, input.establishment())
            result_for_product = product_analysis(selected_product_memory(), start_date, finish_date, input.establishment())
            date_reactive = f"Esta semana, {start_date} al {finish_date}"
            fecha_inicio = start_date
            fecha_fin = finish_date
        if p == "Este mes":
            ano_actual = fecha_actual.year
            mes_actual = fecha_actual.month

            _, ultimo_dia = calendar.monthrange(ano_actual, mes_actual)

            start_date = f"{ano_actual}-{str(mes_actual).zfill(2)}-01"
            finish_date = f"{ano_actual}-{str(mes_actual).zfill(2)}-{str(ultimo_dia).zfill(2)}"

            meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

            result = sales_summary_by_period(start_date, finish_date, input.establishment())
            result_for_graphs = data_graphs_by_date(start_date, finish_date, input.establishment())
            result_for_product = product_analysis(selected_product_memory(), start_date, finish_date, input.establishment())
            date_reactive = f"Este mes, {meses[mes_actual]} {ano_actual}"
            fecha_inicio = start_date
            fecha_fin = finish_date
        if p == "Este año":
            ano_actual = fecha_actual.year

            start_date = f"{ano_actual}-01-01"
            finish_date = f"{ano_actual}-12-31"

            result = sales_summary_by_period(start_date, finish_date, input.establishment())
            result_for_graphs = data_graphs_by_date(start_date, finish_date, input.establishment())
            result_for_product = product_analysis(selected_product_memory(), start_date, finish_date, input.establishment())
            date_reactive = f"Este año, {ano_actual}"
            fecha_inicio = start_date
            fecha_fin = finish_date
        
        processed_data.set((result, result_for_graphs, date_reactive, establishment_reactive))
        dates.set((fecha_inicio, fecha_fin))
        processed_data_for_product.set((result_for_product))

@reactive.effect
@reactive.event(input.btn_filter) # solo se activa con el botón de filtrar
def _handle_manual_filter():
    p = input.period()
    if p in ["dia", "rango", "mes", "ano"]:
        with reactive.isolate():
            result = {}
            result_for_graphs = {}
            establishment_reactive = input.establishment()
            fecha_inicio = ""
            fecha_fin = ""    

            if p == "dia":
                date_dt = input.single_date()
                if not date_dt: return None, None, None
                
                date_str = date_dt.isoformat()
                result = sales_summary_by_period(date_str, date_str, input.establishment())
                result_for_graphs = data_graphs_by_date(date_str, date_str, input.establishment())
                result_for_product = product_analysis(selected_product_memory(), date_str, date_str, input.establishment())
                date_reactive = date_str
                fecha_inicio = date_str
                fecha_fin = date_str

            if p == "rango":
                range_dt = input.date_range()
                if not range_dt: return None, None, None
                
                start_str = range_dt[0].isoformat()
                finish_str = range_dt[1].isoformat()
                
                result = sales_summary_by_period(start_str, finish_str, input.establishment())
                result_for_graphs = data_graphs_by_date(start_str, finish_str, input.establishment())
                result_for_product = product_analysis(selected_product_memory(), start_str, finish_str, input.establishment())
                date_reactive = f"{start_str} al {finish_str}"
                fecha_inicio = start_str
                fecha_fin = finish_str
            
            if p == "mes":
                mes_str = input.selected_month()
                anio_str = input.selected_year_for_month()
                
                if not mes_str or not anio_str: return None, None, None
                
                mes_int = int(mes_str)
                anio_int = int(anio_str)
                
                _, ultimo_dia = calendar.monthrange(anio_int, mes_int)
                
                start_str = f"{anio_int}-{str(mes_int).zfill(2)}-01"
                finish_str = f"{anio_int}-{str(mes_int).zfill(2)}-{str(ultimo_dia).zfill(2)}"
                
                meses = {"1": "Enero", "2": "Febrero", "3": "Marzo", "4": "Abril", "5": "Mayo", "6": "Junio", "7": "Julio", "8": "Agosto", "9": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"}
                nombre_mes = meses.get(mes_str, mes_str)
                
                result = sales_summary_by_period(start_str, finish_str, establishment_reactive)
                result_for_graphs = data_graphs_by_date(start_str, finish_str, establishment_reactive)
                result_for_product = product_analysis(selected_product_memory(), start_str, finish_str, input.establishment())
                date_reactive = f"{nombre_mes} {anio_int}"
                fecha_inicio = start_str
                fecha_fin = finish_str
            
            if p == "ano":
                anio_str = input.selected_year()
                
                if not anio_str: return None, None, None
                
                start_str = f"{anio_str}-01-01"
                finish_str = f"{anio_str}-12-31"
                
                result = sales_summary_by_period(start_str, finish_str, establishment_reactive)
                result_for_graphs = data_graphs_by_date(start_str, finish_str, establishment_reactive)
                result_for_product = product_analysis(selected_product_memory(), start_str, finish_str, input.establishment())
                date_reactive = f"Año {anio_str}"
                fecha_inicio = start_str
                fecha_fin = finish_str

            processed_data.set((result, result_for_graphs, date_reactive, establishment_reactive))
            dates.set((fecha_inicio, fecha_fin))
            processed_data_for_product.set((result_for_product))

@reactive.calc
def sales_summary_data():
    return processed_data.get()

@reactive.calc
def product_analysis_data():
    return processed_data_for_product.get()

@reactive.effect
def populate_search():
    products = graphs_manager.get_description_products()
    if len(products) > 0:
        ui.update_selectize(
            "product_search",
            choices=products,
            selected="",
            server=True
        )
        ui.update_selectize(
            "product_search2",
            choices=products,
            selected="",
            server=True
        )

@reactive.Effect
@reactive.event(input.btn_clear)
def _():
    ui.update_selectize(
        "product_search",
        selected=""
    )
    selected_product_memory.set("")
    result_for_product = product_analysis(selected_product_memory(), "", "", input.establishment())
    processed_data_for_product.set((result_for_product))
    print("Memoria limpiada")

@reactive.Effect
@reactive.event(input.btn_analyze)
def set_selected_product_memory():
    value = input.product_search()
    selected_product_memory.set(value)
    fecha_inicio, fecha_fin = dates()
    result_for_product = product_analysis(selected_product_memory(), fecha_inicio, fecha_fin, input.establishment())
    processed_data_for_product.set((result_for_product))
    print(f"Producto guardado en memoria: {value}") # Debug para consola

# ==================================================
# >>> APP LAYOUT
# ==================================================

ui.nav_spacer() 

with ui.nav_panel("Tablero"):
    with ui.layout_sidebar():
        with ui.sidebar(
            width="20rem", 
            bg="#F9FAFB",
            style="border-right: 1px solid #E5E7EB; padding-top: 2rem;" # Línea divisoria elegante
        ):
            ui.div(
                "Configuración", 
                style="""
                    font-size: 11px; 
                    font-weight: 700; 
                    color: #9CA3AF; /* Gris más claro para el 'over-title' */
                    text-transform: uppercase; 
                    letter-spacing: 0.15em;
                    margin-bottom: 4px;
                """
            )
            ui.h5("Filtros", style="margin-bottom: 2rem; color: #111827; font-weight: 800; font-size: 20px;")

            # 1. Selector de Sucursal
            ui.div(
                ui_core.input_select(
                    "establishment", 
                    "Seleccionar sucursal",
                    choices=["Todas"] + graphs_manager.get_establishments()
                ),
                style="""
                    font-size: 14px; 
                    font-weight: 500; 
                    color: #4B5563;
                """
            )

            ui.hr(style="margin: 0; border-top: 1px solid #E5E7EB; opacity: 0.5;")

            # 2. Selector de Periodo con nuevas opciones
            ui.div(
                ui_core.input_select(
                    "period", 
                    "Periodo", 
                    choices={
                        "Hoy": "Hoy", 
                        "Esta semana": "Esta semana", 
                        "Este mes": "Este mes", 
                        "Este año": "Este año",
                        "dia": "📅 Día específico",
                        "rango": "🗓️ Rango personalizado",
                        "mes": "📅 Mes específico",
                        "ano": "📅 Año específico"
                    }
                ),
                style="""
                    font-size: 14px; 
                    font-weight: 500; 
                    color: #4B5563;
                """
            )
            
            # 3. Panel para FECHA ÚNICA
            ui_core.panel_conditional(
                "input.period === 'dia'",
                ui_core.div(
                    ui_core.div(
                        "Fecha de consulta", 
                        style="font-size: 12px; font-weight: 600; color: #6B7280; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.025em;"
                    ),
                    ui_core.input_date(
                        "single_date", 
                        label=None, # Quitamos el label nativo para usar nuestro div estilizado
                        language="es",
                        width="100%"
                    ),
                    style="""
                        background-color: white; 
                        padding: 16px; 
                        border: 1px solid #E5E7EB; 
                        border-radius: 12px; 
                        margin-top: 1.5rem;
                        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    """
                )
            )

            # 4. Panel para RANGO DE FECHAS
            ui_core.panel_conditional(
                "input.period === 'rango'",
                ui_core.div(
                    ui_core.div(
                        "Rango de análisis", 
                        style="font-size: 12px; font-weight: 600; color: #6B7280; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.025em;"
                    ),
                    ui_core.input_date_range(
                        "date_range", 
                        label=None, 
                        language="es", 
                        separator=" al ",
                        width="100%"
                    ),
                    style="""
                        background-color: white; 
                        padding: 16px; 
                        border: 1px solid #E5E7EB; 
                        border-radius: 12px; 
                        margin-top: 1.5rem;
                        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    """
                )
            )

            # 5. Panel para MES ESPECÍFICO
            ui_core.panel_conditional(
                "input.period === 'mes'",
                ui_core.div(
                    ui_core.div(
                        "Análisis Mensual", 
                        style="font-size: 12px; font-weight: 600; color: #6B7280; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.025em;"
                    ),
                    ui_core.input_select(
                        "selected_month", 
                        "Mes", 
                        choices={
                            "1": "Enero", "2": "Febrero", "3": "Marzo", "4": "Abril",
                            "5": "Mayo", "6": "Junio", "7": "Julio", "8": "Agosto",
                            "9": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
                        },
                        width="100%"
                    ),
                    ui.div(style="margin-top: 10px;"), # Espacio entre selects
                    ui_core.input_select(
                        "selected_year_for_month", 
                        "Año", 
                        choices=graphs_manager.get_available_years(),
                        width="100%"
                    ),
                    style="""
                        background-color: white; 
                        padding: 16px; 
                        border: 1px solid #E5E7EB; 
                        border-radius: 12px; 
                        margin-top: 1.5rem;
                        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    """
                )
            )

            # 6. Panel para AÑO ESPECÍFICO
            ui_core.panel_conditional(
                "input.period === 'ano'",
                ui_core.div(
                    ui_core.div(
                        "Análisis Anual", 
                        style="font-size: 12px; font-weight: 600; color: #6B7280; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.025em;"
                    ),
                    ui_core.input_select(
                        "selected_year", 
                        "Selecciona el año", 
                        choices=graphs_manager.get_available_years(),
                        width="100%"
                    ),
                    style="""
                        background-color: white; 
                        padding: 16px; 
                        border: 1px solid #E5E7EB; 
                        border-radius: 12px; 
                        margin-top: 1.5rem;
                        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    """
                )
            )

            # Versión de botón "Footer" si prefieres mantenerlo separado
            ui_core.panel_conditional(
                "input.period === 'dia' || input.period === 'rango' || input.period === 'mes' || input.period === 'ano'",
                ui.div(
                    ui_core.input_action_button(
                        "btn_filter", "Aplicar Filtro", 
                        class_="btn-primary btn-sm w-100",
                        style="border-radius: 6px;"
                    )
                )
            )

        @render.ui
        def header_dashboard():
            _, _, date_reactive, establishment_reactive = sales_summary_data()
            
            establishment_title = establishment_reactive if establishment_reactive != "Todas" else "Todas las sucursales"

            return ui.div(
                ui.div(
                    f"Ventas en {establishment_title}",
                    style="""
                        font-size: 26px; 
                        font-weight: 800; 
                        color: #1F2937; /* Slate 800 (Casi negro, muy elegante) */
                        line-height: 1.1;
                        letter-spacing: -0.02em; /* Título sólido y apretado */
                    """
                ),
                ui.div(
                    date_reactive,
                    style="""
                        font-size: 14px; 
                        font-weight: 500; 
                        color: #4B5563; /* Slate 600 */
                        margin-top: 5px;
                    """
                ),
                style="margin-bottom: 20px; margin-top: 10px;" 
            )

        # SECCIÓN 1: TARJETAS

        section_title("Métricas generales")
        with ui.layout_columns(col_widths=(3, 3, 3, 3), min_height="120px", class_="fila-responsiva2"): 

            @render.ui
            def value_box1():
                result, _, _, _ = sales_summary_data()
                return ui_core.card(
                    ui_core.card_header("Ingresos totales"),
                    ui_core.p(f"S/{str(result.get("total_sales", "0.00"))}", style="font-weight: 800; font-size: 2rem;")
                )
            
            @render.ui
            def value_box2():
                result, _, _, _ = sales_summary_data()
                return ui_core.card(
                    ui_core.card_header("Ticket promedio"),
                    ui_core.p(f"S/{str(result.get("average_ticket", "0.00"))}", style="font-weight: 800; font-size: 2rem;"),
                    style="height: 100%;"
                )
            
            @render.ui
            def value_box3():
                result, _, _, _ = sales_summary_data()
                return ui_core.card(
                    ui_core.card_header("Pares vendidos"),
                    ui_core.p(str(result.get("total_pairs_sold", "0")), style="font-weight: 800; font-size: 2rem;"),
                    style="height: 100%;"
                )
            
            @render.ui
            def value_box4():
                result, _, _, _ = sales_summary_data()
                return ui_core.card(
                    ui_core.card_header("Nro. Transacciones"),
                    ui_core.p(f"{str(result.get("number_of_transactions", "Sin datos"))}", style="font-weight: 800; font-size: 2rem;"),
                    style="height: 100%;"
                )
        
        # SECCIÓN 2: OTRAS TARJETAS

        with ui.layout_columns(col_widths=(3, 9), min_height="200px", class_="fila-responsiva2"):
            
            @render.ui
            def value_box5():
                result, _, _, _ = sales_summary_data()
                best_product = result.get("best-selling_product", {})
                return ui_core.card(
                    ui_core.card_header("Producto más vendido"),
                    ui_core.p(
                        ui_core.span(
                            str(best_product.get("description", "Sin datos")), 
                            style="font-weight: 800; font-size: 2rem; display: block; color: #000000;"
                        ),
                        f"Pares vendidos: {best_product.get('total_quantity_sold', 'Sin datos')}",
                        ui.br(),
                        f"Ingresos totales: S/{best_product.get('total_revenue', '0.00')}",
                        style="line-height: 1.2; margin-bottom: 0; color: #6B7280; font-size: 14px; font-weight: 400;"
                    ),
                    style="height: 100%;"
                )
            
            with ui.card(full_screen=True):
                ui.card_header("Venta más alta")
                @render.ui
                def value_box6():
                    _, result_for_graphs, _, _ = sales_summary_data()
                    _, sale_id, sale_date, establishment, total = graphs_manager.get_table_highest_sale(result_for_graphs.get("highest_sale", pd.DataFrame))
                    if sale_id != -1:
                        return ui_core.div(
                            ui_core.span("ID: ", style="color: #6B7280; font-size: 14px; font-weight: 400;"),
                            ui_core.span(f" {sale_id}", style="color: #1F2937; font-size: 14px; font-weight: bold; margin-left: 8px; margin-right: 25px;"),
                        
                            ui_core.span("Establecimiento: ", style="color: #6B7280; font-size: 14px; font-weight: 400;"),
                            ui_core.span(establishment, style="color: #1F2937; font-size: 14px; font-weight: bold; margin-left: 8px; margin-right: 25px;"),

                            ui_core.span("Total: ", style="color: #6B7280; font-size: 14px; font-weight: 400;"),
                            ui_core.span(f"S/ {total:,.2f}", style="color: #1F2937; font-size: 14px; font-weight: bold; margin-left: 8px; margin-right: 25px;"),
                            
                            ui_core.span("Fecha de emisión: ", style="color: #6B7280; font-size: 14px; font-weight: 400;"),
                            ui_core.span(sale_date, style="color: #1F2937; font-size: 14px; font-weight: bold; margin-left: 8px;"),
                            
                            # Estilo del contenedor principal (sin fondo ni bordes)
                            style="""
                                display: flex; 
                                justify-content: center; 
                                align-items: center; 
                                padding: 15px 0px 0px; 
                                width: 100%;
                            """
                        )
                    else:
                        return ui_core.div()
                @render_plotly
                def table1():
                    _, result_for_graphs, _, _ = sales_summary_data()
                    table, _, _, _, _ = graphs_manager.get_table_highest_sale(result_for_graphs.get("highest_sale", pd.DataFrame))
                    return table

        # SECCIÓN 3: GRÁFICOS

        section_title("Establecimientos")
        with ui.layout_columns(col_widths=(7, 5), min_height="600px", class_="fila-responsiva2"):

            with ui.div(class_="columna-scroll"):
                
                with ui.card(full_screen=True, max_height="250px"):
                    ui.card_header("Rendimiento por ingresos")
                    @render_plotly
                    def bar1():
                        result, _, _, _ = sales_summary_data()
                        graph1, _ = graphs_manager.get_graph_top_establishments(result.get("top_establishments", {}))
                        return graph1

                with ui.card(full_screen=True, max_height="250px"):
                    ui.card_header("Rendimiento por pares vendidos")
                    @render_plotly
                    def bar2():
                        result, _, _, _ = sales_summary_data()
                        _, graph2 = graphs_manager.get_graph_top_establishments(result.get("top_establishments", {}))
                        return graph2
                    
            with ui.card(full_screen=True):
                ui.card_header("Top métodos de pago")
                @render_plotly
                def bar3():
                    _, result_for_graphs, _, _ = sales_summary_data()
                    return graphs_manager.get_graph_top_payment_methods(result_for_graphs.get("top_payment_methods_per_establishment", {}))

        # SECCIÓN 5: GRÁFICOS

        section_title("Ventas")
        with ui.layout_columns(col_widths=(12), min_height="650px", class_="fila-responsiva2"):

            with ui.card(full_screen=True, gap="5px"):
                ui.card_header("Tendencia de ventas")

                with ui.card_body(gap="0px"):

                    with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                        ui_core.input_select(
                            "chart_type",
                            ui_core.span(
                                "Tipo de gráfico:",
                                style="color: #6B7280; font-size: 14px; font-weight: 400;"
                            ),
                            choices={
                                "area": "Gráfico de áreas", 
                                "linea": "Gráfico de líneas"
                            },
                            width="fit-content"
                        )

                        @render.ui
                        def ui_dinamico_both_establishments():
                            _, result_for_graphs, _, _ = sales_summary_data()
                            df = result_for_graphs.get("top_days_highest_revenue", pd.DataFrame())
                            
                            if not df.empty:
                                # both_establishment = len(df["establishment"].unique()) > 1
                                both_establishment = True
                                if input.establishment() != "Todas":
                                    both_establishment = False
                                
                                # Solo retornamos el input si hay 28 días o más
                                if both_establishment:
                                    return ui_core.input_checkbox(
                                        "both_establishments",
                                        ui_core.span(
                                            "Unir sucursales", 
                                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                                        ),
                                        value=False,
                                        width="fit-content"
                                    )

                            return None
                        


                        @render.ui
                        def ui_dinamico_periodo_agrupacion():
                            _, result_for_graphs, _, _ = sales_summary_data()
                            df = result_for_graphs.get("top_days_highest_revenue", pd.DataFrame())
                            
                            if not df.empty:
                                fechas = pd.to_datetime(df['date_of_issue'])
                                diferencia_dias = (fechas.max() - fechas.min()).days + 1
                                
                                # Solo retornamos el input si hay 28 días o más
                                if 28 <= diferencia_dias < 365:
                                    return ui_core.input_select(
                                        "periodo_agrupacion",
                                        ui_core.span(
                                            "Agrupación:",
                                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                                        ),
                                        choices={"W-MON": "Por semana", "SME": "Por quincena", "D": "Diario"},
                                        width="fit-content"
                                    )
                                if diferencia_dias in {365, 366}:
                                    return ui_core.input_select(
                                        "periodo_agrupacion",
                                        ui_core.span(
                                            "Agrupación:",
                                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                                        ),
                                        choices={"W-MON": "Por semana", "SME": "Por quincena", "ME": "Por mes", "D": "Diario"},
                                        width="fit-content"
                                    )
                        
                            return None

                    @render_plotly
                    def bar4():
                        agrupacion = "D"
                        both_establishments_bool = False
                        try:
                            if hasattr(input, "periodo_agrupacion"):
                                agrupacion = input.periodo_agrupacion()
                        except Exception:
                            pass 
                        try:
                            if hasattr(input, "both_establishments"):
                                both_establishments_bool = input.both_establishments()
                        except Exception:
                            pass 

                        _, result_for_graphs, _, establishment_reactive = sales_summary_data()
                        both_establishments = both_establishments_bool if establishment_reactive == "Todas" else False
                        chart_type = input.chart_type()
                        df = result_for_graphs.get("top_days_highest_revenue", pd.DataFrame())
                        
                        return graphs_manager.get_graph_top_days_revenue(
                            df,
                            agrupacion,
                            both_establishments,
                            chart_type
                        )

        # SECCIÓN 4: GRÁFICOS

        section_title("Productos y tallas")
        with ui.layout_columns(col_widths=(6, 6), min_height="500px", class_="fila-responsiva2"):

            with ui.card(full_screen=True):
                ui.card_header("Top ingresos por productos")

                with ui.card_body(gap="0px"):
                    
                    with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                        ui_core.input_select(
                            "top_r_products",
                            ui_core.span(
                                "Listar:",
                                style="color: #6B7280; font-size: 14px; font-weight: 400;"
                            ),
                            choices={"5": "5 primeros", "10": "10 primeros", "15": "15 primeros", "20": "20 primeros"},
                            width="fit-content"
                        )

                    @render_plotly
                    def bar5():
                        _, result_for_graphs, _, _ = sales_summary_data()
                        df = result_for_graphs.get("top_earnings_per_product", pd.DataFrame)
                        limit_selected = int(input.top_r_products())
                        return graphs_manager.get_graph_top_earnings_per_product(df, limit_selected)
            
            with ui.card(full_screen=True):
                ui.card_header("Top productos más vendidos")

                with ui.card_body(gap="0px"):
                    
                    with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                        ui_core.input_select(
                            "top_s_produts",
                            ui_core.span(
                                "Listar:",
                                style="color: #6B7280; font-size: 14px; font-weight: 400;"
                            ),
                            choices={"5": "5 primeros", "10": "10 primeros", "15": "15 primeros", "20": "20 primeros"},
                            width="fit-content"
                        )

                    @render_plotly
                    def bar6():
                        _, result_for_graphs, _, _ = sales_summary_data()
                        df = result_for_graphs.get("top_best_selling_products", pd.DataFrame)
                        limit_selected = int(input.top_s_produts())
                        return graphs_manager.get_graph_top_best_selling_products(df, limit_selected)
        
        with ui.layout_columns(col_widths=(6, 6), min_height="500px", class_="fila-responsiva2"):

            with ui.card(full_screen=True):
                ui.card_header("Ventas según talla de calzado")

                with ui.card_body(gap="0px"):

                    with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                        ui_core.input_select(
                            "top_n_tallas",
                            ui_core.span(
                                "Listar:",
                                style="color: #6B7280; font-size: 14px; font-weight: 400;"
                            ),
                            choices={"10": "10 primeros", "15": "15 primeros", "20": "20 primeros", "0": "Todas las tallas"},
                            width="fit-content"
                        )

                    @render_plotly
                    def bar7():
                        _, result_for_graphs, _, _ = sales_summary_data()
                        df = result_for_graphs.get("df_top_selling_sizes", pd.DataFrame)
                        limit_selected = int(input.top_n_tallas())
                        return graphs_manager.get_graph_top_selling_sizes(df, limit_selected)
            
        with ui.layout_columns(col_widths=(12), min_height="800px", class_="fila-responsiva2"):

            with ui.card(full_screen=True):
                ui.card_header("Análisis de producto")

                with ui.card_body(gap="0px"):

                    with ui.div(style="display: flex; gap: 15px; align-items: flex-end; margin-bottom: 16px"):

                        ui.input_selectize(
                            "product_search",
                            ui.span(
                                "Buscar producto:",
                                style="color: #6B7280; font-size: 14px; font-weight: 400;"
                            ),
                            choices=[""],
                            multiple=False,
                            options={
                                "placeholder": "Selecciona un producto...",
                                "allowEmptyOption": True,
                            },
                            width="400px"
                        )

                        # Botón para limpiar (Deseleccionar)
                        ui.input_action_button(
                            "btn_clear", 
                            "Limpiar", 
                            class_="btn-secondary", 
                            style="height: 40px;"
                        )

                        ui.input_action_button(
                            "btn_analyze", 
                            "Analizar Producto", 
                            class_="btn-primary", # Clase de Bootstrap para que se vea azul/profesional
                            style="height: 40px;" # Ajusta según la altura de tu selectize
                        )

                    with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                        ui_core.input_select(
                            "chart_type_2",
                            ui_core.span(
                                "Tipo de gráfico:",
                                style="color: #6B7280; font-size: 14px; font-weight: 400;"
                            ),
                            choices={
                                "area": "Gráfico de áreas", 
                                "linea": "Gráfico de líneas"
                            },
                            width="fit-content"
                        )                        

                        @render.ui
                        def ui_dinamico_both_estb_3():
                            _, result_for_graphs, _, _ = sales_summary_data()
                            df = result_for_graphs.get("top_days_highest_revenue", pd.DataFrame())
                            
                            if not df.empty:
                                # both_establishment = len(df["establishment"].unique()) > 1
                                both_establishment = True
                                if input.establishment() != "Todas":
                                    both_establishment = False
                                
                                # Solo retornamos el input si hay 28 días o más
                                if both_establishment:
                                    return ui_core.input_checkbox(
                                        "both_establishments_4",
                                        ui_core.span(
                                            "Unir sucursales", 
                                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                                        ),
                                        value=False,
                                        width="fit-content"
                                    )

                            return None

                        @render.ui
                        def ui_dinamico_periodo_agp_2():
                            _, result_for_graphs, _, _ = sales_summary_data()
                            df = result_for_graphs.get("top_days_highest_revenue", pd.DataFrame())
                            
                            if not df.empty:
                                fechas = pd.to_datetime(df['date_of_issue'])
                                diferencia_dias = (fechas.max() - fechas.min()).days + 1
                                
                                # Solo retornamos el input si hay 28 días o más
                                if 28 <= diferencia_dias < 365:
                                    return ui_core.input_select(
                                        "periodo_agrupacion_2",
                                        ui_core.span(
                                            "Agrupación:",
                                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                                        ),
                                        choices={"W-MON": "Por semana", "SME": "Por quincena", "D": "Diario"},
                                        width="fit-content"
                                    )
                                if diferencia_dias in {365, 366}:
                                    return ui_core.input_select(
                                        "periodo_agrupacion_2",
                                        ui_core.span(
                                            "Agrupación:",
                                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                                        ),
                                        choices={"W-MON": "Por semana", "SME": "Por quincena", "ME": "Por mes", "D": "Diario"},
                                        width="fit-content"
                                    )
                        
                            return None

                    @render_plotly
                    def bar8():
                        agrupacion = "D"
                        both_establishments_bool = False
                        try:
                            if hasattr(input, "periodo_agrupacion_2"):
                                agrupacion = input.periodo_agrupacion_2()
                        except Exception:
                            pass 
                        try:
                            if hasattr(input, "both_establishments_4"):
                                both_establishments_bool = input.both_establishments_4()
                        except Exception:
                            pass 

                        _, _, _, establishment_reactive = sales_summary_data()
                        result_for_product = product_analysis_data()
                        both_establishments = both_establishments_bool if establishment_reactive == "Todas" else False
                        df = result_for_product.get("product_analysis", pd.DataFrame())
                        selected_product = result_for_product.get("selected_product", True)
                        chart_type = input.chart_type_2()
                        
                        return graphs_manager.get_graph_product_sales(
                            df,
                            agrupacion,
                            both_establishments,
                            selected_product,
                            chart_type
                        )

with ui.nav_panel("Predicciones"):

    with ui.layout_columns(col_widths=(12), min_height="500px", class_="fila-responsiva2"):
        with ui.card(full_screen=True):
            ui.card_header("Próximos 30 días")

            with ui.card_body(gap="0px"):
                with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                    ui_core.input_select(
                        "chart_type_3",
                        ui_core.span(
                            "Tipo de gráfico:",
                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                        ),
                        choices={
                            "area": "Gráfico de áreas", 
                            "linea": "Gráfico de líneas"
                        },
                        width="fit-content"
                    )

                    ui_core.input_checkbox(
                        "both_establishments_2",
                        ui_core.span(
                            "Unir sucursales", 
                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                        ),
                        value=False,
                        width="fit-content"
                    )

                @render_plotly
                def bar10():
                    result_predictions = data_graphs_for_predictions()
                    chart_type = input.chart_type_3()
                    return graphs_manager.get_thirty_days_predictions(
                        result_predictions.get("df_thirty_days", pd.DataFrame),
                        input.both_establishments_2(),
                        chart_type
                    )
    
    with ui.layout_columns(col_widths=(12), min_height="500px", class_="fila-responsiva2"):
        with ui.card(full_screen=True):
            ui.card_header("Próximos 6 meses")

            with ui.card_body(gap="0px"):
                with ui.div(style="display: flex; gap: 40px; align-items: flex-start;"):

                    ui_core.input_select(
                        "chart_type_4",
                        ui_core.span(
                            "Tipo de gráfico:",
                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                        ),
                        choices={
                            "area": "Gráfico de áreas", 
                            "linea": "Gráfico de líneas"
                        },
                        width="fit-content"
                    )

                    ui_core.input_checkbox(
                        "both_establishments_3",
                        ui_core.span(
                            "Unir sucursales", 
                            style="color: #6B7280; font-size: 14px; font-weight: 400;"
                        ),
                        value=False,
                        width="fit-content"
                    )
                    
                @render_plotly
                def bar11():
                    result_predictions = data_graphs_for_predictions()
                    chart_type = input.chart_type_4()
                    return graphs_manager.get_six_month_predictions(
                        result_predictions.get("df_six_months", pd.DataFrame),
                        input.both_establishments_3(),
                        chart_type
                    )
    
    with ui.layout_columns(col_widths=(12), min_height="700px", class_="fila-responsiva2"):
        with ui.card(full_screen=True):
            ui.card_header("Inventario. Próximos 30 días")
            with ui.card_body(gap="0px"):
                ui.div(
                    ui_core.input_select(
                        id="establishment_prediction",
                        label="Establecimiento:",
                        choices=["Todas"] + graphs_manager.get_establishments(),
                        width="250px" 
                    ),
                    style="margin-bottom: 25px; padding-top: 10px;" # espacio pequeño
                )
                @render_plotly
                def bar12():
                    result_predictions = data_graphs_for_predictions()
                    return graphs_manager.get_table_inventory_predictions(result_predictions.get("df_inventory_thirty_days", pd.DataFrame), input.establishment_prediction())
            
chat = ui.Chat(id="chat") # componente "Chat"

with ui.nav_panel("Chat"):
    with ui.layout_sidebar():
        with ui.sidebar(
            width="21rem", 
            bg="#F9FAFB", 
            style="border-right: 1px solid #E5E7EB; padding: 1.5rem;"
        ): 
            # SECCIÓN: PROMPTS RÁPIDOS
            ui.div(
                "Asistente IA", 
                style="font-size: 11px; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 4px;"
            )
            ui.h5("Prompts rápidos 💨", style="margin-bottom: 1.5rem; color: #111827; font-weight: 800;")

            def prompt_card(id, label, description):
                return ui.div(
                    ui.div(description, style="font-size: 13px; color: #6B7280; margin-bottom: 10px;"),
                    ui.input_action_button(id, label, class_="btn-primary btn-sm w-100", style="border-radius: 6px;"),
                    style="background: white; border: 1px solid #E5E7EB; padding: 12px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);"
                )

            prompt_card("day_summary", "Resumir Ventas del Día", "Resumen de las ventas del último día en el que se registraron transacciones.")

            ui.div(
                ui.div(
                    "Ingresa el nombre del calzado para realizar un análisis de stock y ventas detallado.", 
                    style="font-size: 13px; color: #6B7280; margin-bottom: 10px;"
                ),

                ui.input_selectize(
                    "product_search2",
                    ui.span(),
                    choices=[""],
                    multiple=False,
                    options={
                        "placeholder": "Selecciona un producto...",
                        "allowEmptyOption": True,
                    },
                    width="400px"
                ),
                
                ui.div(style="margin-top: 10px;"), # espacio pequeño
                
                ui.input_action_button(
                    "btn_product_analysis", 
                    "Analizar Producto", 
                    class_="btn-primary btn-sm w-100", 
                    style="border-radius: 6px;"
                ),
                
                style="""
                    background: white; 
                    border: 1px solid #E5E7EB; 
                    padding: 12px; 
                    border-radius: 10px; 
                    margin-bottom: 12px; 
                    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
                """
            )

            ui.hr(style="margin: 0; border-top: 1px solid #E5E7EB; opacity: 0.6;")

            # SECCIÓN: SERVIDOR MCP
            ui.div(
                "Infraestructura", 
                style="font-size: 11px; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 4px;"
            )
            ui.h5("Servidor MCP", style="margin-bottom: 1rem; color: #111827; font-weight: 800;")

            @render.ui
            async def system_info():
                respuesta_info = await client.get_system_info()
                herramientas = [
                    ("Analizar producto 👞", "Obtiene un resumen estratégico sobre el rendimiento de un determinado producto"),
                    ("Resumen de tallas más vendidas 🩰", "Obtiene el top de las tallas más vendidas, con sus cantidades totales vendidas, establecimientos e ingresos totales."),
                    ("Resumen de ventas 💰", "Obtiene un resumen estadístico de ventas según una determinada fecha."),
                    ("Resumen de ventas por periodo 💰", "Obtiene un resumen estadístico de ventas según un determinado periodo"),
                    ("Rendimiento de establecimientos🏪", "Obtiene el top de los establecimientos con mejor desempeño mediante un análisis"),
                    ("Predicciones de ventas diarias 🔮", "Obtiene predicciones de ventas diarias (próximos 30 días)"),
                    ("Predicciones de ventas mensuales 🔮", "Obtiene predicciones de ventas mensuales (próximos 6 meses)"),
                    ("Stock de producto 👟", "Busca el stock de un calzado según su descripción"),
                    ("Alerta de stock bajo 🚨", "Obtiene un resumen histórico de los principales productos vendidos que están por agotarse (para alertas de stock bajo)"),
                    ("Predicción de inventario 🔮", "Obtiene un resumen de los productos con demanda esperada para los próximos 30 días (para predecir inventario)"),
                    ("Listar tablas del Data Mart", "Lista las tablas de hechos y la dimensión alojadas en el Data Mart")
                ]

                paneles = [
                    ui_core.accordion_panel(nombre, ui_core.p(desc, style="font-size: 12px; margin: 0;"))
                    for nombre, desc in herramientas
                ]

                return ui.div(
                    ui_core.h5("Herramientas Disponibles", style="margin-bottom: 1rem; color: #111827; font-weight: 600"),
                    ui_core.accordion(
                        *paneles,
                        id="system_info_accordion",
                        open=False,
                    ),
                    style="""
                        --bs-accordion-bg: transparent;
                        --bs-accordion-border-color: #E5E7EB;
                        --bs-accordion-btn-padding-y: 0.8rem;
                        font-size: 13px;
                    """
                )

                # return ui.div(
                #     ui_core.accordion(
                #         ui_core.accordion_panel(" Herramientas y su descripción", *[ui_core.p(r, style="font-size: 13px; margin: 2px 0;") for r in herramientas]),
                #         ui_core.accordion_panel("🛠 Herramientas", *[ui_core.p(r, style="font-size: 13px; margin: 2px 0;") for r in respuesta_info.get("tools", [])]),
                #         # ui_core.accordion_panel("📂 Recursos", *[ui_core.p(r, style="font-size: 13px; margin: 2px 0;") for r in respuesta_info.get("resources", [])]),
                #         # ui_core.accordion_panel("📝 Plantillas", *[ui_core.p(r, style="font-size: 13px; margin: 2px 0;") for r in respuesta_info.get("templates", [])]),
                #         id="system_info_accordion",
                #         open=False,
                #     ),
                #     style="""
                #         --bs-accordion-bg: transparent;
                #         --bs-accordion-border-color: #E5E7EB;
                #         --bs-accordion-btn-padding-y: 0.8rem;
                #         font-size: 14px;
                #     """
                # )
            
        chat.update_user_input(placeholder="Ingresa un mensaje...")
        with ui.div(class_="mx-auto", style="max-width: 850px; width:100%; height: 100%; display: flex; flex-direction: column"):
            chat.ui(
                messages=["Hola, soy tu asistente de **Magik Shoes**. ¿Qué datos revisamos hoy?"],
                width="100%",
                height="100%"
            )

# ==================================================
# >>> AUXILIARY FUNCTIONS
# ==================================================

@reactive.effect
def actualizar_opciones_agrupacion():
    
    periodo_seleccionado = input.period() # lo que está seleccionado en el select de ID 'period"
    
    if periodo_seleccionado == 'Este año':
        nuevas_opciones = {"W-MON": "Por semana", "SME": "Por quincena", "ME": "Por mes", "D": "Diario"}
    elif periodo_seleccionado == 'Este mes':
        nuevas_opciones = {"W-MON": "Por semana", "SME": "Por quincena", "D": "Diario"}
    else:
        return
    
    # actualizar el select
    ui.update_select(
        "periodo_agrupacion",
        choices=nuevas_opciones
    )

def obtener_fecha_actual():
    zona_peru = ZoneInfo("America/Lima")

    now_peru = datetime.now(zona_peru)

    fecha_actual = now_peru.date()

    return fecha_actual

# ==================================================
# >>> CHAT LOGIC
# ==================================================

def format_mcp_content(content):
    """Lógica para limpiar y formatear la respuesta del MCP"""
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if hasattr(block, 'text'): text_parts.append(block.text)
            elif isinstance(block, dict):
                # Manejar resultados de herramientas si vienen en la respuesta
                if block.get("type") == "tool_result": 
                    return f"**Resultado de Herramienta:**\n\n{block.get('content')}"
                text_parts.append(block.get('text', ''))
        return "".join(text_parts)
    return content

async def generate_bot_response():
    hoy_peru = obtener_fecha_actual() 
    dia_semana = datetime.now(ZoneInfo("America/Lima")).strftime('%A')

    contexto_temporal = {
        "role": "user",
        "content": (
            f"[SISTEMA] Contexto temporal: "
            f"Hoy es {dia_semana}, {hoy_peru}. "
            "Usa esta fecha como referencia absoluta para 'hoy' y cálculos de periodos."
        )
    }

    # Obtenemos el historial actual de Shiny
    history_chat = chat.messages()
    history_chat_list = list(history_chat)[-15:]
    messages_to_send = [contexto_temporal] + history_chat_list

    # --- DETECCIÓN DINÁMICA DEL CLIENTE ---
    es_ollama = client.__class__.__name__ == "LocalMCPClient"

    if es_ollama:
        # --- FLUJO PARA OLLAMA (Respuesta completa / No Stream) ---
        response = await client.chat(messages_to_send)
        if response:
            clean_response = format_mcp_content(response)
            await chat.append_message(clean_response)
            
    else:
        # --- FLUJO PARA ANTHROPIC (Streaming) ---
        async def response_generator():
            async for chunk in client.chat(messages_to_send):
                yield chunk

        await chat.append_message_stream(response_generator())

@chat.on_user_submit
async def handle_user_input(user_input: str):
    await generate_bot_response()

# ==================================================
# >>> LÓGICA DE BOTONES
# ==================================================

@reactive.Effect
@reactive.event(input.day_summary)
async def _():
    last_day = graphs_manager.get_last_day()
    await chat.append_message({"role": "user", "content": f"Genera un resumen de las ventas del último día de operaciones: {last_day}"})
    ui.notification_show("Análisis en proceso", type="message")
    await generate_bot_response()

@reactive.Effect
@reactive.event(input.btn_product_analysis)
async def _():
    product = input.product_search2()
    producto = str(product).upper().strip()

    if not producto or len(producto) < 3:
        ui.notification_show("Necesitas seleccionar un producto para continuar", type="warning")
        return
    
    await chat.append_message({"role": "user", "content": f"Analiza el producto: {producto}"})
    ui.notification_show("Análisis en proceso", type="message")
    await generate_bot_response()

# @chat.on_user_submit
# async def handle_user_input(user_input: str):
#     history_chat = chat.messages()
#     history_chat_list = list(history_chat)[-15:] # últimos 15 mensajes

#     response = await client.chat(history_chat_list)

#     if response:
#         clean_response = format_mcp_content(response)
#         await chat.append_message(clean_response)
