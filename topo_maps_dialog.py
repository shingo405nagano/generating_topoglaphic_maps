# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeneratingTopographyDialog
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
import json
import os
from typing import Any, Dict, NewType, Union
from pathlib import Path
from PIL import Image
import webbrowser

from matplotlib import pyplot as plt
import numpy as np
from osgeo import gdal
from qgis.core import QgsMapLayerProxyModel
from qgis.core import QgsProject
from qgis.core import QgsRasterLayer
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QMessageBox

from .apps.colors import CsColorMaps
from .apps.colors import RgbColorMaps
from .apps.colors import VintageColorMaps
from .apps.kernels import Kernels
from .apps.kernels import KernelTypes
from .apps.mapper import ContrastOptions
from .apps.mapper import EdgeOptions
from .apps.mapper import GaussianOptions
from .apps.mapper import SlopeOptions
from .apps.mapper import HillshadeOptions
from .apps.mapper import TpiOptions
from .apps.mapper import TriOptions
from .apps.mapper import UnsharpnOptions
from .apps.parts import process
from .custom_color_dialog import CustomColorDialog

OptionsType = NewType('OptionsType', Union[SlopeOptions, TpiOptions, TriOptions, HillshadeOptions])

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = (
    uic
    .loadUiType(
        os.path.join(
            os.path.dirname(__file__), 
            'views\generate_topography_dialog_base.ui'
        )
    )
)

HELP_KERNELS, _ = (
    uic
    .loadUiType(
        os.path.join(
            os.path.dirname(__file__),
            'views\help_kernels.ui'
        ),
    )
)


global CS_MAP_IMG
CS_MAP_IMG = plt.imread('.\\views\\CS-Map__Img.jpg')
global VINTAGE_MAP_IMG
VINTAGE_MAP_IMG = plt.imread('.\\views\\Vintage-Map__Img.jpg')
global RGB_MAP_IMG
RGB_MAP_IMG = plt.imread('.\\views\\RGB-Map__Img.jpg')
global CONFIG_FILE
CONFIG_FILE = '.\\apps\\config.json'


