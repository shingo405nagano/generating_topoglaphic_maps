from dataclasses import dataclass
import datetime
import os
import tempfile
from typing import Dict
from typing import List
from pathlib import Path

from matplotlib import pyplot as plt
import numpy as np
from qgis.core import QgsProject
from qgis.core import QgsRasterLayer
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtCore import QSettings
from qgis.utils import iface as qgis_iface


from .config import Configs
from .config import MapColors
from .custom_color_dialog import CustomColorDialog
from .visualize import plot_histgram
from ..gdal_drawer.kernels import kernels
from ..gdal_drawer.custom import CustomGdalDataset
from ..gdal_drawer.utils.colors import LinearColorMap

configs = Configs()


################################################################################
################# Input tab ####################################################
@dataclass
class FirstResampleSpec:
    execute: bool
    metre_spec: bool
    resolution: float
    denominator: int
    smooth_alg: str


class InputTab(object):
    """This class is used to get the input data from the input tab."""

    def get_input_file_path(self) -> Path:
        """
        ## Summary
            入力設定タブから入力Rasterのファイルパスを取得する。
        Returns:
            Path[str]: The file path of the input raster data.
        """
        if self.radioBtn_InputIsFile.isChecked():
            return self.fileWgt_InputFile.filePath()
        else:
            return self.lyrCombo_InputLyr.currentLayer().source()

    def get_first_resample_spec(self):
        """
        ## Summary
            データを読み込んだ後に、最初にリサンプルを行うかどうかの設定を取得する。
        Returns:
            FirstResampleSpec: The resample specification.
                - execute(bool): Whether to resample the raster data.
                - metre_spec: Whether to specify the resolution in meters.
                - resolution: The resolution of the resampled raster data.
                - denominator: The denominator of the resampled raster data.
                - smooth_alg: The algorithm used to smooth the resampled raster data.
        """
        return FirstResampleSpec(
            execute=self.checkBox_FirstResample.isChecked(),
            metre_spec=self.cmbBox_FirstResampleIs.currentIndex() == 0,
            resolution=self.spinBoxF_FirstResampleResol.value(),
            denominator=self.spinBoxInt_FirstResampleResol.value(),
            smooth_alg=self.comboBox_FirstResampleAlg.currentText(),
        )

    def make_input_tab(self):
        """
        ## Summary
            Make the input tab.
        """
        # Dataset選択
        self.fileWgt_InputFile.setFilter("GeoTiff (*.tif *.tiff *.TIF *.TIFF);;")
        if self.radioBtn_InputIsFile.isChecked():
            # Inputタブで'ファイルを読み込む'が選択された場合
            self._make_input_tab_select_file()
        elif self.radioBtn_InputIsLayer.isChecked():
            # Inputタブで'レイヤーを読み込む'が選択された場合
            self._make_input_tab_select_layer()
        # 最初にリサンプルを行うかどうか
        if self.checkBox_FirstResample.isChecked():
            self.cmbBox_FirstResampleIs.setVisible(True)
            self.comboBox_FirstResampleAlg.setVisible(True)
            self._make_input_tab_first_resample()
            self.l_20.setVisible(True)
        else:
            self._make_input_tab_first_resample_all_false()

    def _make_input_tab_select_file(self):
        """
        ## Summary
            UI settings for file selection.
        """
        self.label_InputFile.setVisible(True)
        self.fileWgt_InputFile.setVisible(True)
        self.label_InputLayer.setVisible(False)
        self.lyrCombo_InputLyr.setVisible(False)

    def _make_input_tab_select_layer(self):
        """
        ## Summary
            UI settings for layer selection.
        """
        drop_lyrs = self._make_input_lyr_drop_list("gdal")
        self.lyrCombo_InputLyr.setExceptedLayerList(drop_lyrs)
        self.lyrCombo_InputLyr.setShowCrs(True)
        self.label_InputFile.setVisible(False)
        self.fileWgt_InputFile.setVisible(False)
        self.label_InputLayer.setVisible(True)
        self.lyrCombo_InputLyr.setVisible(True)

    def _make_input_tab_first_resample(self):
        """
        ## Summary
            UI settings for resampling.
        """
        if self.cmbBox_FirstResampleIs.currentIndex() == 0:
            # select metre
            self.l_19.setVisible(True)
            self.spinBoxF_FirstResampleResol.setVisible(True)
            self.l_21.setVisible(False)
            self.spinBoxInt_FirstResampleResol.setVisible(False)
        elif self.cmbBox_FirstResampleIs.currentIndex() == 1:
            # select cells
            self.l_19.setVisible(False)
            self.spinBoxF_FirstResampleResol.setVisible(False)
            self.l_21.setVisible(True)
            self.spinBoxInt_FirstResampleResol.setVisible(True)

    def _make_input_tab_first_resample_all_false(self):
        """
        ## Summary
            UI settings for resampling when all resampling options are False.
        """
        self.l_19.setVisible(False)
        self.spinBoxF_FirstResampleResol.setVisible(False)
        self.l_21.setVisible(False)
        self.spinBoxInt_FirstResampleResol.setVisible(False)
        self.l_20.setVisible(False)
        self.comboBox_FirstResampleAlg.setVisible(False)
        self.cmbBox_FirstResampleIs.setVisible(False)

    def _make_input_lyr_drop_list(self, provider_type: str) -> List[Path]:
        """
        ## Summary
            Obtain the Layer to be excluded from the list of Layers.
        Args:
            provider_type (str): The type of provider. 'gdal'
        Returns:
            List[Path]: The list of Layers to be excluded.
        """
        lyrs = qgis_iface.mapCanvas().layers()
        filtered = []
        for lyr in lyrs:
            if (lyr.providerType() == provider_type) and isinstance(
                lyr, QgsRasterLayer
            ):
                if 1 < lyr.bandCount():
                    # バンド数が1より大きい場合は除外
                    filtered.append(lyr)
            else:
                filtered.append(lyr)
        return filtered


