import pandas as pd
from sqlalchemy import create_engine, text
import plotly.graph_objects as go
import plotly.express as px

# variables para colores por defecto
gray_soft = "#F4F4F4"

# motor para conexión con BD
engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")

# Obtener establecimientos
def get_establishments():
    query = "SELECT DISTINCT establishment FROM fact_sale_documents ORDER BY establishment ASC;"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    return df["establishment"].to_list()

# Obtener los años que tienen al menos una transacción
def get_available_years():
    query = "SELECT DISTINCT YEAR(date_of_issue) AS sale_year FROM fact_sale_documents ORDER BY sale_year DESC;"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    return df["sale_year"].astype(str).to_list()

# Obtener el último día que registra transacciones
def get_last_day():
    query = "SELECT MAX(date_of_issue) as date_of_issue FROM fact_sale_documents"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if not df.empty and df.iloc[0]["date_of_issue"] is not None:
        return pd.to_datetime(df.iloc[0]["date_of_issue"]).strftime("%Y-%m-%d")

    return None

def get_description_products():
    query = """
        SELECT DISTINCT description 
        FROM dim_items 
        WHERE description NOT LIKE '-%' 
        AND description IS NOT NULL 
        AND description != ''
        ORDER BY description ASC
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    return df['description'].tolist()

# Gráfico de top métodos de pago
def get_graph_top_payment_methods(top_payment_methods_per_establishment: dict):
    if not top_payment_methods_per_establishment:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )
        return fig

    establishments = list(top_payment_methods_per_establishment.keys())
    all_payment_methods = set()
    for methods in top_payment_methods_per_establishment.values():
        all_payment_methods.update(methods.keys())

    payment_methods = {} 
    for method in all_payment_methods:
        payment_methods[method] = [
            top_payment_methods_per_establishment[est].get(method, 0)
            for est in establishments
        ]

    # 1. Creación de trazos con Hover Estilizado
    fig = go.Figure(data=[
        go.Bar(
            name=payment_method, 
            x=establishments, 
            y=totals, 
            text=totals,
            texttemplate="%{y:,.2f}",
            textposition='outside',
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Método: " + payment_method + "<br>" +
                "Total: S/ %{y:,.2f}" +
                "<extra></extra>"
            )
        )
        for payment_method, totals in payment_methods.items()
    ])

    fig.update_layout(
        margin=dict(l=0, r=0, t=55, b=0),
        yaxis_title="Soles (S/)",
        barmode="group",
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",  # Gris oscuro legible
            bordercolor="#E5E7EB"
        ),
        
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1, # Bajamos un poco más la leyenda para que no choque con los nombres de locales
            xanchor="center",
            x=0.5
        )
    )

    return fig

# Gráfico de top establecimientos
def get_graph_top_establishments(top_establishments: dict):
    if not top_establishments:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )

        return fig, fig

    establishments = list(top_establishments.keys())
    revenue = [top_establishments[est].get("total_revenue", 0) for est in establishments]
    quantity = [top_establishments[est].get("total_quantity", 0) for est in establishments]

    max_valor1 = max(revenue) if revenue else 0
    rango_maximo1 = max_valor1 * 1.12
    max_valor2 = max(quantity) if quantity else 0
    rango_maximo2 = max_valor2 * 1.12

    fig1 = go.Figure()

    fig1.add_trace(
        go.Bar(
            x=revenue,
            y=establishments,
            orientation="h",
            marker_color="rgb(239, 85, 59)",
            cliponaxis=False,
            textposition='outside',
            text=revenue,
            texttemplate="%{x:,.2f}",
            hovertemplate=(
                "<b>%{y}</b><br>" +
                "Ingresos: S/ %{x:,.2f}" +
                "<extra></extra>" # <-- Esto borra la cajita secundaria molesta
            )
        )
    )

    fig1.update_layout(
        margin=dict(l=0, r=0, t=55, b=25),
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white", 
            font_size=13, 
            font_family="Arial",
            font_color="#1F2937",
            bordercolor="#E5E7EB",
        )
    )
    
    fig1.update_xaxes(
        title="Soles (S/)",
        range=[0, rango_maximo1]
    )

    fig2 = go.Figure()

    fig2.add_trace(
        go.Bar(
            x=quantity,
            y=establishments,
            orientation="h",
            cliponaxis=False,
            text=quantity,
            textposition='outside',
            hovertemplate=(
                "<b>%{y}</b><br>" +
                "Vendidos: %{x} pares" +
                "<extra></extra>"
            )
        )
    )

    fig2.update_layout(
        margin=dict(l=0, r=0, t=55, b=25),
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white", 
            font_size=13, 
            font_family="Arial",
            font_color="#1F2937",
            bordercolor="#E5E7EB" # Un borde gris muy sutil
        )
    )

    fig2.update_xaxes(
        title="Pares vendidos",
        range=[0, rango_maximo2],
    )

    return fig1, fig2

# Gráfico de top de ganancias por productos
def get_graph_top_earnings_per_product(top_earnings_per_product: pd.DataFrame, top_n: int):
    if top_earnings_per_product.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )
        return fig
    
    # Agrupando las tallas para obtener el "n" top
    top_r_products = (
        top_earnings_per_product.groupby("description")["total_revenue"]
        .sum()
        .nlargest(top_n)
        .index
    )

    # Se aplica el filtro previo con el "n" top
    top_earnings_per_product = top_earnings_per_product[top_earnings_per_product["description"].isin(top_r_products)].copy()

    # 1. Inicializamos la figura de Graph Objects
    fig = go.Figure()

    # 2. Definimos tus colores corporativos
    unique_locals = top_earnings_per_product["establishment"].unique()
    palette = px.colors.qualitative.Plotly 
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}

    titulo_grafico = f"Establecimiento: {unique_locals[0]} " if len(unique_locals) == 1 else ""

    # 4. Iteramos por cada local para crear los trazos (stacks)
    for local in unique_locals:
        df_local = top_earnings_per_product[top_earnings_per_product["establishment"] == local]
        
        fig.add_trace(go.Bar(
            name=local,
            x=df_local["description"], # Nombre del producto
            y=df_local["total_revenue"], # Ingresos
            customdata=df_local["total_quantity_sold"],
            text=df_local["total_revenue"],
            texttemplate="%{y:,.2f}", 
            textposition='outside',
            cliponaxis=False,
            marker_color=color_map[local],
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Local: " + local + "<br>" +
                "Ingreso: S/ %{y:,.2f}" + "<br>" +
                "Pares vendidos: %{customdata:,.0f} pares" +
                "<extra></extra>"
            )
        ))

    # 5. Configuración del Layout y estilo
    fig.update_layout(
        title={
            'text': titulo_grafico,
            'x': 0.02,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        barmode='stack',
        xaxis={'categoryorder': 'total descending', 'title': "Producto"},
        yaxis={'title': "Ingresos (S/)"},
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1, 
            xanchor="center", 
            x=0.5
        ),
        margin=dict(l=0, r=0, t=55, b=0),
        
    )

    return fig

# Gráfico de top productos más vendidos
def get_graph_top_best_selling_products(top_best_selling_products: pd.DataFrame, top_n: int):
    if top_best_selling_products.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )
        return fig

    # Agrupando las tallas para obtener el "n" top
    top_s_products = (
        top_best_selling_products.groupby("description")["total_quantity_sold"]
        .sum()
        .nlargest(top_n)
        .index
    )

    # Se aplica el filtro previo con el "n" top
    top_best_selling_products = top_best_selling_products[top_best_selling_products["description"].isin(top_s_products)].copy()

    fig = go.Figure()

    # 1. Obtenemos los locales únicos y asignamos un color de la paleta 'Plotly' automáticamente
    unique_locals = top_best_selling_products["establishment"].unique()
    palette = px.colors.qualitative.Plotly 
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}

    
    titulo_grafico = f"Establecimiento: {unique_locals[0]} " if len(unique_locals) == 1 else ""

    # 2. Iteramos usando el mapa de colores automático
    for local in unique_locals:
        df_local = top_best_selling_products[top_best_selling_products["establishment"] == local]
        
        fig.add_trace(go.Bar(
            name=local,
            x=df_local["description"],
            y=df_local["total_quantity_sold"],
            customdata=df_local["total_revenue"],
            text=df_local["total_quantity_sold"],
            # text=[f"{int(q)} par" if q == 1 else f"{int(q)} pares" for q in df_local["total_quantity_sold"]],
            textposition='outside',
            cliponaxis=False,
            marker_color=color_map[local],
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Local: " + local + "<br>" +
                "Pares vendidos: %{y:,.0f} pares" + "<br>" +
                "Ingreso: S/ %{customdata:,.2f}" +
                "<extra></extra>"
            )
        ))

    # 3. Configuración del Layout
    fig.update_layout(
        title={
            'text': titulo_grafico,
            'x': 0.05,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        barmode='stack',
        xaxis={
            'title': "Producto",
            'categoryorder': 'array',
            'categoryarray': top_best_selling_products["description"].tolist()
        },
        yaxis={'title': "Ventas (Pares)"},
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1, 
            xanchor="center", 
            x=0.5
        ),
        autosize=True,
        margin=dict(l=0, r=0, t=55, b=0)
    )

    return fig

# Gráfico de ventas según talla de calzado
def get_graph_top_selling_sizes(df_top_selling_sizes: pd.DataFrame, top_n: int):

    if df_top_selling_sizes.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )
        return fig
    
    # Agrupando las tallas para obtener el "n" top
    if top_n != 0:
        top_sizes = (
            df_top_selling_sizes.groupby("size")["total_quantity_sold"]
            .sum()
            .nlargest(top_n)
            .index
        )

        # Se aplica el filtro previo con el "n" top
        df_top_selling_sizes = df_top_selling_sizes[df_top_selling_sizes["size"].isin(top_sizes)].copy()

    # 1. Ordenar por talla para que el eje X sea coherente
    df_top_selling_sizes = df_top_selling_sizes.sort_values(by="size")
    
    fig = go.Figure()

    # 1. Obtener los locales únicos y asignar paleta 'Plotly' automáticamente
    unique_locals = df_top_selling_sizes["establishment"].unique()
    palette = px.colors.qualitative.Plotly
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}

    titulo_grafico = f"Establecimiento: {unique_locals[0]} " if len(unique_locals) == 1 else ""

    # 4. Iterar sobre los locales
    for local in unique_locals:
        df_local = df_top_selling_sizes[df_top_selling_sizes["establishment"] == local]
        
        fig.add_trace(go.Bar(
            name=local,
            x=df_local["size"],
            y=df_local["total_quantity_sold"],
            customdata=df_local["total_revenue"],
            text=df_local["total_quantity_sold"],
            # text=[f"{int(q)} par" if q == 1 else f"{int(q)} pares" for q in df_local["total_quantity_sold"]],
            marker_color=color_map[local],
            textposition='outside',
            cliponaxis=False,
            hovertemplate=(
                "<b>Talla %{x}</b><br>" +
                "Local: " + local + "<br>" +
                "Pares vendidos: %{y:,.0f} pares" + "<br>" +
                "Ingreso: S/ %{customdata:,.2f}" +
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title={
            'text': titulo_grafico,
            'x': 0.05,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        barmode='stack',
        xaxis_type='category',
        xaxis={
            'title': "Talla",
            'categoryorder': 'array',
            'categoryarray': df_top_selling_sizes["size"].tolist()
        },
        yaxis={'title': "Ventas (Pares)"},
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1, 
            xanchor="center", 
            x=0.5
        ),
        margin=dict(l=0, r=0, t=55, b=0),
    )

    return fig

# Gráfico de tendencia de ventas de un determinado producto
def get_graph_product_sales(df_product_sales_trend: pd.DataFrame, agrupacion: str, both_establishments: bool, selected_product: bool, chart_type: str):
    if df_product_sales_trend.empty:
        texto = "No hay datos disponibles para el periodo seleccionado" if selected_product else "Seleccione un producto para cargar los datos de venta"
        fig = go.Figure()
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text=texto,
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )

        return fig
    
    df_modificable = df_product_sales_trend.copy()

    # diferencia de días
    fechas = pd.to_datetime(df_modificable['date_of_issue'])
    diferencia_dias = (fechas.max() - fechas.min()).days + 1

    # agrupación personalizada de fechas
    agp = "D" if diferencia_dias < 28 else agrupacion
    df_modificable = get_group_sales_by_period(df_modificable, agp)

    no_xaxis = False
    if df_modificable.shape[0] < 3:
        if len(df_modificable["establishment"].unique()) == 2 or df_modificable.shape[0] == 1:
            no_xaxis = True

    if both_establishments: # unir sucursales
        df_modificable = df_modificable.groupby("date_of_issue").agg({
            "total": "sum",
            "quantity": "sum"
        }).reset_index()
        
        df_modificable["establishment"] = "Consolidado (Todas)"

    # Nueva columna para fecha en string
    df_modificable["fecha_limpia"] = df_modificable["date_of_issue"].dt.strftime('%Y-%m-%d')

    # Locales únicos y asignamos un color de la paleta 'Plotly' automáticamente
    unique_locals = df_modificable["establishment"].unique()
    palette = px.colors.qualitative.Plotly
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}

    if both_establishments: # color personalizado para "Consolidado (Todas)"
        color_map["Consolidado (Todas)"] = "#1F2937"

    # Valores dinámicos según el tipo de gráfico
    fill_value = "tozeroy" if chart_type == "area" else None

    fig = go.Figure() # figura creada
    for local in unique_locals:
        df_local = df_modificable[df_modificable["establishment"] == local]

        fig.add_trace(go.Scatter(
            x=df_local["fecha_limpia"],
            y=df_local["quantity"],
            customdata=df_local["total"],
            mode="lines+markers",
            fill=fill_value,
            line=dict(width=3, color=color_map[local]),
            name=local,
            marker=dict(size=8),
            hovertemplate=(
                "<b>%{x|%d %b %Y}</b><br>" + # Fecha formateada
                "Local: " + local + "<br>" +
                "Pares vendidos: %{y:,.0f} pares<br>" +
                "Ingresos: S/ %{customdata:,.2f}" +
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title={
            'text': "",
            'x': 0.05,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        xaxis_title="Fecha",
        yaxis_title="Ingresos (S/)",
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=55, b=0)
    )

    if no_xaxis:
        fig.update_xaxes(
            type='category'
        )
    else:
        fig.update_xaxes(
            type='date',
            tickformat="%d %b\n%Y",
        )

    return fig

# Gráfico de tendencia de ventas
def get_graph_top_days_revenue(top_days_highest_revenue: pd.DataFrame, agrupacion: str, both_establishments: bool, chart_type: str):
    if top_days_highest_revenue.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )

        return fig
    
    df_modificable = top_days_highest_revenue.copy()

    # diferencia de días
    fechas = pd.to_datetime(df_modificable['date_of_issue'])
    diferencia_dias = (fechas.max() - fechas.min()).days + 1

    # agrupación personalizada de fechas
    # data_rows = df_modificable.shape[0]
    # agp = "D" if data_rows < 28 else agrupacion
    agp = "D" if diferencia_dias < 28 else agrupacion
    df_modificable = get_group_sales_by_period(df_modificable, agp)

    no_xaxis = False
    if df_modificable.shape[0] < 3:
        if len(df_modificable["establishment"].unique()) == 2 or df_modificable.shape[0] == 1:
            no_xaxis = True

    if both_establishments: # unir sucursales
        df_modificable = df_modificable.groupby("date_of_issue").agg({
            "total": "sum",
            "quantity": "sum"
        }).reset_index()
        
        df_modificable["establishment"] = "Consolidado (Todas)"

    # Nueva columna para fecha en string
    df_modificable["fecha_limpia"] = df_modificable["date_of_issue"].dt.strftime('%Y-%m-%d')

    # Locales únicos y asignamos un color de la paleta 'Plotly' automáticamente
    unique_locals = df_modificable["establishment"].unique()
    palette = px.colors.qualitative.Plotly
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}

    if both_establishments: # color personalizado para "Consolidado (Todas)"
        color_map["Consolidado (Todas)"] = "#1F2937"

    # Valores dinámicos según el tipo de gráfico
    fill_value = "tozeroy" if chart_type == "area" else None

    fig = go.Figure() # figura creada
    for local in unique_locals:
        df_local = df_modificable[df_modificable["establishment"] == local]

        fig.add_trace(go.Scatter(
            x=df_local["fecha_limpia"],
            y=df_local["total"],
            customdata=df_local["quantity"],
            mode="lines+markers",
            fill=fill_value,
            line=dict(width=3, color=color_map[local]),
            name=local,
            marker=dict(size=8),
            hovertemplate=(
                "<b>%{x|%d %b %Y}</b><br>" + # Fecha formateada
                "Local: " + local + "<br>" +
                "Ingresos: S/ %{y:,.2f}<br>" +
                "Pares vendidos: %{customdata:,.0f} pares" +
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title={
            'text': "",
            'x': 0.05,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        xaxis_title="Fecha",
        yaxis_title="Ingresos (S/)",
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=55, b=0)
    )

    if no_xaxis:
        fig.update_xaxes(
            type='category'
        )
    else:
        fig.update_xaxes(
            type='date',
            tickformat="%d %b\n%Y",
        )

    return fig

# Gráfico de venta mas alta
def get_table_highest_sale(highest_sale: pd.DataFrame):
    if highest_sale.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )

        return fig, -1, "", "", float(0)

    sale_id = highest_sale["id"].iloc[0]
    sale_date_dt = pd.to_datetime(highest_sale["date_of_issue"].iloc[0])
    sale_date = sale_date_dt.strftime('%d/%m/%Y')
    establishment = highest_sale["establishment"].iloc[0]
    total = highest_sale["total"].sum()

    highest_sale = highest_sale.drop(columns=["id", "date_of_issue", "establishment"])

    column_map = {
        "description": "Producto",
        "size": "Talla",
        "quantity": "Cantidad",
        "unit_price": "Precio Unitario",
        "total": "Subtotal"
    }

    # mapeo de nombre de columnas
    headers = [column_map.get(col.lower(), col.replace('_', ' ').title()) for col in highest_sale.columns]

    fig = go.Figure(data=[go.Table(
        # 1. ESTILO DE LOS ENCABEZADOS
        header=dict(
            values=headers,
            fill_color=gray_soft,          # Gris ligeramente más oscuro que el fondo
            align='center',
            font=dict(color='#1F2937', size=13, family="Arial", weight="bold"),
            line_color='#E5E7EB',          # Bordes suaves
            height=35
        ),
        # 2. ESTILO DE LAS CELDAS
        cells=dict(
            values=[highest_sale[col] for col in highest_sale.columns],
            fill_color='white',            # Fondo blanco limpio
            align='center',
            font=dict(color='#4B5563', size=12, family="Arial"),
            line_color='#F3F4F6',          # Bordes internos casi invisibles
            height=30
        )
    )])

    # 3. LAYOUT PARA AJUSTAR MÁRGENES
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig, sale_id, sale_date, establishment, total

# función auxiliar
def get_group_sales_by_period(df: pd.DataFrame, agrupacion: str):

    if agrupacion == 'SME':
        df['fecha_grupo'] = df['date_of_issue'].apply(
            lambda x: x.replace(day=15) if x.day <= 15 else x.replace(day=x.days_in_month)
        )
        
        # Agrupamos usando nuestra columna exacta
        df_resumen = df.groupby(['establishment', 'fecha_grupo']).agg({
            'total': 'sum',
            'quantity': 'sum'
        }).reset_index()
        
        df_resumen = df_resumen.rename(columns={'fecha_grupo': 'date_of_issue'})

    else:
        df_resumen = df.groupby([
            'establishment',
            pd.Grouper(key='date_of_issue', freq=agrupacion)
        ]).agg({
            'total': 'sum',
            'quantity': 'sum'
        }).reset_index()
    
    # Ordenamos por si acaso
    df_resumen = df_resumen.sort_values('date_of_issue')

    return df_resumen.copy()

def get_six_month_predictions(df_six_months: pd.DataFrame, both_establishments: bool, chart_type: str):
    if df_six_months.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )

        return fig
        
    if both_establishments: # unir sucursales
        df_six_months = df_six_months.groupby("date_of_issue").agg({
            "yhat": "sum",
            "yhat_lower": "sum",
            "yhat_upper": "sum"
        }).reset_index()
        
        df_six_months["establishment"] = "Consolidado (Todas)"

    # Creación de etiquetas en español
    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    df_six_months["etiqueta_mes"] = df_six_months["date_of_issue"].dt.month.map(meses_es) + " " + df_six_months["date_of_issue"].dt.year.astype(str)

    # Locales únicos y asignamos un color de la paleta 'Plotly' automáticamente
    unique_locals = df_six_months["establishment"].unique()
    palette = px.colors.qualitative.Plotly
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}
    
    if both_establishments: # color personalizado para "Consolidado (Todas)"
        color_map["Consolidado (Todas)"] = "#1F2937"

    # Valores dinámicos según el tipo de gráfico
    fill_value = "tozeroy" if chart_type == "area" else None
    mode_value = "lines" if chart_type == "area" else "lines+markers"

    fig = go.Figure()
    for local in unique_locals:
        df_local = df_six_months[df_six_months["establishment"] == local]

        fig.add_trace(go.Scatter(
            x=df_local["etiqueta_mes"],
            y=df_local["yhat"],
            customdata=df_local[["yhat_lower", "yhat_upper"]].values,
            mode=mode_value,
            fill=fill_value,
            line=dict(width=3, color=color_map[local]),
            name=local,
            marker=dict(size=8) if chart_type == "linea" else None,
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Local: " + local + "<br>" +
                "Ingresos esperados: S/ %{y:,.2f}<br>" +
                "Mínimo esperado: S/ %{customdata[0]:,.2f}<br>" +
                "Máximo esperado: S/ %{customdata[1]:,.2f}" +
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title={
            'text': "",
            'x': 0.05,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        xaxis_title="Fecha",
        yaxis_title="Ingresos esperados (S/)",
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=55, b=0)
    )

    fig.update_xaxes(
        type='category', 
        tickangle=0
    )

    return fig

def get_thirty_days_predictions(df_thirty_days: pd.DataFrame, both_establishments: bool, chart_type: str):
    if df_thirty_days.empty:
        fig = go.Figure()
        
        fig.update_layout(
            title="",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el periodo seleccionado",
                xref="paper", 
                yref="paper",
                x=0.5, 
                y=0.5, 
                showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )

        return fig
        
    if both_establishments: # unir sucursales
        df_thirty_days = df_thirty_days.groupby("date_of_issue").agg({
            "yhat": "sum",
            "yhat_lower": "sum",
            "yhat_upper": "sum"
        }).reset_index()
        
        df_thirty_days["establishment"] = "Consolidado (Todas)"

    # Creación de etiquetas en español
    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    df_thirty_days["fecha_limpia"] = df_thirty_days["date_of_issue"].dt.day.astype(str).str.zfill(2) + " " + df_thirty_days["date_of_issue"].dt.month.map(meses_es)

    # Locales únicos y asignamos un color de la paleta 'Plotly' automáticamente
    unique_locals = df_thirty_days["establishment"].unique()
    palette = px.colors.qualitative.Plotly
    color_map = {local: palette[i % len(palette)] for i, local in enumerate(unique_locals)}
    
    if both_establishments: # color personalizado para "Consolidado (Todas)"
        color_map["Consolidado (Todas)"] = "#1F2937"

    # Valores dinámicos según el tipo de gráfico
    fill_value = "tozeroy" if chart_type == "area" else None
    mode_value = "lines" if chart_type == "area" else "lines+markers"

    fig = go.Figure()
    for local in unique_locals:
        df_local = df_thirty_days[df_thirty_days["establishment"] == local]

        fig.add_trace(go.Scatter(
            x=df_local["fecha_limpia"],
            y=df_local["yhat"],
            customdata=df_local[["yhat_lower", "yhat_upper"]].values,
            mode=mode_value,
            fill=fill_value,
            line=dict(width=3, color=color_map[local]),
            name=local,
            marker=dict(size=8) if chart_type == "linea" else None,
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Local: " + local + "<br>" +
                "Ingresos esperados: S/ %{y:,.2f}<br>" +
                "Mínimo esperado: S/ %{customdata[0]:,.2f}<br>" +
                "Máximo esperado: S/ %{customdata[1]:,.2f}" +
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title={
            'text': "",
            'x': 0.05,
            'xanchor': 'left',
            'font': {
                'size': 14,
                'color': '#1F2937'
            }
        },
        xaxis_title="Fecha",
        yaxis_title="Ingresos esperados (S/)",
        plot_bgcolor=gray_soft,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_color="#1F2937",
            bordercolor="#E5E7EB"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=55, b=0)
    )

    fig.update_xaxes(
        type='category',
        nticks=8,
        tickangle=0
    )

    return fig

def get_table_inventory_predictions(df_inventory_thirty_days: pd.DataFrame, establishment_filter: str):
    """
    Genera una tabla Plotly para las predicciones de inventario.
    Filtra por establecimiento y retorna únicamente el objeto 'fig'.
    """
    
    # 1. Aplicar filtro de establecimiento
    df_filtered = df_inventory_thirty_days.copy()
    
    if establishment_filter != "Todas":
        df_filtered = df_filtered[df_filtered["establishment"] == establishment_filter]

    # 2. Manejo de DataFrame vacío (después del filtro)
    if df_filtered.empty:
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[dict(
                text="No hay datos disponibles para el establecimiento seleccionado",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="gray")
            )]
        )
        return fig

    # 3. Preparación de datos
    # Cálculo de columna Sugerido
    df_filtered["sugerido"] = df_filtered["expected_demand"] + df_filtered["safety_stock"]

    # Eliminamos columnas técnicas
    # Si filtramos por uno solo, quitamos la columna 'establishment' por redundancia
    cols_to_drop = ["prediction_date", "item_id"]
    if establishment_filter != "Todas":
        cols_to_drop.append("establishment")
    
    df_display = df_filtered.drop(columns=cols_to_drop)

    # Mapeo de nombres a español
    column_map = {
        "establishment": "Establecimiento",
        "description": "Producto",
        "size": "Talla",
        "expected_demand": "Demanda Esperada",
        "safety_stock": "Stock Seguridad",
        "sugerido": "Sugerido Total"
    }

    headers = [column_map.get(col, col.replace('_', ' ').title()) for col in df_display.columns]

    # 4. Creación de la tabla Plotly
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color='#E5E7EB',
            align='center',
            font=dict(color='#1F2937', size=13, family="Arial", weight="bold"),
            line_color='#D1D5DB',
            height=35
        ),
        cells=dict(
            values=[df_display[col] for col in df_display.columns],
            fill_color='white',
            align='center',
            font=dict(color='#4B5563', size=12, family="Arial"),
            line_color='#F3F4F6',
            height=30
        )
    )])

    # Ajustes de layout para que se integre bien en la UI
    fig.update_layout(
        autosize=True,       # Permite que Plotly calcule el tamaño automáticamente
        height=None,         # ELIMINA el número fijo (esto es vital)
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig
