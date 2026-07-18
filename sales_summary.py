import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# motor de conexión
engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")

# funciones útiles
def summary_sale(sale: list[dict]):
    primera_fila = sale[0]
    total = 0
    total_cantidades = 0

    for row in sale:
        total_cantidades += row.get("quantity", 0)
        total += row.get("total", 0)

    return [{
        "id": primera_fila.get("id", ""),
        "date_of_issue": primera_fila.get("date_of_issue", ""),
        "total_quantity": total_cantidades,
        "total_revenue": total,
        "establishment": primera_fila.get("establishment", "")
    }]

def days_between(startDate: str, finishDate: str):
    fmt = "%Y-%m-%d"
    startD = datetime.strptime(startDate, fmt).date()
    finishD = datetime.strptime(finishDate, fmt).date()
    return (finishD - startD).days

def where_clause_and_date(query: str, query2: str, startDate: str, finishDate: str):
    where_clause = "" # variable auxiliar para fechas
    date = "All dates" # variable auxiliar para fecha en diccionario final
    if startDate:
        if finishDate:
            where_clause = f"AND date_of_issue BETWEEN '{startDate}' AND '{finishDate}'"
            date = f"{startDate} to {finishDate}"
        else:
            where_clause = f"AND date_of_issue >= '{startDate}'"
            date = f"from {startDate}"
    elif finishDate:
        where_clause = f"AND date_of_issue <= '{finishDate}'"
        date = f"until {finishDate}"

    return [query + where_clause, query2 + where_clause, date]

def get_sales_summary(df: pd.DataFrame, df2: pd.DataFrame):
    # venta total
    total = float(df["total"].sum())

    # producto más vendido
    df_prod_masvendido = (
        df.groupby("description", as_index=False)
        .agg(
          total_quantity_sold=("quantity", "sum"),
          total_revenue=("total", "sum")
        )
        .sort_values(
            by=["total_quantity_sold", "total_revenue"],
            ascending=[False, False]
        )
        .head(1)
    )

    prod_masvendido = df_prod_masvendido.to_dict(orient="records")[0]

    # top 5 productos más vendidos
    df_top_ganancias_productos = (
        df.groupby("description")
        .agg(
            total_quantity_sold=("quantity", "sum"),
            total_revenue=("total", "sum")
        )
        .sort_values(
            by=["total_revenue", "total_quantity_sold"],
            ascending=[False, False]
        )
        .head(3)
        .round(2)
        .to_dict(orient="split")
    )

    top_ganancias_productos = {
        "product_descriptions": df_top_ganancias_productos["index"],
        "metrics": df_top_ganancias_productos["columns"],
        "values": df_top_ganancias_productos["data"]
    }

    # cantidad de transacciones
    cant_transc = int(len(df))

    # ticket promedio
    ticket_promedio = float(df["total"].mean())
    ticket_promedio = float(Decimal(str(ticket_promedio)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)) # redondeo

    # unidades vendidas
    pares_vendidos = int(df["quantity"].sum())

    # venta más alta
    # s_venta_mas_alta = (
    #     df.groupby("id")
    #     ["total"]
    #     .sum()
    #     .sort_values(ascending=False)
    #     .head(1)
    # )

    # id de venta
    # id_venta_mas_alta = s_venta_mas_alta.index[0] 

    # venta_mas_alta = (
    #     df[df["id"] == id_venta_mas_alta]
    # )

    # resumir venta si la lista (productos vendidos en venta) es mayor a tres
    # if len(venta_mas_alta) > 3:
    #     venta_mas_alta = venta_mas_alta.to_dict(orient="records")
    #     dict_venta_mas_alta = summary_sale(dict_venta_mas_alta)
    # else:
    #     venta_mas_alta = venta_mas_alta.to_dict(orient="split")
    #     dict_venta_mas_alta = {
    #         "columns": venta_mas_alta["columns"],
    #         "values": venta_mas_alta["data"]
    #     }

    # top establecimientos 
    top_establecimientos = (
        df.groupby("establishment")
        .agg(
            total_quantity = ("quantity", "sum"),
            total_revenue = ("total", "sum")
        )
        .sort_values(
            by=["total_revenue", "total_quantity"],
            ascending=[False, False]
        ).to_dict(orient="index")
    )

    # métodos de pago
    df2["establishment_clean"] = df2["establishment"].str.replace(" ", "_")

    grouped_payment = (
        df2.groupby(["establishment_clean", "payment_method"])["payment"]
        .sum()
        .sort_values(ascending=False)
    )

    metodos_pago = {
        f"{est}_{metodo}": valor 
        for (est, metodo), valor in grouped_payment.items()
    }

    resumen = {
        "total_sales": total, 
        "best-selling_product": prod_masvendido,
        "top_earnings_per_product": top_ganancias_productos,
        "number_of_transactions": cant_transc,
        "average_ticket": ticket_promedio,
        "total_pairs_sold": pares_vendidos,
        "top_establishments": top_establecimientos,
        "payment_methods": metodos_pago
    }
        # "highest_sale": dict_venta_mas_alta,
    
    return resumen

def get_top_sizes_for_graphs(df: pd.DataFrame, establishment: str = "", description: str = ""):
    """
    Cálculo de las tallas más vendidas
    """

    # Top tallas vendidas
    df_top_tallas_vendidas = (
        df.groupby(["size", "establishment"], as_index=False)
        .agg(
            total_quantity_sold=("quantity", "sum"),
            total_revenue=("total", "sum")
        )
        .sort_values(
            by=["total_quantity_sold", "total_revenue"],
            ascending=[False, False]
        )
        # .head(10)
    )

    return df_top_tallas_vendidas

