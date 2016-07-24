#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Simple REST HTTP Weather Server using DWD weather data for Germany
    Copyright (C) 2016 Andreas Stöckel

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

################################################################################
# AUXILIARY CLASSES
################################################################################

# -----------------------------------------------------------------------------
# Name:        html_table_parser
# Purpose:     Simple class for parsing an (x)html string to extract tables.
#              Written in python3
#
# Author:      Josua Schmid
#
# Created:     05.03.2014
# Copyright:   (c) Josua Schmid 2014
# Licence:     AGPLv3
# -----------------------------------------------------------------------------

from html.parser import HTMLParser


class HTMLTableParser(HTMLParser):
    """ This class serves as a html table parser. It is able to parse multiple
    tables which you feed in. You can access the result per .tables field.
    """

    def __init__(self, decode_html_entities=False, data_separator=' ', ):

        HTMLParser.__init__(self)

        self._parse_html_entities = decode_html_entities
        self._data_separator = data_separator

        self._in_td = False
        self._in_th = False
        self._current_table = []
        self._current_row = []
        self._current_cell = []
        self.tables = []

    def handle_starttag(self, tag, attrs):
        """ We need to remember the opening point for the content of interest.
        The other tags (<table>, <tr>) are only handled at the closing point.
        """
        if tag == 'td':
            self._in_td = True
        if tag == 'th':
            self._in_th = True

    def handle_data(self, data):
        """ This is where we save content to a cell """
        if self._in_td or self._in_th:
            self._current_cell.append(data.strip())

    def handle_charref(self, name):
        """ Handle HTML encoded characters """

        if self._parse_html_entities:
            self.handle_data(self.unescape('&#{};'.format(name)))

    def handle_endtag(self, tag):
        """ Here we exit the tags. If the closing tag is </tr>, we know that we
        can save our currently parsed cells to the current table as a row and
        prepare for a new row. If the closing tag is </table>, we save the
        current table and prepare for a new one.
        """
        if tag == 'td':
            self._in_td = False
        elif tag == 'th':
            self._in_th = False

        if tag in ['td', 'th']:
            final_cell = self._data_separator.join(self._current_cell).strip()
            self._current_row.append(final_cell)
            self._current_cell = []
        elif tag == 'tr':
            self._current_table.append(self._current_row)
            self._current_row = []
        elif tag == 'table':
            self.tables.append(self._current_table)
            self._current_table = []

################################################################################
# TRANSLATION TABLES AND OTHER CONSTANTS
################################################################################

# Datatype used for the numpy structured array
RECORD_DTYPE = [
    ("latitude", "f4"), ("longitude", "f4"), ("altitude", "f4"),
    ("temperature", "f4"), ("pressure", "f4"), ("humidity", "f4"),
    ("precipitation", "f4"), ("wind_direction_x", "f4"),
    ("wind_direction_y", "f4"), ("wind_speed", "f4"), ("wind_speed_max", "f4")
]

# Border contour used when plotting the data
# https://www.google.com/fusiontables/data?docid=1zn8cjdD6qlAFI7ALMEnwn89g50weLi1D-bAGSZw
GERMAN_BORDER = [
    [10.979445, 54.380556], [10.818537, 53.890055], [12.526945, 54.474161],
    [12.924166, 54.426943], [12.369722, 54.265001], [13.02389, 54.399721],
    [13.455832, 54.096109], [13.718332, 54.169718], [13.813055, 53.845278],
    [14.275629, 53.699068], [14.149168, 52.86278], [14.640276, 52.572496],
    [14.599443, 51.818605], [15.03639, 51.285555], [14.828333, 50.865831],
    [14.309721, 51.053606], [12.093706, 50.322535], [12.674444, 49.424997],
    [13.833612, 48.773607], [12.758333, 48.123888], [13.016668, 47.470278],
    [12.735556, 47.684168], [11.095556, 47.396112], [10.478056, 47.591944],
    [10.173334, 47.274721], [9.566725, 47.540453], [8.566111, 47.80694],
    [8.576422, 47.591372], [7.697226, 47.543329], [7.58827, 47.584482],
    [7.57889, 48.119722], [8.22608, 48.964418], [6.362169, 49.459391],
    [6.524446, 49.808611], [6.134417, 50.127848], [6.398207, 50.323175],
    [6.011801, 50.757273], [5.864721, 51.046106], [6.222223, 51.46583],
    [5.9625, 51.807779], [6.82889, 51.965555], [7.065557, 52.385828],
    [6.68889, 52.549166], [7.051668, 52.64361], [7.208364, 53.242807],
    [7.015554, 53.414721], [7.295835, 53.685274], [8.008333, 53.710001],
    [8.503054, 53.354166], [8.665556, 53.893885], [9.832499, 53.536386],
    [8.899721, 53.940828], [8.883612, 54.294168], [8.599443, 54.333887],
    [9.016943, 54.498331], [8.580549, 54.86788], [8.281111, 54.746943],
    [8.393332, 55.053057], [8.664545, 54.913095], [9.44536, 54.825403],
    [9.972776, 54.76111], [9.870279, 54.454439], [10.979445, 54.380556]
]

# Map from wind direction names to vectorial wind direction
DWD_DIRECTION_MAP = {
    "N": (0.00, 1.00),
    "NO": (0.71, 0.71),
    "O": (1.00, 0.00),
    "SO": (0.71, -0.71),
    "S": (0.0, -1.0),
    "SW": (-0.71, -0.71),
    "W": (-1.0, 0.0),
    "NW": (0.71, -0.71),
}

# Map from table column names to the record keys, including a potential scale
# factor
DWD_KEY_MAP = {
    "STATION": "station",
    "Station": "station",
    "HÖHE": "altitude",
    "LUFTD.": "pressure",
    "TEMP.": "temperature",
    "U%": "humidity",
    "RR1": "precipitation",
    "RR30": ("precipitation", 2.0),
    "DD": "wind_direction",
    "FF": ("wind_speed", 1.0 / 3.6),
    "FX": ("wind_speed_max", 1.0 / 3.6),
}

# FTP server URL
DWD_SERVER = "ftp-outgoing2.dwd.de"

# Directory from which the newest file is read
DWD_OBSERVATIONS_URL = "gds/specials/observations/tables/germany/"

# Coordinates (altitude, longitude, latitude) for each of the stations present
# in the dataset
DWD_STATION_LOCATION_MAP = {
    "Aachen": (231, 50.8, 6.02),
    "Angermünde": (54, 53.03, 13.99),
    "Arkona": (42, 54.68, 13.43),
    "Augsburg": (461, 48.43, 10.94),
    "Bad Lippspringe": (140, 51.78, 8.82),
    "Bamberg": (240, 49.87, 10.92),
    "Berlin-Dahlem": (51, 52.45, 13.3),
    "Berlin-Tegel": (36, 52.56, 13.31),
    "Berlin-Tempelhof": (48, 52.47, 13.4),
    "Bremen-Flh.": (4, 53.05, 8.8),
    "Brocken": (1141, 51.8, 10.62),
    "Cottbus": (69, 51.78, 14.32),
    "Cuxhaven": (5, 53.87, 8.71),
    "Dresden-Flh.": (221, 51.13, 13.76),
    "Düsseldorf-Flh.": (37, 51.3, 6.77),
    "Emden": (0, 53.39, 7.23),
    "Erfurt": (316, 50.98, 10.96),
    "Essen": (150, 51.4, 6.97),
    "Fehmarn": (3, 54.53, 11.06),
    "Feldberg/Schw.": (930, 47.87, 8.0),
    "Fichtelberg": (654, 49.98, 11.84),
    "Frankfurt/M-Flh.": (100, 50.03, 8.57),
    "Freudenstadt": (797, 48.45, 8.41),
    "Fritzlar": (172, 51.12, 9.28),
    "Fürstenzell": (476, 48.55, 13.35),
    "Gera": (311, 50.88, 12.13),
    "Gießen/Wettenberg": (203, 50.6, 8.64),
    "Greifswald": (2, 54.1, 13.41),
    "Grosser Arber": (1455, 49.11, 13.14),
    "Görlitz": (238, 51.16, 14.95),
    "Hahn-Flh.": (497, 49.95, 7.26),
    "Hamburg-Flh.": (11, 53.63, 9.99),
    "Hannover-Flh.": (55, 52.46, 9.68),
    "Helgoland": (4, 54.17, 7.89),
    "Hof": (565, 50.31, 11.88),
    "Hohenpeissenberg": (977, 47.8, 11.01),
    "Kahler Asten": (839, 51.18, 8.49),
    "Karlsruhe-Rheinst.": (116, 48.96, 8.29),
    "Kempten": (705, 47.72, 10.33),
    "Kiel": (27, 54.38, 10.14),
    "Konstanz": (443, 47.68, 9.19),
    "Köln/Bonn-Flh.": (92, 50.86, 7.16),
    "Lahr": (155, 48.36, 7.83),
    "Leipzig-Flh.": (131, 51.43, 12.24),
    "Leuchtt. Alte Weser": (0, 53.86, 8.13),
    "Leuchtturm Kiel": (0, 54.5, 10.27),
    "Lindenberg": (98, 52.21, 14.12),
    "List/Sylt": (26, 55.01, 8.41),
    "Lüchow": (17, 52.97, 11.14),
    "Magdeburg": (76, 52.1, 11.58),
    "Mannheim": (96, 49.51, 8.55),
    "Marnitz": (81, 53.32, 11.93),
    "Meiningen": (450, 50.56, 10.38),
    "München-Flh.": (446, 48.35, 11.81),
    "Münster/Osnabr.-Flh.": (48, 52.13, 7.7),
    "Neuruppin": (38, 52.9, 12.81),
    "Norderney": (11, 53.71, 7.15),
    "Nürburg": (485, 50.36, 6.87),
    "Nürnberg-Flh.": (368, 49.43, 11.25),
    "OF-Wetterpark": (119, 50.09, 8.79),
    "Oberstdorf": (806, 47.4, 10.28),
    "Potsdam": (81, 52.38, 13.06),
    "Regensburg": (365, 49.04, 12.1),
    "Rostock": (4, 54.18, 12.08),
    "Saarbrücken-Flh.": (320, 49.21, 7.11),
    "Schleswig": (43, 54.53, 9.55),
    "Schwerin": (59, 53.64, 11.39),
    "Straubing": (350, 48.83, 12.56),
    "Stuttgart-Flh.": (371, 48.69, 9.22),
    "Stötten": (734, 48.67, 9.86),
    "Trier": (132, 49.73, 6.61),
    "UFS Deutsche Bucht": (0, 54.18, 7.46),
    "UFS TW Ems": (0, 54.16, 6.35),
    "Waren": (73, 53.52, 12.67),
    "Wasserkuppe": (921, 50.5, 9.94),
    "Weiden": (440, 49.67, 12.18),
    "Würzburg": (268, 49.77, 9.96),
    "Zugspitze": (2962, 47.42, 10.98),
    "Öhringen": (276, 49.21, 9.52),
}

################################################################################
# WEATHER DATA HANDLING
################################################################################

import numpy as np
import math


class PyDWDApi:
    """
    Class responsible for querying the data from the DWD server. Automatically
    caches the data to reduce the workload on the DWD server.
    """

    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.current_data = None
        self.current_data_modification = 0
        self.timeout = 30 * 60  # Only query the DWD server every 30 minutes!

    @staticmethod
    def _parse_ftp_timestamp(s):
        """
        Converts a UTC FTP timestamp to Unix time.
        """
        from datetime import datetime, tzinfo, timedelta
        from time import mktime
        from calendar import timegm

        class UTC(tzinfo):
            def utcoffset(self, dt):
                return timedelta(0)

            def tzname(self, dt):
                return "UTC"

            def dst(self, dt):
                return timedelta(0)

        t = datetime.strptime(s, "%Y%m%d%H%M%S")
        t.replace(tzinfo=UTC())
        return timegm(t.timetuple())

    @staticmethod
    def _data_filter(data, key):
        """
        Constructs a filter which allows to throw away rows in the data matrix
        without valid data.
        """
        return np.logical_not(np.isnan(data["altitude"]) + np.isnan(data[
            "latitude"]) + np.isnan(data["longitude"]) + np.isnan(data[key]))

    def query(self):
        """
        Queries the current sparse weather data from the server and returns an
        Numpy structured array containing the relevant information.
        """
        import ftplib
        import sys

        # Only query the DWD server if the data is older
        import time
        now = time.time()
        if (now - self.current_data_modification < self.timeout) and (
                not self.current_data is None):
            return self.current_data

        # Log the query
        sys.stdout.write("Querying ftp://" + DWD_SERVER + "/" +
                         DWD_OBSERVATIONS_URL + "...\n")

        # Perform the actual data download
        content = []
        with ftplib.FTP() as f:
            # Connect to the FTP server and login with the given credentials
            f.connect(DWD_SERVER)
            f.login(self.user, self.password)

            # Fetch the directory content end select the most recent "_U_HTML"
            # file
            ls = f.mlsd(DWD_OBSERVATIONS_URL)
            most_recent = None
            for entry in ls:
                # Convert the FTP timestamp to a Unix timestamp
                entry[1]["modify"] = self._parse_ftp_timestamp(entry[1][
                    "modify"])
                name = entry[0]
                attrs = entry[1]
                if (name.endswith("_U_HTML")) and (
                    (most_recent is None) or
                    (attrs["modify"] > most_recent[1]["modify"])):
                    most_recent = entry
            if most_recent is None:
                return None

            # Download the file content
            f.retrlines("RETR " + DWD_OBSERVATIONS_URL + most_recent[0],
                        content.append)

        # Parse the table from the resulting HTML and store the data in a numpy
        # array
        p = HTMLTableParser()
        p.feed("\n".join(content))
        if (len(p.tables) == 0) or (len(p.tables[0]) == 0):
            return None

        # Fetch the table and create the result matrix
        tbl = p.tables[0]
        res = np.zeros((len(tbl) - 1), dtype=RECORD_DTYPE)

        # Translate the table header (row zero)
        header = []  # Translated header names
        scale = []  # Data scale factor
        for col in tbl[0]:
            if col in DWD_KEY_MAP:
                col = DWD_KEY_MAP[col]
                if type(col) is tuple:
                    header.append(col[0])
                    scale.append(col[1])
                else:
                    header.append(col)
                    scale.append(1.0)
            else:
                header.append(None)

        # Parse the actual data
        for j, row in enumerate(tbl[1:]):
            for i, col in enumerate(row):
                if (i >= len(header)) or (header[i] is None):
                    continue
                name = header[i]
                if name == "station":
                    if col in DWD_STATION_LOCATION_MAP:
                        res["latitude"][j] = DWD_STATION_LOCATION_MAP[col][1]
                        res["longitude"][j] = DWD_STATION_LOCATION_MAP[col][2]
                        res["altitude"][j] = DWD_STATION_LOCATION_MAP[col][0]
                    else:
                        res["latitude"][j] = np.NaN
                        res["longitude"][j] = np.NaN
                        res["altitude"][j] = np.NaN
                elif name == "wind_direction":
                    if col in DWD_DIRECTION_MAP:
                        res["wind_direction_x"][j] = DWD_DIRECTION_MAP[col][0]
                        res["wind_direction_y"][j] = DWD_DIRECTION_MAP[col][1]
                    else:
                        res["wind_direction_x"][j] = np.NaN
                        res["wind_direction_y"][j] = np.NaN
                else:
                    try:
                        res[name][j] = float(col) * scale[i]
                    except Exception:
                        res[name][j] = np.NaN

        # Store the translated data in the cache
        self.current_data = res
        self.current_data_modification = most_recent[1]["modify"]

        # Return the data
        return res

    def interpolate(self, key, lats, lons, alts, data=None):
        """
        Returns interpolated data for the given latitudes, longitudes and
        altitudes and the specified data key.
        """
        import scipy.interpolate

        def deg2rad(deg):
            return deg * math.pi / 180.0

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0
            dLat = deg2rad(lat2 - lat1)
            dLon = deg2rad(lon2 - lon1)
            a = ((math.sin(dLat * 0.5)**2) + math.cos(deg2rad(lat1)) *
                 math.cos(deg2rad(lat2)) * (math.sin(dLon * 0.5)**2))
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
            return R * c  # Distance in km

        def data_norm(x1, x2):
            ALT_WEIGHT = 100.0  # Alt. dif. more influential than ground distance
            x1 = x1[:, :, 0]
            x2 = x2[:, 0, :]  # Strip away the superfluous dims
            d1 = x1.shape[1]
            d2 = x2.shape[1]
            res = np.zeros((d1, d2))
            for i in range(d1):
                for j in range(d2):
                    lat1 = x1[1, i]
                    lon1 = x1[0, i]
                    alt1 = x1[2, i]
                    lat2 = x2[1, j]
                    lon2 = x2[0, j]
                    alt2 = x2[2, j]
                    d_ground = haversine(lat1, lon1, lat2, lon2)
                    d_alt = (alt1 - alt2) / 1000.0 * ALT_WEIGHT
                    res[i, j] = np.sqrt(d_ground**2 + d_alt**2)
            return res

        # Query the data and construct a filter containing the valid rows
        data = self.query() if data is None else data
        flt = self._data_filter(data, key)
        if not flt.any():
            return None

        # Create the Rbf interpolator and perform the interpolation
        rbfi = scipy.interpolate.Rbf(data["latitude"][flt],
                                     data["longitude"][flt],
                                     data["altitude"][flt],
                                     data[key][flt],
                                     function="linear",
                                     norm=data_norm)

        return rbfi(lats, lons, alts)

    def plot_map(self, key, resolution=32, altitude=100):
        """
        Returns a Matplotlib figure which pictures the given quantity. Mainly
        for debugging purposes.
        """
        import matplotlib.pyplot as plt

        data = self.query()
        flt = self._data_filter(data, key)

        min_lat = np.min(data["latitude"][flt])
        max_lat = np.max(data["latitude"][flt])
        min_lon = np.min(data["longitude"][flt])
        max_lon = np.max(data["longitude"][flt])

        lats, lons, alts = np.meshgrid(
            np.linspace(min_lat, max_lat, resolution),
            np.linspace(min_lon, max_lon, resolution), [altitude])

        zzs = self.interpolate(key, lats, lons, alts, data)[:, :, 0]

        fig = plt.figure()
        ax = fig.gca()
        ax.imshow(zzs.T,
                  extent=[min_lon, max_lon, min_lat, max_lat],
                  origin="lower")
        for name, loc in DWD_STATION_LOCATION_MAP.items():
            ax.plot(loc[2], loc[1], '+', markersize=5, color='k')
            ax.annotate(name,
                        xy=(loc[2], loc[1]),
                        xytext=(0.1, 0.1),
                        textcoords='offset points')
        border = np.array(GERMAN_BORDER)
        ax.plot(border[:, 0], border[:, 1], '-', color="#dddddd", linewidth=5)
        ax.set_title(key)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        return fig

