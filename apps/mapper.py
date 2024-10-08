# **- coding: utf-8 -**
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
from PIL import ImageEnhance
from PIL import ImageFilter
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

import numpy as np
from osgeo import gdal
import scipy.ndimage

from .colors import Coloring
from .kernels import Kernels
from .kernels import KernelTypes
from .parts import process
colorling = Coloring()



@dataclass
class SlopeOptions:
    checked: bool
    resampling: bool
    resolution: float
    filtering: bool
    gaussian_sigma: float
    cmap: List[List[int]]

    def to_slope_ary(self, org_dst: gdal.Dataset) -> np.ndarray:
        """
        Slope は地形の傾斜（°）を示す指標
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        # リサンプリングを行う（分解能が低い場合はリサンプリングを行うほうがよい）
        x_resol = org_dst.GetGeoTransform()[1]
        y_resol = org_dst.GetGeoTransform()[-1]
        if self.resampling:
            dst = self._resampling_alg(org_dst, self.resolution, self.resolution)
        else:
            dst = process.copy_dataset(org_dst)
        # Slopeを計算する
        _slope_dst = self._slope_alg(dst)
        # 他の画像と合成するために分解能を元に戻す
        if self.resampling:
            slope_dst = self._resampling_alg(
                dst=_slope_dst, 
                x_resol=x_resol, 
                y_resol=y_resol, 
                width=org_dst.RasterXSize, 
                height=org_dst.RasterYSize
            )
        else:
            slope_dst = _slope_dst
        ary = process.nodata_to_nan(slope_dst)
        dst = _slope_dst = slope_dst = None
        ary = self._gaussian_alg(ary, self.filtering, self.gaussian_sigma)
        return ary
    
    def to_slope_img(self, org_dst: gdal.Dataset, **kwargs) -> Image.Image:
        """
        Slopeの配列から画像を生成する
        Args:
            org_dst(gdal.Dataset): Raster data
            progress(QProgressBar): 進捗バー
        Returns:
            Image.Image
        """
        progress = kwargs.get('progress')
        ary = self.to_slope_ary(org_dst)
        if progress:
            progress.emit(13)
        img = colorling.styling(ary, self.cmap)
        if progress:
            progress.emit(19)
        return Image.fromarray(img)

    def _resampling_alg(self, 
        dst: gdal.Dataset, 
        x_resol: float, 
        y_resol: float,
        width: int=None,
        height: int=None
    ) -> gdal.Dataset:
        """
        リサンプリングを行う
        Args:
            dst(gdal.Dataset): Raster data
            x_resol(float): X方向の地上分解能
            y_resol(float): Y方向の地上分解能
            width(int): 幅
            height(int): 高さ
        Returns:
            gdal.Dataset
        """
        if (width is not None) & (height is not None):
            options = self._option_template(dst, x_resol, y_resol, width, height)
        else:
            options = self._option_template(dst, x_resol, y_resol)
        options = gdal.WarpOptions(**options)
        return gdal.Warp('', dst, options=options)

    def _slope_alg(self, dst: gdal.Dataset) -> gdal.Dataset:
        # Slopeを計算する
        return gdal.DEMProcessing(
            destName='',
            srcDS=dst,
            processing='slope',
            format='MEM'
        )
    
    def _gaussian_alg(self, ary: np.ndarray, filtering: bool, sigma: float) -> np.ndarray:
        """
        配列にガウシアンフィルタを適用する
        Args:
            ary(np.ndarray): 配列
            filtering(bool): フィルタリングを行うかどうか
            sigma(float): ガウシアンフィルタの標準偏差
        Returns:
            np.ndarray
        """
        if filtering:
            return scipy.ndimage.gaussian_filter(ary, sigma=sigma)
        else:
            return ary

    def _get_bounds(self, dst: gdal.Dataset) -> Tuple[float]:
        """
        ラスタデータの範囲を取得する
        Args:
            dst(gdal.Dataset): Raster data
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
    
    def _option_template(self, 
        dst: gdal.Dataset,
        x_resol: float, 
        y_resol: float, 
        width: int=None,
        height: int=None
    ) -> dict:
        """
        リサンプリングのオプションテンプレートを取得する
        Args:
            dst(gdal.Dataset): Raster data
            x_resol(float): X方向の地上分解能
            y_resol(float): Y方向の地上分解能
            width(int): 幅
            height(int): 高さ
        Returns:
            dict
        """
        template = dict(
            format='MEM', 
            xRes=x_resol, 
            yRes=y_resol, 
            resampleAlg=gdal.GRA_Bilinear, 
            outputBounds=process.get_bounds(dst)
        )
        if (width is not None) & (height is not None):
            template.update(dict(width=width, height=height))
            [template.pop(key) for key in ['xRes', 'yRes']]
            return template
        return template
             
    def _classification_slope(self, 
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



@dataclass
class TpiOptions:
    checked: bool
    kernel_size_type: str
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

    def to_tpi_ary(self, org_dst: gdal.Dataset) -> np.ndarray:
        """
        Topographic Position Index (TPI) は地形の起伏を示す指標。山頂、谷底、斜面などの地形を示す。プラスなら尾根や峰であり、マイナスなら谷底や河床である。0付近は平坦地を示す。
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        if (self.checked) & (self.kernel_type != KernelTypes.original):
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
    
    def to_tpi_img(self, org_dst: gdal.Dataset, **kwargs) -> Image.Image:
        """
        TPIの配列から画像を生成する
        Args:
            org_dst(gdal.Dataset): Raster data
            progress(QProgressBar): 進捗バー
        Returns:
            Image.Image: TPIのRGBA画像
        """
        progress = kwargs.get('progress')
        ary = self.to_tpi_ary(org_dst)
        if progress:
            progress.emit(57)
        img = colorling.styling(ary, self.cmap)
        if progress:
            progress.emit(63)
        return Image.fromarray(img)

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
            KernelTypes.doughnut: Kernels.doughnut,
            KernelTypes.mean: Kernels.simple,
            KernelTypes.gaussian: Kernels.gaussian,
            KernelTypes.inverse_gaussian: Kernels.inverse_gaussian,
            KernelTypes.four_direction: Kernels.four_directions,
            KernelTypes.eight_direction: Kernels.eight_directions,
        }
        func = funcs.get(self.kernel_type)
        distance_type = [
            'カーネルサイズを距離で指定', 
            'Kernel size specified by distance'
        ]
        if self.kernel_size_type in distance_type:
            kernel_size = Kernels.distance_to_kernel_size(
                one_side_distance=self.one_side_distance,
                cell_size=x_resol
            )
        else:
            kernel_size = Kernels.cells_to_kernel_size(self.one_side_distance)
        
        if KernelTypes.gaussian in self.kernel_type:
            return func(kernel_size, self.sigma)
        return func(kernel_size)



@dataclass
class TriOptions:
    checked: bool
    outlier_treatment: bool
    threshold: float
    cmap: List[List[int]]
    filtering: bool
    gaussian_sigma: float

    def to_tri_ary(self, org_dst: gdal.Dataset) -> np.ndarray:
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
        ary = self._gaussian_alg(ary, self.filtering, self.gaussian_sigma)
        tri_dst = None
        return ary

    def to_tri_img(self, org_dst: gdal.Dataset, **kwargs) -> Image.Image:
        """
        TRIの配列から画像を生成する
        Args:
            org_dst(gdal.Dataset): Raster data
            progress(QProgressBar): 進捗バー
        Returns:
            Image.Image: TRIのRGBA画像
        """
        progress = kwargs.get('progress')
        ary = self.to_tri_ary(org_dst)
        if progress:
            progress.emit(72)
        img = colorling.styling(ary, self.cmap)
        if progress:
            progress.emit(78)
        return Image.fromarray(img)
    
    def _gaussian_alg(self, ary: np.ndarray, filtering: bool, sigma: float) -> np.ndarray:
        """
        配列にガウシアンフィルタを適用する
        Args:
            ary(np.ndarray): 配列
            filtering(bool): フィルタリングを行うかどうか
            sigma(float): ガウシアンフィルタの標準偏差
        Returns:
            np.ndarray
        """
        if filtering:
            return scipy.ndimage.gaussian_filter(ary, sigma=sigma)
        else:
            return ary



@dataclass
class HillshadeOptions:
    checked: bool
    hillshade_type: int
    azimuth: float
    altitude: float
    z_factor: float
    combined: bool
    cmap: List[List[int]]
    filtering: bool
    gaussian_sigma: float

    def to_hillshade_ary(self, org_dst: gdal.Dataset) -> np.ndarray:
        """
        Hillshade は地形の陰影を示す指標
        Args:
            org_dst(gdal.Dataset): Raster data
        Returns:
            np.ndarray
        """
        params = self.parameters_template
        if self.combined:
            params['combined'] = True
        hillshade_dst = (
            gdal.DEMProcessing(
                destName='',
                srcDS=org_dst,
                processing='hillshade',
                format='MEM',
                azimuth=self.azimuth,
                altitude=self.altitude,
                zFactor=self.z_factor
            )
        )
        ary = process.nodata_to_nan(hillshade_dst)
        ary = self._gaussian_alg(ary, self.filtering, self.gaussian_sigma)
        hillshade_dst = None
        return ary
    
    def _gaussian_alg(self, ary: np.ndarray, filtering: bool, sigma: float) -> np.ndarray:
        """
        配列にガウシアンフィルタを適用する
        Args:
            ary(np.ndarray): 配列
            filtering(bool): フィルタリングを行うかどうか
            sigma(float): ガウシアンフィルタの標準偏差
        Returns:
            np.ndarray
        """
        if filtering:
            return scipy.ndimage.gaussian_filter(ary, sigma=sigma)
        else:
            return ary

    def to_hillshade_img(self, org_dst: gdal.Dataset, **kwargs) -> Image.Image:
        """
        Hillshadeの配列から画像を生成する
        Args:
            org_dst(gdal.Dataset): Raster data
            progress(QProgressBar): 進捗バー
        Returns:
            Image.Image: HillshadeのRGBA画像
        """
        progress = kwargs.get('progress')
        ary = self.to_hillshade_ary(org_dst)
        if progress:
            progress.emit(86)
        img = colorling.styling(ary, self.cmap)
        if progress:
            progress.emit(92)
        return Image.fromarray(img)

    @property
    def parameters_template(self) -> Dict[str, Any]:
        """
        Hillshadeのパラメータテンプレート
        Returns:
            Dict[str, Any]
        """
        return dict(
            process='hillshade',
            format='MEM',
            azimuth=self.azimuth,
            altitude=self.altitude, 
            zFactor=self.z_factor
        )



def composite_images(
    dlg,
    slope_img: Image.Image,
    tpi_img: Image.Image,
    tri_img: Image.Image,
    hillshade_img: Image.Image
) -> Image.Image:
    """
    画像を合成する
    Args:
        dlg: ダイアログ
        slope_img(Image.Image): 傾斜画像
        tpi_img(Image.Image): TPI画像
        tri_img(Image.Image): TRI画像
        hillshade_img(Image.Image): Hillshade画像
    Returns:
        Image.Image: 微地形図のRGBA画像
    """
    # Edgeを強調した画像を生成
    edge_options = dlg.get_edge_options()
    if edge_options.checked:
        edge_img = edge_options.to_edge_img(hillshade_img)
        imgs = [edge_img, tpi_img, slope_img]
    else:
        imgs = [tpi_img, slope_img]
    # 画像を合成
    result = Image.alpha_composite(hillshade_img, tri_img)
    for img in imgs:
        result = Image.alpha_composite(result, img)
    # Contrastを適用
    contrast_options = dlg.get_contrast_options()
    result = contrast_options.to_contrast_img(result)
    # Unsharpn Maskを適用
    unsharpn_options = dlg.get_unsharpn_options()
    result = unsharpn_options.to_unsharpn_img(result)
    return result
    

def save_image_rgba(out_file_path: Path, img: Image.Image, org_dst: gdal.Dataset) -> None:
    """
    RGBA画像を保存する
    Args:
        out_file_path(Path): 保存先のファイルパス
        img(Image.Image): 画像
        org_dst(gdal.Dataset): Raster data
    """
    img_ary = np.array(img)
    driver = gdal.GetDriverByName('GTiff')
    driver.Register()
    new_dst = driver.Create(
        out_file_path,
        xsize=org_dst.RasterXSize,
        ysize=org_dst.RasterYSize,
        bands=img_ary.shape[-1],
        eType=gdal.GDT_Byte
    )
    new_dst.SetGeoTransform(org_dst.GetGeoTransform())
    new_dst.SetProjection(org_dst.GetProjection())
    set_colors = [
        gdal.GCI_RedBand,
        gdal.GCI_GreenBand,
        gdal.GCI_BlueBand,
        gdal.GCI_AlphaBand
    ]
    for i, color in enumerate(set_colors):
        band = new_dst.GetRasterBand(i + 1)
        band.WriteArray(img_ary[:, :, i])
        band.SetColorInterpretation(color)
    new_dst.FlushCache()
    new_dst = None



@dataclass
class ContrastOptions:
    checked: bool
    contrast: float

    def to_contrast_img(self, img: Image.Image) -> Image.Image:
        """
        Contrastを適用する
        Args:
            img(Image.Image): 画像
        Returns:
            Image.Image
        """
        if self.checked:
            enhancer = ImageEnhance.Contrast(img)
            return enhancer.enhance(self.contrast)
        return img



@dataclass
class UnsharpnOptions:
    checked: bool
    radius: int
    percent: float
    threshold: int

    def to_unsharpn_img(self, img: Image.Image) -> Image.Image:
        """
        Unsharpn Maskを適用する
        Args:
            img(Image.Image): 画像
        Returns:
            Image.Image
        """
        if self.checked:
            filter_ = ImageFilter.UnsharpMask(
                radius=self.radius, 
                percent=self.percent, 
                threshold=self.threshold
            )
            return img.filter(filter_)
        return img
        


@dataclass
class GaussianOptions:
    checked: bool
    sigma: float

    def to_gaussian_img(self, img: Image.Image) -> Image.Image:
        """
        Gaussian Filterを適用する
        Args:
            img(Image.Image): 画像
        Returns:
            Image.Image
        """
        if self.checked:
            return img.filter(ImageFilter.GaussianBlur(radius=self.sigma))
        return img



@dataclass
class EdgeOptions:
    checked: bool
    unsharpn: UnsharpnOptions
    gaussian: GaussianOptions
    min_area_iqr: float
    color: Tuple[int]

    def to_edge_img(self, img: Image.Image) -> Image.Image:
        """
        Edge Detectionを適用する
        Args:
            img(Image.Image): 画像
        Returns:
            Image.Image
        """
        if self.checked:
            # 画像の前処理
            img = self.unsharpn.to_unsharpn_img(img)
            img = img.convert('L')
            img = self.gaussian.to_gaussian_img(img)
            # エッジ検出
            edge_img = img.filter(ImageFilter.FIND_EDGES)
            # 2値化
            binary_edge_ary = self.binarization(edge_img)
            # ゴミを除去
            cleaned_edge_ary = self.garbage_disposal(binary_edge_ary)
            # 画像に変換
            cleaned_edge_img = self.gray_to_rgba(cleaned_edge_ary)
            return Image.fromarray(cleaned_edge_img)
        return img

    def binarization(self, img: Image.Image) -> np.array:
        """
        2値化を行う
        Args:
            img(Image.Image): 画像
        Returns:
            Image.Image
        """
        edge_ary = np.array(img)
        threshold = 1.5
        q1 = np.quantile(edge_ary, 0.25)
        q3 = np.quantile(edge_ary, 0.75)
        iqr = q3 - q1
        up_thres = int(q3 + threshold * iqr)
        binary_edge = img.point(lambda p: p > up_thres and 255)
        return np.array(binary_edge)
    
    def garbage_disposal(self, binary_edge: np.array) -> np.array:
        """
        小さなエッジを削除する
        Args:
            binary_edge(np.array): 2値化されたエッジ画像
        Returns:
            np.array: ゴミを除去したエッジ画像
        """
        # ラベル付け
        labeled_array, _ = scipy.ndimage.label(binary_edge)
        # 各オブジェクトの面積を計算
        object_areas = np.bincount(labeled_array.ravel())
        # 0番目は背景なので除外
        counts = object_areas[1:]
        # 小さなオブジェクトを削除
        q1 = np.quantile(counts, 0.25)
        q3 = np.quantile(counts, 0.75)
        iqr = q3 - q1
        min_area = q3 + self.min_area_iqr *iqr
        small_objects = np.where(object_areas < min_area)[0]
        mask = np.isin(labeled_array, small_objects)
        binary_edge[mask] = 0
        return binary_edge
    
    def gray_to_rgba(self, ary: np.array) -> np.array:
        # 2値化されたエッジは白になっているので、そのままRGBAに変換する
        def colorize(ary: np.array, color: int) -> np.array:
            return np.where(ary == 255, color, 0).astype('uint8')
        
        red_band = colorize(ary, self.red)
        green_band = colorize(ary, self.green)
        blue_band = colorize(ary, self.blue)
        return np.dstack([red_band, green_band, blue_band, ary])
    
    @property
    def red(self):
        return self.color[0]
    
    @property
    def green(self):
        return self.color[1]
    
    @property
    def blue(self):
        return self.color[2]