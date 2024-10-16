import os

DIR_NAME = os.path.dirname(__file__)

CONFIG_FILE = os.path.join(DIR_NAME, 'apps\\config.json')

SAMPLE_FILES = {
    'SLOPE': os.path.join(DIR_NAME, 'views\\sample\\SLOPE.tif'),
    'TPI': os.path.join(DIR_NAME, 'views\\sample\\TPI.tif'),
    'TRI': os.path.join(DIR_NAME, 'views\\sample\\TRI.tif'),
    'HILLSHADE': os.path.join(DIR_NAME, 'views\\sample\\HILLSHADE.tif'),
}

CUSTOM_UI_FILE = os.path.join(DIR_NAME, 'views\\color_ramp_dlg.ui')

MAIN_DLG_UI_FILE = os.path.join(DIR_NAME, 'views\\generate_topography_dialog_base.ui')

HELP_KERNEL_DLG_UI_FILE = os.path.join(DIR_NAME, 'views\\help_kernels.ui')

CS_MAP_IMG_FILE = os.path.join(DIR_NAME, 'views\\CS-Map__Img.jpg')
VINTAGE_IMG_FILE = os.path.join(DIR_NAME, 'views\\Vintage-Map__Img.jpg')
RGB_MAP_IMG_FILE = os.path.join(DIR_NAME, 'views\\RGB-Map__Img.jpg')