################################################################################
# HTTP Server Handler
################################################################################

import http.server
import urllib.parse
import json


class WeatherHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def _error(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

        self.wfile.write(json.dumps({"error": msg}).encode("utf-8"))

    def do_GET(self):
        def interpolate(key):
            global api
            response = api.interpolate(key, [lat], [lon], [alt], data)
            if response is None:
                return None
            else:
                return response[0]

        def write_interpolated(tar, key, key_tar=None):
            key_tar = key if key_tar is None else key_tar
            res = interpolate(key)
            if not res is None:
                tar[key_tar] = res

        response = {
            "coord": {},
            "main": {},
            "wind": {},
            "dt": api.current_data_modification
        }
        try:
            # Make sure the URL is correct
            o = urllib.parse.urlparse(self.path)
            if o.path != "/api/1.0/weather":
                self._error(404, "Requested file " + o.path + " not found!")
                return

            # Make sure the query is correct
            q = urllib.parse.parse_qs(o.query, keep_blank_values=True)
            keys = list(q.keys())
            keys.sort()
            if (keys != ["alt", "lat", "lon"]):
                self._error(400, "Invalid query")
                return
            try:
                lat = float(q["lat"][0])
                lon = float(q["lon"][0])
                alt = float(q["alt"][0])
            except Exception:
                self._error(400, "Invalid query")
                return

            # Write the coordinates
            response["coord"] = {
                "alt": float(alt),
                "lat": float(lat),
                "lon": float(lon)
            }

            # Query the weather data and add it to the response
            data = api.query()
            write_interpolated(response["main"], "temperature", "temp")
            write_interpolated(response["main"], "pressure")
            write_interpolated(response["main"], "humidity")
            write_interpolated(response["main"], "precipitation")
            write_interpolated(response["wind"], "wind_speed", "speed")
            write_interpolated(response["wind"], "wind_speed_max", "max")
            wind_x = interpolate("wind_direction_x")
            wind_y = interpolate("wind_direction_y")
            if not ((wind_x is None) or (wind_y is None)):
                deg = math.atan2(-wind_x, wind_y) / math.pi * 180.0 + 180.0
                response["wind"]["deg"] = deg

        except:
            import traceback
            self._error(500, traceback.format_exc())
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

        self.wfile.write(json.dumps(response).encode("utf-8"))

################################################################################
# MAIN PROGRAM
################################################################################

if __name__ == '__main__':
    import sys
    import socketserver

    # Check the command line
    if len(sys.argv) != 4:
        sys.stderr.write(
            "Usage: ./pydwdapi <DWD FTP USER> <DWD FTP PASSWORD> <HTTP PORT>\n")
        sys.exit(1)

    # Create the DWD API instance and try to query the data for the first time
    api = PyDWDApi(sys.argv[1], sys.argv[2])
    api.query()

    # Create the server
    port = int(sys.argv[3])
    sys.stdout.write("Starting HTTP server...\n")
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(
        ("127.0.0.1", port), WeatherHTTPRequestHandler)
    httpd.allow_reuse_address = True
    try:
        sys.stdout.write("Listening on port " + str(port) + "...\n")
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    sys.stdout.write("\nStopping HTTP server...\n")
    httpd.shutdown()
