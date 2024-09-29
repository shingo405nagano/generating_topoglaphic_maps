import json
import os
from PIL import Image
from typing import Dict, List

from osgeo import gdal
from qgis.core import QgsGradientColorRamp
from qgis.core import QgsGradientStop
from qgis.gui import QgsColorRampButton
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QBoxLayout
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QSizePolicy


from .apps.colors import Coloring
from .apps.colors import CustomColorMaps

global CONFIG_FILE
CONFIG_FILE = '.\\apps\\config.json'
global SAMPLE_FILES
sample_dir = '.\\views\\sample\\'
SAMPLE_FILES = {
    'SLOPE': os.path.join(sample_dir, 'SLOPE.tif'),
    'TPI': os.path.join(sample_dir, 'TPI.tif'),
    'TRI': os.path.join(sample_dir, 'TRI.tif'),
    'HILLSHADE': os.path.join(sample_dir, 'HILLSHADE.tif')
}


UI , _= (
    uic
    .loadUiType(
        os.path.join(
            os.path.dirname(__file__),
            'views\color_ramp_dlg.ui'
        ),
    )
)

class CustomColorDialog(QtWidgets.QDialog, UI):
    def __init__(self, parent=None):
        super(CustomColorDialog, self).__init__(parent)
        self.COLOR_RAMP = self.read_config_color_ramp()
        self.setupUi(self)
        self.color_ramp_slope = QgsColorRampButton()
        self.color_ramp_tri = QgsColorRampButton()
        self.color_ramp_tpi = QgsColorRampButton()
        self.color_ramp_hillshade = QgsColorRampButton()
        self.make_slope_color_ramp()
        self.make_tpi_color_ramp()
        self.make_tri_color_ramp()
        self.make_hillshade_color_ramp()
        # リセットボタンの表示と非表示
        self.make_reset_btn()
        self.checkBox_Reset.stateChanged.connect(self.make_reset_btn)
        # 登録と初期化
        self.btn_Registration.clicked.connect(self.registration_color_ramp)
        self.btn_Initialize.clicked.connect(self.initialize_color_ramp)
        # サンプル作成
        self.btn_Show.clicked.connect(self.create_sample)
        # ダイアログを閉じる
        self.btn_Cancel.clicked.connect(self.close)
    
    def tr(self, message: str):
        return QCoreApplication.translate('CustomColorDialog', message)
    
    def registration_yes_no(self) -> bool:
        reply = QMessageBox.question(
            None, 
            'Message ...', 
            self.tr('この設定を登録しますか?'), 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            return True
        return False
    
    def initialization_yes_no(self) -> bool:
        reply = QMessageBox.question(
            None, 
            'Message ...', 
            self.tr('この設定を初期化しますか?'), 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            return True
        return False

    def read_config_color_ramp(self) -> Dict[str, List[List[float]]]:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            custom_dict = config['CUSTOM-Map']
        return custom_dict
    
    def _make_color_ramp(self, 
        gpBox: QBoxLayout, 
        color_ramp: QgsColorRampButton, 
        color_name: str
    ) -> None:
        layout = gpBox.layout()
        color_ramp.setColorRamp(self.default_colors(color_name))
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        color_ramp.setSizePolicy(size_policy)
        layout.addWidget(color_ramp)
        gpBox.setLayout(layout)
    
    def make_slope_color_ramp(self) -> None:
        """Slope のカラーランプを作成"""
        self._make_color_ramp(
            self.gpBox_Slope, 
            self.color_ramp_slope, 
            'SLOPE'
        )

    def make_tpi_color_ramp(self) -> None:
        """TPI のカラーランプを作成"""
        self._make_color_ramp(
            self.gpBox_TPI, 
            self.color_ramp_tpi, 
            'TPI'
        )

    def make_tri_color_ramp(self) -> None:
        """TRI のカラーランプを作成"""
        self._make_color_ramp(
            self.gpBox_TRI, 
            self.color_ramp_tri, 
            'TRI'
        )

    def make_hillshade_color_ramp(self) -> None:
        """Hillshade のカラーランプを作成"""
        self._make_color_ramp(
            self.gpBox_Hillshade, 
            self.color_ramp_hillshade, 
            'HILLSHADE'
        )
    
    def default_colors(self, name: str) -> List[List[float]]:
        """
        JSON からカラーランプを取得し、QgsGradientColorRamp オブジェクトを返す
        Args:
            name (str): カラーランプ名
        """
        colors = self.COLOR_RAMP.get(name)
        percents = self._calc_offset_lst(colors)
        color_ramp = QgsGradientColorRamp()
        color_ramp.setColor1(QColor(*self._scaling_255(colors[0])))
        color_ramp.setColor2(QColor(*self._scaling_255(colors[-1])))
        qcolors = []
        for percent, color in zip(percents[1: -1], colors[1: -1]):
            color = QgsGradientStop(
                percent, 
                QColor(*self._scaling_255(color))
            )
            qcolors.append(color)
        color_ramp.setStops(qcolors)
        return color_ramp
    
    def _scaling_255(self, colors: List[float]) -> List[int]:
        """
        0-1 の値を 0-255 にスケーリング
        Args:
            colors (List[float]): 0-1 の値。例）[r, g, b, a]
        """
        return [int(i * 255) for i in colors]
        
    def _calc_offset_lst(self, colors: List[List[float]]) -> List[float]:
        """
        カラーランプのオフセットを計算
        """
        unit = 1 / (len(colors) - 1)
        offset_lst = [round(unit * i, 3) for i in range(len(colors))]
        return offset_lst

    def _get_color_ramp(self, name: str) -> QgsGradientColorRamp:
        colors = {
            "SLOPE": self.color_ramp_slope,
            "TPI": self.color_ramp_tpi,
            "TRI": self.color_ramp_tri,
            "HILLSHADE": self.color_ramp_hillshade
        }
        color_ramp = colors.get(name).colorRamp()
        qcolors = [color_ramp.color1()]
        for stop in color_ramp.stops():
            qcolors.append(stop.color)
        qcolors.append(color_ramp.color2())
        return [self._round(color.getRgbF()) for color in qcolors]
    
    def _round(self, nums: List[float]) -> float:
        return [round(num, 4) for num in nums]
    
    def get_slope_color_ramp(self) -> List[List[float]]:
        """設定した Slope のカラーランプを取得"""
        return self._get_color_ramp("SLOPE")

    def get_tpi_color_ramp(self) -> List[List[float]]:
        """設定した TPI のカラーランプを取得"""
        return self._get_color_ramp("TPI")
    
    def get_tri_color_ramp(self) -> List[List[float]]:
        """設定した TRI のカラーランプを取得"""
        return self._get_color_ramp("TRI")
    
    def get_hillshade_color_ramp(self) -> List[List[float]]:
        """設定した Hillshade のカラーランプを取得"""
        return self._get_color_ramp("HILLSHADE")
    
    def make_reset_btn(self) -> None:
        """リセットボタンを作成"""
        if self.checkBox_Reset.isChecked():
            self.btn_Initialize.setVisible(True)
        else:
            self.btn_Initialize.setVisible(False)

    def registration_temp_color_ramp(self) -> None:
        self.COLOR_RAMP = {
            'SLOPE': self.get_slope_color_ramp(),
            'TPI': self.get_tpi_color_ramp(),
            'TRI': self.get_tri_color_ramp(),
            'HILLSHADE': self.get_hillshade_color_ramp()
        }

    def registration_color_ramp(self) -> None:
        """カラーランプをjsonファイルに登録"""
        if self.registration_yes_no() is False:
            return

        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            custom_dict = config['CUSTOM-Map']
        
        with open(CONFIG_FILE, 'w') as f:
            custom_dict['SLOPE'] = self.get_slope_color_ramp()
            custom_dict['TPI'] = self.get_tpi_color_ramp()
            custom_dict['TRI'] = self.get_tri_color_ramp()
            custom_dict['HILLSHADE'] = self.get_hillshade_color_ramp()
            config['CUSTOM-Map'] = custom_dict
            json_str = self._json_encoder(config)
            f.write(json_str)
        self.COLOR_RAMP = self.read_config_color_ramp()

    def _json_encoder(self, dictionary: dict) -> str:
        """JSONを整形して見やすくする"""
        json_str = json.dumps(dictionary, indent=4)
        json_str = (
            json_str
            .replace('[\n                ', '[')
            .replace(',\n                ', ', ')
            .replace('\n            ]', ']')
        )
        return json_str

    def initialize_color_ramp(self) -> None:
        """カラーランプをリセット"""
        if self.initialization_yes_no() is False:
            return
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            cs_dict = config['CS-Map']
            config['CUSTOM-Map'] = cs_dict
        with open(CONFIG_FILE, 'w') as f:
            json_str = self._json_encoder(config)
            f.write(json_str)
        self.COLOR_RAMP = self.read_config_color_ramp()
        self.make_slope_color_ramp()
        self.make_tpi_color_ramp()
        self.make_tri_color_ramp()
        self.make_hillshade_color_ramp()

    def create_sample(self):
        self.registration_temp_color_ramp()
        coloring = Coloring()
        custom_cmaps = CustomColorMaps()
        custom_cmaps.COLORS_DICT = self.COLOR_RAMP
        cmaps = {
            'SLOPE': custom_cmaps.slope().colors_255,
            'TPI': custom_cmaps.tpi().colors_255,
            'TRI': custom_cmaps.tri().colors_255,
            'HILLSHADE': custom_cmaps.hillshade().colors_255
        }
        names = ['SLOPE', 'TPI', 'TRI', 'HILLSHADE']
        imgs = []
        for name in names:
            _dst = gdal.Open(SAMPLE_FILES.get(name))
            ary = _dst.ReadAsArray()
            img = coloring.styling(ary, cmaps.get(name))
            img = Image.fromarray(img)
            imgs.append(img)
        composited_img = None
        for img in imgs[::-1]:
            if composited_img is None:
                composited_img = img
            else:
                composited_img = Image.alpha_composite(composited_img, img)
        composited_img.show()

