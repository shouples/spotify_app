from dash import dash_table, dcc, html

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc


sign_in = html.Div(
    [
        dmc.Alert(
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
            color='orange',
            show=True,
        )
    ],
    id='sign-in-div',
    hidden=True,
)


visualizations = dbc.Card(
    dbc.Tabs(
        [
            dbc.Tab(
                label='Scatter/Line',
                children=[
                    dbc.Row([
                        dbc.Col("X-axis"),
                        dbc.Col("Y-axis"),
                        dbc.Col("Z-axis"),
                        dbc.Col("Colorby"),
                    ]),
                    dbc.Row([
                        dbc.Col(dcc.Dropdown(id='scatter-xaxis')),
                        dbc.Col(dcc.Dropdown(id='scatter-yaxis')),
                        dbc.Col(dcc.Dropdown(id='scatter-zaxis')),
                        dbc.Col(dcc.Dropdown(id='scatter-colorby')),
                    ]),

                    html.Div(
                        dcc.Graph(id='scatter'),
                        className='my-4',
                    ),
                ],
                style={'padding': '1rem'}
            ),
            dbc.Tab(
                label='Polar',
            ),
            dbc.Tab(
                label='Ternary',
            ),
        ],
    ),
)


content = html.Div(
    [

        dcc.Loading(
            dmc.Alert(
                id='welcome-msg',
                color='indigo',
                show=True,
                className='mb-4',
            ),
        ),

        dbc.Row([
            dbc.Col(
                dbc.FormText("Playlist"), 
                width=10
            ),
            dbc.Col(width=2),
        ]),

        dbc.Row([
            dbc.Col(
                [
                    dcc.Loading(
                        dcc.Dropdown(
                            id='user-playlists',
                            multi=True,
                        )
                    ),
                ],
                width=10,
            ),
            dbc.Col(
                dmc.Button(
                    "Load Tracks", 
                    id='load-playlist',
                    color='green',
                    style={'width': '100%'},
                ),
                width=2,
            )
        ]),

        html.Div(
            dash_table.DataTable(
                id='table',
                page_size=10,
                style_table={
                    'overflowX': 'auto',
                    #'overflowY': 'auto',
                    'color': 'black',
                },
                style_as_list_view=True,
                style_header={
                    'backgroundColor': '#40c057',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_cell={
                    'fontSize': '11px',
                    'minWidth': '150px',
                },
                hidden_columns=[
                    'album.available_markets',
                    'available_markets',
                ],
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
            ),
            className='my-4',
        ),
        dcc.Store(id='track-data'),

        visualizations,
        
    ],
    id='data-div',
    className="py-4",
    hidden=True,
)


page = html.Div(
    id='page-content',
)


main = html.Div(
    [
        html.H1("Spotiviz", className='display-3'),
        html.P("This is a demo dash app to visualize various aspects of the Spotify API with plotly and dash."),
    ],
)


LAYOUT = html.Div(
    [
        main,
        sign_in, 
        content,
        page,
        dcc.Location(id='url'),
    ],
    style={'margin': '1rem'}
)