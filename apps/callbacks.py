from dash import dcc, html, Input, Output, State, ALL, MATCH
from flask import request

import spotipy

import dash
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import pprint
from urllib import parse


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
        logger.info(f"user info: {user}")
        return f"Hello, {username}."


    @app.callback(
        Output('user-playlists', 'options'),
        Input('sign-in-token', 'data'),
        prevent_initial_call=True,
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
        return [{'label': p['name'], 'value': p['id']} for p in playlists]


    @app.callback(
        Output('track-data', 'data'),
        Input('load-playlist', 'n_clicks'),
        [
            State('sign-in-token', 'data'),
            State('user-playlists', 'value'),
            State('user-playlists', 'options'),
        ]
    )
    def load_playlist_tracks(clicks, token, playlist_ids, playlist_options):
        if not (token and playlist_ids):
            return []

        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE)
        auth_manager.get_access_token(token)
        client = spotipy.Spotify(auth_manager=auth_manager)

        playlist_id_to_name = {p['value']: p['label'] for p in playlist_options}
        data = []
        for playlist_id in playlist_ids:
            # pull playlist information to get tracks
            playlist_info = client.playlist(playlist_id)
            logger.info(f"playlist `{playlist_id}` track --> {pprint.pformat(playlist_info, depth=2)}")
            tracks = playlist_info['tracks']['items']

            # add extra track info (acousticness/dancceability/energy/etc)
            track_uris = [t['track']['uri'] for t in tracks]
            feats = client.audio_features(tracks=track_uris)

            for playlist_track, feat in zip(tracks, feats):
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
        return df.to_dict("records")


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
            if c.endswith((".uri", ".id", "available_markets"))
            or "_url" in c or "href" in c
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
        return [columns] * 4


    @app.callback(
        Output('scatter', 'figure'),
        [
            Input('scatter-xaxis', 'value'),
            Input('scatter-yaxis', 'value'),
            Input('scatter-zaxis', 'value'),
            Input('scatter-colorby', 'value'),
        ],
        State('track-data', 'data'),
    )
    def render_scatterplot(xaxis, yaxis, zaxis, colorby, data):
        fig = go.Figure()
        fig.update_layout(
            template='plotly_white',
            height=600,
            margin=dict(t=30, l=0, r=0, b=0),
        )

        if not (data and xaxis and yaxis):
            return fig

        df = pd.DataFrame(data)
        
        df['color'] = ''
        if colorby is not None:
            df['color'] = df[colorby]

        if zaxis is not None:
            for group, group_df in df.groupby('color'):
                fig.add_trace(
                    go.Scatter3d(
                        x=group_df[xaxis],
                        y=group_df[yaxis],
                        z=group_df[zaxis],
                        name=group,
                        mode='markers',
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
                fig.add_trace(
                    go.Scatter(
                        x=group_df[xaxis],
                        y=group_df[yaxis],
                        name=group,
                        mode='markers',
                    )
                )
            fig.update_layout(
                xaxis_title=xaxis,
                yaxis_title=yaxis,
                zaxis_title=zaxis,
            )
            
        return fig


    return app