from datetime import datetime
import pyexiv2
from pyexiv2 import metadata
import numpy as np


def convert_fractions_to_float(fraction):
    return fraction.numerator / fraction.denominator


def convert_dms_to_deg(dms):
    d = convert_fractions_to_float(dms[0])
    m = convert_fractions_to_float(dms[1]) / 60
    s = convert_fractions_to_float(dms[2]) / 3600
    deg = d + m + s
    return deg


def extract_eo(fname, camera_manufacturer):
    if camera_manufacturer == 'DJI':
        meta = metadata.ImageMetadata(fname)
        meta.read()

        latitude = convert_dms_to_deg(meta['Exif.GPSInfo.GPSLatitude'].value)
        longitude = convert_dms_to_deg(meta['Exif.GPSInfo.GPSLongitude'].value)
        altitude = float(meta['Xmp.drone-dji.RelativeAltitude'].value)
        roll = float(meta['Xmp.drone-dji.GimbalRollDegree'].value)
        pitch = float(meta['Xmp.drone-dji.GimbalPitchDegree'].value)
        yaw = float(meta['Xmp.drone-dji.GimbalYawDegree'].value)

    elif camera_manufacturer == 'samsung':
        meta = metadata.ImageMetadata(fname)
        meta.read()

        latitude = convert_dms_to_deg(meta['Exif.GPSInfo.GPSLatitude'].value)
        longitude = convert_dms_to_deg(meta['Exif.GPSInfo.GPSLongitude'].value)
        altitude = convert_fractions_to_float(meta['Exif.GPSInfo.GPSAltitude'].value)
        roll = float(meta['Xmp.DLS.Roll'].value) * 180 / np.pi
        pitch = float(meta['Xmp.DLS.Pitch'].value) * 180 / np.pi
        yaw = float(meta['Xmp.DLS.Yaw'].value) * 180 / np.pi

    result = {
        'longitude': longitude,
        'latitude': latitude,
        'altitude': altitude,
        'roll': roll,
        'pitch': pitch,
        'yaw': yaw
    }

    return result


def get_create_time(fname, camera_manufacturer):
    if camera_manufacturer == 'DJI':
        metadata = pyexiv2.ImageMetadata(fname)
        metadata.read()
        create_time_local = metadata['Exif.Image.DateTime'].value
        create_time = (create_time_local - datetime(1970, 1, 1)).total_seconds() - 3600*9  # GMT+9 (S.Korea)
        return create_time
    elif camera_manufacturer == 'AIMIFY/FLIR/Visible':
        metadata = pyexiv2.ImageMetadata(fname)
        metadata.read()
        create_time_local = metadata['Exif.GPSInfo.GPSTimeStamp'].value
        create_time = (create_time_local - datetime(1970, 1, 1)).total_seconds() - 3600*9  # GMT+9 (S.Korea)
        return create_time

        # time_string = fname.split('/')[-1][0:15]
        # year = int(time_string[0:4])
        # month = int(time_string[4:6])
        # day = int(time_string[6:8])
        # hour = int(time_string[9:11])
        # minute = int(time_string[11:13])
        # second = int(time_string[13:15])
        #
        # dt = datetime(year, month, day, hour, minute, second)

        return datetime.timestamp(dt)


if __name__ == '__main__':
    import os
    print(os.getcwd())
    print(get_create_time('server/image_processing/test_FDPRV.JPG'))