################################################################################
#################### Output tab ###############################################
@dataclass
class OutputSpec:
    sample_only: bool
    sampling_max_cols: int
    sampling_max_rows: int
    add_project: bool
    output_file_path: str
    slope_cmap: LinearColorMap
    tpi_cmap: LinearColorMap
    tri_cmap: LinearColorMap
    hillshade_cmap: LinearColorMap


class OutputTab(object):
    """
    ## Summary
        出力設定タブから出力設定を取得するためのクラス。
    """

    def __init__(self):
        self.temp_file = False

    def tr(self, message: str):
        return QCoreApplication.translate(self.__class__.__name__, message)

    def make_output_tab(self) -> None:
        """
        ## Summary
            Make the output tab.
        """
        self.set_placeholder()
        if self.mapSelectRadioBtn_YourStyle.isChecked():
            # ユーザー定義のスタイルを選択した場合は設定ダイアログを表示出来るように
            self.btn_CustomDlg.setVisible(True)
        else:
            self.btn_CustomDlg.setVisible(False)
        if self.checkBox_Sample.isChecked():
            self.checkBox_AddProject.setVisible(False)
            self.label_OutputFile.setVisible(False)
            self.fileWgt_OutputFile.setVisible(False)
            self.l_8.setVisible(True)
            self.spinBoxInt_SamplingMaxCols.setVisible(True)
            self.l_7.setVisible(True)
            self.spinBoxInt_SamplingMaxRows.setVisible(True)
        else:
            self.checkBox_AddProject.setVisible(True)
            self.label_OutputFile.setVisible(True)
            self.fileWgt_OutputFile.setVisible(True)
            self.l_8.setVisible(False)
            self.spinBoxInt_SamplingMaxCols.setVisible(False)
            self.l_7.setVisible(False)
            self.spinBoxInt_SamplingMaxRows.setVisible(False)

    def show_map_styles(self) -> None:
        """
        ## Summary
            Display the map styles is used matpliotlib. The images displayed here are pre-created images.
        """
        imgs = [configs.org_map_img, configs.vintage_map_img, configs.rgb_map_img]
        titles = ["Original-Map Styled", "Vintage-Map Styled", "RGB-Map Styled"]
        _ax = None
        fig = plt.figure(figsize=(12, 8))
        for i, (img, title) in enumerate(zip(imgs, titles), start=1):
            ax = fig.add_subplot(2, 2, i, sharex=_ax, sharey=_ax)
            ax.set_title(title, fontsize=17, fontweight="bold")
            ax.imshow(img)
            ax.axis("off")
            _ax = ax
        plt.subplots_adjust(
            left=0.05, right=0.95, top=0.95, bottom=0.05, wspace=0.05, hspace=0.08
        )
        plt.show()

    def show_custom_color_dlg(self) -> None:
        """
        ## Summary
            Display the custom color dialog.
        """
        self.custom_color_dlg = CustomColorDialog(self)
        self.custom_color_dlg.show()

    def get_output_spec(self) -> OutputSpec:
        """
        ## Summary
            Get the output specification.
        Returns:
            OutputSpec: The output specification.
                - sample_only: Whether to output only the sample.
                - sampling_max_cols: The maximum number of columns to be output.
                - sampling_max_rows: The maximum number of rows to be output.
                - add_project: Whether to add the output raster data to the project.
                - output_file_path: The file path of the output raster data.
                - slope_cmap: The color map for the slope.
                - tpi_cmap: The color map for the TPI.
                - tri_cmap: The color map for the TRI.
                - hillshade_cmap: The color map for the hillshade.
        """
        return OutputSpec(
            sample_only=self.checkBox_Sample.isChecked(),
            sampling_max_cols=self.spinBoxInt_SamplingMaxCols.value(),
            sampling_max_rows=self.spinBoxInt_SamplingMaxRows.value(),
            add_project=self.checkBox_AddProject.isChecked(),
            output_file_path=self.get_file_path(),
            slope_cmap=self.get_cmaps()["slope"],
            tpi_cmap=self.get_cmaps()["tpi"],
            tri_cmap=self.get_cmaps()["tri"],
            hillshade_cmap=self.get_cmaps()["hillshade"],
        )

    def get_style_name(self) -> str:
        """
        ## Summary
            Get the style name.
        Returns:
            str: The style name.
        """
        if self.mapSelectRadioBtn_Org.isChecked():
            return "Original-Map"
        elif self.mapSelectRadioBtn_RGB.isChecked():
            return "RGB-Map"
        elif self.mapSelectRadioBtn_Vintage.isChecked():
            return "Vintage-Map"
        else:
            return "CUSTOM-Map"

    def get_cmaps(self) -> Dict[str, LinearColorMap]:
        """
        ## Summary
            Get the color maps for the slope, TPI, TRI, and hillshade.
        Returns:
            Dict[str, LinearColorMap]: The color maps for the 'slope', 'tpi', 'tri', and 'hillshade'.
        """
        map_name = self.get_style_name()
        map_colors = MapColors(map_name)
        return {
            "slope": map_colors.slope_cmap(),
            "tpi": map_colors.tpi_cmap(),
            "tri": map_colors.tri_cmap(),
            "hillshade": map_colors.hillshade_cmap(),
        }

    def set_placeholder(self) -> None:
        """
        ## Summary
            Set the placeholder text for the output file path.
        """
        locale = QSettings().value("locale/userLocale")[0:2]
        if locale == "ja":
            txt = "[一時ファイルに保存]"
        else:
            txt = "[Save to temporary file]"
        fwgt = self.fileWgt_OutputFile
        fwgt.lineEdit().setPlaceholderText(txt)
        self.fileWgt_OutputFile.setFilter("GeoTiff (*.tif);;")

    def get_file_path(self) -> Path:
        """
        ## Summary
            Get the file path of the output raster data.
        Returns:
            Path[str]: The file path of the output raster data. If empty, create temporary file
        """
        path = self.fileWgt_OutputFile.filePath()
        if path == "":
            # ファイルパスが空の場合、一時ファイルを作成
            with tempfile.NamedTemporaryFile(suffix="_topoMaps.tif") as tf:
                path = tf.name
            # レイヤーも強制的に追加
            self.checkBox_AddProject.setChecked(True)
            self.temp_file = True
            return path
        self.temp_file = False
        return path

    def add_lyr(self, output_file_path: Path, prefix: str = "") -> None:
        """
        ## Summary
            Add the output raster data to the project.
        Args:
            output_file_path (Path): The file path of the output raster data.
        """
        if self.checkBox_AddProject.isChecked():
            if self.temp_file:
                lyr_name = self.str_time(prefix=prefix)
            else:
                lyr_name = os.path.basename(output_file_path).split(".")[0]
            lyr = QgsRasterLayer(output_file_path, lyr_name, "gdal")
            QgsProject.instance().addMapLayer(lyr)
        self.temp_file = False

    def str_time(self, prefix: str = "", suffix: str = "") -> str:
        """
        ## Summary
            Get the current time as a string.
        Args:
            prefix (str): The prefix of the string.
            suffix (str): The suffix of the string.
        Returns:
            str: The current time as a string.
        """
        now = datetime.datetime.now()
        st = now.strftime("%H:%M:%S")
        prefix = prefix if prefix == "" else f"{prefix}_"
        suffix = suffix if suffix == "" else f"_{suffix}"
        return f"{prefix}TempFile_{st}{suffix}"


