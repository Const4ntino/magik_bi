import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from prophet import Prophet
import time
from datetime import datetime

def generar_predicciones_inventario():
    print("Iniciando predicciónes de inventario SKU Multi-Local con Prophet...")
    start_time = time.time()
    
    # engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")
    engine = create_engine("mysql+pymysql://root:@localhost/datamart_magik")
    
    try:
        # Extraer toda el historial de ventas
        query = """
            SELECT 
                date_of_issue, 
                establishment, 
                item_id, 
                description, 
                size, 
                quantity 
            FROM fact_sale_documents
            WHERE status = 'AC'; -- Solo ventas válidas
        """
        
        with engine.connect() as conn:
            df_hist = pd.read_sql(text(query), conn)
            
        df_hist['date_of_issue'] = pd.to_datetime(df_hist['date_of_issue'])
        fecha_hoy = datetime.now().date()
        
        print(f"Data extraída: {len(df_hist)} Registros de venta de productos.")

        # Aplico FILTRO INTELIGENTE (Regla de Pareto simplificada)
        # Agrupar para saber cuántos pares ha vendido cada combinación en total
        ventas_totales = df_hist.groupby(['establishment', 'item_id', 'size'])['quantity'].sum().reset_index()
        
        # Predicciones soloo de los zapatos que se hayan vendido más de 15 veces
        combos_ganadores = ventas_totales[ventas_totales['quantity'] >= 15]
        print(f"Se encontraron {len(combos_ganadores)} combinaciones de alta rotación para predecir.")

        predicciones_inventario = []

        # Bucle de entrenamiento (Un modelo por cada combinación)
        for index, row in combos_ganadores.iterrows():
            local = row['establishment']
            item = row['item_id']
            talla = row['size']
            
            # Filtrar la historia exacta del zapato en determinado local
            df_sku = df_hist[(df_hist['establishment'] == local) & 
                             (df_hist['item_id'] == item) & 
                             (df_hist['size'] == talla)].copy()
            
            # Guardar el nombre del calzado
            descripcion = df_sku['description'].iloc[0] 
            
            # Agrupar semanalmente para reducir el ruido que tienen las ventas diariaas
            df_semanal = df_sku.resample('W', on='date_of_issue')['quantity'].sum().reset_index()
            df_semanal.rename(columns={'date_of_issue': 'ds', 'quantity': 'y'}, inplace=True)
            
            # Si un zapato tiene menos de 3 semanas de datos, Prophet fallará o dará datos erróneos. Entonces se omite.
            if len(df_semanal) < 3:
                continue
                
            try:
                # Entrenar el modelo
                modelo = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=False,
                    yearly_seasonality=True 
                )
                
                modelo.fit(df_semanal) # entrenamiento
                
                # Generar predicciones
                futuro = modelo.make_future_dataframe(periods=4, freq='W')
                prediccion = modelo.predict(futuro)
                
                # Se filtra solo las 4 semanas predichas
                ultima_fecha = df_semanal['ds'].max()
                futuro_pred = prediccion[prediccion['ds'] > ultima_fecha]
                
                # Consolidar las ventas esperadas
                demanda_esperada = futuro_pred['yhat'].sum() # Se suma las ventas esperadas
                stock_seguridad = futuro_pred['yhat_upper'].sum() # Las ventas máximas esperadas como stock de seguridad
                
                # Guardar los resultados redondeando hacia arriba (para no guardar decimales)
                predicciones_inventario.append({
                    'prediction_date': fecha_hoy,
                    'establishment': local,
                    'item_id': item,
                    'description': descripcion,
                    'size': talla,
                    'expected_demand': int(np.ceil(max(0, demanda_esperada))),
                    'safety_stock': int(np.ceil(max(0, stock_seguridad)))
                })
                
            except Exception as e:
                # Si hay algún problema con el entrenamiento del modelo concurrente entonces se omte.
                continue

        # Persistencia
        if predicciones_inventario:
            df_final = pd.DataFrame(predicciones_inventario)
            
            # Ordenar
            df_final = df_final.sort_values(by=['establishment', 'description', 'size'])
            
            nombre_tabla = 'fact_inventory_predictions'
            print(f"Guardando {len(df_final)} filas en {nombre_tabla}...")
            
            df_final.to_sql(
                name=nombre_tabla, 
                con=engine, 
                if_exists='replace',
                index=False
            )
            
            tiempo_total = round(time.time() - start_time, 2)
            print(f"Proceso completo en {tiempo_total} segundos")
        else:
            print("No se generaron predicciones. Revisa la cantidad de datos.")

    except Exception as e:
        print(f"Error crítico en el script: {e}")

if __name__ == "__main__":
    generar_predicciones_inventario()