class InputTab(object):
    def make_input_dlg(self) -> None:
        """
        入力ファイルのダイアログを設定
        ファイルにチェックを入れている時はファイル選択ダイアログを表示し、レイヤー選択を非表示にする。レイヤーにチェックを入れている時はファイル選択ダイアログを非表示にし、レイヤー選択を表示する
        """
        self.file_filter()
        if self.radioBtn_InputIsFile.isChecked():
            self.label_InputFile.setVisible(True)
            self.fileWgt_InputFile.setVisible(True)
            self.label_InputLayer.setVisible(False)
            self.lyrCombo_InputLyr.setVisible(False)
        elif self.__in_raster():
            self.label_InputFile.setVisible(False)
            self.fileWgt_InputFile.setVisible(False)
            self.label_InputLayer.setVisible(True)
            self.lyrCombo_InputLyr.setVisible(True)
        else:
            self.radioBtn_InputIsFile.setChecked(True)
            self.make_input_dlg()
    
    def __in_raster(self) -> bool:
        """Raster データが存在するか確認"""
        lyrs = QgsProject.instance().mapLayers().values()
        rasters = False
        fmts = ['.tif', '.tiff']
        for lyr in lyrs:
            source = lyr.source().lower()
            for fmt in fmts:
                if source.endswith(fmt):
                    rasters = True
                    break
            if rasters:
                break
        return rasters
    
    def show_custom_color_dlg(self) -> None:
        """カーネルのヘルプを表示"""
        self.custom_color_dlg= CustomColorDialog(self)
        self.custom_color_dlg.show()

    def make_your_styling(self) -> None:
        if self.mapSelectRadioBtn_YourStyle.isChecked():
            self.btn_CustomDlg.setVisible(True)
        else:
            self.btn_CustomDlg.setVisible(False)

    def show_map_styles(self) -> None:
        """マップスタイルを適用した場合のプレビューを表示"""
        imgs = [CS_MAP_IMG, VINTAGE_MAP_IMG, RGB_MAP_IMG]
        titles = ['CS-Map Styled', 'Vintage-Map Styled', 'RGB-Map Styled']
        _ax = None
        fig = plt.figure(figsize=(8, 8))
        for i, (img, title) in enumerate(zip(imgs, titles), start=1):
            ax = fig.add_subplot(2, 2, i, sharex=_ax, sharey=_ax)
            ax.set_title(title, fontsize=15, fontweight='bold')
            ax.imshow(img)
            ax.axis('off')
            _ax = ax
        plt.subplots_adjust(wspace=0.05, hspace=0.15)
        plt.show()
    
    @property
    def get_input_file_path(self) -> Path:
        """
        ファイルパスを取得
        Returns:
            Path: ファイルパス
        """
        if self.radioBtn_InputIsFile.isChecked():
            return self.fileWgt_InputFile.filePath()
        else:
            return self.lyrCombo_InputLyr.currentLayer().source()
    
    def first_perform_resample(self, dst: gdal.Dataset) -> bool:
        """
        ラスターデータの解像度を変更する
        Args:
            dst(gdal.Dataset): ラスターデータ
        Returns:
            dst(gdal.Dataset): リサンプリング後のラスターデータ
        """
        algs = {
            'Nearest Neighbour': gdal.GRA_NearestNeighbour,
            'Bilinear': gdal.GRA_Bilinear,
            'Cubic': gdal.GRA_Cubic,
            'Cubic Spline': gdal.GRA_CubicSpline,
        }
        if self.checkBox_StartResample.isChecked():
            if self.rarioBtn_ResolIsAbs.isChecked():
                # 絶対値で解像度を指定
                resolution = self.spinBoxF_StartResampleResol.value()
            elif self.radioBtn_ResolIsRel.isChecked():
                # 相対値で解像度を指定
                resolution = self.spinBoxInt_StartResampleResol.value()
                org_resol = dst.GetGeoTransform()[1]
                resolution = org_resol / resolution
            alg = algs.get(self.comboBox_StartResampleAlg.currentText())
            dst = process.resampling(dst, resolution, alg)
            return dst
        else:
            return dst
    
    def make_resample_dlg(self) -> None:
        """リサンプルのダイアログを設定"""
        if self.checkBox_StartResample.isChecked():
            self.rarioBtn_ResolIsAbs.setVisible(True)
            self.radioBtn_ResolIsRel.setVisible(True)
            if self.rarioBtn_ResolIsAbs.isChecked():
                self.l_19.setVisible(True)
                self.l_21.setVisible(False)
                self.spinBoxF_StartResampleResol.setVisible(True)
                self.spinBoxInt_StartResampleResol.setVisible(False)
            else:
                self.l_19.setVisible(False)
                self.l_21.setVisible(True)
                self.spinBoxF_StartResampleResol.setVisible(False)
                self.spinBoxInt_StartResampleResol.setVisible(True)
            self.l_20.setVisible(True)
            self.comboBox_StartResampleAlg.setVisible(True)
        else:
            self.rarioBtn_ResolIsAbs.setVisible(False)
            self.radioBtn_ResolIsRel.setVisible(False)
            self.l_19.setVisible(False)
            self.l_20.setVisible(False)
            self.l_21.setVisible(False)
            self.spinBoxF_StartResampleResol.setVisible(False)
            self.spinBoxInt_StartResampleResol.setVisible(False)
            self.comboBox_StartResampleAlg.setVisible(False)



