"""
Dashboard Interactivo de Monitoreo de Sistemas
Departamento de Sistemas y Computación - ITM
Autor: Jordan Rivera Rodriguez
Fecha: Julio 2025

Dashboard web interactivo para visualización en tiempo real de métricas
y estado de los sistemas del departamento.
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import psutil
import json
from collections import deque
import threading
import time


class MonitoreoSistemas:
    """
    Clase para recopilar métricas de sistemas en tiempo real.
    
    Mantiene un buffer circular de datos históricos y proporciona
    métodos para obtener estadísticas actuales y tendencias.
    """
    
    def __init__(self, max_puntos=100):
        """
        Inicializa el monitor de sistemas.
        
        Args:
            max_puntos (int): Número máximo de puntos a mantener en historial
        """
        self.max_puntos = max_puntos
        self.datos_cpu = deque(maxlen=max_puntos)
        self.datos_memoria = deque(maxlen=max_puntos)
        self.datos_disco = deque(maxlen=max_puntos)
        self.datos_red = deque(maxlen=max_puntos)
        self.timestamps = deque(maxlen=max_puntos)
        self.activo = True
        
        # Iniciar thread de recolección
        self.thread_monitor = threading.Thread(target=self._recolectar_metricas)
        self.thread_monitor.daemon = True
        self.thread_monitor.start()
    
    def _recolectar_metricas(self):
        """
        Recolecta métricas del sistema cada segundo.
        Thread que se ejecuta continuamente en segundo plano.
        """
        bytes_enviados_prev = psutil.net_io_counters().bytes_sent
        bytes_recibidos_prev = psutil.net_io_counters().bytes_recv
        
        while self.activo:
            try:
                # CPU
                cpu_percent = psutil.cpu_percent(interval=1)
                self.datos_cpu.append(cpu_percent)
                
                # Memoria
                memoria = psutil.virtual_memory()
                self.datos_memoria.append(memoria.percent)
                
                # Disco
                disco = psutil.disk_usage('/')
                self.datos_disco.append(disco.percent)
                
                # Red (MB/s)
                net = psutil.net_io_counters()
                bytes_enviados = (net.bytes_sent - bytes_enviados_prev) / 1024 / 1024
                bytes_recibidos = (net.bytes_recv - bytes_recibidos_prev) / 1024 / 1024
                self.datos_red.append({
                    'enviados': bytes_enviados,
                    'recibidos': bytes_recibidos
                })
                bytes_enviados_prev = net.bytes_sent
                bytes_recibidos_prev = net.bytes_recv
                
                # Timestamp
                self.timestamps.append(datetime.now())
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error en recolección de métricas: {e}")
                time.sleep(5)
    
    def obtener_datos_actuales(self):
        """
        Obtiene las métricas más recientes del sistema.
        
        Returns:
            dict: Diccionario con métricas actuales
        """
        return {
            'cpu': list(self.datos_cpu),
            'memoria': list(self.datos_memoria),
            'disco': list(self.datos_disco),
            'red': list(self.datos_red),
            'timestamps': [t.strftime('%H:%M:%S') for t in self.timestamps]
        }
    
    def obtener_estadisticas(self):
        """
        Calcula estadísticas de las métricas recolectadas.
        
        Returns:
            dict: Estadísticas de CPU, memoria, disco y red
        """
        if not self.datos_cpu:
            return {}
            
        return {
            'cpu': {
                'actual': self.datos_cpu[-1] if self.datos_cpu else 0,
                'promedio': np.mean(self.datos_cpu),
                'maximo': max(self.datos_cpu),
                'minimo': min(self.datos_cpu)
            },
            'memoria': {
                'actual': self.datos_memoria[-1] if self.datos_memoria else 0,
                'promedio': np.mean(self.datos_memoria),
                'total_gb': psutil.virtual_memory().total / 1024**3
            },
            'disco': {
                'actual': self.datos_disco[-1] if self.datos_disco else 0,
                'total_gb': psutil.disk_usage('/').total / 1024**3,
                'libre_gb': psutil.disk_usage('/').free / 1024**3
            }
        }


# Inicializar monitor
monitor = MonitoreoSistemas()

# Crear aplicación Dash
app = dash.Dash(__name__)

# Estilos CSS personalizados
app.layout = html.Div([
    html.Div([
        html.H1('Dashboard de Monitoreo de Sistemas', 
                style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.H3('Departamento de Sistemas y Computación - ITM',
                style={'textAlign': 'center', 'color': '#7f8c8d'}),
        html.Hr()
    ]),
    
    # Cards de estadísticas
    html.Div([
        html.Div([
            html.Div([
                html.H4('CPU', style={'color': '#3498db'}),
                html.H2(id='cpu-actual', children='0%'),
                html.P(id='cpu-promedio', children='Promedio: 0%')
            ], className='stat-card', style={
                'backgroundColor': '#ecf0f1',
                'padding': '20px',
                'borderRadius': '10px',
                'textAlign': 'center',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], className='four columns'),
        
        html.Div([
            html.Div([
                html.H4('Memoria', style={'color': '#e74c3c'}),
                html.H2(id='memoria-actual', children='0%'),
                html.P(id='memoria-total', children='Total: 0 GB')
            ], className='stat-card', style={
                'backgroundColor': '#ecf0f1',
                'padding': '20px',
                'borderRadius': '10px',
                'textAlign': 'center',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], className='four columns'),
        
        html.Div([
            html.Div([
                html.H4('Disco', style={'color': '#2ecc71'}),
                html.H2(id='disco-actual', children='0%'),
                html.P(id='disco-libre', children='Libre: 0 GB')
            ], className='stat-card', style={
                'backgroundColor': '#ecf0f1',
                'padding': '20px',
                'borderRadius': '10px',
                'textAlign': 'center',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], className='four columns'),
    ], className='row', style={'marginBottom': '30px'}),
    
    # Gráficos en tiempo real
    html.Div([
        dcc.Graph(id='grafico-cpu', style={'height': '300px'}),
        dcc.Graph(id='grafico-memoria', style={'height': '300px'}),
        dcc.Graph(id='grafico-red', style={'height': '300px'})
    ]),
    
    # Intervalo para actualización automática
    dcc.Interval(
        id='interval-component',
        interval=2000,  # Actualizar cada 2 segundos
        n_intervals=0
    )
], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})


@app.callback(
    [Output('cpu-actual', 'children'),
     Output('cpu-promedio', 'children'),
     Output('memoria-actual', 'children'),
     Output('memoria-total', 'children'),
     Output('disco-actual', 'children'),
     Output('disco-libre', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def actualizar_estadisticas(n):
    """
    Actualiza las tarjetas de estadísticas con los valores más recientes.
    
    Args:
        n: Número de intervalos transcurridos (no utilizado directamente)
        
    Returns:
        tuple: Valores actualizados para cada componente
    """
    stats = monitor.obtener_estadisticas()
    
    if not stats:
        return '0%', 'Promedio: 0%', '0%', 'Total: 0 GB', '0%', 'Libre: 0 GB'
    
    return (
        f"{stats['cpu']['actual']:.1f}%",
        f"Promedio: {stats['cpu']['promedio']:.1f}%",
        f"{stats['memoria']['actual']:.1f}%",
        f"Total: {stats['memoria']['total_gb']:.1f} GB",
        f"{stats['disco']['actual']:.1f}%",
        f"Libre: {stats['disco']['libre_gb']:.1f} GB"
    )


@app.callback(
    Output('grafico-cpu', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def actualizar_grafico_cpu(n):
    """
    Actualiza el gráfico de uso de CPU.
    
    Returns:
        dict: Figura de Plotly con el gráfico actualizado
    """
    datos = monitor.obtener_datos_actuales()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=datos['timestamps'],
        y=datos['cpu'],
        mode='lines+markers',
        name='CPU %',
        line=dict(color='#3498db', width=2),
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.2)'
    ))
    
    fig.update_layout(
        title='Uso de CPU en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis_title='Porcentaje (%)',
        yaxis=dict(range=[0, 100]),
        template='plotly_white',
        height=250,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig


@app.callback(
    Output('grafico-memoria', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def actualizar_grafico_memoria(n):
    """
    Actualiza el gráfico de uso de memoria.
    
    Returns:
        dict: Figura de Plotly con el gráfico actualizado
    """
    datos = monitor.obtener_datos_actuales()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=datos['timestamps'],
        y=datos['memoria'],
        mode='lines+markers',
        name='Memoria %',
        line=dict(color='#e74c3c', width=2),
        fill='tozeroy',
        fillcolor='rgba(231, 76, 60, 0.2)'
    ))
    
    fig.update_layout(
        title='Uso de Memoria en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis_title='Porcentaje (%)',
        yaxis=dict(range=[0, 100]),
        template='plotly_white',
        height=250,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig


@app.callback(
    Output('grafico-red', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def actualizar_grafico_red(n):
    """
    Actualiza el gráfico de tráfico de red.
    
    Returns:
        dict: Figura de Plotly con el gráfico actualizado
    """
    datos = monitor.obtener_datos_actuales()
    
    if not datos['red']:
        return go.Figure()
    
    enviados = [d['enviados'] for d in datos['red']]
    recibidos = [d['recibidos'] for d in datos['red']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=datos['timestamps'],
        y=enviados,
        mode='lines',
        name='Enviados (MB/s)',
        line=dict(color='#2ecc71', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=datos['timestamps'],
        y=recibidos,
        mode='lines',
        name='Recibidos (MB/s)',
        line=dict(color='#f39c12', width=2)
    ))
    
    fig.update_layout(
        title='Tráfico de Red en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis_title='MB/s',
        template='plotly_white',
        height=250,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


if __name__ == '__main__':
    print("Iniciando Dashboard de Monitoreo...")
    print("Acceder a http://127.0.0.1:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)