################################################################################
#################### Slope tab ###############################################
@dataclass
class SlopeOptions:
    metre_spec: bool
    distance: float
    cells: int
    execute_gaussian_filter: bool
    sigma: float
    change_alpha: bool
    alpha: float


class SlopeTab(object):
    """
    ## Summary
        This class is used to get the slope data from the slope tab.
    """

    def make_slope_tab(self):
        if self.cmbBox_SlopeDistanceSpec.currentIndex() == 0:
            self.spinBoxF_SlopeDistanceMetre.setVisible(True)
            self.spinBoxInt_SlopeDistanceCells.setVisible(False)
            self.l_16.setVisible(True)
            self.l_18.setVisible(False)
        else:
            self.spinBoxF_SlopeDistanceMetre.setVisible(False)
            self.spinBoxInt_SlopeDistanceCells.setVisible(True)
            self.l_16.setVisible(False)
            self.l_18.setVisible(True)

    def get_slope_options(self):
        return SlopeOptions(
            metre_spec=self.cmbBox_SlopeDistanceSpec.currentIndex() == 0,
            distance=self.spinBoxF_SlopeDistanceMetre.value(),
            cells=self.spinBoxInt_SlopeDistanceCells.value(),
            execute_gaussian_filter=self.gpBox_SlopeGauss.isChecked(),
            sigma=self.spinBoxF_SlopeGaussSigma.value(),
            change_alpha=self.gpBox_SlopeAlpha.isChecked(),
            alpha=self.spinBoxInt_SlopeAlpha.value() * 0.01,
        )

    def show_slope_gaussian_kernel(self, unit: float):
        options = self.get_slope_options()
        kernel = kernels.gaussian_kernel(options.sigma)
        kernels.plot_kernel_3d(kernel, unit_length=unit)