class OutputTab(object):
    @property
    def select_map_style(self) -> Union[CsColorMaps, VintageColorMaps]:
        """
        Radio buttonで選択されたカラーマップを返す
        Returns:
            Union[CsColorMaps, VintageColorMaps]
        """
        if self.mapSelectRadioBtn_BR.isChecked():
            return CsColorMaps()
        elif self.mapSelectRadioBtn_Vintage.isChecked():
            return VintageColorMaps()
        elif self.mapSelectRadioBtn_RGB.isChecked():
            return RgbColorMaps()
        else:
            # 設定したカスタムカラーマップを取得
            from .apps.colors import CustomColorMaps
            file = '.\\apps\\config.json'
            with open(file, mode='r') as f:
                config = json.load(f)
                cmap = config.get('CUSTOM-Map')
            custom_color_maps = CustomColorMaps()
            custom_color_maps.COLORS_DICT = cmap
            return custom_color_maps
    
    def make_output_dlg(self) -> None:
        """出力ファイルのダイアログを設定"""
        if self.checkBox_Sample.isChecked():
            self.checkBox_AddProject.setVisible(False)
            self.label_OutputFile.setVisible(False)
            self.fileWgt_OutputFile.setVisible(False)
        else:
            self.checkBox_AddProject.setVisible(True)
            self.label_OutputFile.setVisible(True)
            self.fileWgt_OutputFile.setVisible(True)

    @property
    def get_output_file_path(self) -> Path:
        """
        ファイルパスを取得
        Returns:
            Path: ファイルパス
        """
        return self.fileWgt_OutputFile.filePath()

    def add_lyr(self) -> None:
        """プロジェクトにレイヤーを追加"""
        if self.checkBox_AddProject.isChecked():
            self.textBrowser_Log.append("Add a raster layer to project\n")
            file_path = self.get_output_file_path
            lyr_name = os.path.basename(file_path).split('.')[0]
            lyr = QgsRasterLayer(file_path, lyr_name, 'gdal')
            QgsProject.instance().addMapLayer(lyr)



class SlopeTab(object):
    def get_slope_options(self) -> SlopeOptions:
        """Slope に関するオプションを取得
        Returns:
            SlopeOptions: Slope に関するオプション
                resampling(bool): Resampling を行うかどうか
                resolution(int): 解像度
                filtering(bool): フィルタリングを行うかどうか
                gaussian_sigma(float): ガウシアンフィルタの標準偏差
                cmap: カラーマップ
        """
        options = SlopeOptions(
            checked=self.gpBox_Slope.isChecked(),
            resampling=self.gpBox_SlopeResample.isChecked(),
            resolution=self.spinBoxF_ResampleResol.value(),
            filtering=self.gpBox_SlopeGauss.isChecked(),
            gaussian_sigma=self.spinBoxF_SlopeGaussSigma.value(),
            cmap=self.select_map_style.slope().colors_255
        )
        return options

    def _change_slope_alpha_param_from_slider(self) -> None:
        # 透過率のスライダーの値を変更
        alpha = self.hSlider_SlopeAlpha.value()
        self.spinBoxInt_SlopeAlpha.setValue(alpha)
    
    def _change_slope_alpha_param_from_spinbox(self) -> None:
        # 透過率のスピンボックスの値を変更
        alpha = self.spinBoxInt_SlopeAlpha.value()
        self.hSlider_SlopeAlpha.setValue(alpha)



