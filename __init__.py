# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeneratingTopography
                                 A QGIS plugin
 DTMから地形図を生成
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-08-26
        copyright            : (C) 2024 by ShingoNagano
        email                : shingosnaganon@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

import glob
import os
import tempfile

# Debugging in VSCode
# import debugpy
# import shutil

# debugpy.configure(python=shutil.which("python"))
# try:
#     debugpy.listen(("localhost", 5656))
# except:
#     debugpy.connect(("localhost", 5656))
# END Debugging in VSCode


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GeneratingTopography class from file GeneratingTopography.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .topo_maps import TopoMaps

    return TopoMaps(iface)


def clean_temp_topomaps():
    temp_dir = tempfile.gettempdir()
    topo_maps_files = glob.glob(os.path.join(temp_dir, "*_topoMaps.tif"))
    for file_path in topo_maps_files:
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")


clean_temp_topomaps()
