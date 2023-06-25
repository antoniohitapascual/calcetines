import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output, State

import pandas as pd
import re
import io
import plotly.graph_objects as go


#  *************************** CONFIGURACIÓN *************************** #º
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "styles.css"])
# Para render.com
server = app.server
app.title = 'El Calcetines: Dashboard'
app._favicon = "favicon.png"

#  *************************** CARGA DE DATOS *************************** #
hoja = './input/FinalOutput230520.xlsx'

#    Carga de datos y preparación del dataframe
df_total = pd.read_excel(hoja)


df_filtrado = pd.DataFrame()


# *************************** DISEÑO DEL DASHBOARD *************************** #

# *****                     Layout del título                  ***** #
titulo = dbc.Row(
    [
        dbc.Col(
            html.Img(src="assets/images/falke_germany_1895_logo.svg", style={'height':'35%', 'width':'35%'}),
            className="text-center"
        ),
    ]
)







# *****                     Objetos del panel izquierdo                    ***** #
# Etiquetas de línea de producto y categoría
label_product_line = html.H1("Product Line",style={'textAlign': 'Left'}, className="h2")
label_category = html.H1("Category",style={'textAlign': 'Left'}, className="h2")

# Filtros de línea de producto y categoría
dropdown_product_line = dcc.Dropdown(
                                        id='productline-dropdown',
                                        className='dropdown',
                                        options=[{'label': i, 'value': i} for i in df_total['ProductLine'].unique()],
                                        value=df_total['ProductLine'].unique()[0]
                                    )
dropdown_category = dcc.Dropdown(
                                        id='category-dropdown',
                                        className='dropdown',
                                        # options=[{'label': i, 'value': i} for i in ['Category1', 'Category2', 'Category3', 'Category4', 'UDF_SEASON_CLASS', 'UDF_GENDER', 'UDF_PRODUCT_CATEGORY', 'ProductLineDesc']],        
                                        options=[{'label': i, 'value': i} for i in ['Category1', 'Category2', 'Category3', 'Category4', 'UDF_SEASON_CLASS', 'UDF_GENDER', 'UDF_PRODUCT_CATEGORY', 'ProductLineDesc']],
                                        value='Category1'
                                    )

#            La tabla de datos va dentro de un div para poder aplicarle estilos css
tabla_datos = html.Div(
                            className='table-container',
                            children=[
                                dash_table.DataTable(
                                    id='summary-table',
                                    columns=[],
                                )
                            ]
                        )

# Slider para la variación de fechas
label_slider = html.H1("Prop Order",style={'textAlign': 'Left'}, className="h2")
slider_prop_order = html.Div([dcc.Slider(0, 100, 5, value=75, id="slider-prop-order", className="slider")])



# *****                     Layout panel izquierdo                  ***** #
panel_izquierdo = dbc.Col([
    label_product_line, 
    dropdown_product_line,
    label_slider,
    slider_prop_order,
    label_category, 
    dropdown_category,
    tabla_datos
],
    className='vertical-separator')


# *****                     Objetos del panel derecho                    ***** #
btn_download = html.Div([html.Button("Download data", id="btn_excel"), dcc.Download(id="download-excel-index")])
grafico_barras = dcc.Graph(id='summary-graph')
grafico_lineas = dcc.Graph(id='timeline-graph')


# *****                     Layout panel derecho                  ***** #
panel_derecho = dbc.Col([
    grafico_barras,
    grafico_lineas,
    btn_download
])

# *************************** LAYOUT GENERAL *************************** #
# Este layout recoge los objetos que hemos creado anteriormente
app.layout = dbc.Container([
    dbc.Row([
        titulo,
        dbc.Row([
            panel_izquierdo,
            panel_derecho
    ])
    ])
], fluid=True)