class TpiTab(object):
    def get_tpi_options(self) -> TpiOptions:
        """TPI に関するオプションを取得
        Returns:
            TpiOptions: TPI に関するオプション
                kernel_size_type(str): カーネルサイズの種類
                one_side_distance(int): 中心セルからの距離
                kernel_type(str): カーネルの種類
                sigma(float): ガウシアンフィルタの標準偏差
                outlier_treatment(bool): 外れ値処理を行うかどうか
                threshold(int): 外れ値の閾値
                cmap: カラーマップ
        """
        # Kernel typeを取得
        if self.radioBtn_OrgKernel.isChecked():
            kernel_type = KernelTypes.original
        elif self.radioBtn_DoughnutKernel.isChecked():
            kernel_type = KernelTypes.doughnut
        elif self.radioBtn_MeanKernel.isChecked():
            kernel_type = KernelTypes.mean
        elif self.radioBtn_GaussKernel.isChecked():
            kernel_type = KernelTypes.gaussian
        elif self.radioBtn_InvGaussKernel.isChecked():
            kernel_type = KernelTypes.inverse_gaussian
        elif self.radioBtn_4DirecKernel.isChecked():
            kernel_type = KernelTypes.four_direction
        elif self.radioBtn_8DirecKernel.isChecked():
            kernel_type = KernelTypes.eight_direction
        else:
            kernel_type = KernelTypes.original
        
        # カーネルサイズを取得
        distance_types = [
            'カーネルサイズを距離で指定', 
            'Kernel size specified by distance'
        ]
        if self.cmbBox_Kernel.currentText() in distance_types:
            one_side_distance = self.spinBoxF_KernelSize.value()
        else:
            one_side_distance = self.spinBoxInt_KernelSize.value()
        
        # TPI に関するオプションを取得
        options = TpiOptions(
            checked=self.gpBox_Tpi.isChecked(),
            kernel_size_type=self.cmbBox_Kernel.currentText(),
            one_side_distance=one_side_distance,
            kernel_type=kernel_type,
            sigma=self.spinBoxF_GaussSigma.value(),
            outlier_treatment=self.gpBox_TpiOutTreatment.isChecked(),
            threshold=self.spinBoxF_TpiThres.value(),
            cmap=self.select_map_style.tpi().colors_255
        )
        return options

    def make_tpi_dlg_gaussian(self) -> None:
        """TPI の設定でガウシアンカーネルを選択した場合、ガウシアンカーネルのパラメータを表示"""
        self._make_dlg_gaussian_param()
        self._make_dlg_kernel_param()

    def make_tpi_dlg_distance_param(self) -> None:
        distance_type = [
            'カーネルサイズを距離で指定', 
            'Kernel size specified by distance'
        ]
        if self.cmbBox_Kernel.currentText() in distance_type:
            self.spinBoxF_KernelSize.setVisible(True)
            self.spinBoxInt_KernelSize.setVisible(False)
        else:
            self.spinBoxF_KernelSize.setVisible(False)
            self.spinBoxInt_KernelSize.setVisible(True)

    def make_tpi_dlg_original(self) -> None:
        """TPI の設定で隣接セルを使用した場合に、パラメータを非表示にする"""
        self._erase_dlg_gaussian_param()
        self._erase_dlg_kernel_param()

    def make_tpi_dlg_other(self) -> None:
        """TPi の設定でガウシアンカーネル以外を選択した場合、パラメータを表示する"""
        self._erase_dlg_gaussian_param()
        self._make_dlg_kernel_param()
    
    def _make_dlg_gaussian_param(self) -> None:
        # TPI の設定でガウシアンカーネルを選択した場合、ガウシアンカーネルのパラメータを表示
        self.l_4.setVisible(True)
        self.spinBoxF_GaussSigma.setVisible(True)
    
    def _erase_dlg_gaussian_param(self) -> None:
        # TPI の設定でガウシアンカーネル以外を選択した場合、ガウシアンカーネルのパラメータを非表示
        self.l_4.setVisible(False)
        self.spinBoxF_GaussSigma.setVisible(False)

    def _make_dlg_kernel_param(self) -> None:
        # TPI の設定でカーネルサイズを選択した場合、カーネルサイズのパラメータを表示
        self.l_15.setVisible(True)
        self.cmbBox_Kernel.setVisible(True)
        self.spinBoxF_KernelSize.setVisible(True)
    
    def _erase_dlg_kernel_param(self) -> None:
        # TPI の設定でカーネルサイズ以外を選択した場合、カーネルサイズのパラメータを非表示
        self.l_15.setVisible(False)
        self.cmbBox_Kernel.setVisible(False)
        self.spinBoxF_KernelSize.setVisible(False)

    def _change_tpi_alpha_param_from_slider(self) -> None:
        # 透過率のスライダーの値を変更
        alpha = self.hSlider_TpiAlpha.value()
        self.spinBoxInt_TpiAlpha.setValue(alpha)

    def _change_tpi_alpha_param_from_spinbox(self) -> None:
        # 透過率のスピンボックスの値を変更
        alpha = self.spinBoxInt_TpiAlpha.value()
        self.hSlider_TpiAlpha.setValue(alpha)

    def show_kernel_help(self) -> None:
        """カーネルのヘルプを表示"""
        self.help_kernels_dialog = KernelHelpDialog(self)
        self.help_kernels_dialog.show()



