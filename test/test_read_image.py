import cv2
img = cv2.imread("/hdd/ldm_workspace/1482/20190830_090724_079.tif")
cv2.imshow("cc",img)
cv2.waitKey(0)
# file = '20190830_090624_084_8b_33.200096_126.274895_301.012_91.31 _-84.85_-23.82.JPG'
#
# file_name = file.split('\\')[-1].split('.')[0][:-3]
#
# fname_split = file.split('\\')[-1].split('_')
# latitude = float(fname_split[4])
# longitude = float(fname_split[5])
# altitude = float(fname_split[6])
# roll = float(fname_split[7])
# pitch = float(fname_split[8])
# yaw = float(fname_split[9][:-4])
#
# extension_name = file.split('.')[-1]
# print('A new file detected: %s' % file_name)
# print('extenstion: ', extension_name)
