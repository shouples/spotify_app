from dash import dcc, html, Input, Output, State, ALL, MATCH
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from flask import request
from urllib import parse

import logging
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import pprint
import spotipy


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s.%(funcName)s | %(msg)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

CHAR_LIMIT = 40
SCOPE = 'user-library-read playlist-read-private'


def register_callbacks(app):
    logger = app.logger


    @app.callback(
        Output('sign-in-token', 'data'),
        Input('url', 'href'),
    )
    def store_token(url):
        parsed = parse.urlparse(url)
        args = parse.parse_qs(parsed.query)
        if args:
            token = args['code'][0]
            return token
        return


    @app.callback(
        Output('page-content', 'children'),
        Input('sign-in-token', 'data'),
        [
            State('sign-in-div', 'children'),
            State('data-div', 'children'),
        ]
    )
    def toggle_signin(token, sign_in, data):
        if not token:
            return sign_in
        
        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE)
        auth_manager.get_access_token(token)
        client = spotipy.Spotify(auth_manager=auth_manager)
        try:
            user = client.me()
            return data
        except Exception as e:
            logger.error(e)
        return sign_in


    @app.callback(
        Output('sign-in-url', 'href'),
        Input('url', 'href'),
    )
    def show_sign_in_link(x):
        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE)
        return auth_manager.get_authorize_url()


    @app.callback(
        Output('welcome-msg', 'children'),
        Input('sign-in-token', 'data'),
    )
    def show_welcome(token):
        if not token:
            return []
        
        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE)
        auth_manager.get_access_token(token)
        client = spotipy.Spotify(auth_manager=auth_manager)

        user = client.me()
        username = user['display_name']
        user_icon = user['images'][0]['url']
        logger.info(f"user info: {user}")

        user_bar = dbc.Row([
            dbc.Col(
                html.Img(
                    src=user_icon,
                    height='50px',
                )
            ),
            dbc.Col(
                html.H5(username, style={'color': '#ccc'})
            ),
        ])
        return user_bar


    @app.callback(
        Output('playlists', 'data'),
        Input('sign-in-token', 'data'),
    )
    def show_playlists(token):
        if not token:
            return dash.no_update

        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE)
        auth_manager.get_access_token(token)
        client = spotipy.Spotify(auth_manager=auth_manager)

        playlist_resp = client.current_user_playlists(limit=50)
        logger.info(f"playlist_resp keys: {playlist_resp.keys()}")
        if 'items' not in playlist_resp:
            return []
        playlists = playlist_resp['items']
        logger.info(f"playlists: {len(playlists)} --> {playlists[0]}")

        options = []
        for playlist in playlists:
            playlist_label = playlist['name'][:CHAR_LIMIT]
            if len(playlist['name']) > CHAR_LIMIT:
                playlist_label += "..."
            options.append({
                'label': playlist_label, 
                'value': playlist['id']
            })
        # options = sorted(options, key=lambda x: x['label'])
        return options


    @app.callback(
        Output('track-data', 'data'),
        Input('playlists', 'value'),
        [
            State('sign-in-token', 'data'),
            State('playlists', 'data'),
        ]
    )
    def load_playlist_tracks(playlist_ids, token, playlist_options):
        if not (token and playlist_ids):
            return []

        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE)
        auth_manager.get_access_token(token)
        client = spotipy.Spotify(auth_manager=auth_manager)

        playlist_id_to_name = {p['value']: p['label'] for p in playlist_options}

        data = []
        for playlist_id in playlist_ids:

            # pull playlist information to get tracks
            playlist_resp = client.playlist_items(playlist_id, fields=['total'])
            logger.info(f"playlist_resp --> {playlist_resp}")
            if 'total' not in playlist_resp:
                logger.warning(f"`total` not in playlist_items() response: {playlist_resp}")
                continue

            tracks = []
            total = playlist_resp['total']
            tracks_count = len(tracks)
            while tracks_count < total:
                playlist_info = client.playlist_items(playlist_id, offset=tracks_count)
                playlist_tracks = playlist_info['items']
                logger.info(f"playlist `{playlist_id}` tracks ({tracks_count}/{total}) --> {pprint.pformat(playlist_info, depth=2)}")
                tracks += playlist_tracks
                tracks_count = len(tracks)

                # add extra track info (acousticness/dancceability/energy/etc)
                track_uris = [t['track']['uri'] for t in playlist_tracks]
                feats = client.audio_features(tracks=track_uris)

                for playlist_track, feat in zip(playlist_tracks, feats):
                    track = playlist_track['track']
                    track['user_playlist'] = playlist_id_to_name[playlist_id]
                    feat_rec = {"audio_feature." + k: v for k, v in feat.items()}
                    track.update(feat_rec)

                    for k, v in playlist_track.items():
                        if isinstance(v, (dict, list)):
                            logger.warning(f"not adding {type(v)} --> {k}: {v}")
                            continue
                        track[k] = v

                    if track not in data:
                        data.append(track)

        df = pd.json_normalize(data)
        df['artists'] = df['artists'].apply(
            lambda x: ", ".join(sorted([a['name'] for a in x]))
        )

        for col in df.columns:
            has_lists = df[col].apply(lambda x: isinstance(x, list)).any()
            if not has_lists.any():
                continue
            try:
                df[col] = df[col].apply(lambda x: "/".join(x))
            except Exception as e:
                logger.error(f"error expanding `{col}`: {e} --> {df[col].values[0]}")
                df.drop(col, axis=1, inplace=True)

        for col in ['added_at', 'album.release_date']:
            if col not in df.columns:
                df[col] = pd.NA
            df[col] = pd.to_datetime(df[col])

        return df.to_dict("records")


    @app.callback(
        Output('scatter-colorby', 'value'),
        Input('track-data', 'data'),
        State('scatter-colorby', 'value'),
    )
    def set_default_colorby(data, colorby):
        if not data:
            return dash.no_update
        colorby = colorby or 'user_playlist'
        return colorby

    
    @app.callback(
        Output('polar-colorby', 'value'),
        Input('track-data', 'data'),
        State('polar-colorby', 'value'),
    )
    def set_default_colorby(data, colorby):
        if not data:
            return dash.no_update
        colorby = colorby or 'user_playlist'
        return colorby


    @app.callback(
        Output('table', 'columns'),
        Input('track-data', 'data'),
    )
    def show_table_columns(data):
        if not data:
            return []

        df = pd.DataFrame(data)
        columns = [
            {'id': col, 'name': col, 'hideable': True}
            for col in df.columns
        ]
        columns = sorted(columns, key=lambda x: x['name'])
        return columns


    @app.callback(
        Output('table', 'hidden_columns'),
        Input('track-data', 'data'),
    )
    def show_table_columns(data):
        if not data:
            return []

        df = pd.DataFrame(data)
        columns = [
            c for c in df.columns 
            if c.endswith((".uri", ".id", "available_markets", "isrc"))
            or "_url" in c or "href" in c
            or c == 'id'
        ]
        return columns


    @app.callback(
        Output('table', 'data'),
        Input('track-data', 'data')
    )
    def show_table(data):
        if not data:
            return []
        logger.info(f"loading {len(data)} row(s) into table: {pprint.pformat(data[:3], depth=2)}")
        return data


    @app.callback(
        [
            Output('scatter-xaxis', 'options'),
            Output('scatter-yaxis', 'options'),
            Output('scatter-zaxis', 'options'),
            Output('scatter-colorby', 'options'),
            Output('polar-dims', 'options'),
            Output('polar-colorby', 'options'),
        ],
        Input('track-data', 'data'),
    )
    def add_columns(data):
        if not data:
            return dash.no_update

        df = pd.DataFrame(data)
        columns = [
            {'label': col, 'value': col}
            for col in df.columns
        ]
        columns = sorted(columns, key=lambda x: x['label'])
        return [columns] * 6


    @app.callback(
        Output('scatter', 'figure'),
        [
            Input('scatter-xaxis', 'value'),
            Input('scatter-yaxis', 'value'),
            Input('scatter-zaxis', 'value'),
            Input('scatter-colorby', 'value'),
            Input('scatter-showlines', 'value'),
        ],
        State('track-data', 'data'),
    )
    def render_scatterplot(xaxis, yaxis, zaxis, colorby, show_lines, data):
        fig = go.Figure()
        fig.update_layout(
            template='plotly_dark',
            height=600,
            margin=dict(t=30, l=0, r=0, b=0),
        )

        if not (data and xaxis and yaxis):
            return fig

        df = pd.DataFrame(data)
        
        df['color'] = ''
        if colorby is not None:
            df['color'] = df[colorby]

        mode = 'markers'
        if show_lines:
            mode = 'markers+lines'
            df.sort_values(xaxis, inplace=True)

        if zaxis is not None:
            for group, group_df in df.groupby('color'):
                group_label = group[:CHAR_LIMIT]
                if len(group) > CHAR_LIMIT:
                    group_label += "..."
                fig.add_trace(
                    go.Scatter3d(
                        x=group_df[xaxis],
                        y=group_df[yaxis],
                        z=group_df[zaxis],
                        name=group_label,
                        mode=mode,
                        marker=dict(
                            opacity=0.6,
                        ),
                    )
                )
            fig.update_layout(
                scene=dict(
                    xaxis_title=xaxis,
                    yaxis_title=yaxis,
                    zaxis_title=zaxis,
                )
            )

        else:
            # 2D plot
            for group, group_df in df.groupby('color'):
                group_label = group[:CHAR_LIMIT]
                if len(group) > CHAR_LIMIT:
                    group_label += "..."
                fig.add_trace(
                    go.Scatter(
                        x=group_df[xaxis],
                        y=group_df[yaxis],
                        name=group_label,
                        mode=mode,
                        marker=dict(
                            opacity=0.6,
                        ),
                    )
                )
            fig.update_layout(
                xaxis_title=xaxis,
                yaxis_title=yaxis,
            )

        return fig


    @app.callback(
        Output('polar-dims', 'value'),
        Input('track-data', 'data'),
        State('polar-dims', 'value'),
    )
    def show_default_polar_dimensions(data, dims):
        if not data:
            return []
        df = pd.DataFrame(data)
        default_dims = [
            'audio_feature.acousticness',
            'audio_feature.danceability',
            'audio_feature.energy',
            'audio_feature.instrumentalness',
            'audio_feature.liveness',
            'audio_feature.speechiness',
            'audio_feature.valence',
        ]
        dims = dims or default_dims
        return dims


    @app.callback(
        Output('polar', 'figure'),
        [
            Input('polar-dims', 'value'),
            Input('polar-range-min', 'value'),
            Input('polar-range-max', 'value'),
            Input('polar-colorby', 'value'),
            Input('polar-showlines', 'value'),
        ],
        State('track-data', 'data'),
    )
    def render_polarplot(dims, range_min, range_max, colorby, show_lines, data):
        fig = go.Figure()
        fig.update_layout(
            template='plotly_dark',
            height=600,
            margin=dict(t=10, l=0, r=0, b=10),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[range_min, range_max]
                )
            ),
        )

        if not (data and dims):
            return fig
        if len(dims) < 2:
            return fig

        df = pd.DataFrame(data)
        
        df['color'] = ''
        if colorby is not None:
            df['color'] = df[colorby]

        mode = 'markers'
        fill = None
        if show_lines:
            mode = 'markers+lines'
            fill = 'toself'
            
        for group, group_df in df.groupby('color'):
            group_label = group[:CHAR_LIMIT]
            if len(group) > CHAR_LIMIT:
                group_label += "..."

            melted_df = group_df.melt(
                id_vars=['id'],
                value_vars=dims,
            ).sort_values(['id', 'variable'])

            fig.add_trace(
                go.Scatterpolargl(
                    r=melted_df['value'],
                    theta=melted_df['variable'],
                    marker=dict(
                        opacity=0.5,
                    ),
                    fill=fill,
                    mode=mode,
                    name=group_label,
                ),
            )

        return fig


    return app