class TriTab(object):
    def get_tri_options(self) -> TriOptions:
        """TRI に関するオプションを取得
        Returns:
            TriOptions: TRI に関するオプション
                outlier_treatment(bool): 外れ値処理を行うかどうか
                threshold(int): 外れ値の閾値
                cmap: カラーマップ
        """
        options = TriOptions(
            checked=self.gpBox_Tri.isChecked(),
            outlier_treatment=self.checkBox_TriOutTreatment.isChecked(),
            threshold=self.spinBoxF_TriThres.value(),
            cmap=self.select_map_style.tri().colors_255,
            filtering=self.gpBox_HillshadeGauss.isChecked(),
            gaussian_sigma=self.spinBoxF_HillshadeGaussSigma.value()
        )
        return options



class HillshadeTab(object):
    def get_hillshade_options(self) -> HillshadeOptions:
        """
        Hillshade に関するオプションを取得
        Returns:
            HillshadeOptions: Hillshade に関するオプション
                hillshade_type(str): Hillshade の種類
                azimuth(int): 方位角
                altitude(int): 高度
                z_factor(float): Z_Factor
                combined(bool): Slope と Hillshade を合成するかどうか
                cmap: カラーマップ
                filtering(bool): フィルタリングを行うかどうか
                gaussian_sigma(float): ガウシアンフィルタの標準偏差
        """
        options = HillshadeOptions(
            checked=self.gpBox_Hillshade.isChecked(),
            hillshade_type=self.cmbBox_HillshadeType.currentText(),
            azimuth=self.spinBoxInt_HillshadeAzimuth.value(),
            altitude=self.spinBoxInt_HillshadeHight.value(),
            z_factor=self.spinBoxF_HillshadeHighlight.value(),
            combined=self.checkBox_CombinedSlope.isChecked(),
            cmap=self.select_map_style.hillshade().colors_255,
            filtering=self.gpBox_HillshadeGauss.isChecked(),
            gaussian_sigma=self.spinBoxF_HillshadeGaussSigma.value()
        )
        return options



