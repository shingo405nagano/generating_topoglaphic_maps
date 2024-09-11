import os

from osgeo import gdal
from qgis.PyQt.QtWidgets import QMessageBox

class ExeptionMessage(object):
    def __init__(self, dlg):
        self.dlg = dlg
        self._error_font = "QLabel {color: red; font-weight: bold;}"
        self._success_font = "QLabel {color: black;}"

    def msg(self, message: str) -> None:
        QMessageBox.information(
            None,
            'Error Message ...',
            message
        )

    def check_input_file_path(self) -> bool:
        if os.path.exists(self.dlg.get_input_file_path):
            self.dlg.label_Log.setStyleSheet(self._success_font)
            return True
        else:
            self.dlg.label_Log.setStyleSheet(self._error_font)
            self.dlg.label_Log.setText('No such file or directory')
            self.msg('No such file or directory')
            return False
        
    def check_output_file_path(self) -> bool:
        if self.checkBox_Sample.isChecked():
            self.dlg.label_Log.setStyleSheet(self._success_font)
            return True
        elif self.dlg.get_output_file_path == '':
            self.dlg.label_Log.setStyleSheet(self._error_font)
            self.dlg.label_Log.setText('Output file path is not specified')
        # ---------------------- ここから ----------------------

    def _check_file_fmt(self) -> bool:
        if self.dlg.get_output_file_path.endswith('.tif'):
            self.dlg.label_Log.setStyleSheet(self._success_font)
            return True
        else:
            self.dlg.label_Log.setStyleSheet(self._error_font)
            self.dlg.label_Log.setText('File format is not supported.')
            self.msg('File format is not supported.\nPlease select .tif file.')
            return False
    
    def check_raster_band(self) -> bool:
        dst = gdal.Open(self.dlg.get_input_file_path)
        bands = dst.RasterCount
        dst = None
        if 1 == bands:
            self.dlg.label_Log.setStyleSheet(self._success_font)
            return True
        else:
            self.dlg.label_Log.setStyleSheet(self._error_font)
            self.dlg.label_Log.setText('Many bands')
            self.msg(f"""
More bands than expected.
Input: {bands} bands
Expected: 1 band
""")
            return False
        