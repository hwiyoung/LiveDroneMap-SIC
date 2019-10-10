import os
import pyexiv2

for root, dirs, files in os.walk('/mnt/AIMIFY/live_image/20191010/sony'):
    for file in files:
        filename = os.path.splitext(file)[0]
        extension = os.path.splitext(file)[1]
        file_path = root + '/' + file

        metadata = pyexiv2.ImageMetadata(file_path)
        metadata.read()

    print('hello')