class OthersTab(object):
    def get_contrast_options(self) -> ContrastOptions:
        """コントラストの設定を取得"""
        contrast = ContrastOptions(
            checked=self.gpBox_Contrast.isChecked(),
            contrast=self.spinBoxF_Contrast.value()
        )
        return contrast

    def _change_contrast_param_from_slider(self) -> None:
        # コントラストのスライダーの値を変更
        int_value = self.hSlider_Contrast.value()
        contrast = int_value * 0.01
        self.spinBoxF_Contrast.setValue(contrast)
    
    def _change_contrast_param_from_spinbox(self) -> None:
        # コントラストのスピンボックスの値を変更
        float_value = self.spinBoxF_Contrast.value()
        contrast = int(float_value * 100)
        self.hSlider_Contrast.setValue(contrast)
    
    def get_unsharpn_options(self) -> UnsharpnOptions:
        """アンシャープマスキングの設定を取得"""
        unsharpn = UnsharpnOptions(
            checked=self.gpBox_Unsharpn.isChecked(),
            radius=self.spinBoxF_UnsharpnRads.value(),
            percent=self.spinBoxInt_UnsharpnPer.value(),
            threshold=self.spinBoxInt_UnsharpnThres.value()
        )
        return unsharpn
    
    def get_edge_options(self) -> EdgeOptions:
        """エッジ検出の設定を取得"""
        unsharpn = UnsharpnOptions(
            checked=self.checkBox_EdgeUnsharpn.isChecked(),
            radius=self.spinBoxF_EdgeUnsharpnRads.value(),
            percent=self.spinBoxInt_EdgeUnsharpnPer.value(),
            threshold=self.spinBoxInt_EdgeUnsharpnThres.value()
        )
        gaussian = GaussianOptions(
            checked=self.checkBox_EdgeGauss.isChecked(),
            sigma=self.spinBoxF_EdgeUnsharpnSigma.value()
        )
        edge = EdgeOptions(
            checked=self.gpBox_Edge.isChecked(),
            unsharpn=unsharpn,
            gaussian=gaussian,
            min_area_iqr=self.spinBoxF_EdgeUnsharpn_IQR.value(),
            color=self.clrBtn_EdgeColor.color().getRgb()
        )
        return edge
    
    def make_other_tab(self) -> None:
        """Others Tab の設定"""
        self._make_edge_unsharpn_dlg()
        self._make_edge_gauss_dlg()

    def _make_edge_unsharpn_dlg(self) -> None:
        objs = [
            self.l_6.setVisible,
            self.spinBoxF_EdgeUnsharpnRads.setVisible,
            self.l_7.setVisible,
            self.spinBoxInt_EdgeUnsharpnPer.setVisible,
            self.l_8.setVisible,
            self.spinBoxInt_EdgeUnsharpnThres.setVisible
        ]
        if self.checkBox_EdgeUnsharpn.isChecked():
            for obj in objs:
                obj(True)
        else:
            for obj in objs:
                obj(False)
    
    def _make_edge_gauss_dlg(self) -> None:
        objs = [
            self.l_22.setVisible,
            self.spinBoxF_EdgeUnsharpnSigma.setVisible
        ]
        if self.checkBox_EdgeGauss.isChecked():
            for obj in objs:
                obj(True)
        else:
            for obj in objs:
                obj(False)



