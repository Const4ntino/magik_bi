from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from typing import List, Dict, Any
from sale_predicts_summary import sale_predictions, monthly_sale_predictions, inventory_alerts
from products_summary import low_stock_alert, top_sizes, inventory_status, product_analysis
from sales_summary import sales_summary_by_date, sales_summary_by_period, top_establishments

# instancia del servidor MCP
mcp = FastMCP("Magik BI")

DATABASE_URL = "mysql+pymysql://mcp_user:constantino2003@localhost/datamart_magik"

engine = create_engine(DATABASE_URL, pool_recycle=3600)

# ==================================================
# >>> HERRAMIENTAS
# ==================================================

@mcp.tool()
def list_tables() -> List[str]:
    """
    Lista todas las tablas disponibles del Datamart (Galaxy Schema).
    Útil para que el LLM conozca las tablas de hechos y las dimensiones
    """
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tablas = list(result.scalars().all())
        return tablas

# >>>>> HERRAMIENTAS 'PRODUCTS'

@mcp.tool()
def get_product_analysis(description: str, warehouse: str = "", min_stock: int | None = None) -> Dict[str, Any]:
    """
    Obtiene un resumen estratégico sobre el rendimiento de un determinado producto
        Args:
            description: Nombre del producto (obligatorio)
        Returns:
            Diccionario con stock de producto, sus ventas, proyección de ventas, valor del inventario.
    """
    return product_analysis(description, warehouse, min_stock)

@mcp.tool()
def get_top_sizes(startDate: str = "", finishDate: str = "", establishment: str = "", description: str = "") -> Dict[str, Any]:
    """
    Obtiene el top de las tallas más vendidas, con sus cantidades totales vendidas e ingresos totales.
    Todos los parámetros son opcionales. Formato estricto para fechas: 'YYYY-MM-DD'
    Args:
        startDate: Fecha de inicio para el análisis (default: "")
        finishDate: Fecha de cierre para el análisis (default: "")
        establishment: Establecimiento para el análisis (default: "", valores admitidos: "Bagua", "Bagua Grande", "Feria")
        description: Nombre del producto (default: "", si se ingresa debe ser en mayúsculas)
    Returns:
        lista de tallas con su establecimiento, cantidad total vendida e ingresos totales
    """
    return top_sizes(startDate, finishDate, establishment, description)

# >>>>> HERRAMIENTAS 'SALES'

@mcp.tool()
def get_sales_summary_by_date(date: str, establishment: str = "", include_context: bool = False) -> dict:
    """
    Obtiene un resumen estadístico de ventas según una determinada fecha estrictamente con el formato: 'YYYY-MM-DD'
    Args:
        date: Fecha
        establishment: Establecimiento para el análisis de ventas (default: "", valores admitidos: "Bagua", "Bagua Grande")
        include_context: Contexto estratégico para generar recomendaciones (default: False)
    Returns:
        Diccionario con venta total, producto más vendido, ticket promedio, establecimiento con más ventas, métodos de pago.
    """
    return sales_summary_by_date(date, establishment, include_context)

@mcp.tool()
def get_sales_summary_by_period(startDate: str = "", finishDate: str = "", establishment: str = "", include_context: bool = False) -> dict:
    """
    Obtiene un resumen estadístico de ventas según un determinado periodo (opcional), ambas fechas estrictamente con el formato: 'YYYY-MM-DD'
    Args:
        startDate: Fecha de inicio para el análisis de ventas (default: "")
        finishDate: Fecha de cierre para el análisis de ventas (default: "")
        establishment: Establecimiento para el análisis de ventas (default: "", valores admitidos: "Bagua", "Bagua Grande")
        include_context: Contexto estratégico para generar recomendaciones (default: False)
    Returns:
        Diccionario con venta total, producto más vendido, top productos que generan más ingresos, ticket promedio, establecimiento con más ventas, métodos de pago, días con más ventas.
    """
    
    return sales_summary_by_period(startDate, finishDate, establishment, include_context)

