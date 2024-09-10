from dataclasses import dataclass
from typing import Callable

import numpy as np


def _adjust_distance(func) -> int:
    """
    カーネルのサイズを調整するデコレータ
    """
    def wrapper(*args, **kwargs):
        if 'distance' in kwargs:
            if kwargs['distance'] % 2 == 0:
                kwargs['distance'] += 1
        else:
            args = list(args)
            if args[0] % 2 == 0:
                args[0] += 1
        return func(*args, **kwargs)
    return wrapper


def distance_to_kernel_size(one_side_distance: float, cell_size: float) -> int:
    """
    カーネルのサイズを計算する。
    Args:
        one_side_distance(int): 中心からの距離
        cell_size(float): セルのサイズ
    Returns:
        cells(int): カーネルのサイズ
    """
    divd, remainder = divmod(one_side_distance, abs(cell_size))
    if 0 < remainder:
        divd += 1
    return int(divd * 2)

def cells_to_kernel_size(one_side_distance: int) -> int:
    """
    カーネルのサイズを計算する。
    Args:
        one_side_distance(int): 中心からの距離
    Returns:
        cells(int): カーネルのサイズ
    """
    return int(one_side_distance * 2)


@_adjust_distance
def simple_kernel(distance: int) -> np.ndarray:
    """
    畳み込みに使用するシンプルなカーネルを生成する。
    Args:
        distance(int): カーネルのサイズ
    Returns:
        np.ndarray
    Examples:
        >>> simple_kernel(3)
        array([[0.11111111, 0.11111111, 0.11111111],
               [0.11111111, 0.11111111, 0.11111111],
               [0.11111111, 0.11111111, 0.11111111]])
    """
    shape = (distance, distance)
    cells = distance * distance
    return np.ones(shape) / cells


@_adjust_distance
def doughnut_kernel(distance: int) -> np.ndarray:
    """
    畳み込みに使用するドーナツ型のカーネルを生成する。
    Args:
        distance(int): カーネルのサイズ
    Returns:
        np.ndarray
    Examples:
        >>> doughnut_kernel(5)
        array([[0.0625, 0.0625, 0.0625, 0.0625, 0.0625],
               [0.0625, 0.    , 0.    , 0.    , 0.0625],
               [0.0625, 0.    , 0.    , 0.    , 0.0625],
               [0.0625, 0.    , 0.    , 0.    , 0.0625],
               [0.0625, 0.0625, 0.0625, 0.0625, 0.0625]])
    """
    shape = (distance, distance)
    outer_cells = (distance - 1) * 4
    input_val = 1 / outer_cells
    kernel = np.zeros(shape)
    kernel[:1] = input_val
    kernel[-1:] = input_val
    kernel[:, :1] = input_val
    kernel[:, -1:] = input_val
    return kernel


@_adjust_distance
def _gaussian_kernel(distance, sigma, func):
    shape = (distance, distance)
    kernel = np.zeros(shape)
    center = distance // 2
    for y in range(distance):
        for x in range(distance):
            val = func(x, y, center, sigma)
            kernel[y, x] = val
    kernel /= kernel.sum()
    return kernel


def gaussian_kernel(distance: int, sigma: float) -> np.ndarray:
    """
    畳み込みに使用するガウシアンカーネルを生成する。
    Args:
        distance(int): カーネルのサイズ
        sigma(float): ガウシアンの標準偏差
    Returns:
        np.ndarray
    Examples:
        >>> gaussian_kernel(3, 1)
        array([[0.07511361, 0.1238414 , 0.07511361],
               [0.1238414 , 0.20417996, 0.1238414 ],
               [0.07511361, 0.1238414 , 0.07511361]])
    """
    def _gaussian(x, y, center, sigma):
        return np.exp(-((x - center) ** 2 + (y - center) ** 2) / (2 * sigma ** 2))

    return _gaussian_kernel(distance, sigma, _gaussian)