class OpenWeb(object):
    def __init__(self):
        locale = QSettings().value('locale/userLocale')[0:2]
        if locale == 'ja':
            self.lang = 'ja'
        else:
            self.lang = 'en'
        
        with open(CONFIG_FILE, mode='r') as f:
            self.urls = json.load(f).get('Documents').get(self.lang)

    def open_web(self, tab_name: str) -> None:
        """GitHub にあるドキュメントを開く"""
        reply = QMessageBox.question(
            None,
            'Message ...',
            'Open the document in the browser?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            webbrowser.open(self.urls.get(tab_name))

    def open_slope_doc(self) -> None:
        self.open_web('SLOPE')
    
    def open_tpi_doc(self) -> None:
        self.open_web('TPI')
    
    def open_hillshade_doc(self) -> None:
        self.open_web('HILLSHADE')
    
    def open_others_doc(self) -> None:
        self.open_web('OTHERS')



class TopoMapsDialog(
    QtWidgets.QDialog, FORM_CLASS, InputTab, OutputTab, 
    OthersTab, SlopeTab, TpiTab, TriTab, HillshadeTab
):
    def __init__(self, parent=None):
        """Constructor."""
        super(TopoMapsDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self._error_font = "QLabel {color: red; font-weight: bold;}"
        self._success_font = "QLabel {color: black;}"
        self.web = OpenWeb()

        # Set the help dialog to None
        # ファイルの読み書きを設定
        self.make_input_dlg()
        self.radioBtn_InputIsFile.toggled.connect(self.make_input_dlg)
        self.radioBtn_InputIsLayer.toggled.connect(self.make_input_dlg)
        self.checkBox_Sample.stateChanged.connect(self.make_output_dlg)
        
        # ログの初期化
        self.textBrowser_Log.clear()

        # Resampleのダイアログ設定
        self.make_resample_dlg()
        self.checkBox_StartResample.stateChanged.connect(self.make_resample_dlg)
        self.rarioBtn_ResolIsAbs.toggled.connect(self.make_resample_dlg)
        self.radioBtn_ResolIsRel.toggled.connect(self.make_resample_dlg)
        
        # Slope のダイアログ設定
        self.hSlider_SlopeAlpha.valueChanged.connect(
            self._change_slope_alpha_param_from_slider)
        self.spinBoxInt_SlopeAlpha.valueChanged.connect(
            self._change_slope_alpha_param_from_spinbox)
        self.btn_OpenDocSlope.clicked.connect(self.web.open_slope_doc)

        # TPI のダイアログ設定
        self._erase_dlg_gaussian_param()
        self.make_tpi_dlg_distance_param()
        self.cmbBox_Kernel.currentIndexChanged.connect(self.make_tpi_dlg_distance_param)
        self.radioBtn_OrgKernel.toggled.connect(self.make_tpi_dlg_original)
        self.radioBtn_DoughnutKernel.toggled.connect(self.make_tpi_dlg_other)
        self.radioBtn_MeanKernel.toggled.connect(self.make_tpi_dlg_other)
        self.radioBtn_GaussKernel.toggled.connect(self.make_tpi_dlg_gaussian)
        self.radioBtn_InvGaussKernel.toggled.connect(self.make_tpi_dlg_gaussian)
        self.radioBtn_4DirecKernel.toggled.connect(self.make_tpi_dlg_other)
        self.radioBtn_8DirecKernel.toggled.connect(self.make_tpi_dlg_other)
        self.hSlider_TpiAlpha.valueChanged.connect(
            self._change_tpi_alpha_param_from_slider)
        self.spinBoxInt_TpiAlpha.valueChanged.connect(
            self._change_tpi_alpha_param_from_spinbox)
        self.btn_OpenDocTpi.clicked.connect(self.web.open_tpi_doc)

        # Hillshade のダイアログ設定
        self.btn_OpenDocHillshade.clicked.connect(self.web.open_hillshade_doc)
        
        # マップスタイルのプレビューを表示
        self.btn_ShowStyles.clicked.connect(self.show_map_styles)
        self.pushBtn_GaussHint.clicked.connect(self.show_gaussian_hint)
        self.pushBtn_GaussHint_.clicked.connect(self.show_gaussian_hint)

        # KernelHelpDialogの表示
        self.btn_ShowTpiHint.clicked.connect(self.show_kernel_help)
        self.pushBtn_Cancel.clicked.connect(self.close_dlg)
        self.btn_CustomDlg.clicked.connect(self.show_custom_color_dlg)
        self.make_your_styling()
        self.mapSelectRadioBtn_YourStyle.toggled.connect(self.make_your_styling)

        # Othres Tab
        self.make_other_tab()
        self.hSlider_Contrast.valueChanged.connect(
            self._change_contrast_param_from_slider
        )
        self.spinBoxF_Contrast.valueChanged.connect(
            self._change_contrast_param_from_spinbox
        )
        self.checkBox_EdgeUnsharpn.stateChanged.connect(self._make_edge_unsharpn_dlg)
        self.checkBox_EdgeGauss.stateChanged.connect(self._make_edge_gauss_dlg)
        self.btn_OpenDocOthers.clicked.connect(self.web.open_others_doc)

    def tr(self, message):
        """
        Args:
            message(str): 翻訳するメッセージ
        Returns:
            str: 翻訳されたメッセージ
        """
        return QCoreApplication.translate("TopoMapsDialog", message)

    def file_filter(self) -> None:
        """RasterData のみを選択できるようにする"""
        self.fileWgt_InputFile.setFilter("GeoTiff (*.tif *.tiff *.TIF *.TIFF);;")
        self.lyrCombo_InputLyr.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.lyrCombo_InputLyr.setExcludedProviders(['wms', 'other_provider'])
        self.fileWgt_OutputFile.setFilter("GeoTiff (*.tif);;")

    def show_gaussian_hint(self) -> None:
        """ガウシアンカーネルのヒントを表示"""
        one_side = 7
        sigma_lst = [round(v, 2) for v in np.arange(1.0, 4.01, 0.01)]
        distance_list = np.arange(0, one_side) + 1
        distance_list = (distance_list[::-1] * -1).tolist() + [0] + distance_list.tolist()
        cmap = plt.get_cmap('cool', len(sigma_lst))
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.set_title("Sigma values of Gaussian Kernel", fontsize=15, fontweight='bold')
        for i, sigma in enumerate(sigma_lst):
            kernel = Kernels.gaussian(one_side * 2, sigma)[:, one_side + 1]
            ax.plot(distance_list, kernel, c=cmap(i))
        plt.text(1.15, 0.45, 'sigma', rotation=270, transform=ax.transAxes, fontsize=13)
        ax.vlines(0, 0.0, 0.1, ls='dashed', lw=3, color='black', label='Target Cell')
        ax.legend()
        ax.set_xlabel('Distance', fontsize=12)
        ax.set_ylabel('Weight', fontsize=12)
        sm = plt.cm.ScalarMappable(
            norm=plt.Normalize(vmin=min(sigma_lst), vmax=max(sigma_lst)), 
            cmap=cmap)
        fig.colorbar(sm, ticks=np.arange(min(sigma_lst), max(sigma_lst) + 1, 1), ax=ax)
        plt.show()

    def write_options(self) -> None:
        """設定をTextBrowserに書き込む"""
        log_board = self.textBrowser_Log
        log_board.clear()
        log_board.append('\n')
        log_board.append('___________________________________________\n')
        log_board.append("<<< Set options >>>\n")
        log_board.append(f"Input File: {self.get_input_file_path}\n")
        log_board.append(f"Output File: {self.get_output_file_path}\n")
        log_board.append(f"Color: {CsColorMaps.__qualname__}\n")
        log_board.append(f"Resampling: {self.checkBox_StartResample.isChecked()}\n")
        if self.checkBox_StartResample.isChecked():
            log_board.append(f"Resolution: {self.spinBoxF_StartResampleResol.value()}\n")
            log_board.append(f"Algorithm: {self.comboBox_StartResampleAlg.currentText()}\n")
        log_board.append(f"Slope: {self.__del_cmap(self.get_slope_options())}\n")
        log_board.append(f"TPI: {self.__del_cmap(self.get_tpi_options())}\n")
        log_board.append(f"TRI: {self.__del_cmap(self.get_tri_options())}\n")
        log_board.append(f"Hillshade: {self.__del_cmap(self.get_hillshade_options())}\n")
    
    def __del_cmap(self, options: OptionsType) -> Dict[str, Any]:
        """カラーマップを削除"""
        options_dict = options.__dict__.copy()
        options_dict.pop('cmap')
        return options_dict
                       
    def change_alpha(self, img: Image.Image, alpha: float) -> Image.Image:
        """
        画像の透過率を変更
        Args:
            img(Image.Image): 画像
            alpha(float): 透過率
        Returns:
            Image.Image: 透過率を変更したRGBA画像
        """
        ary = np.array(img)
        alpha_band = ary[:, :, 3]
        new_alpha_band = (alpha_band * alpha).astype('uint8')
        ary[:,:,3] = new_alpha_band
        new_img = Image.fromarray(ary)
        return new_img
        
    def close_dlg(self) -> None:
        self.close()



class KernelHelpDialog(QtWidgets.QDialog, HELP_KERNELS):
    def __init__(self, parent=None):
        """カーネルのヘルプダイアログ"""
        super(KernelHelpDialog, self).__init__(parent)
        self.setupUi(self)
        self.show()
        self.btn_Close.clicked.connect(self.close)

