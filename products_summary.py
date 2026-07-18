import pandas as pd
import json
from sqlalchemy import create_engine, text
from sales_summary import where_clause_and_date

# motor de conexión
engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")

def inventory_status(description: str = "", warehouse: str = "", min_stock: int = 2):
    """
    Consulta el stock actual y lo cruza con el historial de ventas de los últimos 30 días.
    Retorna nombres de columnas completos para máxima claridad del modelo.
    """
    
    # CTE para calcular ventas recientes y última fecha de movimiento
    query = """
        WITH ventas_recientes AS (
            SELECT 
                description, 
                size, 
                SUM(quantity) as quantity_sale_30d,
                MAX(date_of_issue) as last_sale_date
            FROM fact_sale_documents
            WHERE date_of_issue >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY description, size
        )
        SELECT 
            i.description,
            i.size,
            i.stock as actualy_stock, 
            COALESCE(v.quantity_sale_30d, 0) as quantity_sale_30d,
            COALESCE(v.last_sale_date, 'Sin ventas') as last_sale_date,
            i.warehouse,
            i.sale_unit_price
        FROM dim_items i
        LEFT JOIN ventas_recientes v 
            ON i.description = v.description 
            AND i.size = v.size
        WHERE 1=1
    """

    # Filtros dinámicos
    if description:
        query += f" AND i.description LIKE '%{description.strip().upper()}%'"   
    
    if warehouse:
        query += f" AND i.warehouse = '{warehouse.strip().capitalize()}'"
    
    if min_stock is not None:
        query += f" AND i.stock <= {min_stock}"

    # Ordenar por mayor demanda y menor stock (prioridad de reposición)
    query += " ORDER BY quantity_sale_30d DESC, actualy_stock ASC LIMIT 35"

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        if df.empty:
            return {
                "estado": "sin_resultados", 
                "mensaje": "No se encontraron productos con los filtros aplicados."
            }

        # Limpiar formato de fecha para el JSON
        df['last_sale_date'] = df['last_sale_date'].astype(str).str[:10]
        producto = df.iloc[0, 0]
        df = df.drop(columns="description")
        # Usamos orient="split" para mantener la estructura limpia (columnas por un lado, datos por otro)
        resultado = df.to_dict(orient="split")

        return {
            "product": producto,
            "context": "Ventas calculadas sobre los últimos 30 días naturales.",
            "total_records": len(df),
            "metrics": resultado["columns"],
            "values": resultado["data"],
        }

    except Exception as e:
        return {"estado": "error", "mensaje_error": str(e)}
    


def low_stock_alert(threshold: int = 3, startDate: str = None, finishDate: str = None, establishment: str = None):
    # Usamos una sola query para que la base de datos haga el trabajo pesado
    query = """
        SELECT 
            i.id,
            i.description, 
            i.size, 
            i.stock, 
            i.sale_unit_price, 
            i.warehouse,
            SUM(s.quantity) as total_quantity_sold
        FROM dim_items i
        INNER JOIN fact_sale_documents s 
            ON i.id = s.item_id   -- Cruce rápido por ID
            AND i.size = s.size         -- Diferenciación por talla
            AND i.warehouse = s.establishment
        WHERE 1=1
    """
    
    params = {}
    
    # Filtros aplicados directamente en la base de datos
    if establishment:
        query += " AND i.warehouse = :establishment"
        params['establishment'] = establishment
    
    if startDate and finishDate:
        query += " AND s.date_of_issue BETWEEN :startDate AND :finishDate"
        params['startDate'] = startDate
        params['finishDate'] = finishDate
    elif startDate:
        query += " AND s.date_of_issue = :startDate"
        params['startDate'] = startDate

    # Agrupamos por los campos necesarios
    query += " GROUP BY i.id, i.description, i.size, i.stock, i.sale_unit_price, i.warehouse"

    with engine.connect() as conn:
        df_filtrado = pd.read_sql(text(query), conn, params=params)

    if df_filtrado.empty:
        return {"metrics": [], "values": []}

    # Lógica de Score y Reposición (en Python porque es ligera sobre el resultado filtrado)
    df_filtrado["score"] = df_filtrado["total_quantity_sold"] / df_filtrado["stock"].replace(0, 0.5)
    
    # Sugerencia de stock a pedir (Ventas - Stock actual, mínimo 0)
    df_filtrado["to_restock"] = (df_filtrado["total_quantity_sold"] - df_filtrado["stock"]).clip(lower=0)

    # Filtrado por umbral
    mask = df_filtrado["stock"] <= threshold if threshold >= 0 else df_filtrado["stock"] < 0
    df_top = df_filtrado[mask].sort_values(by=["score", "sale_unit_price"], ascending=False).head(10)

    dict_res = df_top.to_dict(orient="split")
    return {"metrics": dict_res["columns"], "values": dict_res["data"]}

