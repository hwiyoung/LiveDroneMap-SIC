import os
import numpy as np
import cv2
import time
from osgeo import ogr
from osgeo import gdal
from server.image_processing.orthophoto_generation.ExifData import restoreOrientation, getExif
from server.image_processing.orthophoto_generation.EoData import geographic2plane, Rot3D
from server.image_processing.orthophoto_generation.Boundary import boundary, export_bbox_to_wkt3
from server.image_processing.orthophoto_generation.BackprojectionResample import projectedCoord, backProjection, \
    resample, create_pnga


def rectify(output_path, img_fname, restored_image, focal_length, pixel_size,
             eo, R_GC, ground_height, epsg, gsd='auto'):
    """
    Rectifies a given drone image on a reference plane
    :param output_path: A path which an individual orthophoto will be generated
    :param img_fname: A name of raw image
    :param restored_image: Numpy array of an image which orientation were restored
    :param focal_length: A focal length of a raw image
    :param pixel_size: A pixel size of a raw image
    :param eo: EOP of raw image - [x, y, z, o, p, k]
    :param R_GC: Rotation matrix from Ground to Camera
    :param ground_height: A height of ground which a drone is launched
    :param epsg: An EPSG number of a coordinate system of a generated individual orthophoto
    :param gsd: Ground Sampling Distance of a raw image
    :return: Boundary box of a generated orthophoto in wkt format
    """

    rectify_time = time.time()

    dst = os.path.join(output_path, img_fname.split(".")[0])

    # 2. Extract a projected boundary of the image
    print('boundary')
    start_time = time.time()
    bbox, proj_bbox = boundary(restored_image, eo, R_GC, ground_height, pixel_size, focal_length)   # 4x1, 4x3
    print("--- %s seconds ---" % (time.time() - start_time))

    if gsd == 'auto':
        gsd = (pixel_size * (eo[2] - ground_height)) / focal_length  # unit: m/px

    # Boundary size
    boundary_cols = int((bbox[1, 0] - bbox[0, 0]) / gsd)
    boundary_rows = int((bbox[3, 0] - bbox[2, 0]) / gsd)

    print('projectedCoord')
    start_time = time.time()
    proj_coords = projectedCoord(bbox, boundary_rows, boundary_cols, gsd, eo, ground_height)
    print("--- %s seconds ---" % (time.time() - start_time))

    # Image size
    image_size = np.reshape(restored_image.shape[0:2], (2, 1))

    print('backProjection')
    start_time = time.time()
    backProj_coords = backProjection(proj_coords, R_GC, focal_length, pixel_size, image_size)
    print("--- %s seconds ---" % (time.time() - start_time))

    print('resample')
    start_time = time.time()
    b, g, r, a = resample(backProj_coords, boundary_rows, boundary_cols, restored_image)
    print("--- %s seconds ---" % (time.time() - start_time))

    print('Save the image in png')
    start_time = time.time()
    create_pnga(b, g, r, a, bbox, gsd, epsg, dst)
    print("--- %s seconds ---" % (time.time() - start_time))

    print('*** Processing time per each image')
    print("--- %s seconds ---" % (time.time() - rectify_time))

    bbox_wkt = export_bbox_to_wkt3(proj_bbox)
    return bbox_wkt