################################################################################
#################### TPI tab ###############################################
@dataclass
class TpiOptions:
    kernel_spec: str
    metre_spec: bool
    distance: float
    cells: int
    sigma: float
    coef: float
    execute_outlier_treatment: bool
    iqr: float
    change_alpha: bool
    alpha: float
    multiple_tpi: bool
    multiples_distance: float


class TpiTab(object):
    def get_tpi_options(self):
        if self.radioBtn_OrgKernel.isChecked():
            kernel_spec = "org"
        elif self.radioBtn_GaussKernel.isChecked():
            kernel_spec = "gauss"
        elif self.radioBtn_InvGaussKernel.isChecked():
            kernel_spec = "inv_gauss"
        elif self.radioBtn_MeanKernel.isChecked():
            kernel_spec = "mean"
        elif self.radioBtn_DoughnutKernel.isChecked():
            kernel_spec = "doughnut"
        else:
            kernel_spec = "org"
        return TpiOptions(
            kernel_spec=kernel_spec,
            metre_spec=self.cmbBox_KernelDistanceSpec.currentIndex() == 0,
            distance=self.spinBoxF_KernelSizeMetre.value(),
            cells=self.spinBoxInt_KernelSizeCells.value(),
            sigma=self.spinBoxF_TpiGaussSigma.value(),
            coef=self.spinBoxF_TpiGaussCoef.value(),
            execute_outlier_treatment=self.gpBox_TpiOutTreatment.isChecked(),
            iqr=self.spinBoxF_TpiIQR.value(),
            change_alpha=self.gpBox_TpiAlpha.isChecked(),
            alpha=self.spinBoxInt_TpiAlpha.value() * 0.01,
            multiple_tpi=self.gpBox_MultipleTpi.isChecked(),
            multiples_distance=self.spinBoxF_TpiMultiplesDistance.value(),
        )

    def make_tpi_tab(self) -> None:
        """TPIタブの設定を変更する"""
        if self.radioBtn_DoughnutKernel.isChecked():
            self._make_tpi_tab_select_kernel_is_other()
        elif self.radioBtn_MeanKernel.isChecked():
            self._make_tpi_tab_select_kernel_is_other()
        elif self.radioBtn_OrgKernel.isChecked():
            self._make_tpi_tab_select_kernel_is_org()
        elif self.radioBtn_GaussKernel.isChecked():
            self._make_tpi_tab_select_kernel_is_gauss()
        elif self.radioBtn_InvGaussKernel.isChecked():
            self._make_tpi_tab_select_kernel_is_gauss()

    def _make_tpi_tab_select_kernel_is_org(self) -> None:
        """TPIタブのカーネル設定で"隣接セル"が選択された場合の設定を行う"""
        self.cmbBox_KernelDistanceSpec.setVisible(False)
        self.l_15.setVisible(False)
        self.spinBoxF_KernelSizeMetre.setVisible(False)
        self.spinBoxInt_KernelSizeCells.setVisible(False)
        self.l_4.setVisible(False)
        self.spinBoxF_TpiGaussSigma.setVisible(False)
        self.l_5.setVisible(False)
        self.spinBoxF_TpiGaussCoef.setVisible(False)

    def _make_tpi_tab_select_kernel_is_gauss(self) -> None:
        """TPIタブのカーネル設定で"ガウシアン"か"逆ガウシアン"が選択された場合の設定を行う"""
        self.cmbBox_KernelDistanceSpec.setVisible(False)
        self.l_15.setVisible(False)
        self.spinBoxF_KernelSizeMetre.setVisible(False)
        self.spinBoxInt_KernelSizeCells.setVisible(False)
        self.l_4.setVisible(True)
        self.spinBoxF_TpiGaussSigma.setVisible(True)
        self.l_5.setVisible(True)
        self.spinBoxF_TpiGaussCoef.setVisible(True)

    def _make_tpi_tab_select_kernel_is_other(self) -> None:
        """TPIタブのカーネル設定で"平均化"か"ドーナツ"が選択された場合の設定を行う"""
        self.cmbBox_KernelDistanceSpec.setVisible(True)
        self.l_15.setVisible(True)
        if self.cmbBox_KernelDistanceSpec.currentIndex() == 0:
            self.spinBoxF_KernelSizeMetre.setVisible(True)
            self.spinBoxInt_KernelSizeCells.setVisible(False)
        else:
            self.spinBoxF_KernelSizeMetre.setVisible(False)
            self.spinBoxInt_KernelSizeCells.setVisible(True)
        self.l_4.setVisible(False)
        self.spinBoxF_TpiGaussSigma.setVisible(False)
        self.l_5.setVisible(False)
        self.spinBoxF_TpiGaussCoef.setVisible(False)

    def generate_kernel(self, dst: CustomGdalDataset, **kwargs) -> np.array:
        """
        畳み込み用のカーネルを生成する。
        Args:
            dst(CustomGdalDataset): 入力データセット
            **kwargs:
                multiples(float): tpiのカーネルサイズを大きくする場合の倍率
        Returns:
            np.array: カーネル
        """
        options = self.get_tpi_options()
        # multiplesが指定されている場合は、カーネルサイズを大きくする
        sigma = options.sigma * kwargs.get("multiples", 1.0)
        distance = options.distance * kwargs.get("multiples", 1.0)
        cells = int(options.cells * kwargs.get("multiples", 1.0))
        if options.kernel_spec == "org":
            # gdal.DEMProcessing で計算するため、カーネルは不要
            kernel = None
        elif options.kernel_spec == "gauss":
            kernel = kernels.gaussian_kernel(sigma, options.coef)
        elif options.kernel_spec == "inv_gauss":
            kernel = kernels.inverse_gaussian_kernel(sigma, options.coef)
        elif options.metre_spec:
            # 畳み込みのカーネルサイズをメートル単位で指定
            if options.kernel_spec == "mean":
                kernel = dst.mean_kernel_from_distance(distance, True)
            else:
                kernel = dst.doughnut_kernel_from_distance(distance, True)
        else:
            # 畳み込みのカーネルサイズをセル数で指定
            if options.kernel_spec == "mean":
                kernel = kernels.mean_kernel(cells)
            else:
                kernel = kernels.doughnut_kernel(cells)
        return kernel

    def show_kernel(self, dst: CustomGdalDataset) -> None:
        """
        カーネルを`matplotlib`で表示する。
        Args:
            dst(CustomGdalDataset): 入力データセット
        """
        options = self.get_tpi_options()
        kernel = self.generate_kernel(dst)
        if kernel is not None:
            if options.kernel_spec == "doughnut":
                kernels.plot_kernel_3d(
                    kernel=kernel, unit_length=dst.x_resolution, is_marker=True
                )
            else:
                kernels.plot_kernel_3d(kernel=kernel, unit_length=dst.x_resolution)
        dst = None

    def show_tpi_histogram(self, dst: CustomGdalDataset) -> None:
        ary = dst.array()
        plot_histgram(ary)


