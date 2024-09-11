# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TopoMaps
                                 A QGIS plugin
 DTMから地形図を生成
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-08-26
        git sha              : $Format:%H$
        copyright            : (C) 2024 by ShingoNagano
        email                : shingosnaganon@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
os.chdir(os.path.dirname(__file__))

from matplotlib import pyplot as plt
import numpy as np
from osgeo import gdal
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .apps.colors import Coloring
from .apps.mapper import composite_images
from .apps.mapper import save_image_rgba
from .apps.parts import process
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .topo_maps_dialog import TopoMapsDialog
from .topo_maps_dialog import KernelHelpDialog
coloring = Coloring()



class TopoMaps:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = TopoMapsDialog()
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TopoMaps_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Topo Maps')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Topo Maps', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/generate_topography/views/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'地形図の生成'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Generating Topographic map'),
                action
            )
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
        else:
            self.dlg = None
            self.dlg = TopoMapsDialog()
        
        # show the dialog
        self.dlg.show()
        print(self.dlg)
        print(type(self.dlg))
        # 微地形図の作成
        self.dlg.pushBtn_Execute.clicked.connect(self.execute_algorithom)


    def execute_algorithom(self):
        self.dlg.write_options()
        progress = self.dlg.progressBar
        label_log = self.dlg.label_Log
        label_log.setText('処理の開始 ... ')
        progress.setValue(0)
        label_log.setText('ファイルの読み込み')
        log_board = self.dlg.textBrowser_Log
        # Rasterの読み込み
        self.dlg.check_file()
        org_dst = gdal.Open(self.dlg.get_input_file_path)

        # サンプルのを表示するだけの場合は、Rasterのサイズを縮小する
        if self.dlg.checkBox_Sample.isChecked():
            org_dst = process.get_sample_raster(org_dst)
        # RasterSizeをLogに書き込む
        self.dlg._new_line
        log_board.append("<<< Original raster size >>>\n")
        self.dlg.show_input_data(org_dst)
        
        # リサンプルの実行
        org_dst = self.dlg.first_perform_resample(org_dst)
        if self.dlg.checkBox_StartResample.isChecked():
            # リサンプルした場合はもう一度RasterSizeをLogに書き込む
            self.dlg._new_line
            log_board.append("<<< Resampled raster size >>>\n")
            self.dlg.show_input_data(org_dst)
        progress.setValue(1)
        
        self.dlg._new_line
        log_board.append("<<< Start to calculate topographic maps >>>\n")
        # 傾斜の計算とRGBA化
        label_log.setText('傾斜の計算中')
        log_board.append("Start to calculate slope\n")
        slope_options = self.dlg.get_slope_options()
        slope_img = slope_options.to_slope_img(org_dst, progress=progress)
        log_board.append("Slope calculation is completed\n\n")
        
        # TPI の計算とRGBA化
        label_log.setText('TPIの計算中')
        log_board.append("Start to calculate TPI\n")
        tpi_options = self.dlg.get_tpi_options()
        tpi_img = tpi_options.to_tpi_img(org_dst, progress=progress)
        log_board.append("TPI calculation is completed\n\n")
        
        # TRI の計算とRGBA化
        label_log.setText('TRIの計算中')
        log_board.append("Start to calculate TRI\n")
        tri_options = self.dlg.get_tri_options()
        tri_img = tri_options.to_tri_img(org_dst, progress=progress)
        log_board.append("TRI calculation is completed\n\n")

        # Hillshade の計算とRGBA化
        label_log.setText('Hillshadeの計算中')
        log_board.append("Start to calculate Hillshade\n")
        hillshade_options = self.dlg.get_hillshade_options()
        hillshade_img = hillshade_options.to_hillshade_img(org_dst, progress=progress)
        log_board.append("Hillshade calculation is completed\n\n")

        # 透過率の変更
        defalut_alpha = 100
        if self.dlg.spinBoxInt_SlopeAlpha.value() != defalut_alpha:
            alpha = self.dlg.spinBoxInt_SlopeAlpha.value() * 0.01
            slope_img = self.dlg.change_alpha(slope_img, alpha)
        if self.dlg.spinBoxInt_TpiAlpha.value() != defalut_alpha:
            alpha = self.dlg.spinBoxInt_TpiAlpha.value() * 0.01
            tpi_img = self.dlg.change_alpha(tpi_img, alpha)

        # 画像の合成
        label_log.setText('画像の合成中')
        log_board.append("Start compositing images\n")
        composited_img = composite_images(slope_img, tpi_img, 
                                        tri_img, hillshade_img)
        log_board.append("Composite images is completed\n\n")
        progress.setValue(97)
        if self.dlg.checkBox_Sample.isChecked():
            label_log.setText('Sampleを表示します')
            img = np.array(composited_img)
            plt.title('Sample Image', fontweight='bold', fontsize=18)
            plt.imshow(img)
            plt.axis('off')
            plt.show()
        else:
            # Rasterの保存
            label_log.setText('ファイルの保存を開始')
            log_board.append("Start writing raster file\n")
            save_image_rgba(
                out_file_path=self.dlg.get_output_file_path,
                img=composited_img,
                org_dst=org_dst
            )
            self.dlg.add_lyr()
            progress.setValue(100)
            log_board.append("Writing raster file is completed\n\n")
            log_board.append("<<< Finish >>>")
            label_log.setText('処理が完了しました')

