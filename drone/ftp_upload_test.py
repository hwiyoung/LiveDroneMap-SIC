import os
import time
import pysftp
from tqdm import tqdm
from config.config_watchdog import BaseConfig as Config

myHostname = "61.38.45.112"
myUsername = "innopam-ldm"
myPassword = "innopam#1"
myPort = 5001

# local_path = '/mnt/AIMIFY/sample/20190830/Flir_name'
# local_path = '/mnt/AIMIFY/live_image/abx101/20191025/sony'
local_path = "/mnt/mingha88/LDM"
# local_path = "/mnt/mingha88/PMJeju/1_kau_1010/191010/1_/annotated"

remote_path = '/home/innopam-ldm/PycharmProjects/livedronemap/drone/downloads'
# remote_path = '/mnt/AIMIFY/live_image/abx101/20191025/sony_test'

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

with pysftp.Connection(host=myHostname, username=myUsername, password=myPassword, port=myPort, cnopts=cnopts) as sftp:
    # Switch to a remote directory
    sftp.cwd(remote_path)

    # Upload data
    fname_list = os.listdir(local_path)
    fname_list.sort()

    for fname in tqdm(fname_list):
        sftp.put(local_path + '/' + fname, remote_path + '/' + fname)
        time.sleep(5)