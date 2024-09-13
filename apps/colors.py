# **- coding: utf-8 -**
import json
from typing import Dict, List, NamedTuple, Tuple

from matplotlib.colors import LinearSegmentedColormap
import numpy as np


conf_path = r"./apps/config.json"
with open(conf_path, mode='r') as file:
    config = json.load(file)
    global CS_COLORS
    CS_COLORS = config['CS-Map']
    global VINRAGE_COLORS
    VINRAGE_COLORS = config['Vintage-Map']
    global RGB_COLORS
    RGB_COLORS = config['RGB-Map']



class Cmap(NamedTuple):
    cmap: LinearSegmentedColormap
    colors: List[Tuple[float]]
    colors_255: List[Tuple[int]]



class ColorMaps(object):
    def __init__(self, COLORS_DICT: Dict[str, List[List[float]]]):
        self.COLORS_DICT = COLORS_DICT

    def _list_to_cmap(self, 
        colors: List[Tuple[float]], 
        name: str
    ) -> LinearSegmentedColormap:
        """
        リストからカラーマップを作成
        Args:
            colors(List[Tuple[float]]): 0-1のRGBA値のリスト
            name(str): カラーマップ名
        """
        cmap = LinearSegmentedColormap.from_list(name=name, colors=colors, N=256)
        return cmap
    
    def _get_cmap(self, name: str) -> Cmap:
        """
        カラーマップを取得
        Args:
            name(str): app/config.jsonに記録しているカラーマップ名
        """
        cmap = self._list_to_cmap(self.COLORS_DICT[name], name)
        colors = [cmap(i) for i in range(0, 256)]
        colors_255 = [tuple(int(255 * c) for c in color) for color in colors]
        return Cmap(cmap=cmap, colors=colors, colors_255=colors_255)
        
    def slope(self, name='SLOPE') -> Cmap:
        """
        傾斜角度のカラーマップ①を取得
        Args:
            name(str): app/config.jsonに記録しているカラーマップ名
        Returns:
            Cmap:
                cmap(LinearSegmentedColormap): カラーマップ
                colors(List[Tuple[float]]): 0-1のRGBA値のリスト
                colors_255(List[Tuple[int]]): 0-255のRGBA値のリスト 
        """
        return self._get_cmap(name)


    def tpi(self, name='TPI') -> Cmap:
        """
        Topographic Position Index（地形位置指数）①のカラーマップを取得
        Args:
            name(str): app/config.jsonに記録しているカラーマップ名
        Returns:
            Cmap:
                cmap(LinearSegmentedColormap): カラーマップ
                colors(List[Tuple[float]]): 0-1のRGBA値のリスト
                colors_255(List[Tuple[int]]): 0-255のRGBA値のリスト 
        """
        return self._get_cmap(name)


    def tri(self, name='TRI') -> Cmap:
        """
        Terrain Ruggedness Index（地形凹凸指数）のカラーマップを取得
        Args:
            name(str): app/config.jsonに記録しているカラーマップ名
        Returns:
            Cmap:
                cmap(LinearSegmentedColormap): カラーマップ
                colors(List[Tuple[float]]): 0-1のRGBA値のリスト
                colors_255(List[Tuple[int]]): 0-255のRGBA値のリスト 
        """
        return self._get_cmap(name)
    

    def hillshade(self, name='HILLSHADE') -> Cmap:
        """
        地形陰影のカラーマップを取得
        Args:
            name(str): app/config.jsonに記録しているカラーマップ名
        Returns:
            Cmap:
                cmap(LinearSegmentedColormap): カラーマップ
                colors(List[Tuple[float]]): 0-1のRGBA値のリスト
                colors_255(List[Tuple[int]]): 0-255のRGBA値のリスト 
        """
        return self._get_cmap(name)




class CsColorMaps(ColorMaps):
    def __init__(self):
        super().__init__(CS_COLORS)



class VintageColorMaps(ColorMaps):
    def __init__(self):
        super().__init__(VINRAGE_COLORS)



class RgbColorMaps(ColorMaps):
    def __init__(self):
        super().__init__(RGB_COLORS)



class Coloring(object):
    def scaling(self, 
        ary: np.ndarray, 
        minimum: int=0, 
        maximum: int=255
    ) -> np.ndarray:
        """
        配列のスケーリング
        Args:
            ary(np.ndarray): 配列
            minimum(int): 最小値
            maximum(int): 最大値
        Returns:
            np.ndarray
        """
        ary_min = np.nanmin(ary)
        ary_max = np.nanmax(ary)
        scaled = (ary - ary_min) / (ary_max - ary_min) * (maximum - minimum) + minimum
        scaled[np.isnan(scaled)] = 256
        return scaled.astype('uint16')
    
    def get_color(self,
        idx_ary: np.ndarray, 
        colors: List[List[int]],
    ) -> np.ndarray:
        """
        配列に カラーマップを適用し、RGBAの配列を取得
        Args:
            idx_ary(np.ndarray): 配列
            colors(List[List[int]]): カラーマップ
            nodata(int): nodataの値
        Returns:
            np.ndarray
        """
        rows, cols = idx_ary.shape
        bands = 4
        colors += [(0, 0, 0, 0)]
        colors = np.array(colors)
        color_ary = colors[idx_ary]
        return (
            np
            .array(color_ary)
            .astype('uint16')
            .reshape(rows, cols, bands)
        )
    
    def styling(self, ary: np.ndarray, cmap: List[List[int]]) -> np.ndarray:
        """
        配列にカラーマップを適用し、RGBA画像を作成
        Args:
            ary(np.ndarray): 配列
            cmap(List[List[int]]): カラーマップ
        Returns:
            np.ndarray
        """
        scaled_ary = self.scaling(ary)
        img = self.get_color(scaled_ary, cmap)
        return img.astype('uint8')