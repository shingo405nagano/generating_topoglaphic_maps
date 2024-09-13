# **- coding: utf-8 -**
from dataclasses import dataclass
import os

from osgeo import gdal
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox


class ExeptionMessage(object):
    def __init__(self, dlg):
        super().__init__()
        self.dlg = dlg
        self.file_not_found = self.tr('入力ファイルが存在しません')
        self.file_is_not_specified = self.tr('出力ファイルが指定されていません')
        self.mismuch_band = self.tr('RasterDataのBand数が期待値と異なります')
        self.yes_no_msg = self.tr('このまま処理をする場合は少し時間が掛かります。 処理を続行しますか?')

    def tr(self, message):
        """翻訳関数"""
        return QCoreApplication.translate('ExeptionMessage', message)

    def msg(self, message: str) -> None:
        """エラーメッセージを表示"""
        QMessageBox.information(None, 'Error Message ...', message)

    @property
    def check_input_file_path(self) -> bool:
        # 入力ファイルが存在しない場合にエラーメッセージを表示
        file_path = self.dlg.get_input_file_path
        if file_path is None:
            self.msg(self.file_not_found)
            return False
        elif not os.path.exists(file_path):
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
    
    def yes_no(self, dst: gdal.Dataset) -> bool:
        # ファイルサイズが大きい場合に確認メッセージを表示
        size = dst.RasterXSize * dst.RasterYSize
        threshold = 25_000_000
        if threshold < size:
            reply = QMessageBox.question(
                None,
                'Message',
                self.yes_no_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                return True
            else:
                return False
        else:
            return True
        