################################################################################
#################### TRI tab ###############################################
@dataclass
class TriOptions:
    execute: bool
    execute_gaussian_filter: bool
    sigma: float
    execute_outlier_treatment: bool
    iqr: float
    change_alpha: bool
    alpha: float


class TriTab(object):
    def get_tri_options(self):
        return TriOptions(
            execute=self.gpBox_Tri.isChecked(),
            execute_gaussian_filter=self.gpBox_TriGauss.isChecked(),
            sigma=self.spinBoxF_TriGaussSigma.value(),
            execute_outlier_treatment=self.gpBox_TriOutTreatment.isChecked(),
            iqr=self.spinBoxF_TriIQR_.value(),
            change_alpha=self.gpBox_TriAlpha.isChecked(),
            alpha=self.spinBoxInt_TriAlpha.value() * 0.01,
        )

    def show_tri_gaussian_kernel(self, unit: float):
        options = self.get_tri_options()
        kernel = kernels.gaussian_kernel(options.sigma)
        kernels.plot_kernel_3d(kernel, unit_length=unit)


################################################################################
#################### Hillshade tab #############################################
@dataclass
class HillshadeOptions:
    hillshade_type: str
    azimuth: float
    altitude: float
    z_factor: float
    combined: bool
    execute_gaussian_filter: bool
    sigma: float
    execute_outlier_treatment: bool
    iqr: float