def get_sales_summary_for_graphs(df: pd.DataFrame, df2: pd.DataFrame, startDate: str = "", finishDate: str = ""):
    
    # top 10 productos más ingresos
    # 1. Identificamos los nombres de los 10 productos con más ingresos totales
    top_10_nombres_total = (
        df.groupby("description")["total"].sum()
        .sort_values(ascending=False)
        .head(20)
        .index
    )

    # 2. Filtramos el DataFrame original para quedarnos solo con esos productos
    df_top_ganancias_productos_prev = df[df["description"].isin(top_10_nombres_total)]

    # 3. Agrupamos por descripción Y establecimiento para el desglose
    df_top_ganancias_productos = (
        df_top_ganancias_productos_prev.groupby(["description", "establishment"], as_index=False)
        .agg(
            total_quantity_sold=("quantity", "sum"),
            total_revenue=("total", "sum")
        )
        # Ordenamos para que las barras se vean bien en el gráfico
        .sort_values(by=["total_revenue"], ascending=False)
        .round(2)
    )

    # top 10 productos más vendidos
    # 1. Primero calculamos el Top 10 GLOBAL (para saber qué productos entran)
    top_10_productos_quantity = (
        df.groupby("description")["quantity"].sum()
        .sort_values(ascending=False)
        .head(20)
        .index.tolist()
    )

    # 2. Filtramos el DataFrame ORIGINAL usando esa lista
    # Se usa .copy() para evitar el aviso de "SettingWithCopyWarning"
    df_filtrado = df[df["description"].isin(top_10_productos_quantity)].copy()

    # 3. Ahora agrupamos por producto Y local sobre el set ya filtrado
    # Esto garantiza que las longitudes siempre coincidan perfectamente
    df_stack = (
        df_filtrado.groupby(["description", "establishment"], as_index=False)
        .agg(
            total_quantity_sold=("quantity", "sum"),
            total_revenue=("total", "sum")
        )
    )

    # 4. Ordenamos el resultado final para que el #1 de ventas salga primero
    # Creamos una columna temporal de 'orden' basada en nuestra lista original
    df_stack["orden"] = df_stack["description"].apply(lambda x: top_10_productos_quantity.index(x))
    df_top_productos_mas_vendidos = df_stack.sort_values("orden").drop(columns=["orden"])

    # métodos de pago
    grouped_payment = (
        df2.groupby(["establishment", "payment_method"])["payment"]
        .sum()
    )

    dict_metodos_por_establecimientos = (
        grouped_payment
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )

    # venta más alta
    s_venta_mas_alta = (
        df.groupby("id")
        ["total"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    ) # solo obtiene la venta más alta resumida en la sumatoria del total

    id_venta_mas_alta = s_venta_mas_alta.index[0] # id de venta

    venta_mas_alta = df[df["id"] == id_venta_mas_alta] # todos los detalles de la venta

    # top tallas más vendidas
    df_top_tallas_vendidas = get_top_sizes_for_graphs(df)

    # >>> top días con más ingresos
    df_dias_ingresos = df.groupby(['date_of_issue', 'establishment']).agg({
        'total': 'sum',
        'quantity': 'sum'
    }).reset_index()

    rango_fechas = pd.date_range(start=startDate, end=finishDate)

    # establecimientos
    query = "SELECT DISTINCT establishment FROM fact_sale_documents ORDER BY establishment ASC;"

    with engine.connect() as conn:
        establishments = pd.read_sql(text(query), conn)

    locales = establishments["establishment"].to_list()

    # creación de una tabla maestra con TODAS las combinaciones posibles (Producto Cartesiano)
    idx = pd.MultiIndex.from_product([rango_fechas, locales], names=['date_of_issue', 'establishment'])
    df_maestro = pd.DataFrame(index=idx).reset_index()

    # unir con las ventas reales
    df_dias_ingresos = pd.merge(df_maestro, df_dias_ingresos, on=['date_of_issue', 'establishment'], how='left')

    # rellenar 'na' con 0
    df_dias_ingresos[['total', 'quantity']] = df_dias_ingresos[['total', 'quantity']].fillna(0)

    resumen = {
        "top_earnings_per_product": df_top_ganancias_productos,
        "top_best_selling_products": df_top_productos_mas_vendidos.round(2),
        "top_payment_methods_per_establishment": dict_metodos_por_establecimientos,
        "highest_sale": venta_mas_alta,
        "df_top_selling_sizes": df_top_tallas_vendidas,
        "top_days_highest_revenue": df_dias_ingresos
    }

    return resumen

def get_product_analysis(df: pd.DataFrame, startDate: str = "", finishDate: str = ""):

    df_ventas_producto = df.groupby(['date_of_issue', 'establishment']).agg({
        'total': 'sum',
        'quantity': 'sum'
    }).reset_index()

    rango_fechas = pd.date_range(start=startDate, end=finishDate)

    # establecimientos
    query = "SELECT DISTINCT establishment FROM fact_sale_documents ORDER BY establishment ASC;"

    with engine.connect() as conn:
        establishments = pd.read_sql(text(query), conn)

    locales = establishments["establishment"].to_list()

    # creación de una tabla maestra con TODAS las combinaciones posibles (Producto Cartesiano)
    idx = pd.MultiIndex.from_product([rango_fechas, locales], names=['date_of_issue', 'establishment'])
    df_maestro = pd.DataFrame(index=idx).reset_index()

    # unir con las ventas reales
    df_ventas_producto = pd.merge(df_maestro, df_ventas_producto, on=['date_of_issue', 'establishment'], how='left')

    # rellenar 'na' con 0
    df_ventas_producto[['total', 'quantity']] = df_ventas_producto[['total', 'quantity']].fillna(0)

    resumen = {
        "product_analysis": df_ventas_producto
    }

    return resumen

# funciones para el servidor MCP

def sales_summary_by_date(date: str, establishment: str = "", include_context: bool = False):
    """
    Cálculo de estadísticas clave de ventas para una fecha específica
    """
    query = f"""
        SELECT id, description, size, quantity, unit_price, total, establishment, date_of_issue
        FROM fact_sale_documents
        WHERE date_of_issue = '{date}'
    """

    query2 = f"""
        SELECT id, establishment, payment, payment_method, date_of_issue
        FROM fact_earnings
        WHERE date_of_issue = '{date}'
    """

    if establishment and establishment != "Todas":
        # print(">>>>> SÍ HAY ESTABLECIMIENTO: ", establishment)
        query += f" AND establishment = '{establishment.strip().capitalize()}'"
        query2 += f" AND establishment = '{establishment.strip().capitalize()}'"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df2 = pd.read_sql(text(query2), conn)

    if df.empty:
        return {"mensaje": f"No se encontraron ventas para la fecha: {date}"}

    # Cálculos estadísticos
    resumen = get_sales_summary(df, df2)

    resumen = {
        "date": date,
        **resumen
    }

    if include_context:
        # fecha de hace 7 días
        dt = datetime.strptime(date, "%Y-%m-%d")
        dt_subtracted = dt - timedelta(days= 7)
        seven_days_ago = dt_subtracted.strftime("%Y-%m-%d")
        
        # estas son las descripciones de los productos que generaron más ingresos (top 3)
        products = resumen.get("top_earnings_per_product", {})
        product_descriptions = list(products.get("product_descriptions", [])) # es una lista de los nombres de los productos
        # esta es la descripción del producto con más ventas (top 1)
        product = resumen.get("best-selling_product", {})
        product_description = product.get("description", "")

        if product_description and (product_description not in product_descriptions):
            product_descriptions.insert(0, product_description)

        # query3 enriquecida con analítica estadística global
        query3 = """
        WITH ventas_diarias AS (
            -- Agrupamos las ventas por día para poder calcular la desviación estándar real sobre totales diarios
            SELECT 
                date_of_issue,
                SUM(total) as total_dia
            FROM fact_sale_documents
            WHERE date_of_issue >= CAST(:target_day AS DATE) - INTERVAL 90 DAY
            AND date_of_issue < CAST(:target_day AS DATE)
            AND WEEKDAY(date_of_issue) = WEEKDAY(CAST(:target_day AS DATE))
            GROUP BY date_of_issue
        ),
        tendencia AS (
            -- Calculamos la venta total de los últimos 7 días vs los 7 días anteriores a esos
            SELECT 
                SUM(CASE WHEN date_of_issue >= CAST(:target_day AS DATE) - INTERVAL 7 DAY THEN total ELSE 0 END) as ultimos_7_dias,
                SUM(CASE WHEN date_of_issue >= CAST(:target_day AS DATE) - INTERVAL 14 DAY AND date_of_issue < CAST(:target_day AS DATE) - INTERVAL 7 DAY THEN total ELSE 0 END) as anteriores_7_dias
            FROM fact_sale_documents
            WHERE date_of_issue >= CAST(:target_day AS DATE) - INTERVAL 14 DAY
        )
        SELECT 
            (SELECT COALESCE(SUM(yhat), 0) FROM fact_sale_predictions WHERE date_of_issue = :target_day) as venta_predicha,
            (SELECT COALESCE(SUM(total), 0) FROM fact_sale_documents WHERE date_of_issue = :seven_days_ago) as venta_hace_7_dias,
            COALESCE((SELECT AVG(total_dia) FROM ventas_diarias), 0) as promedio_historico_dia,
            COALESCE((SELECT STDDEV(total_dia) FROM ventas_diarias), 0) as desviacion_estandar_dia,
            (SELECT CASE 
                WHEN anteriores_7_dias = 0 THEN 0 
                ELSE ((ultimos_7_dias - anteriores_7_dias) / anteriores_7_dias) * 100 
            END FROM tendencia) as tendencia_semanal_pct
        """

        # query3: Obtiene los benchmarks globales (Predicción de hoy vs Real de hace 7 días)
        # query3 = """
        # SELECT 
        #     (SELECT COALESCE(SUM(yhat), 0) FROM fact_sale_predictions WHERE date_of_issue = :current_date) as venta_predicha,
        #     (SELECT COALESCE(SUM(total), 0) FROM fact_sale_documents WHERE date_of_issue = :seven_days_ago) as venta_hace_7_dias
        # """

        # query4: Inventario actual y alertas futuras para los productos estrella del día
        # query4 = """
        # SELECT 
        #     i.description,
        #     i.size as talla,
        #     i.warehouse as establecimiento,
        #     SUM(i.stock) as stock_actual,
        #     COALESCE(SUM(p.expected_demand), 0) as demanda_esperada,
        #     COALESCE(SUM(p.safety_stock), 0) as stock_seguridad
        # FROM dim_items i
        # LEFT JOIN fact_inventory_predictions p 
        #     ON i.description = p.description 
        #     AND i.size = p.size 
        #     AND i.warehouse = p.establishment
        # WHERE i.description IN :products
        # GROUP BY i.description, i.size, i.warehouse
        # """

        # query4: PUREZA DE INVENTARIO (Trae el 100% del stock real actual)
        query4 = """
        SELECT 
            description,
            size as talla,
            warehouse as establecimiento,
            SUM(stock) as stock_actual
        FROM dim_items
        WHERE description IN :products
        GROUP BY description, size, warehouse
        """

        # query5: PUREZA DE PREDICCIONES (Trae el 100% de la demanda y seguridad proyectada)
        query5 = """
        SELECT 
            description,
            size as talla,
            establishment as establecimiento,
            SUM(expected_demand) as demanda_esperada,
            SUM(safety_stock) as stock_seguridad
        FROM fact_inventory_predictions
        WHERE description IN :products
        GROUP BY description, size, establishment
        """

        # AND p.prediction_date = :current_date

        # Validación por si un día no hubo ventas y la lista viene vacía
        if not product_descriptions:
            product_descriptions = ["S/D"] 

        params_globales = {"target_day": date, "seven_days_ago": seven_days_ago}
        params_productos = {"target_day": date, "products": tuple(product_descriptions)}

        with engine.connect() as conn:
            df3 = pd.read_sql(text(query3), conn, params=params_globales)
            df4 = pd.read_sql(text(query4), conn, params=params_productos)
            df5 = pd.read_sql(text(query5), conn, params=params_productos)

        strategic_context = get_context_sales_summary(df3, df4, df5)

        resumen = {
            **resumen,
            **strategic_context
        }

    return resumen

def sales_summary_by_period(startDate: str = "", finishDate: str = "", establishment: str = "", include_context: bool = False):
    """
    Cálculo de estadísticas clave de ventas para una periodo específico
    """
    query = f"""
        SELECT id, date_of_issue, description, size, quantity, unit_price, total, establishment
        FROM fact_sale_documents
        WHERE 1=1 
    """

    query2 = f"""
        SELECT id, establishment, payment, payment_method, date_of_issue
        FROM fact_earnings 
        WHERE 1=1 
    """

    # función para agregar la cláusula 'WHERE' para fechas
    query, query2, date = where_clause_and_date(query, query2, startDate, finishDate)

    if establishment and establishment != "Todas":
        query += f" AND establishment = '{establishment.strip().capitalize()}'"
        query2 += f" AND establishment = '{establishment.strip().capitalize()}'"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df2 = pd.read_sql(text(query2), conn)

    if df.empty:
        return {"mensaje": f"No se encontraron ventas para el periodo: '{startDate}' - '{finishDate}'"}

    # Cálculos estadísticos
    resumen = get_sales_summary(df, df2)

    resumen = {
        "date": date,
        **resumen
    }

    days_btw = 0 # variable auxiliar (days between: días entre)
    rows_head = 0 # variable auxiliar (rows head: numero de filas)
    # dias con más ventas (solo si es un resumen de más de 2 días)
    if startDate and finishDate:
        days_btw = days_between(startDate, finishDate)
        if days_btw > 60:
            rows_head = 7
        elif days_btw > 28:
            rows_head = 5
        elif days_btw > 6:
            rows_head = 3
        elif days_btw > 2:
            rows_head = 1
        else:
            rows_head = 0
    else:
        days_btw, rows_head = 3, 7

    if days_btw > 2:
        df_dias_mayor_ganancia = (
            df.groupby("date_of_issue")
            .agg(
                total_quantity = ("quantity", "sum"),
                total_revenue = ("total", "sum")
            )
            .sort_values(
                by=["total_revenue", "total_quantity"],
                ascending=[False, False]
            ) # type: pandas.DataFrame
        )
        
        df_dias_mayor_ganancia.index = pd.to_datetime(df_dias_mayor_ganancia.index)
        df_dias_mayor_ganancia.index = df_dias_mayor_ganancia.index.strftime("%Y-%m-%d_%A")

        dias_mayor_ganancia = df_dias_mayor_ganancia.head(rows_head).to_dict(orient="split")

        resumen["days_most_revenue"] = {
            "date_dayname": dias_mayor_ganancia["index"],
            "metrics": dias_mayor_ganancia["columns"],
            "values": dias_mayor_ganancia["data"]
        }

    if include_context:

        # NUEVO: Si hay startDate pero no finishDate, asumimos que finishDate es hoy
        if startDate and not finishDate:
            finishDate = datetime.today().strftime('%Y-%m-%d')

        # 1. Lógica de Fechas
        tiene_fechas = bool(startDate and finishDate)
        
        # Valores por defecto en caso de no tener periodo definido
        start_actual = finish_actual = start_prev = finish_prev = start_ly = finish_ly = "1900-01-01"
        es_2023 = False

        if tiene_fechas:
            dt_start = pd.to_datetime(startDate)
            dt_finish = pd.to_datetime(finishDate)
            dias_periodo = (dt_finish - dt_start).days

            # Periodo actual (strings para SQL)
            start_actual = dt_start.strftime('%Y-%m-%d')
            finish_actual = dt_finish.strftime('%Y-%m-%d')

            # Periodo previo exacto (mismos días)
            dt_start_prev = dt_start - pd.Timedelta(days=dias_periodo + 1)
            dt_finish_prev = dt_start - pd.Timedelta(days=1)
            start_prev = dt_start_prev.strftime('%Y-%m-%d')
            finish_prev = dt_finish_prev.strftime('%Y-%m-%d')

            # Año anterior
            if dt_start.year == 2023:
                es_2023 = True # No comparamos con 2022
            else:
                dt_start_ly = dt_start - relativedelta(years=1)
                dt_finish_ly = dt_finish - relativedelta(years=1)
                start_ly = dt_start_ly.strftime('%Y-%m-%d')
                finish_ly = dt_finish_ly.strftime('%Y-%m-%d')

        # 2. Query SQL Optimizado (Alias en español)
        # Usamos condicionales para traer todo en una sola vuelta a la DB
        query3 = """
            SELECT 
                -- Periodo Previo
                SUM(CASE WHEN date_of_issue BETWEEN :start_prev AND :finish_prev THEN total ELSE 0 END) AS ventas_periodo_anterior,
                
                -- Año Anterior
                SUM(CASE WHEN date_of_issue BETWEEN :start_ly AND :finish_ly THEN total ELSE 0 END) AS ventas_ano_anterior_mismo_periodo,
                
                -- Métricas del Periodo Actual (para artículos por ticket)
                SUM(CASE WHEN date_of_issue BETWEEN :start_actual AND :finish_actual THEN quantity ELSE 0 END) AS articulos_periodo_actual,
                COUNT(DISTINCT CASE WHEN date_of_issue BETWEEN :start_actual AND :finish_actual THEN id ELSE NULL END) AS tickets_periodo_actual,
                
                -- Histórico Global
                SUM(total) AS ventas_historicas_totales,
                COUNT(DISTINCT id) AS cantidad_tickets_historicos,
                SUM(quantity) AS articulos_historicos_totales
                
            FROM fact_sale_documents
            WHERE (:est = '' OR establishment = :est)
        """

        params_globales = {
            "start_actual": start_actual, "finish_actual": finish_actual,
            "start_prev": start_prev, "finish_prev": finish_prev,
            "start_ly": start_ly, "finish_ly": finish_ly,
            "est": establishment
        }

        # estas son las descripciones de los productos que generaron más ingresos (top 3)
        products = resumen.get("top_earnings_per_product", {})
        product_descriptions = list(products.get("product_descriptions", [])) # es una lista de los nombres de los productos
        # esta es la descripción del producto con más ventas (top 1)
        product = resumen.get("best-selling_product", {})
        product_description = product.get("description", "")

        if product_description and (product_description not in product_descriptions):
            product_descriptions.insert(0, product_description)

        # query4: PUREZA DE INVENTARIO (Trae el 100% del stock real actual)
        query4 = """
        SELECT 
            description,
            size as talla,
            warehouse as establecimiento,
            SUM(stock) as stock_actual
        FROM dim_items
        WHERE description IN :products
        GROUP BY description, size, warehouse
        """

        # query5: PUREZA DE PREDICCIONES (Trae el 100% de la demanda y seguridad proyectada)
        query5 = """
        SELECT 
            description,
            size as talla,
            establishment as establecimiento,
            SUM(expected_demand) as demanda_esperada,
            SUM(safety_stock) as stock_seguridad
        FROM fact_inventory_predictions
        WHERE description IN :products
        GROUP BY description, size, establishment
        """

        # AND p.prediction_date = :current_date

        # Validación por si un día no hubo ventas y la lista viene vacía
        if not product_descriptions:
            product_descriptions = ["S/D"] 

        params_productos = {"target_day": date, "products": tuple(product_descriptions)}

        with engine.connect() as conn:
            df3 = pd.read_sql(text(query3), conn, params=params_globales)
            df4 = pd.read_sql(text(query4), conn, params=params_productos)
            df5 = pd.read_sql(text(query5), conn, params=params_productos)

        strategic_context = get_context_sales_summary_by_period(df3, df4, df5, tiene_fechas, es_2023)

        resumen = {
            **resumen,
            **strategic_context
        }

    return resumen

def top_establishments(startDate: str = "", finishDate: str = "", establishment: str = ""):
    """
    Cálculo de estadísticas del top de establecimientos con más desempeño
    """

    query = f"""
        SELECT * FROM fact_sale_documents
        WHERE 1=1 
    """
    query2 = f"""
        SELECT * FROM fact_earnings
        WHERE 1=1 
    """

    if establishment:
        query += f"AND establishment = '{establishment}'"

    # función para agregar la cláusula 'WHERE' para fechas
    query, query2, date = where_clause_and_date(query, query2, startDate, finishDate)

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df2 = pd.read_sql(text(query2), conn)

    # top ingresos y cantidades vendidas por establecimiento
    df_top_establecimientos = (
        df.groupby("establishment", as_index=False)
        .agg(
            total_quantity_sold=("quantity", "sum"),
            total_revenue=("total", "sum")
        )
    )

    df_top_establecimientos["establishment"] = df_top_establecimientos["establishment"].str.replace(" ", "_")
    dict_top_est = df_top_establecimientos.to_dict(orient="split")
    top_establecimientos = {
        "metrics": dict_top_est["columns"],
        "values": dict_top_est["data"]
    }

    establishments = list(df_top_establecimientos["establishment"])

    # top productos más comprados
    df_top_products = (
        df.groupby(["description", "size", "establishment"], as_index=False)
        .agg(
            total_quantity_sold=("quantity", "sum"),
            total_revenue=("total", "sum")
        )
    )

    top_productos = {}
    # filtro por establecimientos de top productos más comprados
    for establishment_name in establishments:
        df_top_product_filter = (
            df_top_products[df_top_products["establishment"] == establishment_name]
            .sort_values(
                by=["total_quantity_sold", "total_revenue"],
                ascending=[False, False]
            )
            .head(3)               
        )

        df_top_product_filter = df_top_product_filter.drop(columns="establishment")
        dict_top_product_filter = df_top_product_filter.to_dict(orient="split")
        top_productos["in_" + establishment_name.replace(" ", "_")] = {
            "metrics": dict_top_product_filter["columns"],
            "values": dict_top_product_filter["data"]
        }

    # top medios de pago
    df_top_payment_methods = (
        df2.groupby(["establishment", "payment_method"], as_index=False)
        .agg(
            total_payments=("payment", "sum"),
            total_transactions=("payment_method", "size")
        )
    )

    top_medios_pago = {}
    # filtro por establecimientos de top medios de pago
    # for establishment_name in df_top_establecimientos.index:
    for establishment_name in establishments:
        df_top_payment_methods_filter = (
            df_top_payment_methods[df_top_payment_methods["establishment"] == establishment_name]
            .sort_values("total_payments", ascending=False)
        )

        df_top_payment_methods_filter = df_top_payment_methods_filter.drop(columns="establishment")
        dict_top_payment_methods_f = df_top_payment_methods_filter.to_dict(orient="split")

        top_medios_pago["in_" + establishment_name.replace(" ", "_")] = {
            "metrics": dict_top_payment_methods_f["columns"],
            "values": dict_top_payment_methods_f["data"],
        }

    # procedimiento para saber cuántas filas devovler de días con más ventas según establecimiento
    days_btw = 0 # variable auxiliar (days between: días entre)
    rows_head = 0 # variable auxiliar (rows head: numero de filas)
    # dias con más ventas (solo si es un resumen de más de 2 días)
    if startDate and finishDate:
        days_btw = days_between(startDate, finishDate)
        if days_btw > 2:
            rows_head = 1
            if days_btw > 6:
                rows_head = 3
    else:
        days_btw = 3
        rows_head = 3

    # diccionario final
    resumen = {
        "data_date": date,
        "top_establishments": top_establecimientos,
        "top_products": top_productos,
        "top_payment_methods": top_medios_pago
    }

    # solo ver días con más ganancia si la diferencia de la fecha es mayor a 2
    if days_btw > 2:
        # top días con más ventas
        df_top_sales = (
            df.groupby(["date_of_issue", "establishment"], as_index=False)
            .agg(
                total_quantity_sold=("quantity", "sum"),
                total_revenue=("total", "sum")
            )
        )
        top_ventas_por_dia = {}
        # for establishment_name in df_top_establecimientos.index:
        for establishment_name in establishments:
            df_top_sales_filter = (
                df_top_sales[df_top_sales["establishment"] == establishment_name]
                .sort_values(
                    by=["total_quantity_sold", "total_revenue"],
                    ascending=[False, False]
                )
            )

            df_top_sales_filter = df_top_sales_filter.drop(columns="establishment")

            df_top_sales_filter["date_of_issue"] = pd.to_datetime(df_top_sales_filter["date_of_issue"])
            df_top_sales_filter["date_of_issue"] = (
                df_top_sales_filter["date_of_issue"]
                .dt.strftime("%Y-%m-%d %A")
                .str.replace(" ", "_")
            )
            dic_top_sales_f = df_top_sales_filter.head(rows_head).to_dict(orient="split")
            top_ventas_por_dia["in_" + establishment_name.replace(" ", "_")] = {
                "metrics": dic_top_sales_f["columns"],
                "values": dic_top_sales_f["data"],
            }
            
            # df_top_sales_filter.set_index("date_of_issue", inplace=True)
            # df_top_sales_filter.index = pd.to_datetime(df_top_sales_filter.index)
            # df_top_sales_filter.index = df_top_sales_filter.index.strftime("%Y-%m-%d %A")
            # df_top_sales_filter.index = df_top_sales_filter.index.str.replace(" ", "_")
            # top_ventas_por_dia["in_" + establishment_name.replace(" ", "_")] = df_top_sales_filter.head(rows_head).to_dict(orient="index")
    
        resumen["days_most_sales"] = top_ventas_por_dia

        # top días de semana
        df["day_name"] = df["date_of_issue"].dt.day_name()
        
        df_top_sales_dayname = (
            df.groupby(["day_name", "establishment"], as_index=False)
            .agg(
                total_quantity_sold=("quantity", "sum"),
                total_revenue=("total", "sum")      
            )
        )

        top_ventas_nombre_dia = {}
        for establishment_name in establishments:
            df_top_sales_dayname_filter = (
                df_top_sales_dayname[df_top_sales_dayname["establishment"] == establishment_name]
                .sort_values(
                    by=["total_quantity_sold", "total_revenue"],
                    ascending=[False, False]
                )
            )

            df_top_sales_dayname_filter = df_top_sales_dayname_filter.drop(columns="establishment")
            dict_top_sales_dayname_f = df_top_sales_dayname_filter.head(rows_head).to_dict(orient="split")
            top_ventas_nombre_dia["in_" + establishment_name.replace(" ", "_")] = {
                "metrics": dict_top_sales_dayname_f["columns"],
                "values": dict_top_sales_dayname_f["data"],
            }
        
        resumen["dayname_most_sales"] = top_ventas_nombre_dia
    
    return resumen

def product_analysis(description: str, startDate: str = "", finishDate: str = "", establishment: str = ""):
    """
    Obtener ganacias y pares vendidos de un determinado producto
    """
    date = "" # fecha para diccionario
    query = f"""
        SELECT id, size, quantity, unit_price, total, establishment, date_of_issue
        FROM fact_sale_documents
        WHERE 1=1 
    """

    if not description or description == "":
        return {
            "mensaje": "No se determinó el producto",
            "selected_product": False
        }

    query, _, date = where_clause_and_date(query, "", startDate, finishDate)

    if establishment and establishment != "Todas":
        query += f" AND establishment = '{establishment.strip().capitalize()}'"
    
    query += f" AND description = '{description.strip().capitalize()}'"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        return {
            "mensaje": f"No se encontraron ventas para la fecha: {startDate}",
            "selected_product": True
        }

    # Cálculos estadísticos
    resumen = get_product_analysis(df, startDate, finishDate)

    resumen = {
        "date": date,
        **resumen
    }

    return resumen

def data_graphs_by_date(startDate: str, finishDate: str = "", establishment: str = ""):
    """
    Cálculo de estadísticas clave de ventas para una fecha específica, según establecimiento (para gráficos)
    """
    date = "" # fecha para diccionario
    query = f"""
        SELECT id, description, size, quantity, unit_price, total, establishment, date_of_issue
        FROM fact_sale_documents
        WHERE 1=1 
    """

    query2 = f"""
        SELECT id, establishment, payment, payment_method, date_of_issue
        FROM fact_earnings
        WHERE 1=1 
    """

    query, query2, date = where_clause_and_date(query, query2, startDate, finishDate)

    if establishment and establishment != "Todas":
        # print(">>> SOLO QUE EXISTA: ", establishment)
        query += f" AND establishment = '{establishment.strip().capitalize()}'"
        query2 += f" AND establishment = '{establishment.strip().capitalize()}'"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df2 = pd.read_sql(text(query2), conn)

    if df.empty:
        return {"mensaje": f"No se encontraron ventas para la fecha: {startDate}"}

    # Cálculos estadísticos
    resumen = get_sales_summary_for_graphs(df, df2, startDate, finishDate)

    resumen = {
        "date": date,
        **resumen
    }

    return resumen

def data_graphs_for_predictions():

    query = f"""
        SELECT date_of_issue, establishment, yhat, yhat_lower, yhat_upper
        FROM fact_sale_predictions_monthly
    """

    query2 = f"""
        SELECT date_of_issue, establishment, yhat, yhat_lower, yhat_upper
        FROM fact_sale_predictions
    """

    query3 = f"""
        SELECT * FROM fact_inventory_predictions
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df2 = pd.read_sql(text(query2), conn)
        df3 = pd.read_sql(text(query3), conn)

    if df.empty and df2.empty and df3.empty:
        return {"mensaje": f"No se encontraron registros de predicciones"}

    return {
        "df_six_months": df,
        "df_thirty_days": df2,
        "df_inventory_thirty_days": df3
    }

# ==================================================
# >>> MÉTODOS PARA OBTENER CONTEXTO ESTRATÉGICO
# ==================================================

def get_context_sales_summary(df3: pd.DataFrame, df4: pd.DataFrame, df5: pd.DataFrame):
    contexto = {
        "strategic_context": {
            "historical_comparison": {
                "same_day_sales_in_previous_week": 0.0,
                "sales_forecast_for_target_date": 0.0
            },
            "inventory_status_of_top_products": [],
            "demand_projection_next_30_days": []
        }
    }
    
    # 1. Benchmarks Globales Estadísticos (df3)
    if not df3.empty:
        row = df3.iloc[0]
        
        # Calculamos una dirección de tendencia amigable para ahorrarle razonamiento al modelo
        pct_tendencia = float(row["tendencia_semanal_pct"])
        direccion_tendencia = f"+{pct_tendencia:.1f}% (Alza)" if pct_tendencia >= 0 else f"{pct_tendencia:.1f}% (Baja)"

        contexto["strategic_context"]["historical_comparison"] = {
            "same_day_sales_in_previous_week": float(row["venta_hace_7_dias"]),
            "sales_forecast_for_target_date": float(row["venta_predicha"]),
            "average_sales_for_the_day_of_the_week(last_3_months)": round(float(row["promedio_historico_dia"]), 2),
            "standard_deviation_for_the_day_of_the_week(last_3_months)": round(float(row["desviacion_estandar_dia"]), 2),
            "trading_trend_last_7_days": direccion_tendencia
        }

    mapa_skus = {}

    # Llenar con datos de Stock Real (df4)
    if not df4.empty:
        for _, row in df4.iterrows():
            llave = (row["description"], str(row["talla"]), row["establecimiento"])
            mapa_skus[llave] = {
                "stock_actual": int(row["stock_actual"]),
                "demanda_esperada": 0,
                "stock_seguridad": 0
            }

    # Llenar/Actualizar con datos de Predicciones (df5) - ¡Aquí entran las 9 unidades!
    if not df5.empty:
        for _, row in df5.iterrows():
            llave = (row["description"], str(row["talla"]), row["establecimiento"])
            if llave not in mapa_skus:
                mapa_skus[llave] = {"stock_actual": 0, "demanda_esperada": 0, "stock_seguridad": 0}
            
            mapa_skus[llave]["demanda_esperada"] = int(row["demanda_esperada"])
            mapa_skus[llave]["stock_seguridad"] = int(row["stock_seguridad"])

    # 2. Construir el JSON agrupando por Producto a partir del mapa unificado
    import collections
    productos_agrupados = collections.defaultdict(list)
    for (prod, talla, tienda), datos in mapa_skus.items():
        productos_agrupados[prod].append((talla, tienda, datos))

    for prod_desc, componentes in productos_agrupados.items():
        stock_global = 0
        demanda_total_esperada = 0
        alerta_stock_critico = False
        riesgo_quiebre_global = False
        tallas_criticas = []
        
        # CAMBIO: Usamos un diccionario para agrupar los quiebres por tienda
        quiebres_por_tienda = {} 
        stock_por_establecimiento = {}

        for talla, tienda, datos in componentes:
            stock_sku = datos["stock_actual"]
            demanda_sku = datos["demanda_esperada"]
            seguridad_sku = datos["stock_seguridad"]

            # Acumuladores globales
            stock_global += stock_sku
            demanda_total_esperada += demanda_sku

            # Estructura por tienda
            if tienda not in stock_por_establecimiento:
                stock_por_establecimiento[tienda] = {}
            stock_por_establecimiento[tienda][talla] = stock_sku

            # Alertas lógicas por SKU individual
            if stock_sku < seguridad_sku:
                alerta_stock_critico = True
                tallas_criticas.append(talla)
            
            # Si la demanda supera al stock, registramos el quiebre asociado a esa tienda
            if demanda_sku > stock_sku:
                riesgo_quiebre_global = True
                if tienda not in quiebres_por_tienda:
                    quiebres_por_tienda[tienda] = []
                quiebres_por_tienda[tienda].append(talla)

        # Armar Bloque A: Inventario
        contexto["strategic_context"]["inventory_status_of_top_products"].append({
            "description": prod_desc,
            "global_stock": stock_global,
            "stock_in_sizes_per_establishment": stock_por_establecimiento,
            "critical_stock_alert": alerta_stock_critico,
            "sizes_on_critical_alert": list(set(tallas_criticas))
        })

        # Bloque B: Proyecciones con el nuevo mapa de quiebres por establecimiento
        if demanda_total_esperada > 0:
            contexto["strategic_context"]["demand_projection_next_30_days"].append({
                "description": prod_desc,
                "expected_demand": demanda_total_esperada,
                "risk_of_stockout": riesgo_quiebre_global,
                # Enviamos solo las tiendas que sí tienen quiebres para ahorrar tokens
                "stockout_per_establishment": quiebres_por_tienda 
            })

    return contexto

def get_context_sales_summary_by_period(df3: pd.DataFrame, df4: pd.DataFrame, df5: pd.DataFrame, tiene_fechas: bool, es_2023: bool):

    contexto = {
        "strategic_context": {
            "historical_comparison": {},
            "inventory_status_of_top_products": [],
            "demand_projection_next_30_days": []
        }
    }

    # Sección de comparasión histórica
    # 4. Cálculo de ratios y mapeo de variables (Variables en español)
    row = df3.iloc[0]
    
    ventas_periodo_anterior = round(float(row['ventas_periodo_anterior']), 2) if tiene_fechas else "No aplicable por falta de rango de fechas"
    
    # Manejo de la regla de 2023
    if not tiene_fechas:
        ventas_ano_anterior_mismo_periodo = "No aplicable por falta de rango de fechas"
    elif es_2023:
        ventas_ano_anterior_mismo_periodo = "Sin registros previos (el sistema inició en 2023)"
    else:
        ventas_ano_anterior_mismo_periodo = round(float(row['ventas_ano_anterior_mismo_periodo']), 2)

    # Evitar divisiones por cero
    tickets_hist = row['cantidad_tickets_historicos']
    tickets_act = row['tickets_periodo_actual']

    ticket_promedio_historico = round(float(row['ventas_historicas_totales'] / tickets_hist), 2) if tickets_hist > 0 else 0.0
    articulos_por_ticket_historico = round(float(row['articulos_historicos_totales'] / tickets_hist), 2) if tickets_hist > 0 else 0.0
    articulos_por_ticket_periodo = round(float(row['articulos_periodo_actual'] / tickets_act), 2) if tickets_act > 0 else 0.0

    # 5. Diccionario Final (Llaves en inglés, Variables en español)
    contexto["strategic_context"]["historical_comparison"] = {
        "previous_period_sales": ventas_periodo_anterior,
        "same_period_last_year_sales": ventas_ano_anterior_mismo_periodo,
        "historical_average_ticket": ticket_promedio_historico,
        "items_per_ticket_period": articulos_por_ticket_periodo,
        "historical_items_per_ticket": articulos_por_ticket_historico
    }

    # Sección de inventario
    mapa_skus = {}

    # Llenar con datos de Stock Real (df4)
    if not df4.empty:
        for _, row in df4.iterrows():
            llave = (row["description"], str(row["talla"]), row["establecimiento"])
            mapa_skus[llave] = {
                "stock_actual": int(row["stock_actual"]),
                "demanda_esperada": 0,
                "stock_seguridad": 0
            }

    # Llenar/Actualizar con datos de Predicciones (df5) - ¡Aquí entran las 9 unidades!
    if not df5.empty:
        for _, row in df5.iterrows():
            llave = (row["description"], str(row["talla"]), row["establecimiento"])
            if llave not in mapa_skus:
                mapa_skus[llave] = {"stock_actual": 0, "demanda_esperada": 0, "stock_seguridad": 0}
            
            mapa_skus[llave]["demanda_esperada"] = int(row["demanda_esperada"])
            mapa_skus[llave]["stock_seguridad"] = int(row["stock_seguridad"])

    # 2. Construir el JSON agrupando por Producto a partir del mapa unificado
    import collections
    productos_agrupados = collections.defaultdict(list)
    for (prod, talla, tienda), datos in mapa_skus.items():
        productos_agrupados[prod].append((talla, tienda, datos))

    for prod_desc, componentes in productos_agrupados.items():
        stock_global = 0
        demanda_total_esperada = 0
        alerta_stock_critico = False
        riesgo_quiebre_global = False
        tallas_criticas = []
        
        # CAMBIO: Usamos un diccionario para agrupar los quiebres por tienda
        quiebres_por_tienda = {} 
        stock_por_establecimiento = {}

        for talla, tienda, datos in componentes:
            stock_sku = datos["stock_actual"]
            demanda_sku = datos["demanda_esperada"]
            seguridad_sku = datos["stock_seguridad"]

            # Acumuladores globales
            stock_global += stock_sku
            demanda_total_esperada += demanda_sku

            # Estructura por tienda
            if tienda not in stock_por_establecimiento:
                stock_por_establecimiento[tienda] = {}
            stock_por_establecimiento[tienda][talla] = stock_sku

            # Alertas lógicas por SKU individual
            if stock_sku < seguridad_sku:
                alerta_stock_critico = True
                tallas_criticas.append(talla)
            
            # Si la demanda supera al stock, registramos el quiebre asociado a esa tienda
            if demanda_sku > stock_sku:
                riesgo_quiebre_global = True
                if tienda not in quiebres_por_tienda:
                    quiebres_por_tienda[tienda] = []
                quiebres_por_tienda[tienda].append(talla)

        # Armar Bloque A: Inventario
        contexto["strategic_context"]["inventory_status_of_top_products"].append({
            "description": prod_desc,
            "global_stock": stock_global,
            "stock_in_sizes_per_establishment": stock_por_establecimiento,
            "critical_stock_alert": alerta_stock_critico,
            "sizes_on_critical_alert": list(set(tallas_criticas))
        })

        # Bloque B: Proyecciones con el nuevo mapa de quiebres por establecimiento
        if demanda_total_esperada > 0:
            contexto["strategic_context"]["demand_projection_next_30_days"].append({
                "description": prod_desc,
                "expected_demand": demanda_total_esperada,
                "risk_of_stockout": riesgo_quiebre_global,
                # Enviamos solo las tiendas que sí tienen quiebres para ahorrar tokens
                "stockout_per_establishment": quiebres_por_tienda 
            })

    return contexto
