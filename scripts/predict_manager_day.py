import pandas as pd
from sqlalchemy import create_engine, text
from prophet import Prophet
import time

def generar_y_guardar_predicciones_por_local():
    print("Iniciando predicción diaria Multi-Local con Prophet...")
    start_time = time.time()
    
    engine = create_engine("mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik")
    
    try:
        query = """
            SELECT 
                date_of_issue AS ds, 
                establishment,
                SUM(payment) AS y 
            FROM fact_earnings
            GROUP BY date_of_issue, establishment
            ORDER BY date_of_issue ASC, establishment ASC;
        """
        
        with engine.connect() as conn:
            df_hist = pd.read_sql(text(query), conn)
            
        df_hist['ds'] = pd.to_datetime(df_hist['ds'])
        ultima_fecha_real = df_hist['ds'].max()
        
        locales = df_hist['establishment'].unique()
        print(f"Se encontraron {len(locales)} locales: {', '.join(locales)}")
        print(f"Última fecha de venta real: {ultima_fecha_real.date()}")

        feriados_comerciales = pd.DataFrame({
            'holiday': 'picos_retail',
            'ds': pd.to_datetime([
                '2023-02-14', '2024-02-14', '2025-02-14', '2026-02-14', '2027-02-14',
                '2023-05-14', '2024-05-12', '2025-05-11', '2026-05-10', '2027-05-09'
            ]),
            'lower_window': -1,
            'upper_window': 0,
        })

        todas_las_predicciones = []

        for local in locales:
            print(f"Entrenando modelo para: {local}...")
            
            df_local = df_hist[df_hist['establishment'] == local].copy()
            
            modelo = Prophet(
                seasonality_mode='multiplicative',
                holidays=feriados_comerciales,
                daily_seasonality=False,
                weekly_seasonality=True, 
                yearly_seasonality=True,    
                changepoint_prior_scale=0.06, # flexibilidad de la tendencia
                seasonality_prior_scale=10.0 # peso de las estacionalidades (valor recomendado)
            )
            modelo.add_country_holidays(country_name='PE')
            
            modelo.fit(df_local[['ds', 'y']])
            futuro = modelo.make_future_dataframe(periods=30)
            prediccion = modelo.predict(futuro)
            
            df_solo_futuro = prediccion[prediccion['ds'] > ultima_fecha_real][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            
            df_solo_futuro['establishment'] = local
            
            todas_las_predicciones.append(df_solo_futuro)

        print("Uniendo predicciones de todos los locales...")
        df_final = pd.concat(todas_las_predicciones, ignore_index=True)
        
        df_final['yhat'] = df_final['yhat'].clip(lower=0)
        df_final['yhat_lower'] = df_final['yhat_lower'].clip(lower=0)
        df_final['yhat_upper'] = df_final['yhat_upper'].clip(lower=0)
        
        df_final = df_final.sort_values(by=['ds', 'establishment']).reset_index(drop=True)
        
        df_final = df_final[['ds', 'establishment', 'yhat', 'yhat_lower', 'yhat_upper']]
        df_final.rename(columns={"ds": "date_of_issue"}, inplace=True)
        
        print(f"Guardando {len(df_final)} filas en fact_sale_predictions...")
        df_final.to_sql(
            name='fact_sale_predictions', 
            con=engine, 
            if_exists='replace', 
            index=False
        )
        
        tiempo_total = round(time.time() - start_time, 2)
        print(f"Proceso completo en {tiempo_total} segundos")
        
    except Exception as e:
        print(f"Error crítico: {e}")

if __name__ == "__main__":
    generar_y_guardar_predicciones_por_local()