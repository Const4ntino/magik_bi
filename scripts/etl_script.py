from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("mysql+pymysql://facturacion:75478910Jc28@5.161.118.178:3306/smart_magik")

df_inventory_kardex = pd.read_sql("SELECT * FROM inventory_kardex", engine)
df_item_sizes = pd.read_sql("SELECT * FROM item_sizes", engine)
df_sale_notes = pd.read_sql("SELECT * FROM sale_notes", engine)

df_items = pd.read_sql("SELECT * FROM items", engine)
df_sale_note_items = pd.read_sql("SELECT * FROM sale_note_items", engine)
df_document_items = pd.read_sql("SELECT * FROM document_items", engine)
df_documents = pd.read_sql("SELECT * FROM documents", engine)

df_invoices = pd.read_sql("SELECT * FROM invoices", engine)
df_document_payments = pd.read_sql("SELECT * FROM document_payments", engine)

df_global_payments = pd.read_sql("SELECT * FROM global_payments", engine)
df_item_movement = pd.read_sql("SELECT * FROM item_movement", engine)
df_districts = pd.read_sql("SELECT * FROM districts", engine)
df_provinces = pd.read_sql("SELECT * FROM provinces", engine)

columnas_valiosas = ["date_of_issue", "item_id", "quantity", "inventory_kardexable_type", "warehouse_id"]

df_kardex_final = df_inventory_kardex[columnas_valiosas].copy()

df_kardex_final["inventory_kardexable_type"].value_counts()

mapeo = {
    'App\\Models\\Tenant\\Document': 'Factura/Boleta',
    'App\\Models\\Tenant\\SaleNote': 'Nota de Venta',
    'Modules\\Inventory\\Models\\Inventory': 'Movimiento de Inventario'
}
df_kardex_final["tipo_movimiento"] = df_kardex_final["inventory_kardexable_type"].map(mapeo)

df_kardex_final["warehouse_id"] = df_kardex_final["warehouse_id"].astype(str)

mapeo_warehouses = {
    "1": "Bagua",
    "2": "Feria",
    "3": "Bagua Grande"
}

df_kardex_final["almacen"] = df_kardex_final["warehouse_id"].map(mapeo_warehouses)

df_kardex_final = df_kardex_final.drop(columns=["inventory_kardexable_type", "warehouse_id"])

df_kardex_final["date_of_issue"] = pd.to_datetime(df_kardex_final["date_of_issue"])

df_kardex_final = df_kardex_final.rename(columns={"tipo_movimiento": "movement_type", "almacen": "warehouse"})

columnas_valiosas = ["id", "establishment_id", "state_type_id", "date_of_issue", "total"]

df_sale_notes_final = df_sale_notes[columnas_valiosas].copy()

df_sale_notes_final["state_type_id"] = df_sale_notes_final["state_type_id"].astype(str)

mapeo = {
    "01": "Registrado",
    "03": "Enviado",
    "05": "Aceptado",
    "07": "Observado",
    "09": "Rechazado",
    "11": "Anulado",
    "13": "Por anular",
    "55": "Interno"
}
df_sale_notes_final["estado"] = df_sale_notes_final["state_type_id"].map(mapeo)

df_sale_notes_final["date_of_issue"] = pd.to_datetime(df_sale_notes_final["date_of_issue"])

df_sale_notes_final = df_sale_notes_final.rename(columns={"estado": "status", "establecimiento": "warehouse"})

columnas_valiosas = ["sale_note_id", "item_id", "item", "quantity", "unit_value", "total"]

df_sale_note_items_final = df_sale_note_items[columnas_valiosas].copy()

df_sale_note_items_final = df_sale_note_items_final.rename(columns={"unit_value": "unit_price"})

import json

def extraer_lista_tallas(item_str):
    try:
        lista_tallas = json.loads(item_str)
        return lista_tallas.get("sizes_selected", [])
    except:
        return []

