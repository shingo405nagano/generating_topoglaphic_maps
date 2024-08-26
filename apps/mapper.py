import json
from pathlib import Path
from typing import Callable
from typing import List
from typing import NamedTuple

import numpy as np
from osgeo import gdal
import scipy.ndimage

from .colors import Coloring
from .kernels import Kernels
from .parts import process
colorling = Coloring()



class SlopeOptions(NamedTuple):
    checked: bool
    resampling: bool
    resolution: float
    cmap: List[List[int]]

    def to_slope(self, org_dst: gdal.Dataset) -> np.ndarray:
        """
        Slope は地形の傾斜（°）を示す指標
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        nodata = org_dst.GetRasterBand(1).GetNoDataValue()
        if self.resampling:
            dst = process.resampling(org_dst, self.resolution, self.resolution)
        else:
            dst = org_dst
        slope_dst = (
            gdal
            .DEMProcessing(
                destName='',
                srcDS=dst,
                processing='slope',
                computeEdges=True,
                format='MEM',
            )
        )
        if self.resampling:
            # リサンプリングして傾斜を計算した場合はもとに戻す。
            slope_dst = (
                process
                .resampling(
                    slope_dst, 
                    org_dst.GetGeoTransform()[1], 
                    org_dst.GetGeoTransform()[5]
                )
            )
        ary = process.nodata_to_nan(slope_dst)
        slope_dst = None
        return ary
    
    def classification_slope(self, 
        ary: np.ndarray, 
        thresholds: List[int]=list(range(0, 60, 5)) + [100]
    ) -> np.ndarray:
        """
        Slopeを分類する
        Args:
            ary(np.ndarray): Slopeの配列
            thresholds(List[int]): 分類する閾値
        Returns:
            np.ndarray
        """
        clsd_ary = np.zeros(ary.shape, dtype=np.uint8)
        for i, threshold in enumerate(thresholds[1: ]):
            lwt = thresholds[i]
            upt = threshold
            mask = np.where((lwt <= ary) & (ary < upt), True, False)
            clsd_ary[mask] = i
        return clsd_ary



class TpiOptions(NamedTuple):
    checked: bool
    one_side_distance: float
    kernel_type: str 
    sigma: float
    outlier_treatment: bool
    threshold: float
    cmap: List[List[int]]
    """
    Args:
        Kernel_type(str): カーネルの種類 ['Normal', 'Doughnut', 'Mean', 'Gaussian', 'InverseGaussian', '4-Direction', '8-Direction']
    """

    def to_tpi(self, org_dst: gdal.Dataset,) -> np.ndarray:
        """
        Topographic Position Index (TPI) は地形の起伏を示す指標。山頂、谷底、斜面などの地形を示す。プラスなら尾根や峰であり、マイナスなら谷底や河床である。0付近は平坦地を示す。
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        if self.checked:
            band = org_dst.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            ary = band.ReadAsArray()
            ary = process.nodata_to_nan(ary, nodata)
            kernel = self._select_kernel(org_dst)
            comparison_ary = scipy.ndimage.convolve(ary, kernel, mode='constant')
            ary = ary - comparison_ary
        else:
            # gdalを使用してTPIを計算する
            tpi_dst = (
                gdal
                .DEMProcessing(
                    destName='',
                    srcDS=org_dst,
                    processing='TPI',
                    format='MEM',
                    computeEdges=True,
                )
            )
            ary = process.nodata_to_nan(tpi_dst)
            tpi_dst = None

        if self.outlier_treatment:
            ary = process.outlier_treatment(ary, self.threshold)
       
        return ary
    
    def _select_kernel(self, org_dst: gdal.Dataset) -> np.ndarray:
        """
        畳み込みに使用するカーネルを選択し、生成する。
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        x_resol = org_dst.GetGeoTransform()[1]
        funcs = {
            'Normal': Kernels.simple,
            'Doughnut': Kernels.doughnut,
            'Mean': Kernels.simple,
            'Gaussian': Kernels.gaussian,
            'InverseGaussian': Kernels.inverse_gaussian,
            '4-Direction': Kernels.four_directions,
            '8-Direction': Kernels.eight_directions,
        }
        func = funcs.get(self.kernel_type)
        kernel_size = Kernels.distance_to_kernel_size(
            one_side_distance=self.one_side_distance,
            cell_size=x_resol
        )
        if 'Gaussian' in self.kernel_type:
            return func(kernel_size, self.sigma)
        return func(kernel_size)



class TriOptions(NamedTuple):
    checked: bool
    outlier_treatment: bool
    threshold: float
    cmap: List[List[int]]

    def to_tri(self, org_dst: gdal.Dataset) -> np.ndarray:
        """
        Terrain Ruggedness Index (TRI) は地形の凹凸の複雑さを示す指標
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        tri_dst = (
            gdal
            .DEMProcessing(
                destName='',
                srcDS=org_dst,
                processing='TRI',
                format='MEM',
                computeEdges=True,
            )
        )
        ary = process.nodata_to_nan(tri_dst)
        if self.outlier_treatment:
            ary = process.outlier_treatment(ary, self.threshold)
        tri_dst = None
        return ary
    


