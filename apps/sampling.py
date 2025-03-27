import numpy as np
import shapely

from ..gdal_drawer.custom import CustomGdalDataset


class SamplingRaster(object):
    """
    ## Summary
        RasterDataから指定したサイズのサンプルを取得するクラス。
    Args:
        dst (CustomGdalDataset): The raster dataset.
        max_rows (int): The maximum number of rows.
        max_cols (int): The maximum number of columns.
    Examples:
        >>> from apps.sampling import SamplingRaster
        >>> from apps.gdal_drawer.custom import gdal_open
        >>> dst = gdal_open('path/to/raster.tif')
        >>> sampling_raster = SamplingRaster(dst, 100, 100)
        >>> sample_dst = sampling_raster.sample_dst
    """

    def __init__(self, dst: CustomGdalDataset, max_rows, max_cols):
        self.sample_dst = None
        if dst.RasterXSize <= max_cols and dst.RasterYSize <= max_rows:
            self.sample_dst = dst
        else:
            funcs = [
                self._get_center_raster,
                self._get_lower_left_corner_raster,
                self._get_lower_right_corner_raster,
                self._get_upper_left_corner_raster,
                self._get_upper_right_corner_raster,
            ]
            valid_values = []
            for func in funcs:
                _sample_dst = func(dst, max_rows, max_cols)
                _sample_raster = _sample_dst.array()
                size = _sample_raster.size
                valid_values.append((size - np.isnan(_sample_raster).sum()) / size)
            max_index = np.argmax(valid_values)
            self.sample_dst = funcs[max_index](dst, max_rows, max_cols)

    def _get_upper_left_corner_raster(
        self, dst: CustomGdalDataset, max_rows: int, max_cols: int
    ) -> CustomGdalDataset:
        """
        ## Summary
            左上のRasterを取得する。
        Args:
            dst (CustomGdalDataset): The raster dataset.
            max_rows (int): The maximum number of rows.
            max_cols (int): The maximum number of columns.
        Returns:
            CustomGdalDataset: The sampled raster dataset.
        """
        bounds = dst.bounds()
        x_min, y_min, x_max, y_max = bounds
        x_max = x_min + max_cols * dst.x_resolution
        y_min = y_max + max_rows * dst.y_resolution
        bounds = shapely.box(x_min, y_min, x_max, y_max)
        new_dst = dst.clip_by_bounds(bounds)
        return new_dst

    def _get_upper_right_corner_raster(
        self, dst: CustomGdalDataset, max_rows: int, max_cols: int
    ) -> CustomGdalDataset:
        """
        ## Summary
            右上のRasterを取得する。
        Args:
            dst (CustomGdalDataset): The raster dataset.
            max_rows (int): The maximum number of rows.
            max_cols (int): The maximum number of columns.
        Returns:
            CustomGdalDataset: The sampled raster dataset.
        """
        bounds = dst.bounds()
        x_min, y_min, x_max, y_max = bounds
        x_min = x_max - max_cols * dst.x_resolution
        y_min = y_max + max_rows * dst.y_resolution
        bounds = shapely.box(x_min, y_min, x_max, y_max)
        new_dst = dst.clip_by_bounds(bounds)
        return new_dst

    def _get_lower_left_corner_raster(
        self, dst: CustomGdalDataset, max_rows: int, max_cols: int
    ) -> CustomGdalDataset:
        """
        ## Summary
            左下のRasterを取得する。
        Args:
            dst (CustomGdalDataset): The raster dataset.
            max_rows (int): The maximum number of rows.
            max_cols (int): The maximum number of columns.
        Returns:
            CustomGdalDataset: The sampled raster dataset.
        """
        bounds = dst.bounds()
        x_min, y_min, x_max, y_max = bounds
        x_max = x_min + max_cols * dst.x_resolution
        y_max = y_min - max_rows * dst.y_resolution
        bounds = shapely.box(x_min, y_min, x_max, y_max)
        new_dst = dst.clip_by_bounds(bounds)
        return new_dst

    def _get_lower_right_corner_raster(
        self, dst: CustomGdalDataset, max_rows: int, max_cols: int
    ) -> CustomGdalDataset:
        """
        ## Summary
            右下のRasterを取得する。
        Args:
            dst (CustomGdalDataset): The raster dataset.
            max_rows (int): The maximum number of rows.
            max_cols (int): The maximum number of columns.
        Returns:
            CustomGdalDataset: The sampled raster dataset.
        """
        bounds = dst.bounds()
        x_min, y_min, x_max, y_max = bounds
        x_min = x_max - max_cols * dst.x_resolution
        y_max = y_min - max_rows * dst.y_resolution
        bounds = shapely.box(x_min, y_min, x_max, y_max)
        new_dst = dst.clip_by_bounds(bounds)
        return new_dst

    def _get_center_raster(
        self, dst: CustomGdalDataset, max_rows: int, max_cols: int
    ) -> CustomGdalDataset:
        """
        ## Summary
            中央のRasterを取得する。
        Args:
            dst (CustomGdalDataset): The raster dataset.
            max_rows (int): The maximum number of rows.
            max_cols (int): The maximum number of columns.
        Returns:
            CustomGdalDataset: The sampled raster dataset.
        """
        bounds = dst.bounds()
        x_min, y_min, x_max, y_max = bounds
        x_min = x_min + (x_max - x_min) / 2 - max_cols * dst.x_resolution / 2
        y_min = y_min + (y_max - y_min) / 2 - max_rows * dst.y_resolution / 2
        x_max = x_min + max_cols * dst.x_resolution
        y_max = y_min + max_rows * dst.y_resolution
        bounds = shapely.box(x_min, y_min, x_max, y_max)
        new_dst = dst.clip_by_bounds(bounds)
        return new_dst
