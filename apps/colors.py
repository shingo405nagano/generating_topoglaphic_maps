import json
from typing import Dict, List, NamedTuple, Tuple

from matplotlib.colors import LinearSegmentedColormap
import numpy as np


conf_path = r"./apps/config.json"
with open(conf_path, mode='r') as file:
    config = json.load(file)
    global VINRAGE_COLORS
    VINRAGE_COLORS = config['VintageMap']
    global B2R_COLORS
    B2R_COLORS = config['BlueToRedMap']



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
        cmap = LinearSegmentedColormap.from_list(name=name, colors=colors, N=256)
        return cmap
    
    def _get_cmap(self, name: str) -> Cmap:
        cmap = self._list_to_cmap(self.COLORS_DICT[name], name)
        colors = [cmap(i) for i in range(0, 256)]
        colors_255 = [tuple(int(255 * c) for c in color) for color in colors]
        return Cmap(cmap=cmap, colors=colors, colors_255=colors_255)


    @property
    def order_by_top_to(self) -> None:
        return list(self.COLORS_DICT.keys())



class VintageColorMaps(ColorMaps):
    def __init__(self):
        super().__init__(VINRAGE_COLORS)


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
        Topographic Position Index（地形位置指数）のカラーマップを取得
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



class Blue2RedColorMaps(ColorMaps):
    def __init__(self):
        super().__init__(B2R_COLORS)

    
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
        return scaled.astype('uint8')
    
    def get_color(self,
        idx_ary: np.ndarray, 
        colors: List[List[int]], 
        nodata: int=-9999
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
        idx_ary = np.where(idx_ary == nodata, 256, idx_ary)
        color_ary = colors[idx_ary]
        return (
            np
            .array(color_ary)
            .astype('uint8')
            .reshape(rows, cols, bands)
        )
    
    def styling(self, ary: np.ndarray, cmap: List[List[int]]) -> np.ndarray:
        scaled_ary = self.scaling(ary)
        del ary
        if 0 < scaled_ary[np.isnan(scaled_ary)].size:
            scaled_ary[np.isnan(scaled_ary)] = -9999
        img = self.get_color(scaled_ary, cmap, -9999)
        return img


if __name__ == '__main__':
    vintage_cmaps = VintageColorMaps()
    print(vintage_cmaps.order_by_top_to)