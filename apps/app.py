import callbacks
import layout

import dash_bootstrap_components as dbc
import dash
import flask


app = dash.Dash(
    server=flask.Flask(__name__),
    title="Spotiviz",
    external_stylesheets=[
        dbc.themes.ZEPHYR,
        dbc.icons.FONT_AWESOME,
    ],
)
server = app.server


app.layout = layout.LAYOUT
callbacks.register_callbacks(app)


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)