def top_sizes(startDate: str = "", finishDate: str = "", establishment: str = "", description: str = ""):
    """
    Cálculo de las tallas más vendidas
    """
    query = """
        SELECT description, sale_unit_price, size, stock, warehouse
        FROM dim_items 
        WHERE 1=1 
    """
    query2 = """
        SELECT establishment, description, size, quantity, total
        FROM fact_sale_documents 
        WHERE 1=1 
    """

    _, query2, date = where_clause_and_date("", query2, startDate, finishDate)

    if establishment:
        query += f"AND warehouse = '{establishment.strip().capitalize()}'"
        query2 += f"AND establishment = '{establishment.strip().capitalize()}'"

    if description:
        query += f"AND description = '{description.strip().upper()}'"
        query2 += f"AND description = '{description.strip().upper()}'"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df2 = pd.read_sql(text(query2), conn)

    # Top tallas vendidas
    df_top_tallas_vendidas = (
        df2.groupby(["size", "establishment"], as_index=False)
        .agg(
            total_quantity_sold=("quantity", sum),
            total_revenue=("total", sum)
        )
        .sort_values(
            by=["total_quantity_sold", "total_revenue"],
            ascending=[False, False]
        )
        .head(10)
        .assign(unique_id=lambda x: x["size"].astype(str) + "_" + x["establishment"].str.replace(" ", "_"))
        .drop(columns=["size", "establishment"])
        .set_index("unique_id")
        .to_dict(orient="split")
    )   

    top_tallas_vendidas = {
        "data_date": date,
        "size_and_establishment": df_top_tallas_vendidas["index"],
        "metrics": df_top_tallas_vendidas["columns"],
        "values": df_top_tallas_vendidas["data"]
    }

    return top_tallas_vendidas

def product_analysis(description: str = "", warehouse: str = "", min_stock: int | None = None):
    
    if not description or len(description.strip()) < 3:
        return {"status": "error", "message": "Debe proporcionar un nombre de producto válido"}

    search_term = description.strip()
    
    try:
        with engine.connect() as conn:
            # PASO 1: Buscamos solo en la dimensión 'dim_items' con FULLTEXT
            query_items = text("SELECT * FROM dim_items WHERE MATCH(description) AGAINST(:search IN NATURAL LANGUAGE MODE)")
            df_items_raw = pd.read_sql(query_items, conn, params={"search": search_term})

        if df_items_raw.empty:
            return {"status": "empty", "message": f"No se encontró stock para '{description}'."}

        # Búsqueda de productos similares
        all_matches = df_items_raw['description'].unique()
        search_term_upper = search_term.upper()
        
        if search_term_upper in all_matches:
            exact_description = search_term_upper
        else:
            starts_with = [d for d in all_matches if d.startswith(search_term_upper)]
            exact_description = min(starts_with, key=len) if starts_with else all_matches[0]
        # *----------------------------------------------------------------------------------------*

        # PASO 2: Traemos ventas y predicciones usando el nombre EXACTO
        with engine.connect() as conn:
            query_sales = text("SELECT * FROM fact_sale_documents WHERE description = :exact")
            query_preds = text("SELECT * FROM fact_inventory_predictions WHERE description = :exact")
            
            params_exact = {"exact": exact_description}
            
            df_sales = pd.read_sql(query_sales, conn, params=params_exact)
            df_preds = pd.read_sql(query_preds, conn, params=params_exact)

        # Filtramos estrictamente el inventario por el producto principal
        df_items = df_items_raw[df_items_raw['description'] == exact_description].copy()

        # --- A. ANÁLISIS HISTÓRICO ---
        best_month_txt = "N/A"
        best_month_val = 0.0
        if not df_sales.empty:
            df_sales['date_of_issue'] = pd.to_datetime(df_sales['date_of_issue'])
            sales_by_month = df_sales.set_index('date_of_issue').resample('ME')['total'].sum()
            if not sales_by_month.empty:
                best_month_txt = sales_by_month.idxmax().strftime("%B %Y")
                best_month_val = float(sales_by_month.max())

        # --- B. CRUCE TÉCNICO SIN DUPLICADOS ---
        last_30_days = pd.Timestamp.now() - pd.Timedelta(days=30)
        
        if not df_sales.empty:
            vta_reciente = df_sales[df_sales['date_of_issue'] >= last_30_days].groupby(['size']).agg({'quantity': 'sum'}).rename(columns={'quantity': 'vta_30d'}).reset_index()
        else:
            vta_reciente = pd.DataFrame(columns=['size', 'vta_30d'])
        
        if not df_preds.empty:
            preds_agg = df_preds.groupby(['size']).agg({'expected_demand': 'sum', 'safety_stock': 'max'}).reset_index()
        else:
            preds_agg = pd.DataFrame(columns=['size', 'expected_demand', 'safety_stock'])

        # Unimos al inventario
        main_df = pd.merge(df_items, vta_reciente, on=['size'], how='left')
        main_df = pd.merge(main_df, preds_agg, on=['size'], how='left').fillna(0)

        if min_stock is not None:
            main_df = main_df[main_df['stock'] <= min_stock]

        detalle_tecnico = main_df.astype(object).to_dict(orient='records')

        # Ventas reales
        ventas_reales_30d = int(vta_reciente['vta_30d'].sum()) if not vta_reciente.empty else 0

        # --- C. OTROS HALLAZGOS (other_findings) ---
        # Extraemos los siguientes resultados más relevantes descartando el principal
        other_findings_list = [d for d in all_matches if d != exact_description][:6]

        return {
            "product": exact_description,
            "executive_summary": {
                "total_stock": int(main_df['stock'].sum()),
                "sales_last_30d": ventas_reales_30d,
                "total_inventory_value": round(float((main_df['stock'] * main_df['sale_unit_price']).sum()), 2),
                "historical_record": f"{best_month_txt} (S/. {best_month_val:,.2f})"
            },
            "technical_detail": {
                "columns": ["Size", "Current Stock", "Sales 30d", "Warehouse", "Unit Price", "Expected Demand"],
                "data": [[r['size'], r['stock'], r['vta_30d'], r['warehouse'], r['sale_unit_price'], r['expected_demand']] for r in detalle_tecnico]
            },
            "other_findings": other_findings_list
        }

    except Exception as e:
        return {"status": "error", "message": f"Fallo en análisis integrado: {str(e)}"}