@mcp.tool()
def get_top_establishments(startDate: str = "", finishDate: str = "", establishment: str = "") -> Dict[str, Any]:
    """
    Obtiene el top de los establecimientos con mejor desempeño mediante un análisis, ambas fechas son opcionales, estrictamente con el formato: 'YYYY-MM-DD'
    Args:
        startDate: Fecha de inicio para el análisis (default: "")
        finishDate: Fecha de cierre para el análisis (default: "")
        establishment: Establecimiento específico para el análisis (default: "", valores admitidos: "Bagua", "Bagua Grande", "Feria")
    Returns:
        Diccionario con el top de establecimientos (con métricas), medios de pagos más usados, días con más ventas, top de productos vendidos y top de tallas vendidas en establecimientos.
    """
    return top_establishments(startDate, finishDate, establishment)

# >>>>> HERRAMIENTAS 'PREDICTIONS'

@mcp.tool()
def get_predictions(startDate: str = "", finishDate: str = "", establishment: str = "") -> Dict[str, Any]:
    """
    Obtiene predicciones de ventas diarias (como máximo los próximos 30 días) según el establecimiento (por defecto serán todos). Ambas fechas son opcionales, estrictamente con el formato: 'YYYY-MM-DD'
    Args:
        startDate: Fecha de inicio para el análisis predictivo (default: "")
        finishDate: Fecha de cierre para el análisis predictivo (default: "")
        establishment: Establecimiento específico para el análisis predictivo (default: "", valores admitidos: "Bagua", "Bagua Grande")
    Returns:
        Diccionario con las predicciones, su fecha, monto esperado y máximo/mínimo esperado.
    """
    return sale_predictions(startDate, finishDate, establishment)

@mcp.tool()
def get_monthly_predictions(startDate: str = "", finishDate: str = "", establishment: str = "") -> Dict[str, Any]:
    """
    Obtiene predicciones de ventas mensuales (como máximo los 6 meses siguientes) según el establecimiento (por defecto serán todos). Ambas fechas son opcionales, estrictamente con el formato: 'YYYY-MM-DD'
    Args:
        startDate: Fecha de inicio para el análisis predictivo (default: "",)
        finishDate: Fecha de cierre para el análisis predictivo (default: "")
        establishment: Establecimiento específico para el análisis predictivo (default: "", valores admitidos: "Bagua", "Bagua Grande")
    Returns:
        Diccionario con las predicciones, su fecha, monto esperado y máximo/mínimo esperado.
    """
    return monthly_sale_predictions(startDate, finishDate, establishment)

# >>>>> HERRAMIENTAS 'STOCK'

@mcp.tool()
def get_inventory_stock(description: str, warehouse: str = "", min_stock: int = 2) -> Dict[str, Any]:
    """
    Busca el stock de un calzado según su descripción
    tabla: dim_items
        Args:
            description: Nombre del producto (obligatorio)
            warehouse: Almacén específico (default: "", valores admitidos: "Bagua", "Bagua Grande", "Feria")
            min_stock: Cantidad mínima para alertar
        Returns:
            Diccionario con stock de producto, precio, y almacén
    """
    return inventory_status(description, warehouse, min_stock)

@mcp.tool()
def get_low_stock_alert(threshold: int = 3, startDate: str = "", finishDate: str = "", establishment: str = "") -> Dict[str, Any]:
    """
    Obtiene un resumen histórico de los principales productos vendidos que están por agotarse (usarse para alertas de stock bajo).
    De ingresarse fecha, debe ser estrictamente con el formato: 'YYYY-MM-DD'
    Args:
        threshold: Cantidad mínima de unidades para activar alerta (default: 2, -1 para ver productos con stock negativo)
        startDate: Fecha de inicio para el análisis (default: "")
        finishDate: Fecha de cierre para el análisis (default: "")
        establishment: Establecimiento para el análisis (default: "", valores admitidos: "Bagua", "Bagua Grande", "Feria")
    Returns:
        lista de productos con su descripción, talla, stock, puntaje, cantidad total vendida, precio unitario y almacén
    """
    return low_stock_alert(threshold, startDate, finishDate, establishment)

@mcp.tool()
def get_inventory_prediction(establishment: str = "") -> Dict[str, Any]:
    """
    Obtiene un resumen de los productos top con demanda esperada para los próximos 30 días según predicciones (usarse para predecir inventario).
    Args:
        establishment: Establecimiento para el resumen (default: "", valores admitidos: "Bagua", "Bagua Grande", "Feria")
    Returns:
        lista de productos con stock actual, stock de seguridad, y stock necesario.
    """
    return inventory_alerts(establishment)

if __name__ == "__main__":
    mcp.run() # arrancar servidor