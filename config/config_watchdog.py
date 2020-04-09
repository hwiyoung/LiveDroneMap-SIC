class BaseConfig:
    LDM_ADDRESS = 'http://127.0.0.1:30022/'
    MAGO3D_ADDRESS = 'http://ys.innopam.com:20080/'
    LDM_PROJECT_NAME = 'SIC-tutorial'
    DIRECTORY_FOR_OUTPUT = "/internalCompany/P2019.SeoulChallenge/00_output"
    # DIRECTORY_TO_WATCH = "/internalCompany/P2019.SeoulChallenge/test_dir_watch"
    DIRECTORY_TO_WATCH = "/internalCompany/P2019.SeoulChallenge/00_drone"
    # DIRECTORY_IMAGE_CHECK = 'drone/examples'
    # DIRECTORY_TO_WATCH = 'drone/downloads'
    IMAGE_FILE_EXT = 'png'
    EO_FILE_EXT = 'txt'
    UPLOAD_INTERVAL = 1
    CAMERA_MANUFACTURER = 'samsung'     # DJI / samsung
    VISUALIZATION_MODE = 'LOCAL'    # MAGO3D / LOCAL
