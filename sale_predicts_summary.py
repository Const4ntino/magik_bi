import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sales_summary import where_clause_and_date

# motor de conexión
engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")

def sale_predictions(startDate: str = "", finishDate: str = "", establishment: str = ""):
    """
    Obtiene predicciones (de los próximos 30 días)
    """
    query = """
        SELECT date_of_issue, establishment, yhat, yhat_lower, yhat_upper
        FROM fact_sale_predictions
        WHERE 1=1 
    """

    query, _, date_range_str = where_clause_and_date(query, "date_of_issue", startDate, finishDate)

    if establishment:
        query += f" AND establishment = '{establishment.strip().capitalize()}'"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        return {
            "message": f"No se encontraron predicciones para el rango {date_range_str}",
            "data": None
        }

    dias_unicos = df['date_of_issue'].nunique()

    total_esperado = float(df['yhat'].sum())
    peor_escenario = float(df['yhat_lower'].sum())
    mejor_escenario = float(df['yhat_upper'].sum())

    response = {
        "context": {
            "date_range": date_range_str,
            "establishment": establishment.strip().capitalize() if establishment else "Todas",
            "days_analyzed": dias_unicos
        },
        "summary": {
            "expected_revenue": round(total_esperado, 2),
            "worst_case_scenario": round(peor_escenario, 2),
            "best_case_scenario": round(mejor_escenario, 2)
        }
    }

    if dias_unicos > 1:
        response["summary"]["daily_average"] = round(float(df['yhat'].mean()), 2)

        idx_max = df['yhat'].idxmax()
        idx_min = df['yhat'].idxmin()

        response["highlights"] = {
            "peak_day": {
                "date": str(df.loc[idx_max, 'date_of_issue'])[:10], 
                "expected_sales": round(float(df.loc[idx_max, 'yhat']), 2)
            },
            "slowest_day": {
                "date": str(df.loc[idx_min, 'date_of_issue'])[:10], 
                "expected_sales": round(float(df.loc[idx_min, 'yhat']), 2)
            }
        }
    else:
        fecha_unica = str(df['date_of_issue'].iloc[0])[:10]
        response["highlights"] = {
            "note": f"Predicción específica para un solo día ({fecha_unica})."
        }

    if dias_unicos <= 7:
        daily_data = {}
        for _, row in df.iterrows():
            fecha = str(row['date_of_issue'])[:10]
            local = row['establishment']
            
            if local not in daily_data:
                daily_data[local] = {}
                
            daily_data[local][fecha] = [
                round(row['yhat'], 1), 
                round(row['yhat_lower'], 1), 
                round(row['yhat_upper'], 1)
            ]
            
        response["daily_breakdown"] = {
            "legend": "[expected, min, max] per establishment",
            "data": daily_data
        }

    return response

def monthly_sale_predictions(startDate: str = "", finishDate: str = "", establishment: str = ""):
    """
    Obtiene las predicciones de ventas mensuales para los próximos 6 meses.
    Retorna un diccionario con los registros encontrados.
    """
    query = """
        SELECT 
            date_of_issue, 
            establishment, 
            yhat, 
            yhat_lower, 
            yhat_upper
        FROM fact_sale_predictions_monthly
        WHERE 1=1 
    """

    query, _, _ = where_clause_and_date(query, "date_of_issue", startDate, finishDate)

    if establishment:
        est_cleaned = establishment.strip().capitalize()
        query += f" AND establishment = '{est_cleaned}'"

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        
        if not df.empty:
            if 'date_of_issue' in df.columns:
                df['date_of_issue'] = df['date_of_issue'].dt.strftime('%Y-%m')
                columns = ["yhat", "yhat_lower", "yhat_upper"]
                df[columns] = df[columns].round(2)
                dict_df = df.to_dict(orient="split")
            return {
                "metrics": dict_df["columns"],
                "values": dict_df["data"]
            }
        else:
            return {
                "message": "No se encontraron predicciones para los criterios seleccionados."
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def inventory_alerts(establishment: str = ""):
    """
    Cruza el inventario actual con las predicciones para generar alertas de compra.
    """
    query = """
        SELECT 
            p.establishment AS local,
            p.description AS producto,
            p.size AS talla,
            i.stock AS stock_actual,
            p.expected_demand AS demanda_esperada,
            p.safety_stock AS stock_seguridad,
            (p.safety_stock - i.stock) AS cantidad_a_comprar
        FROM fact_inventory_predictions p
        JOIN dim_items i 
            ON p.item_id = i.id 
            AND p.size = i.size 
            AND p.establishment = i.warehouse
        WHERE i.stock < p.safety_stock
    """

    if establishment:
        query += f" AND p.establishment = '{establishment.strip().capitalize()}'"
        
    query += " ORDER BY cantidad_a_comprar DESC, p.establishment ASC;"

    with engine.connect() as conn:
        df_alertas = pd.read_sql(text(query), conn)

    if df_alertas.empty:
        return {
            "message": "El stock actual es suficiente para cubrir la demanda esperada en los próximos 30 días.",
        }
    
    alertas_por_local = {}
    
    for local in df_alertas['local'].unique():
        df_local = df_alertas[df_alertas['local'] == local]
        
        columnas = ["item", "current_stock", "needed_stock", "to_order"]
        lista_productos = []
        for _, row in df_local.iterrows():
            lista_productos.append([
                f"{row['producto']} (Talla {row['talla']})",
                int(row['stock_actual']),
                int(row['stock_seguridad']),
                int(row['cantidad_a_comprar'])
            ])
            
        alertas_por_local[local] = {
            "metrics": columnas,
            "values":lista_productos
        } 

    return {
        "context": {
            "message": "Se encontraron quiebres de stock inminentes basados en la predicción a 30 días.",
            "total_items_to_reorder": len(df_alertas)
        },
        "reorder_list": alertas_por_local
    }