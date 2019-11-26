class BaseConfig:
    LDM_ADDRESS = 'http://127.0.0.1:30010/'
    MAGO3D_ADDRESS = 'http://ys.innopam.com:20080/'
    LDM_PROJECT_NAME = 'Sandbox_Jeju'
    DIRECTORY_IMAGE_CHECK = "/mnt/mingha88/PMJeju/0_kau_0830/Jeju_KAU_Ocean" #'drone/examples'
    # DIRECTORY_IMAGE_CHECK = 'drone/examples'
    # DIRECTORY_TO_WATCH = "/mnt/mingha88/LDM"
    DIRECTORY_TO_WATCH = 'drone/downloads'
    # DIRECTORY_TO_WATCH = "/mnt/AIMIFY/live_image/abx101/20191126/sony"
    # DIRECTORY_TO_WATCH = "/Jeju"
    IMAGE_FILE_EXT = 'JPG'
    EO_FILE_EXT = 'txt'
    UPLOAD_INTERVAL = 1
    # CAMERA_MANUFACTURER = 'AIMIFY/FLIR/Visible'
    CAMERA_MANUFACTURER = 'AIMIFY/SONY'
