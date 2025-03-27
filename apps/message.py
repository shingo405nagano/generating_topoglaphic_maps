# **- coding: utf-8 -**
import os
from pathlib import Path
from typing import Any

from osgeo import gdal
import pyproj
from qgis.core import Qgis
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import iface as qgis_iface

from ..gdal_drawer.custom import CustomGdalDataset
from .tabs import FirstResampleSpec
from .tabs import HillshadeOptions
from .tabs import SlopeOptions
from .tabs import TpiOptions
from .tabs import TriOptions


class Message(object):
    def __init__(self):
        self._file_extensions = [".tif", ".tiff"]
        self._file_not_specified = self.tr("入力ファイルが指定されていません。")
        self._file_not_found = self.tr("入力ファイルが見つかりません。")
        self._input_file_extension_error = self.tr(
            "入力ファイルの拡張子が.tifまたは.tiffではありません。"
        )
        self._output_file_extension_error = self.tr(
            "出力ファイルの拡張子が.tifまたは.tiffではありません。"
        )
        self._raster_band_error = self.tr("入力ラスターのバンド数が1よりも多いです。")
        self._output_folder_does_not_exist = self.tr("出力フォルダが存在しません。")
        self._finished_msg = self.tr("計算が完了しました。")
        self._user_cancel_msg = self.tr(
            "ユーザーが操作をキャンセルしたかもしれません。"
        )

    def tr(self, message):
        """
        Args:
            message(str): 翻訳するメッセージ
        Returns:
            str: 翻訳されたメッセージ
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def err_msg(self, message: str):
        """
        ## Summary
            エラーメッセージを表示する。
        Args:
            message(str): エラーメッセージ
        """
        QMessageBox.critical(None, self.tr("Error"), message)

    def check_input_file_path(self, file_path: Path) -> bool:
        """
        ## Summary
            入力ファイルのパスが正しいかどうかをチェックする。問題があればエラーメッセージをポップアップで表示する。
        Args:
            file_path (Path): 入力ファイルのパス
        Returns:
            bool: チェック結果
        """
        if file_path is None:
            # ファイルが指定されていない場合にエラーメッセージを表示
            self.err_msg(self._file_not_specified)
            return False
        elif not os.path.exists(file_path):
            # ファイルが存在しない場合にエラーメッセージを表示
            self.err_msg(self._file_not_found)
            return False
        elif Path(file_path).suffix not in self._file_extensions:
            self.err_msg(self._input_file_extension_error)
            return False
        _dst = gdal.Open(file_path)
        if _dst.RasterCount != 1:
            self.err_msg(self._raster_band_error)
            return False
        return True

    def check_output_file_path(self, file_path: Path, is_sample: bool) -> bool:
        """
        ## Summary
            出力ファイルのパスが正しいかどうかをチェックする。問題があればエラーメッセージをポップアップで表示する。
        Args:
            file_path (Path): 出力ファイルのパス
            is_sample (bool): サンプルのみの場合はTrue
        Returns:
            bool: チェック結果
        """
        if is_sample:
            # サンプルのみの場合は出力ファイルを指定しなくともよい
            return True
        elif not os.path.isdir(os.path.dirname(file_path)):
            # 出力フォルダが存在しない場合にエラーメッセージを表示
            self.err_msg(self._output_folder_does_not_exist)
            return False
        elif Path(file_path).suffix not in self._file_extensions:
            self.err_msg(self._output_file_extension_error)
            return False
        return True

    def created_infomation(self, MESSAGE_CATEGORY: str, dst: CustomGdalDataset) -> None:
        """
        ## Summary
            作成したデータセットの情報をQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            dst (CustomGdalDataset): 作成したデータセット
        """
        bounds = dst.bounds()
        resol = dst.cell_size_in_metre()
        degrees = dst.cell_size_in_degree()
        txt = (
            "Created dataset: {"
            f"'Size': [{dst.RasterXSize} x {dst.RasterYSize} x {dst.RasterCount}], "
            f"'Projection': [EPSG:{pyproj.CRS(dst.GetProjection()).to_epsg()}], "
            f"'Bounds': [{bounds.x_min}, {bounds.y_min}, {bounds.x_max}, {bounds.y_max}], "
            f"'Resolution(m)': [{resol.x_size}, {resol.y_size}], "
            f"'Degree': [{degrees.x_size}, {degrees.y_size}], "
        )
        QgsMessageLog.logMessage(txt + "}", MESSAGE_CATEGORY, Qgis.Info)

    def start_read_raster(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Rasterの読み込みを開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage("Reading raster dataset", MESSAGE_CATEGORY, Qgis.Info)

    def end_read_raster(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Rasterの読み込みが完了したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Reading raster is completed.", MESSAGE_CATEGORY, Qgis.Info
        )

    def start_resampling_raster(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Rasterのリサンプリングを開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Resampling raster dataset", MESSAGE_CATEGORY, Qgis.Info
        )

    def resampling_spec(
        self, MESSAGE_CATEGORY: str, resampling_spec: FirstResampleSpec
    ) -> None:
        """
        ## Summary
            リサンプリングの仕様をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            resampling_spec (FirstResampleSpec): リサンプリ
        """
        txt = (
            "Resampling specification: {"
            f"'SmoothAlgorithm': {resampling_spec.smooth_alg}, "
        )
        if resampling_spec.metre_spec:
            txt += f"'Resolution': {resampling_spec.resolution} m, "
        else:
            resampling_spec.denominator
            txt += f"'Denominator': {resampling_spec.denominator}, "
        QgsMessageLog.logMessage(txt + "}", MESSAGE_CATEGORY, Qgis.Info)

    def end_resampling_raster(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Rasterのリサンプリングが完了したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Resampling raster is completed.", MESSAGE_CATEGORY, Qgis.Success
        )

    def start_slope_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Slopeの計算を開始することをQGISのログコンソールに表示する。
        """
        QgsMessageLog.logMessage(
            "Start slope calculation.", MESSAGE_CATEGORY, Qgis.Info
        )

    def slope_spec(self, MESSAGE_CATEGORY: str, slope_spec: SlopeOptions) -> None:
        """
        ## Summary
            Slopeの仕様をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            slope_spec (SlopeOptions): Slopeの仕様
        """
        txt = "Slope calculation specification: {"
        if slope_spec.metre_spec:
            txt += f"'Distance[m]': {slope_spec.distance}, "
        else:
            txt += f"'Cells': {slope_spec.distance}, "
        if slope_spec.execute_gaussian_filter:
            txt += f"'Gaussian filter sigma': {slope_spec.sigma}, "
        if slope_spec.change_alpha:
            txt += f"'Relative alpha': {slope_spec.alpha}, "
        QgsMessageLog.logMessage(txt + "}", MESSAGE_CATEGORY, Qgis.Info)

    def end_slope_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Slopeの計算が完了したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Slope calculation is completed.", MESSAGE_CATEGORY, Qgis.Success
        )

    def start_tpi_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            TPIの計算を開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage("Start TPI calculation.", MESSAGE_CATEGORY, Qgis.Info)

    def tpi_spec(self, MESSAGE_CATEGORY: str, tpi_spec: TpiOptions) -> None:
        """
        ## Summary
            TPIの仕様をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            tpi_spec (TpiOptions): TPIの仕様
        """
        txt = f"TPI calculation specification: {{'Kernel': {tpi_spec.kernel_spec}, "
        if "gauss" in tpi_spec.kernel_spec.lower():
            txt += (
                f"'Gaussian filter sigma': {tpi_spec.sigma}, "
                f"'Gaussian filter coef': {tpi_spec.coef}, "
            )
        else:
            if tpi_spec.metre_spec:
                txt += f"'Distance[m]': {tpi_spec.distance}, "
            else:
                txt += f"'Cells': {tpi_spec.distance}, "
        if tpi_spec.execute_outlier_treatment:
            txt += f"'Outlier treatment is IQR x':  {tpi_spec.iqr}, "
        if tpi_spec.change_alpha:
            txt += f"'Relative alpha': {tpi_spec.alpha}, "
        if tpi_spec.multiple_tpi:
            txt += f"'Multiples distance': {tpi_spec.multiples_distance}, "
        QgsMessageLog.logMessage(txt + "}", MESSAGE_CATEGORY, Qgis.Info)

    def end_tpi_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            TPIの計算が完了したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "TPI calculation is completed.", MESSAGE_CATEGORY, Qgis.Success
        )

    def start_tri_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            TRIの計算を開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage("Start TRI calculation.", MESSAGE_CATEGORY, Qgis.Info)

    def tri_spec(self, MESSAGE_CATEGORY: str, tri_spec: TriOptions) -> None:
        """
        ## Summary
            TRIの仕様をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            tri_spec (TriOptions): TRIの仕様
        """
        txt = "TRI calculation specification: {"
        if tri_spec.execute_gaussian_filter:
            txt += f"'Gaussian filter sigma': {tri_spec.sigma}, "
        if tri_spec.execute_outlier_treatment:
            txt += f"'Outlier treatment is IQR x': {tri_spec.iqr}, "
        if tri_spec.change_alpha:
            txt += f"'Relative alpha': {tri_spec.alpha}, "
        QgsMessageLog.logMessage(txt + "}", MESSAGE_CATEGORY, Qgis.Info)

    def end_tri_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            TRIの計算が完了したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "TRI calculation is completed.", MESSAGE_CATEGORY, Qgis.Success
        )

    def start_hillshade_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            Hillshadeの計算を開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Start hillshade calculation.", MESSAGE_CATEGORY, Qgis.Info
        )

    def hillshade_spec(
        self, MESSAGE_CATEGORY: str, hillshade_spec: HillshadeOptions
    ) -> None:
        """
        ## Summary
            Hillshadeの仕様をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            hillshade_spec (HillshadeOptions): Hillshadeの仕様
        """
        txt = (
            "Hillshade calculation specification: {"
            f"'Hillshade type': {hillshade_spec.hillshade_type}, "
        )
        if hillshade_spec.hillshade_type == "single":
            txt += f"'Azimuth': {hillshade_spec.azimuth}, "
        txt += (
            f"'Altitude': {hillshade_spec.altitude}, "
            f"'Z-factor': {hillshade_spec.z_factor}, "
            "'Comblined': {hillshade_spec.combined}, "
        )
        if hillshade_spec.execute_gaussian_filter:
            txt += f"'Gaussian filter sigma': {hillshade_spec.sigma}, "
        if hillshade_spec.execute_outlier_treatment:
            txt += f"'Outlier treatment is IQR x': {hillshade_spec.iqr}, "
        QgsMessageLog.logMessage(txt + "}", MESSAGE_CATEGORY, Qgis.Info)

    def end_hillshade_calculation(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            TPIの計算を開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Hillshade calculation is completed.", MESSAGE_CATEGORY, Qgis.Success
        )

    def start_composite_image(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            画像の合成を開始することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Start compositing images.", MESSAGE_CATEGORY, Qgis.Info
        )

    def end_composite_image(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            画像の合成が完了したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(
            "Image compositing is completed.", MESSAGE_CATEGORY, Qgis.Success
        )

    def show_raster(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            ラスターを表示することをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage("Show raster", MESSAGE_CATEGORY, Qgis.Info)

    def run_task(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            タスクを追加したことをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage("Task added", MESSAGE_CATEGORY, Qgis.Info)

    def finished_msg_on_the_bar(self) -> None:
        """
        ## Summary
            完了メッセージをQGISのメッセージバーに表示する。
        """
        qgis_iface.messageBar().pushMessage(
            "Success Message: ", self._finished_msg, level=Qgis.Success, duration=10
        )

    def finished_msg(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            完了メッセージをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage("Finished\n", MESSAGE_CATEGORY, Qgis.Success)

    def user_cancel_msg_on_the_bar(self) -> None:
        """
        ## Summary
            キャンセルメッセージをQGISのメッセージバーに表示する。
        """
        qgis_iface.messageBar().pushMessage(
            "Canceled Message: ", self._user_cancel_msg, level=Qgis.Warning, duration=10
        )

    def user_cancel_msg(self, MESSAGE_CATEGORY: str) -> None:
        """
        ## Summary
            キャンセルメッセージをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
        """
        QgsMessageLog.logMessage(self._user_cancel_msg, MESSAGE_CATEGORY, Qgis.Warning)

    def exception_msg_on_the_bar(self, exception: Any) -> None:
        """
        ## Summary
            例外メッセージをQGISのメッセージバーに表示する。
        Args:
            exception (Any): 例外メッセージ
        """
        qgis_iface.messageBar().pushMessage(
            "Error Message: ", exception, level=Qgis.Critical, duration=10
        )

    def exception_msg(self, MESSAGE_CATEGORY: str, exception: Any) -> None:
        """
        ## Summary
            例外メッセージをQGISのログコンソールに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            exception (Any): 例外メッセージ
        """
        QgsMessageLog.logMessage(exception, MESSAGE_CATEGORY, Qgis.Critical)

    def computing_time(self, MESSAGE_CATEGORY: str, computing_time: float) -> None:
        """
        ## Summary
            計算時間をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            computing_time (float): 計算時間
        """
        QgsMessageLog.logMessage(
            f"Computing time: {computing_time} sec", MESSAGE_CATEGORY, Qgis.Success
        )

    def delete_file(self, MESSAGE_CATEGORY: str, file_path: Path) -> None:
        """
        ## Summary
            ファイルの削除をログに表示する。
        Args:
            MESSAGE_CATEGORY (str): メッセージカテゴリ。QGISのログコンソールタブのタイトルに使用される。
            file_path (Path): 削除するファイルのパス
        """
        QgsMessageLog.logMessage(
            f"Delete file: {file_path}", MESSAGE_CATEGORY, Qgis.Info
        )


msg = Message()
