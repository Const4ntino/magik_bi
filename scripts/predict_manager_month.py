import pandas as pd
from sqlalchemy import create_engine, text
from prophet import Prophet
import time

def generar_predicciones_mensuales():
    print("Iniciando predicción mensual Multi-Local con Prophet...")
    start_time = time.time()
    
    # engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")
    engine = create_engine("mysql+pymysql://root:@localhost/datamart_magik")
    
    try:
        # Extraer la data agrupada por MES y LOCAL
        # WHERE para ignorar el mes actual en curso
        query = """
            SELECT 
                DATE_FORMAT(date_of_issue, '%Y-%m-01') AS ds, 
                establishment,
                SUM(payment) AS y 
            FROM fact_earnings
            WHERE date_of_issue < DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
            GROUP BY ds, establishment
            ORDER BY ds ASC, establishment ASC;
        """
        
        with engine.connect() as conn:
            df_hist = pd.read_sql(text(query), conn)
            
        df_hist['ds'] = pd.to_datetime(df_hist['ds'])
        ultima_fecha_real = df_hist['ds'].max()
        
        locales = df_hist['establishment'].unique()
        print(f"Data mensual extraída. Último mes registrado: {ultima_fecha_real.strftime('%Y-%m')}")

        todas_las_predicciones = []

        for local in locales:
            print(f"Entrenando modelo para: {local}...")
            
            df_local = df_hist[df_hist['establishment'] == local].copy()
            
            modelo = Prophet(
                seasonality_mode='multiplicative',
                daily_seasonality=False,
                weekly_seasonality=False, 
                yearly_seasonality=True,
                changepoint_prior_scale=0.1,
            )
            
            modelo.fit(df_local[['ds', 'y']])
            futuro = modelo.make_future_dataframe(periods=6, freq='MS')
            prediccion = modelo.predict(futuro)
            
            # Filtramos solo el futuro
            df_solo_futuro = prediccion[prediccion['ds'] > ultima_fecha_real][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            df_solo_futuro['establishment'] = local
            
            todas_las_predicciones.append(df_solo_futuro)

        # Consolidar
        df_final = pd.concat(todas_las_predicciones, ignore_index=True)
        
        df_final['yhat'] = df_final['yhat'].clip(lower=0)
        df_final['yhat_lower'] = df_final['yhat_lower'].clip(lower=0)
        df_final['yhat_upper'] = df_final['yhat_upper'].clip(lower=0)
        
        df_final = df_final.sort_values(by=['ds', 'establishment']).reset_index(drop=True)
        df_final = df_final[['ds', 'establishment', 'yhat', 'yhat_lower', 'yhat_upper']]

        df_final.rename(columns={"ds": "date_of_issue"}, inplace=True)
        
        # Guardar en una nueva tabla
        nombre_tabla = 'fact_sale_predictions_monthly'
        print(f"Guardando {len(df_final)} proyecciones mensuales en {nombre_tabla}...")
        
        df_final.to_sql(
            name=nombre_tabla, 
            con=engine, 
            if_exists='replace', 
            index=False
        )
        
        tiempo_total = round(time.time() - start_time, 2)
        print(f"Proceso completo en {tiempo_total} segundos")
        
    except Exception as e:
        print(f"Error crítico: {e}")

if __name__ == "__main__":
    generar_predicciones_mensuales()