df_sale_note_items_final["items_list"] = df_sale_note_items_final["item"].apply(extraer_lista_tallas)

df_sale_note_items_final["description"] = (
    df_sale_note_items_final["item"]
    .apply(lambda x: json.loads(x).get("description") if isinstance(x, str) else "")       
)

df_sale_note_items_explode = df_sale_note_items_final.explode("items_list")

df_sale_note_items_explode = df_sale_note_items_explode.drop(columns=["item", "quantity", "total"])

df_sale_note_items_explode["size"] = (
    df_sale_note_items_explode["items_list"]
    .apply(lambda x: x.get("size") if isinstance(x, dict) else None)
)

df_sale_note_items_explode["quantity"] = (
    df_sale_note_items_explode["items_list"]
    .apply(lambda x: x.get("qty") if isinstance(x, dict) else 1)
)

df_sale_note_items_explode["total"] = df_sale_note_items_explode["unit_price"] * df_sale_note_items_explode["quantity"].astype(float)

df_sale_note_items_explode = df_sale_note_items_explode.drop(columns=["items_list"])

df_sales_final = pd.merge(df_sale_notes_final, df_sale_note_items_explode, left_on="id", right_on="sale_note_id")

df_sales_final = df_sales_final.drop(columns=["total_x", "sale_note_id"])

df_sales_final = df_sales_final.rename(columns={"total_y": "total"})

columnas_valiosas = ["id", "description", "sale_unit_price"]

df_items_final = df_items[columnas_valiosas].copy()

columnas_valiosas = ["id", "item_id", "warehouse_id", "size", "stock"]

df_item_sizes_final = df_item_sizes[columnas_valiosas].copy()

df_item_sizes_final["warehouse_id"] = df_item_sizes_final["warehouse_id"].astype(str)

mapeo_warehouses = {
    "1": "Bagua",
    "2": "Feria",
    "3": "Bagua Grande"
}

df_item_sizes_final["almacen"] = df_item_sizes_final["warehouse_id"].map(mapeo_warehouses)

df_dim_items = pd.merge(df_items_final, df_item_sizes_final, left_on="id", right_on="item_id")

df_dim_items = df_dim_items.drop(columns=["id_y", "item_id", "warehouse_id"])

df_dim_items = df_dim_items.rename(columns={"id_x": "id", "almacen" : "warehouse"})

columnas_valiosas = ["id", "state_type_id", "establishment_id", "date_of_issue", "total"]

df_documents_final = df_documents[columnas_valiosas].copy()

df_documents_final["establishment_id"] = df_documents_final["establishment_id"].astype(str)

mapeo = {
    "1": "Bagua",
    "2": "Feria",
    "3": "Bagua Grande"
}

df_documents_final["establecimiento"] = df_documents_final["establishment_id"].map(mapeo)

df_documents_final["date_of_issue"] = pd.to_datetime(df_documents_final["date_of_issue"])

df_state_types = pd.read_sql("SELECT * FROM state_types", engine)

mapeo_state_types = {
    str(df_state_types["id"][indice]) :
    str(df_state_types["description"][indice]) for indice in df_state_types.index
}

df_documents_final["estado"] = df_documents_final["state_type_id"].map(mapeo_state_types)

df_documents_final = df_documents_final.drop(columns=["state_type_id", "establishment_id"])

df_documents_final["date_of_issue"] = pd.to_datetime(df_documents_final["date_of_issue"])

df_documents_final = df_documents_final.rename(columns={"establecimiento": "establishment", "estado": "status"})

columnas_valiosas = ["document_id", "payment_method_type_id", "payment"]

df_document_payments_final = df_document_payments[columnas_valiosas].copy()

df_payment_method_types = pd.read_sql("SELECT * FROM payment_method_types", engine)

mapeo_payment_method_types = {
    str(df_payment_method_types["id"][indice]) :
    str(df_payment_method_types["description"][indice]) for indice in df_payment_method_types.index
}

