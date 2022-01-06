from dash import dash_table, dcc, html

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc


GREEN = '#40c057'

sign_in = html.Div(
    [
        dbc.Card(
            [
                html.P("Sign in to get started."),
                html.A(
                    dmc.Button(
                        "Sign In",
                        id='sign-in',
                        compact=True,
                        color='green',
                    ),
                    id='sign-in-url',
                ),
                dcc.Store(id='sign-in-debug'),
                dcc.Store(id='sign-in-token'),
            ],
            color='dark',
            body=True,
        )
    ],
    id='sign-in-div',
    hidden=True,
)


LABEL_STYLE = {
    'color': 'white',
    'backgroundColor': '#191919',
}
ACTIVE_LABEL_STYLE = {
    'color': GREEN,
    'backgroundColor': '#191919',
    'boxShadow': f'inset 0 -2px 0 {GREEN}'
}

scatterplot_tab = dbc.Tab(
    label_style=LABEL_STYLE,
    active_label_style=ACTIVE_LABEL_STYLE,
    label='Scatter/Line',
    children=[
        dbc.Row([
            dbc.Col(dbc.FormText("X-axis")),
            dbc.Col(dbc.FormText("Y-axis")),
            dbc.Col(dbc.FormText("Z-axis")),
            dbc.Col(dbc.FormText("Colorby")),
            dbc.Col(dbc.FormText("")),
        ]),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='scatter-xaxis')),
            dbc.Col(dcc.Dropdown(id='scatter-yaxis')),
            dbc.Col(dcc.Dropdown(id='scatter-zaxis')),
            dbc.Col(dcc.Dropdown(id='scatter-colorby')),
            dbc.Col(dbc.Switch(
                id='scatter-showlines',
                label="Show lines?",
            )),
        ]),
        html.Div(
            dcc.Graph(id='scatter'),
            className='my-4',
        ),
    ],
    style={'padding': '1rem'}
)

polarplot_tab = dbc.Tab(
    label_style=LABEL_STYLE,
    active_label_style=ACTIVE_LABEL_STYLE,
    label='Polar',
    children=[
        dbc.Row([
            dbc.Col(dbc.FormText("Dimensions (theta)"), width=6),
            dbc.Col(dbc.FormText("Range")),
            dbc.Col(),
            dbc.Col(dbc.FormText("Colorby")),
            dbc.Col(dbc.FormText("")),
        ]),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='polar-dims', multi=True), width=6),
            dbc.Col(dbc.Input(id='polar-range-min', type='number')),
            dbc.Col(dbc.Input(id='polar-range-max', type='number')),
            dbc.Col(dcc.Dropdown(id='polar-colorby')),
            dbc.Col(dbc.Switch(
                id='polar-showlines',
                label="Fill?",
                value=True,
            )),
        ]),
        html.Div(
            dcc.Graph(id='polar'),
            className='my-4',
        ),
    ],
    style={'padding': '1rem'}
)

ternaryplot_tab = dbc.Tab(
    label_style=LABEL_STYLE,
    active_label_style=ACTIVE_LABEL_STYLE,
    label='Ternary',
    children=[

    ],
    style={'padding': '1rem'}
)

visualizations = dbc.Tabs(
    [
        scatterplot_tab,
        polarplot_tab,
        ternaryplot_tab,
    ],
    style={
        'border-width': '0px',
    }
)


sidebar = html.Div(
    [
        html.H3("Spotiviz", style={'color': 'white'}),
        html.P("This is a demo dash app to visualize various aspects of the Spotify API with plotly and dash."),
        html.Hr(),
        html.Div(
            dmc.Chips(
                id='playlists',
                data=[],
                direction='column',
                color='green',
                multiple=True,
                size='xs',
                variant='filled',
                # style={
                #     'color': 'white',
                #     'background-color': 'black'
                # }
            ),
            style={
                'height': '60%',
                'overflow-y': 'auto',
            }
        ),
        html.Div(
            dcc.Loading(
                html.Div(
                    id='welcome-msg',
                ),
            ),
            style={
                'position': 'fixed',
                'bottom': 0,
                'left': '1rem',
                'padding': '1rem 0rem',
            }
        )
    ],
    style={
        'background-color': 'black',
        'padding': '1rem',
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'height': '100%',
        'width': '20rem',
    }
)


content = html.Div(
    [
        visualizations,
        html.Div(
            dash_table.DataTable(
                id='table',
                page_size=20,
                style_table={
                    'overflowX': 'auto',
                    #'overflowY': 'auto',
                    'color': 'white',
                },
                style_as_list_view=True,
                style_header={
                    'backgroundColor': GREEN,
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_cell={
                    'fontSize': '11px',
                    'minWidth': '150px',
                    'backgroundColor': '#111',
                },
                style_data={
                    'borderColor': '#333',
                },
                hidden_columns=[
                    'album.available_markets',
                    'available_markets',
                ],
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                #row_selectable="single",
            ),
            className='my-4',
        ),
        dcc.Store(id='track-data'),
    ],
    id='data-div',
    className="py-4",
    hidden=True,
)


page = html.Div(
    id='page-content',
    style={
        'padding': '1rem',
        'position': 'fixed',
        'top': 0,
        'left': '20rem',
        'right': '0',
        #'width': '80%',
        'height': '100%',
    }
)


LAYOUT = html.Div(
    [
        sidebar, 
        page,
        sign_in, 
        content,
        dcc.Location(id='url'),
    ],
)