# ******************************************** CALLBACKS *********************************************** #
# Los callbacks son funciones que se ejecutan cuando se produce un evento
@app.callback(
    Output('summary-table', 'data'),
    Output('summary-table', 'columns'), 
    Output('summary-graph', 'figure'),    
    Output('timeline-graph', 'figure'),    
    Input('productline-dropdown', 'value'),
    Input('slider-prop-order', 'value'),
    Input('category-dropdown', 'value')
)
def update_table_and_graph(selected_productline, slider_value, selected_category):
    ''' 
        Esta función se ejecuta cuando cambia el valor de alguno de los dropdowns selected_productline o selected_category
    '''
    # Traemos la referencia al dataframe global
    global df_filtrado

    # Filtramos el dataframe por la línea de producto seleccionada
    df_filtered = df_total[df_total['ProductLine'] == selected_productline]
    
    # Calculamos el campo PropOrder
    df_filtered['PropOrder'] = slider_value * df_filtered['3MCov'] - df_filtered['StockPrev']
    
    # Buscamos las columnas que cumplen el patron YYYY-MM
    pattern = r'^\d{4}-\d{2}$'  # Este es un patrón que coincide con cuatro dígitos seguidos de un guión seguido de dos dígitos
    date_columns = [col for col in df_filtered.columns if re.match(pattern, col)]
    
    # Paso a numerico las columnas que son numéricas
    # Lista de columnas a convertir.
    columns_to_convert = ['QuantityOnHand', 'QuantityOnPurchaseOrder', 'QuantityOnSalesOrder', 'QuantityOnBackOrder', 'PropOrder']

    df_filtered[columns_to_convert] = df_filtered[columns_to_convert].apply(pd.to_numeric, errors='coerce')
    
    # Diccionario inicial con las columnas fijas
    agg_dict = {
        'QuantityOnHand': 'sum',
        'QuantityOnPurchaseOrder': 'sum',
        'QuantityOnSalesOrder': 'sum',
        'QuantityOnBackOrder': 'sum',
        'PropOrder': 'sum'
    }

    # Actualizar el diccionario con las columnas dinámicas
    for column in date_columns:
        agg_dict[column] = 'sum'

    # Agrupar el dataframe por la categoría seleccionada y aplicar las funciones de agregación
    df_grouped = df_filtered.groupby(selected_category).agg(agg_dict).reset_index()


     
    # Aplicar formato a los campos numéricos
    df_grouped[['QuantityOnHand', 'QuantityOnPurchaseOrder', 'QuantityOnSalesOrder', 'QuantityOnBackOrder', 'PropOrder']] = df_grouped[['QuantityOnHand', 'QuantityOnPurchaseOrder', 'QuantityOnSalesOrder', 'QuantityOnBackOrder', 'PropOrder']].applymap(format_number)




    # +++++++++++ Gráfico de barras +++++++++++ #
    figure = {
        'data': [
            {'x': df_grouped[selected_category], 'y': df_grouped['QuantityOnHand'], 'type': 'bar', 'name': 'QuantityOnHand'},
            {'x': df_grouped[selected_category], 'y': df_grouped['QuantityOnPurchaseOrder'], 'type': 'bar', 'name': 'QuantityOnPurchaseOrder'},
            {'x': df_grouped[selected_category], 'y': df_grouped['QuantityOnSalesOrder'], 'type': 'bar', 'name': 'QuantityOnSalesOrder'},
            {'x': df_grouped[selected_category], 'y': df_grouped['QuantityOnBackOrder'], 'type': 'bar', 'name': 'QuantityOnBackOrder'},
            {'x': df_grouped[selected_category], 'y': df_grouped['PropOrder'], 'type': 'bar', 'name': 'PropOrder'}
        ],
        'layout': {
            'title': 'Summary per Product Line'
        }
    }

     # +++++++++++ Gráfico de líneas +++++++++++ #
    line_figure = go.Figure()
    
    # Sumamos las columnas que cumplen el patrón
    df_sum = df_grouped[date_columns].sum().to_frame().T

    # Añadir una traza
    line_figure.add_trace(
        go.Scatter(
            x=df_sum.columns,  # meses
            y=df_sum.iloc[0],  # valores
            mode='lines+markers',  # lineas conectadas con marcadores
            name='Suma de valores',
        )
    )

    line_figure.update_layout(
        title='Sales per Product Line',
        xaxis_title='Mes',
        yaxis_title='Suma de valores',
    )




    # Crea la lista de columnas dinámicamente basándote en el selected_category y las otras columnas
    columns=[{'name': i, 'id': i} for i in [selected_category, 'QuantityOnHand', 'QuantityOnPurchaseOrder', 'QuantityOnSalesOrder', 'QuantityOnBackOrder', 'PropOrder']]

    # Paso a la variable global el dataframe filtrado para que esté disponible en otros callbacks
    df_filtrado = df_filtered

    return df_grouped.to_dict('records'), columns, figure, line_figure


@app.callback(
        Output("download-excel-index", "data"), 
        Input("btn_excel", "n_clicks")
)
def func(n_clicks):
    # Traemos la referencia al dataframe global
    global df_filtrado
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate
    else:
        return dcc.send_data_frame(df_filtrado.to_excel, "download_data.xlsx", sheet_name="Sheet_name_1", index = False)
    

# *************************** FUNCIONES AUXILIARES *************************** #    
def format_number(value):
    return "{:,.0f}".format(value)

def convert_columns_to_int(df, column_list):    
    for column in column_list:
        df[column] = df[column].astype(int)
    return df



# *************************** EJECUCIÓN *************************** #
if __name__ == '__main__':
    # app.run_server(debug=True)
    app.run_server(debug=False, host='tebada.duckdns.org')
