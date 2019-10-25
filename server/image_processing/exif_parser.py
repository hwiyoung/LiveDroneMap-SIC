from datetime import datetime

import pyexiv2


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
        metadata = pyexiv2.ImageMetadata(fname)
        metadata.read()

        latitude = metadata['Exif.GPSInfo.GPSLatitude'].value
        longitude = metadata['Exif.GPSInfo.GPSLongitude'].value
        altitude = metadata['Xmp.drone-dji.AbsoluteAltitude'].value
        roll = float(metadata['Xmp.drone-dji.FlightRollDegree'].value)
        pitch = float(metadata['Xmp.drone-dji.FlightPitchDegree'].value)
        yaw = float(metadata['Xmp.drone-dji.FlightYawDegree'].value)

        latitude = convert_dms_to_deg(latitude)
        longitude = convert_dms_to_deg(longitude)
        altitude = float(altitude)

    elif camera_manufacturer == 'AIMIFY/FLIR/Visible':
        fname_split = fname.split('/')[-1].split('_')
        latitude = float(fname_split[4])
        longitude = float(fname_split[5])
        altitude = float(fname_split[6])
        roll = float(fname_split[7])
        pitch = float(fname_split[8])
        yaw = float(fname_split[9][:-4])

    elif camera_manufacturer == 'AIMIFY/SONY':
        fname_split = fname.split('/')[-1].split('_')
        latitude = float(fname_split[2])
        longitude = float(fname_split[3])
        altitude = float(fname_split[4])
        roll = float(fname_split[5])
        pitch = float(fname_split[6])
        yaw = float(fname_split[7][:-4])

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