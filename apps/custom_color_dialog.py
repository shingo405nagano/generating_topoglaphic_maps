import json
from PIL import Image
from typing import Dict
from typing import List

from matplotlib.colors import to_hex
from qgis.core import QgsGradientColorRamp
from qgis.core import QgsGradientStop
from qgis.gui import QgsColorRampButton
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QBoxLayout
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QSizePolicy

from .config import Configs
from .config import CONFIG_FILE_PATH
from .config import CustomMapColors
from ..gdal_drawer.utils.colors import CustomCmap
custom_cmap = CustomCmap()
custom_map_colors = CustomMapColors()
configs = Configs()



class CustomColorDialog(QtWidgets.QDialog, configs.custom_color_form):
    def __init__(self, parent=None):
        super(CustomColorDialog, self).__init__(parent)
        self._init_name = 'Original-Map'
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
        # カラーランプの設定
        self.your_color = self._generate_color_sentence()
        # リセットボタンの表示と非表示
        self.make_reset_btn()
        self.checkBox_Reset.stateChanged.connect(self.make_reset_btn)
        # 登録と初期化
        self.btn_Registration.clicked.connect(self.registration_color_ramp)
        self.btn_Initialize.clicked.connect(self.initialize_color_ramp)
        # サンプル作成
        self.btn_Show.clicked.connect(self.create_sample)
        # ダイアログを閉じる
        self.btn_Close.clicked.connect(self.close_dlg)
    
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
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            custom_dict = config['CUSTOM-Map']
        return custom_dict

    def _generate_color_sentence(self) -> str:
        sentence = ''
        for _, rgba_lst in self.color_ramps().items():
            for rgba in rgba_lst:
                sentence += to_hex(rgba[:3])
                sentence += hex(int(rgba[-1]))
        return sentence

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

    def _get_color_ramp(self, 
        name: str, 
        get_positions: bool=False
    ) -> QgsGradientColorRamp:
        colors = {
            "SLOPE": self.color_ramp_slope,
            "TPI": self.color_ramp_tpi,
            "TRI": self.color_ramp_tri,
            "HILLSHADE": self.color_ramp_hillshade
        }
        color_ramp = colors.get(name).colorRamp()
        qcolors = [color_ramp.color1()]
        positions = [0.0]
        for stop in color_ramp.stops():
            qcolors.append(stop.color)
            positions.append(stop.offset)
        qcolors.append(color_ramp.color2())
        positions.append(1.0)
        if get_positions:
            # Colorの位置を指定する場合に使用
            return [self._round(color.getRgbF()) for color in qcolors]  
        colors = []
        for color in qcolors:
            rgba = [color.red(), color.green(), color.blue(), color.alpha()]
            colors.append([c / 255 for c in rgba])
        return colors
    
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
    
    def color_ramps(self) -> Dict[str, List[List[float]]]:
        """設定したカラーランプを取得"""
        return {
            "SLOPE": self.get_slope_color_ramp(),
            "TPI": self.get_tpi_color_ramp(),
            "TRI": self.get_tri_color_ramp(),
            "HILLSHADE": self.get_hillshade_color_ramp()
        }

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

    def registration_color_ramp(self, ok: bool=False) -> None:
        """カラーランプをjsonファイルに登録"""
        if not ok:
            if self.registration_yes_no() is False:
                return

        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            custom_dict = config['CUSTOM-Map']
        
        with open(CONFIG_FILE_PATH, 'w') as f:
            custom_dict['SLOPE'] = self.get_slope_color_ramp()
            custom_dict['TPI'] = self.get_tpi_color_ramp()
            custom_dict['TRI'] = self.get_tri_color_ramp()
            custom_dict['HILLSHADE'] = self.get_hillshade_color_ramp()
            config['CUSTOM-Map'] = custom_dict
            json_str = self._json_encoder(config)
            f.write(json_str)
            self.your_color = self._generate_color_sentence()
        
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
        
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            cs_dict = config[self._init_name]
            config['CUSTOM-Map'] = cs_dict
        with open(CONFIG_FILE_PATH, 'w') as f:
            json_str = self._json_encoder(config)
            f.write(json_str)
        
        self.your_color = self._generate_color_sentence()
        self.COLOR_RAMP = self.read_config_color_ramp()
        self.make_slope_color_ramp()
        self.make_tpi_color_ramp()
        self.make_tri_color_ramp()
        self.make_hillshade_color_ramp()

    def create_sample(self):
        self.registration_temp_color_ramp()
        rasters = [
            configs.sample_slope_raster,
            configs.sample_tpi_raster,
            configs.sample_tri_raster,
            configs.sample_hillshade_raster
        ]
        imgs = []
        for raster, colors in zip(rasters, self.COLOR_RAMP.values()):
            cmap = custom_cmap.color_list_to_linear_cmap(colors)
            img = cmap.values_to_img(raster, 'inta').astype('uint8')
            img = Image.fromarray(img)
            imgs.append(img)
        composited_img = None
        for img in imgs[::-1]:
            if composited_img is None:
                composited_img = img
            else:
                composited_img = Image.alpha_composite(composited_img, img)
        composited_img.show()

    def close_dlg(self):
        sentence = self._generate_color_sentence()
        if sentence != self.your_color:
            if self.registration_yes_no():
                self.registration_color_ramp(True)
            else:
                self.close()
        self.close()