df_document_payments_final["payment_method"] = df_document_payments_final["payment_method_type_id"].map(mapeo_payment_method_types)

df_document_payments_final = df_document_payments_final.drop(columns="payment_method_type_id")

columnas_valiosas = ["document_id", "item_id", "item", "quantity", "unit_price", "total"]

df_document_items_final = df_document_items[columnas_valiosas].copy()

df_document_items_final["items_list"] = df_document_items_final["item"].apply(extraer_lista_tallas)

df_document_items_final["description"] = (
    df_document_items_final["item"]
    .apply(lambda x: json.loads(x).get("description") if isinstance(x, str) else "")       
)

df_document_items_explode = df_document_items_final.explode("items_list")

df_document_items_explode = df_document_items_explode.drop(columns=["item", "quantity", "total"])

df_document_items_explode["size"] = (
    df_document_items_explode["items_list"]
    .apply(lambda x: x.get("size") if isinstance(x, dict) else None)
)

df_document_items_explode["quantity"] = (
    df_document_items_explode["items_list"]
    .apply(lambda x: x.get("qty") if isinstance(x, dict) else 1)
)

df_document_items_explode["total"] = df_document_items_explode["unit_price"] * df_document_items_explode["quantity"].astype(float)

df_document_items_explode = df_document_items_explode.drop(columns=["items_list"])

id_faltante = df_document_items_explode[df_document_items_explode["size"].isna()]

df_document_items_explode["size"] = df_document_items_explode["size"].fillna("Genérico")

df_earnings_final = pd.merge(df_documents_final, df_document_payments_final, left_on="id", right_on="document_id", how="left")

df_earnings_final = df_earnings_final.drop(columns=["total", "document_id"])

valores_validos = ["Aceptado", "Registrado"]

df_earnings_final = df_earnings_final[df_earnings_final["status"].isin(valores_validos)]

df_sold_final = pd.merge(df_documents_final, df_document_items_explode, left_on="id", right_on="document_id", how="left")

df_sold_final = df_sold_final.drop(columns=["total_x", "document_id"])

df_sold_final = df_sold_final.rename(columns={"total_y": "total"})

valores_validos = ["Aceptado", "Registrado"]

df_sold_final = df_sold_final[df_sold_final["status"].isin(valores_validos)]

from sqlalchemy import text

engine_root = create_engine("mysql+pymysql://root:@localhost:3306")

with engine_root.connect() as conn:
    conn.execute(text("DROP DATABASE IF EXISTS datamart_magik"))
    conn.execute(text("CREATE DATABASE datamart_magik"))
    conn.commit()
    
engine_datamart = create_engine("mysql+pymysql://root:@localhost:3306/datamart_magik")

df_dim_items.to_sql("dim_items", con=engine_datamart, if_exists="replace", index=False)

df_sales_final.to_sql("fact_sale_notes", con=engine_datamart, if_exists="replace", index=False)

df_kardex_final.to_sql("fact_kardex", con=engine_datamart, if_exists="replace", index=False)

df_earnings_final.to_sql("fact_earnings", con=engine_datamart, if_exists="replace", index=False)

df_sold_final.to_sql("fact_sale_documents", con=engine_datamart, if_exists="replace", index=False)

from sqlalchemy.exc import OperationalError

def configurar_base_datos(engine):
    query = "ALTER TABLE dim_items ADD FULLTEXT idx_fulltext_desc (description);"
    
    try:
        with engine.begin() as conn:
            conn.execute(text(query))
            print("Índice FULLTEXT creado exitosamente.")
            
    except OperationalError as e:
        if "Duplicate key name" in str(e) or "1061" in str(e):
            print("El índice FULLTEXT ya existe. Todo listo.")
        else:
            print(f"Ocurrió un error al configurar la BD: {e}")

configurar_base_datos(engine_datamart)