import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine
import os
import time

# Conexión a la base de datos de Docker
# El host 'db' coincide con el nombre del servicio en docker-compose
DB_PASS = os.getenv('DB_PASS', 'password')
engine = create_engine(f'postgresql://postgres:{DB_PASS}@db:5432/valenbisi')

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Estado de Valenbisi (Procesado con DBT)", style={'textAlign': 'center', 'color': '#2c3e50'}),
    dcc.Graph(id='live-update-graph'),
    dcc.Interval(
        id='interval-component',
        interval=30*1000, # Se actualiza cada 30 segundos
        n_intervals=0
    )
])

# Esta función se ejecuta cada vez que el reloj (Interval) "suena"
@app.callback(Output('live-update-graph', 'figure'),
              Input('interval-component', 'n_intervals'))
def update_graph_live(n):
    try:
        # Lectura directa de la tabla transformada que ya incluye coordenadas
        df = pd.read_sql("""
            SELECT DISTINCT ON (station_id)
                station_id,
                station_name,
                bicis_promedio,
                huecos_promedio,
                latitude,
                longitude
            FROM uso_horario
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY station_id, hora DESC  -- última hora disponible de cada estación
        """, engine)
        
        if df.empty:
            # Crear figura vacía con mensaje
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.update_layout(
                title="Esperando datos... Ejecuta el collector primero",
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[{
                    "text": "No hay datos disponibles. Asegúrate de que:<br>1. El collector esté recolectando datos<br>2. dbt run se haya ejecutado",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 14}
                }]
            )
            return fig

        fig = px.scatter_mapbox(df, 
                                lat="latitude", 
                                lon="longitude", 
                                color="bicis_promedio",
                                size="bicis_promedio",
                                hover_name="station_name",
                                color_continuous_scale=px.colors.cyclical.IceFire,
                                zoom=12, 
                                height=700)
        
        fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
        return fig
    except Exception as e:
        print(f"Error: {e}")
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {str(e)}",
            xaxis={"visible": False},
            yaxis={"visible": False}
        )
        return fig

if __name__ == '__main__':
    # Es vital que el host sea 0.0.0.0 para que Docker lo exponga al Mac
    app.run(host='0.0.0.0', port=8050, debug=False)