class HillshadeTab(object):
    def get_hillshade_options(self):
        if self.cmbBox_HillshadeType.currentIndex() == 0:
            hillshade_type = "single"
        else:
            hillshade_type = "multiple"
        return HillshadeOptions(
            hillshade_type=hillshade_type,
            azimuth=self.spinBoxInt_HillshadeAzimuth.value(),
            altitude=self.spinBoxInt_HillshadeHight.value(),
            z_factor=self.spinBoxF_HillshadeHighlight.value(),
            combined=self.checkBox_CombinedSlope.isChecked(),
            execute_gaussian_filter=self.gpBox_HillshadeGauss.isChecked(),
            sigma=self.spinBoxF_HillshadeGaussSigma.value(),
            execute_outlier_treatment=self.gpBox_HillshadeOutTreatment.isChecked(),
            iqr=self.spinBoxF_HillshadeIQR.value(),
        )

    def make_hillshade_tab(self):
        if self.cmbBox_HillshadeType.currentIndex() == 0:
            self.spinBoxInt_HillshadeAzimuth.setVisible(True)
            self.l_11.setVisible(True)
            self.checkBox_CombinedSlope.setVisible(True)
        else:
            self.spinBoxInt_HillshadeAzimuth.setVisible(False)
            self.l_11.setVisible(False)
            self.checkBox_CombinedSlope.setVisible(False)

    def show_hillshade_gaussian_kernel(self, unit: float):
        options = self.get_hillshade_options()
        kernel = kernels.gaussian_kernel(options.sigma)
        kernels.plot_kernel_3d(kernel, unit_length=unit)


################################################################################
#################### Others tab ###############################################
@dataclass
class OthersOptions:
    execute_unsharpn_mask: bool
    unsharpn_radius: float
    unsharpn_percent: int
    unsharpn_threshold: int
    execute_contrast: bool
    contrast_value: float


class OthersTab(object):
    def get_others_options(self):
        return OthersOptions(
            execute_unsharpn_mask=self.gpBox_Unsharpn.isChecked(),
            unsharpn_radius=self.spinBoxF_UnsharpnRads.value(),
            unsharpn_percent=self.spinBoxInt_UnsharpnPer.value(),
            unsharpn_threshold=self.spinBoxInt_UnsharpnThres.value(),
            execute_contrast=self.gpBox_Contrast.isChecked(),
            contrast_value=self.spinBoxF_Contrast.value(),
        )

    def make_others_tab_change_slider(self):
        self.spinBoxF_Contrast.setValue(self.hSlider_Contrast.value() * 0.01)
