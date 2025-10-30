# -*- coding: utf-8 -*-
#
# Copyright 2023 Goyo <goyodiaz@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import base64
import io

import matplotlib.pyplot as plt
import pandas as pd
import pyproj
import rasterio as rio
import streamlit as st
from affine import Affine
from wrg import WRG

__version__ = "0.0.1.dev"


def main():
    st.title("WRG explorer")
    uploaded = st.file_uploader(
        label="Upload WRG", key="uploaded", on_change=on_wrg_uploaded
    )
    if uploaded is None:
        st.stop()

    wrg = st.session_state.wrg
    left, right, bottom, top = tuple(map(float, wrg.extent()))

    attrs = pd.Series(
        {
            "Hub height": wrg.hub_height(),
            "Width:": wrg.nx,
            "Height": wrg.ny,
            "Number of sectors": wrg.nsectors,
            "Left, right, bottom, top": [left, right, bottom, top],
        },
        name="",
        dtype=str,
    )
    st.dataframe(attrs)

    variable = st.selectbox(
        label="Variable",
        options=[
            "Elevation",
            "Global scale",
            "Global shape",
            "Global speed",
            "Directional scale",
            "Directional shape",
            "Directional speed",
            "Directional frequency",
        ],
    )
    if variable == "Elevation":
        sector = None
        imdata = wrg.elev()
    elif variable == "Global scale":
        sector = None
        imdata = wrg.global_scale()
    elif variable == "Global shape":
        sector = None
        imdata = wrg.global_shape()
        sector = None
    elif variable == "Global speed":
        sector = None
        imdata = wrg.global_speed()
    elif variable == "Directional scale":
        sector = st.select_slider(label="Sector", options=range(wrg.nsectors))
        imdata = wrg.scale()[:, :, sector]
    elif variable == "Directional shape":
        sector = st.select_slider(label="Sector", options=range(wrg.nsectors))
        imdata = wrg.shape()[:, :, sector]
    elif variable == "Directional speed":
        sector = st.select_slider(label="Sector", options=range(wrg.nsectors))
        imdata = wrg.speed()[:, :, sector]
    elif variable == "Directional frequency":
        sector = st.select_slider(label="Sector", options=range(wrg.nsectors))
        imdata = wrg.freq()[:, :, sector]

    ax = plt.subplot()
    im = ax.imshow(imdata, origin="lower", extent=(left, right, bottom, top))
    cbar = ax.figure.colorbar(im)
    display_fig(ax.figure)

    pyproj_crs = st.selectbox(
        label="Coordinate reference system",
        options=get_crss(),
        index=None,
        format_func=lambda crs: f"{crs.name} ({crs.auth_name}:{crs.code})",
    )

    buf = io.BytesIO()
    with rio.open(
        fp=buf,
        mode="w",
        driver="GTiff",
        width=wrg.nx,
        height=wrg.ny,
        count=1,
        crs=(
            rio.crs.CRS.from_authority(
                auth_name=pyproj_crs.auth_name, code=pyproj_crs.code
            )
            if pyproj_crs
            else None
        ),
        transform=Affine.translation(xoff=left, yoff=top)
        * Affine.scale(wrg.cell_size, -wrg.cell_size),
        dtype=wrg.data.dtype,
        sharing=False,  # make it thread-safe.
    ) as tds:
        tds.write(imdata[::-1, :], indexes=1)

    variable = "_".join(variable.lower().split())
    if sector is None:
        file_name = f"{variable}.tif"
    else:
        file_name = f"{variable}_{sector:0>2}.tif"
    file_name = st.text_input(label="File name", value=file_name)

    st.download_button(
        label="Download",
        data=buf.getvalue(),
        file_name=file_name,
        mime="image/tiff; application=geotiff",
    )


@st.cache_resource
def get_crss():
    return pyproj.database.query_crs_info()


def on_wrg_uploaded():
    if st.session_state.uploaded is not None:
        st.session_state.wrg = WRG.from_file(buf=st.session_state.uploaded)


def display_fig(fig):
    # Using st.pyplot or st.image leads to changes in image size for reasons still unknown.
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    html = f"""<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">"""
    st.html(html)


if __name__ == "__main__":
    main()
