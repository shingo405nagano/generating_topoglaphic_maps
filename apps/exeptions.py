from dataclasses import dataclass
import os

from osgeo import gdal
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox



class Message(object):
    def __init__(self):
        self.file_not_found = self.tr('入力ファイルが存在しません')
        self.file_is_not_specified = self.tr('出力ファイルが指定されていません')
        self.mismuch_band = self.tr('RasterDataのBand数が期待値と異なります')

    def tr(self, message):
        return QCoreApplication.translate('ExeptionMesssage', message)



class ExeptionMessage(Message):
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg

    def msg(self, message: str) -> None:
        QMessageBox.information(None, 'Error Message ...', message)

    @property
    def check_input_file_path(self) -> bool:
        # 入力ファイルが存在しない場合にエラーメッセージを表示
        if not os.path.exists(self.dlg.get_input_file_path):
            self.msg(self.file_not_found)
            return False
        return True
    
    @property
    def check_output_file_path(self) -> bool:
        # 出力ファイルが指定されていない場合にエラーメッセージを表示
        if self.dlg.checkBox_Sample.isChecked():
            # サンプルのみの場合は出力ファイルを指定しない
            return True
        elif self.dlg.get_output_file_path == '':
            self.msg(self.file_is_not_specified)
            return False
        else:
            return True
    
    @property
    def check_raster_band(self) -> bool:
        # バンド数が1でない場合にエラーメッセージを表示
        dst = gdal.Open(self.dlg.get_input_file_path)
        bands = dst.RasterCount
        dst = None
        if 1 == bands:
            return True
        else:
            self.msg(self.mismuch_band)
            return False
        
    