class HillshadeOptions(NamedTuple):
    checked: bool
    hillshade_type: int
    azimuth: float
    altitude: float
    z_factor: float
    combined: bool
    cmap: List[List[int]]

    def to_hillshade(self, 
        org_dst: gdal.Dataset, 
        azimuth: float=None
    ) -> np.ndarray:
        """
        Hillshade は地形の陰影を示す指標
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        hillshade_dst = (
            gdal
            .DEMProcessing(
                destName='',
                srcDS=org_dst,
                processing='hillshade',
                format='MEM',
                computeEdges=True,
                azimuth=azimuth,
                altitude=self.altitude,
                zFactor=self.z_factor
            )
        )
        ary = process.nodata_to_nan(hillshade_dst)
        hillshade_dst = None
        return ary
    
    def combined_hillshade(self, 
        org_dst: gdal.Dataset, 
    ) -> np.ndarray:
        """
        複数のHillshadeを結合する
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        azimuth_lst = []
        for add in [0, 90, 180, 270]:
            add_azimuth = self.azimuth + add
            if 360 <= add_azimuth:
                add_azimuth -= 360
            azimuth_lst.append(add_azimuth)
        hillshades = []
        for azimuth in azimuth_lst:
            hillshade = self.to_hillshade(org_dst, azimuth=azimuth)
            hillshades.append(hillshade)
        return self._ary_composite(hillshades)
    
    def _ary_composite(self, arys: List[np.ndarray]) -> np.ndarray:
        """
        Hillshadeを結合する
        Args:
            arys(List[np.ndarray]): Hillshadeの配列
        Returns:
            np.ndarray
        """
        result = np.zeros(arys[0].shape, dtype=np.float32)
        for ary in arys:
            result += ary
        return (ary / len(arys)).astype(np.uint8)



class Mapping(object):
    def __init__(self, 
        in_file: Path,
        choiced_map: int,
        out_file: Path,
        slope_options: SlopeOptions, 
        tpi_options: TpiOptions, 
        tri_options: TriOptions, 
        hillshade_options: HillshadeOptions
    ) -> None:
        self.slope_options = slope_options
        self.tpi_options = tpi_options
        self.tri_options = tri_options
        self.hillshade_options = hillshade_options
        self.dst = gdal.Open(in_file)
    
    def slope_map(self):
        slope_ary = (
            self.slope_options
            .classification_slope(
                self.slope_options.to_slope(self.dst)
            )
        )
        scaled_slope = colorling.scaling(slope_ary)
        slope_img = colorling.get_color(scaled_slope, self.slope_options.cmap)
        return slope_img
    
    def tpi_map(self):
        cell_size = self.dst.GetGeoTransform()[1]
        kernel_size = (
            Kernels
            .distance_to_kernel_size(
                one_side_distance=self.tpi_options.one_side_distance,
                cell_size=cell_size
            )
        )
    


        

        
        
        
