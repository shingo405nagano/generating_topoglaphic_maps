# **- coding: utf-8 -**
from PIL import Image
from typing import Callable

from osgeo import gdal
import pyproj
from qgis.PyQt.QtCore import QCoreApplication


class MyLogger(object):
    def __init__(self, dlg):
        self.dlg = dlg
        self.log_label = self.dlg.label_Log
        self.log_board = self.dlg.textBrowser_Log
        self._stop_process = self.tr('処理を中止しました')
        self._resample_first = self.tr('Resample を実行します')
        self._clipping = self.tr('RasterData の Sample を取得')
        self._start_slope = self.tr('傾斜の計算中')
        self._start_tpi = self.tr('TPI の計算中')
        self._start_tri = self.tr('TRI の計算中')
        self._start_hillshade = self.tr('陰影起伏図の計算中')
        self._start_composite = self.tr('画像の合成開始')
        self._show_sample = self.tr('Sample を表示します')
        self._writing_raster = self.tr('RasterData の書き込み開始')
        self._completed = self.tr('処理が完了しました')
    
    def tr(self, message):
        """
        Args:
            message(str): 翻訳するメッセージ
        Returns:
            str: 翻訳されたメッセージ
        """
        return QCoreApplication.translate('MyLogger', message)
    
    @property
    def _new_line(self) -> None:
        """改行を追加する"""
        self.log_board.append('\n')
        self.log_board.append('___________________________________________\n')
    
    def title(self, title: str) -> None:
        """ログにタイトルを追加する"""
        self.log_board.append(f'<<< {title} >>>\n')

    @property
    def stop_process(self) -> None:
        """処理を中止する際にログを表示する"""
        self.log_label.setText(self._stop_process)
        self.log_board.append('Process is stopped\n')

    @property
    def start_log(self) -> None:
        """処理を開始する際にログを表示する"""
        self.log_label.setText('Starting process ...')
        self.log_board.append("Start process ...\n")
        self.log_board.append("Reading raster data ...\n")

    @property
    def input_raster_size(self) -> None:
        """入力ラスタのサイズをログに表示する"""
        self._new_line
        self.title('Original raster size')
    
    def resample_log(self, func: Callable, *args) -> None:
        """Resampleのログを表示する"""
        self.log_label.setText(self._resample_first)
        self._new_line
        self.title('Resampled raster size')
        result = func(*args)
        self.log_board.append('Resampling is completed\n')
        return result

    def clipping_raster_log(self, func: Callable, *args) -> None:
        """RasterDataのSampleを取得する際のログを表示する"""
        self.log_label.setText(self._clipping)
        self._new_line
        self.title('_clipping raster data')
        self.log_board.append('Start to _clipping raster data\n')
        result = func(*args)
        self.log_board.append('_clipping raster data is completed\n')
        return result

    def show_input_data(self, dst: gdal.Dataset) -> None:
        """入力データの情報をログに表示する
        Args:
            dst(gdal.Dataset): 入力データ
        """
        crs = pyproj.CRS(dst.GetProjection())
        proj = crs.to_json_dict()
        self.log_board.append(f"Name: {proj['name']}\n")
        self.log_board.append(f"EPSG: {proj['id']['code']}\n")
        transform = dst.GetGeoTransform()
        x_min = transform[0]
        y_max = transform[3]
        x_max = x_min + transform[1] * dst.RasterXSize
        y_min = y_max + transform[5] * dst.RasterYSize
        self.log_board.append(f"Scope X: x_min={x_min}, x_max{x_max}\n")
        self.log_board.append(f"Scope Y: y_min={y_min}, y_max={y_max}\n")
        self.log_board.append(f"Resolution: x={transform[1]}, y={transform[5]}\n")
        self.log_board.append(f"Width(Cells): {dst.RasterXSize}\n")
        self.log_board.append(f"Height(Cells): {dst.RasterYSize}\n")

    def slope_log(self, func: Callable, *args, **kwargs) -> Image.Image:
        """
        傾斜の計算のログを表示する
        Args:
            func(Callable): 傾斜の計算関数
            *args: 傾斜の計算関数の引数
            **kwargs: 傾斜の計算関数のキーワード引数
        Retruns:
            Image.Image: 傾斜のRGBA画像
        """
        self.log_label.setText(self._start_slope)
        self._new_line
        self.title('Start to calculate topographic maps')
        self._new_line
        self.title('Start to calculate slope')
        self.log_board.append('Calculating slope ...\n')
        result = func(*args, **kwargs)
        self.log_board.append('Slope calculation is completed\n')
        return result

    def tpi_log(self, func: Callable, *args, **kwargs) -> Image.Image:
        """
        TPIの計算のログを表示する
        Args:
            func(Callable): TPIの計算関数
            *args: TPIの計算関数の引数
            **kwargs: TPIの計算関数のキーワード引数
        Retruns:
            Image.Image: TPIのRGBA画像
        """
        self.log_label.setText(self._start_tpi)
        self._new_line
        self.title('Start to calculate TPI')
        result = func(*args, **kwargs)
        self.log_board.append('TPI calculation is completed\n')
        return result
    
    def tri_log(self, func: Callable, *args, **kwargs) -> Image.Image:
        """
        TRIの計算のログを表示する
        Args:
            func(Callable): TRIの計算関数
            *args: TRIの計算関数の引数
            **kwargs: TRIの計算関数のキーワード引数
        Retruns:
            Image.Image: TRIのRGBA画像
        """
        self.log_label.setText(self._start_tri)
        self._new_line
        self.title('Start to calculate TRI')
        result = func(*args, **kwargs)
        self.log_board.append('TRI calculation is completed\n')
        return result
    
    def hillshade_log(self, func: Callable, *args, **kwargs) -> Image.Image:
        """
        地形陰影の計算のログを表示する
        Args:
            func(Callable): 地形陰影の計算関数
            *args: 地形陰影の計算関数の引数
            **kwargs: 地形陰影の計算関数のキーワード引数
        Retruns:
            Image.Image: 地形陰影のRGBA画像
        """
        self.log_label.setText(self._start_hillshade)
        self._new_line
        self.title('Start to calculate Hillshade')
        result = func(*args, **kwargs)
        self.log_board.append('Hillshade calculation is completed\n')
        return result

    def composite_log(self, func: Callable, *args, **kwargs) -> Image.Image:
        """
        画像の合成のログを表示する
        Args:
            func(Callable): 画像の合成関数
            *args: 画像の合成関数の引数
            **kwargs: 画像の合成関数のキーワード引数
        Retruns:
            Image.Image: 微地形図のRGBA画像
        """
        self.log_label.setText(self._start_composite)
        self._new_line
        self.title('Start to composite images')
        self.log_board.append('Composite images ...\n')
        result = func(*args, **kwargs)
        self.log_board.append('Composite images is completed\n')
        return result

    @property
    def show_sample_img(self) -> None:
        """Sample画像を表示する際のログを表示する"""
        self.log_label.setText(self._show_sample)
        self._new_line
        self.title('Show Sample Image')
        self.log_board.append('Process is completed')
    
    def write_raster_log(self, func: Callable, *args, **kwargs):
        """RasterDataの書き込みのログを表示する"""
        self.log_label.setText(self._writing_raster)
        self._new_line
        self.title('Write raster file')
        self.log_board.append('Start writing raster file\n')
        func(*args, **kwargs)
        self.log_board.append('Writing raster file is completed\n')
        self.log_label.setText(self._completed)
        self.title('Process is completed')
    
    def add_lyr_log(self, func: Callable):
        """QGISのMapにRasterを追加する際のログを表示する"""
        self.log_board.append('Add layer to Project\n')
        func()
        self.log_board.append('Add layer is completed\n')
