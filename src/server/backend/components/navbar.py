import dash_bootstrap_components as dbc
from backend.param.constants import CORR_URL, ABOUT_URL, CORR_OUT_URL, DEV_CTX_URL, RESULT_URL

from backend.param.styles import LINK_DARK_CONTENT_STYLE
from backend.param.colors import PRIMARY_DARK


def navbar():
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Home", href="/home", style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("Correlate", href=CORR_URL, style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("Log", href=CORR_OUT_URL, style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("Deviation & Context", href=DEV_CTX_URL, style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("Result", href=RESULT_URL, style=LINK_DARK_CONTENT_STYLE)),
            dbc.NavItem(dbc.NavLink("About", href=ABOUT_URL, style=LINK_DARK_CONTENT_STYLE))
        ],
        id="navbar",
        brand="Contect",
        brand_href="/home",
        sticky="top",
        color=PRIMARY_DARK,
        dark=True,
        fluid=True,
        style={"width": "100%",
               "margin": "0",
               "padding": "0"}
    )

