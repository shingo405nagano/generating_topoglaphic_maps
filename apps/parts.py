# **- coding: utf-8 -**
import math
from typing import Any
from typing import List
from typing import Tuple
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

    def resampling(self, dst: gdal.Dataset, resolution: float, alg: int) -> gdal.Dataset:
        """
        ラスターデータの解像度を変更する
        Args:
            dst(gdal.Dataset): ラスターデータ
            resolution(int): 解像度
        Returns:
            gdal.Dataset
        """
        bounds = self.get_bounds(dst)
        options = gdal.WarpOptions(
            xRes=resolution, yRes=resolution, format='MEM', outputBounds=bounds, resampleAlg=alg
        )
        return gdal.Warp('', dst, options=options)

    def copy_dataset(self, dst: gdal.Dataset) -> gdal.Dataset:
        """
        ラスターデータをコピーする
        Args:
            dst(gdal.Dataset): ラスターデータ
        Returns:
            gdal.Dataset
        """
        return gdal.GetDriverByName('MEM').CreateCopy('', dst)

    def get_bounds(self, dst: gdal.Dataset) -> Tuple[float]:
        """
        ラスターデータの範囲を取得する
        Args:
            dst(gdal.Dataset): ラスターデータ
        Returns:
            Tuple[float]: (x_min, y_min, x_max, y_max)
        """
        transform = dst.GetGeoTransform()
        x_min = transform[0]
        y_max = transform[3]
        rows = dst.RasterYSize
        cols = dst.RasterXSize
        x_resol = transform[1]
        y_resol = transform[-1]
        x_max = x_min + cols * x_resol
        y_min = y_max + rows * y_resol
        return (x_min, y_min, x_max, y_max)
    
    def get_sample_raster(self, org_dst: gdal.Dataset) -> gdal.Dataset:
        """
        ラスターデータのサンプリングを行う
        Args:
            org_dst(gdal.Dataset): ラスターデータ
        Returns:
            gdal.Dataset
        """
        def nodata_checker(ary: np.ndarray, nodata: Any) -> float:
            """NoDataの割合を計算する"""
            if nodata is None:
                data_size = ary[ary != nodata].size
            elif math.isnan(nodata):
                data_size = ary[~np.isnan(ary)].size
            else:
                data_size = ary[ary != nodata].size
            total_size = ary.size
            return data_size / total_size

        def calc_center_xy(org_dst: gdal.Dataset) -> List[int]:
            """中心座標を計算する"""
            X_SIZE, Y_SIZE = org_dst.RasterXSize, org_dst.RasterYSize
            x_center, y_center = int(X_SIZE / 2), int(Y_SIZE / 2)
            return [x_center, y_center]
        
        band = org_dst.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        if nodata is None:
            nodata = np.nan
        ary = org_dst.ReadAsArray()
        maximum_size = 5_000_000
        if org_dst.RasterXSize * org_dst.RasterYSize < maximum_size:
            # サイズが小さい場合はそのまま使用する
            new_ary = ary
        else:
            # サイズが大きい場合は、サンプリングする
            rows = int(ary.shape[0] * 0.25)
            cols = int(rows * 1.3)
            if 2_000 < rows:
                # サンプリングサイズが大きい場合は、サイズを調整する
                rows = 1_800
                cols = 2_500
            
            # Nodataのセルが多い場合は、別な箇所をサンプリングする
            arys = [
                ary[: rows, : cols],
                ary[: rows, -cols:],
                ary[-rows:, : cols],
                ary[-cols:, -cols:]
            ]
            new_ary = None
            for _ary in arys:
                if 0.8 < nodata_checker(_ary, nodata):
                    new_ary = _ary
                    del arys
                    break
                else:
                    continue
            if new_ary is None:
                x_center, y_center = calc_center_xy(org_dst)
                herf_x_size, herf_y_size = [int(size / 2) for size in [rows, cols]]
                new_ary = ary[
                    x_center - herf_x_size: x_center + herf_x_size,
                    y_center - herf_y_size: y_center + herf_y_size
                ]
        
        # データセットを作成
        driver = gdal.GetDriverByName('MEM')
        driver.Register()
        new_dst = driver.Create(
            '',
            xsize=new_ary.shape[1],
            ysize=new_ary.shape[0],
            bands=1, 
            eType=gdal.GDT_Float32
        )
        new_dst.SetGeoTransform(org_dst.GetGeoTransform())
        new_dst.SetProjection(org_dst.GetProjection())
        band = new_dst.GetRasterBand(1)
        band.WriteArray(new_ary)
        band.SetNoDataValue(nodata)
        return new_dst
        


process = Process()