def inverse_gaussian_kernel(distance: int, sigma: float) -> np.ndarray:
    """
    畳み込みに使用する逆ガウシアンカーネルを生成する。
    Args:
        distance(int): カーネルのサイズ
        sigma(float): ガウシアンの標準偏差
    Returns:
        np.ndarray
    Examples:
        >>> inverse_gaussian_kernel(3, 1)
        array([[0.20417996, 0.1238414 , 0.20417996],
               [0.1238414 , 0.07511361, 0.1238414 ],
               [0.20417996, 0.1238414 , 0.20417996]])
    """
    def _inverse_gaussian(x, y, center, sigma):
        return np.exp(((x - center) ** 2 + (y - center) ** 2) / (2 * sigma ** 2))
    
    return _gaussian_kernel(distance, sigma, _inverse_gaussian)


@_adjust_distance
def four_directions_kernel(distance: int) -> np.ndarray:
    """
    畳み込みに使用する4方向カーネルを生成する。
    Args:
        distance(int): カーネルのサイズ
    Returns:
        np.ndarray
    Examples:
        >>> four_directions_kernel(3)
        array([[0.   0.   0.25 0.   0.  ]
               [0.   0.   0.   0.   0.  ]
               [0.25 0.   0.   0.   0.25]
               [0.   0.   0.   0.   0.  ]
               [0.   0.   0.25 0.   0.  ]])
    """
    shape = (distance, distance)
    center = int((distance - 1) / 2)
    input_val = 1 / 4
    kernel = np.zeros(shape)
    kernel[: 1, center: center + 1] = input_val # 中心上
    kernel[center: center + 1, : 1] = input_val # 中心左
    kernel[center: center + 1, -1:] = input_val # 中心右
    kernel[-1:, center: center + 1] = input_val # 中心下
    return kernel


@_adjust_distance
def eight_directions_kernel(distance: int) -> np.ndarray:
    """
    畳み込みに使用する8方向カーネルを生成する。
    Args:
        distance(int): カーネルのサイズ
    Returns:
        np.ndarray
    Examples:
        >>> eight_directions_kernel(5)
        array([[0.125 0.    0.125 0.    0.125]
               [0.    0.    0.    0.    0.   ]
               [0.125 0.    0.    0.    0.125]
               [0.    0.    0.    0.    0.   ]
               [0.125 0.    0.125 0.    0.125]])
    """
    shape = (distance, distance)
    center = int((distance - 1) / 2)
    input_val = 1 / 8
    kernel = np.zeros(shape)
    kernel[: 1,: 1][0] = input_val # 左上
    kernel[: 1, center: center + 1] = input_val # 中心上
    kernel[: 1, -1: ] = input_val # 右上
    kernel[center: center + 1, : 1] = input_val # 中心左
    kernel[center: center + 1, -1:] = input_val # 中心右
    kernel[-1:,:1] = input_val # 左下
    kernel[-1:, center: center + 1] = input_val # 中心下
    kernel[-1:,-1:] = input_val # 右下
    return kernel



@dataclass
class KernelTypes:
    original: str = 'Original'
    doughnut: str = 'Doughnut'
    mean: str = 'Mean'
    gaussian: str = 'Gaussian'
    inverse_gaussian: str = 'InverseGaussian'
    four_direction: str = '4-Direction'
    eight_direction: str = '8-Direction'

    

class Kernels(object):
    distance_to_kernel_size: Callable[[float, float], int] = distance_to_kernel_size
    cells_to_kernel_size: Callable[[int], int] = cells_to_kernel_size
    simple: Callable[[int], np.ndarray] = simple_kernel
    doughnut: Callable[[int], np.ndarray] = doughnut_kernel
    gaussian: Callable[[int, float], np.ndarray] = gaussian_kernel
    inverse_gaussian: Callable[[int, float], np.ndarray] = inverse_gaussian_kernel
    four_directions: Callable[[int], np.ndarray] = four_directions_kernel
    eight_directions: Callable[[int], np.ndarray] = eight_directions_kernel



if __name__ == '__main__':
    # kernel_type = 'カーネルサイズを距離で指定'
    kernel_type = 'カーネルサイズをセル数で指定'
    one_side_distance = 5
    sigma = 2
    if kernel_type == 'カーネルサイズを距離で指定':
        print(Kernels.distance_to_kernel_size(one_side_distance, 0.5))
    elif kernel_type == 'カーネルサイズをセル数で指定':
        print(Kernels.cells_to_kernel_size(one_side_distance))
    