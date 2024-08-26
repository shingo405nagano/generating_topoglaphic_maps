"""
process.write_raster_to_mem
    Rasterデータをメモリ上に作成する。

process.get_ary
    Rasterデータの配列を取得する。

process.nodata_to_nan
    RasterデータのNoDataをnanに変換し、配列を返す。

process.outlier_treatment
    四分位範囲を用いた外れ値処理

process.convolution
    畳み込み処理を行う

process.resampling
    ラスターデータの解像度を変更する
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Callable
from typing import NamedTuple
from typing import Union

import numpy as np
from osgeo import gdal
import scipy.ndimage


class Process(object):
    def write_raster_to_mem(self,
        org_dst: gdal.Dataset, 
        ary: np.ndarray, 
        data_type: int=gdal.GDT_Float32,
        nodata: Any=np.nan
    ) -> gdal.Dataset:
        """
        メモリ上にラスターデータを作成する
        Args:
            org_dst(gdal.Dataset): ラスターデータ
            ary(np.ndarray): ラスターデータの配列
            data_type(int): データ型
            nodata(Any): NoData
        Returns:    
            gdal.Dataset
        """
        driver = gdal.GetDriverByName('MEM')
        driver.Register()
        new_dst = driver.Create(
            '',
            xsize=org_dst.RasterXSize, 
            ysize=org_dst.RasterYSize, 
            bands=1, 
            eType=data_type
        )
        new_dst.SetGeoTransform(org_dst.GetGeoTransform())
        new_dst.SetProjection(org_dst.GetProjection())
        band = new_dst.GetRasterBand(1)
        # データの書き込み
        band.WriteArray(ary)
        band.SetNoDataValue(nodata)
        return new_dst


    def get_ary(self,
        data: Union[gdal.Dataset, np.ndarray],
        band: int=1
    ) -> np.ndarray:
        """
        ラスターデータの配列を取得する
        Args:
            data(Union[gdal.Dataset, np.ndarray]): ラスターデータ
            band(int): バンド
        Returns:
            np.ndarray
        """
        if isinstance(data, gdal.Dataset):
            band = data.GetRasterBand(band)
            ary = band.ReadAsArray()
        else:
            ary = data
        return ary


    def nodata_to_nan(self,
        data: Union[gdal.Dataset, np.ndarray], 
        nodata: int=-9999,
    ) -> np.ndarray:
        """
        ラスターデータのNoDataをnanに変換し、配列を返す
        Args:
            data(Union[gdal.Dataset, np.ndarray]): ラスターデータ
            nodata(int): NoData
        Returns:
            np.ndarray
        """
        if isinstance(data, gdal.Dataset):
            nodata = data.GetRasterBand(1).GetNoDataValue()
        ary = self.get_ary(data)
        return np.where(ary == nodata, np.nan, ary)
        

    def outlier_treatment(self,
        data: Union[gdal.Dataset, np.ndarray], 
        threshold: int=2,
        ) -> np.ndarray:
        """
        四分位範囲を用いた外れ値処理
        Args:
            data(Union[gdal.Dataset, np.ndarray]): ラスターデータ
            threshold(int): 外れ値の閾値
        Returns:
            np.ndarray
        """
        ary = self.get_ary(data)
        q1 = np.nanquantile(ary, 0.25)
        q3 = np.nanquantile(ary, 0.75)
        iqr = q3 - q1
        lwt = q1 - threshold * iqr
        uwt = q3 + threshold * iqr
        processed = (
            np.where(ary < lwt, lwt, 
                np.where(uwt < ary, uwt, ary)
            )
        )
        return processed


    def convolution(self,
        data: Union[gdal.Dataset, np.ndarray], 
        kernel: np.ndarray,
        mode='constant',
    ) -> Union[np.ndarray]:
        """
        畳み込み処理を行う
        Args:
            data(Union[gdal.Dataset, np.ndarray]): ラスターデータ
            kernel(np.ndarray): カーネル
            mode(str): モード
        Returns:
            np.ndarray
        """
        if isinstance(data, gdal.Dataset):
            nodata = data.GetRasterBand(1).GetNoDataValue()
        else:
            nodata = -9999
        ary = self.get_ary(data)
        ary = self.nodata_to_nan(ary, nodata)
        convd_ary = scipy.ndimage.convolve(ary, kernel, mode=mode, cval=np.nan)
        return convd_ary


    def resampling(self, dst: gdal.Dataset, x_res: int, y_res: int) -> gdal.Dataset:
        """
        ラスターデータの解像度を変更する
        Args:
            dst(gdal.Dataset): ラスターデータ
            x_res(int): X方向の解像度
            y_res(int): Y方向の解像度
        Returns:
            gdal.Dataset
        """
        dst = gdal.Warp('', dst, xRes=x_res, yRes=y_res, format='MEM')
        return dst

    
    def copy_dataset(dst: gdal.Dataset) -> gdal.Dataset:
        """
        ラスターデータをコピーする
        Args:
            dst(gdal.Dataset): ラスターデータ
        Returns:
            gdal.Dataset
        """
        return gdal.GetDriverByName('MEM').CreateCopy('', dst)


process = Process()
