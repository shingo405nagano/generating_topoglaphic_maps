import json
import os
from pathlib import Path
from typing import List


from matplotlib import pyplot as plt

from qgis.PyQt import uic

from ..gdal_drawer.utils.colors import CustomCmap
from ..gdal_drawer.utils.colors import LinearColorMap
custom_cmap = CustomCmap()

# 1つ上の階層のディレクトリパスを取得
current_dir = os.path.dirname(os.path.abspath(__file__))
DIR_NAME = os.path.abspath(os.path.join(current_dir, os.pardir))

global CONFIG_FILE_PATH
CONFIG_FILE_PATH = os.path.join(DIR_NAME, 'apps\\config.json')
with open(CONFIG_FILE_PATH, 'r', encoding='UTF-8') as f:
    global CONFIG
    CONFIG = json.load(f)

################################################################################
#----------------------------------- Colors -----------------------------------#
class MapColors(object):
    """
    ## Summary
        各Mapの色を設定するクラス。
        'map_name' is Original-Map or Vintage-Map or RGB-Map or CUSTOM-Map.
    """
    def __init__(self, map_name: str):
        self.colors = CONFIG[map_name]

    @property
    def slope_colors(self) -> List[List[float]]:
        """
        ## Summary
            Slopeの設定された色のリストを返す。
        Returns:
            List[List[float]]: 色は0~1の範囲で設定されている。
        """
        return self.colors['SLOPE']
    
    def slope_cmap(self, color_potitions: List[float]=None) -> LinearColorMap:
        """
        ## Summary
            Slopeの色をLinearColorMapに変換する。
        Args:
            color_potitions (List[float], optional): [description]. Defaults to None.各色の位置を指定する場合はここにリストで指定する。
        Returns:
            LinearColorMap: LinearColorMapは、matplotlib.colors.LinearSegmentedColormapのWrapperクラス。
        """
        func = custom_cmap.color_list_to_linear_cmap
        if color_potitions is not None:
            return func(self.slope_colors, color_potitions)
        return func(self.slope_colors)
    
    @property
    def tpi_colors(self) -> List[List[float]]:
        """
        ## Summary
            TPIの設定された色のリストを返す。
        Returns:
            List[float]: 色は0~1の範囲で設定されている。
        """
        return self.colors['TPI']
    
    def tpi_cmap(self, color_potitions: List[float]=None) -> LinearColorMap:
        """
        ## Summary
            TPIの色をLinearColorMapに変換する。
        Args:
            color_potitions (List[float], optional): [description]. Defaults to None.各色の位置を指定する場合はここにリストで指定する。
        Returns:
            LinearColorMap: LinearColorMapは、matplotlib.colors.LinearSegmentedColormapのWrapperクラス。
        """
        func = custom_cmap.color_list_to_linear_cmap
        if color_potitions is not None:
            return func(self.tpi_colors, color_potitions)
        return func(self.tpi_colors)
    
    @property
    def tri_colors(self) -> List[float]:
        """
        ## Summary
            TRIの設定された色のリストを返す。
        Returns:
            List[float]: 色は0~1の範囲で設定されている。
        """
        return self.colors['TRI']
    
    def tri_cmap(self, color_potitions: List[float]=None) -> LinearColorMap:
        """
        ## Summary
            TRIの色をLinearColorMapに変換する。
        Args:
            color_potitions (List[float], optional): [description]. Defaults to None.各色の位置を指定する場合はここにリストで指定する。
        Returns:
            LinearColorMap: LinearColorMapは、matplotlib.colors.LinearSegmentedColormapのWrapperクラス。
        """
        func = custom_cmap.color_list_to_linear_cmap
        if color_potitions is not None:
            return func(self.tri_colors, color_potitions)
        return func(self.tri_colors)

    @property
    def hillshade_colors(self) -> List[List[float]]:
        """
        ## Summary
            Hillshadeの設定された色のリストを返す。
        Returns:
            List[float]: 色は0~1の範囲で設定されている。
        """
        return self.colors['HILLSHADE']
    
    def hillshade_cmap(self, color_potitions: List[float]=None) -> LinearColorMap:
        """
        ## Summary
            Hillshadeの色をLinearColorMapに変換する。
        Args:
            color_potitions (List[float], optional): [description]. Defaults to None.各色の位置を指定する場合はここにリストで指定する。
        Returns:
            LinearColorMap: LinearColorMapは、matplotlib.colors.LinearSegmentedColormapのWrapperクラス。
        """
        func = custom_cmap.color_list_to_linear_cmap
        if color_potitions is not None:
            return func(self.hillshade_colors, color_potitions)
        return func(self.hillshade_colors)


class OriginalMapColors(MapColors):
    """
    ## Summary
        Original-Mapの色を設定するクラス。
    """
    def __init__(self):
        super().__init__('Original-Map')


class VintageMapColors(MapColors):
    """
    ## Summary
        Vintage-Mapの色を設定するクラス。
    """
    def __init__(self):
        super().__init__('Vintage-Map')


class RgbMapColors(MapColors):
    """
    ## Summary
        RGB-Mapの色を設定するクラス。
    """
    def __init__(self):
        super().__init__('RGB-Map')


class CustomMapColors(MapColors):
    """
    ## Summary
        Custom-Mapの色を設定するクラス。
    """
    def __init__(self):
        super().__init__('CUSTOM-Map')
    


################################################################################        
#----------------------------------- Configs ----------------------------------#
class Configs(object):
    def __init__(self):
        self.main_form, _ = self.load(
            os.path.join(DIR_NAME, CONFIG['Form']['Main'])
        )
        self.custom_color_form, _ = self.load(
            os.path.join(DIR_NAME, CONFIG['Form']['CustomColor'])
        )
        self.org_map_img = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['ORIGINAL_MAP_IMG'])
        )
        self.vintage_map_img = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['VINTAGE_MAP_IMG'])
        )
        self.rgb_map_img = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['RGB_MAP_IMG'])
        )
        self.sample_slope_raster = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['SAMPLE_SLOPE_IMG'])
        )
        self.sample_tpi_raster = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['SAMPLE_TPI_IMG'])
        )
        self.sample_tri_raster = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['SAMPLE_TRI_IMG'])
        )
        self.sample_hillshade_raster = plt.imread(
            os.path.join(DIR_NAME, CONFIG['IMG_PATH']['SAMPLE_HILLSHADE_IMG'])
        )

    def load(self, path: Path):
        return uic.loadUiType(path)



configs = Configs()