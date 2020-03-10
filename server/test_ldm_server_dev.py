import json
import os
import time
import cv2
import socket
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request
from werkzeug.utils import secure_filename

from config import config_flask
from server.image_processing.img_metadata_generation import create_img_metadata_udp, create_obj_metadata
from clients.webodm import WebODM
from clients.mago3d import Mago3D

from server.image_processing.orthophoto_generation.Orthophoto import rectify, rectify2
from server.image_processing.orthophoto_generation.ExifData import get_metadata
from server.image_processing.orthophoto_generation.EoData import rpy_to_opk, geographic2plane
from server.image_processing.orthophoto_generation.Boundary import transform_bbox

# Convert pixel bbox to world bbox
from server.image_processing.orthophoto_generation.Boundary import pcs2ccs, projection
from server.image_processing.orthophoto_generation.EoData import Rot3D, latlon2tmcentral, tmcentral2latlon
from server.image_processing.orthophoto_generation.ExifData import getExif, restoreOrientation

from struct import *

# socket for sending
TCP_IP = '192.168.0.24'
TCP_PORT = 5010

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.connect((TCP_IP, TCP_PORT))
print('connected!')

# def highlighting_bbox(image,bbox):
#     idx = 0
#     blue = (255, 0, 0)
#     green = (0, 255, 0)
#     red = (0, 0, 255)
#     black = (0, 0, 0)
#     purple = (128,0,128)
#     notorange = (255,127,80)
#     object_color = {1: blue, 2: green, 3: black, 4: red, 5: purple, 6: notorange}
#     for object_id in bbox[4]:
#         if object_id == 6:
#             test = 0
#         image = cv2.rectangle(image, (bbox[0][idx] - 5, bbox[1][idx] - 5), (bbox[2][idx] + 5, bbox[3][idx] + 5), object_color[object_id], 5)
#         idx += 1
#     return image

# #########################
# # Client for map viewer #
# #########################
# s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# dest = ("localhost", 57820)
# print("binding...")

# Initialize flask
app = Flask(__name__)
app.config.from_object(config_flask.BaseConfig)

# Initialize multi-thread
executor = ThreadPoolExecutor(2)

# Initialize Mago3D client
mago3d = Mago3D(
    url=app.config['MAGO3D_CONFIG']['url'],
    user_id=app.config['MAGO3D_CONFIG']['user_id'],
    api_key=app.config['MAGO3D_CONFIG']['api_key']
)

height_threshold = 100

from server.my_drones import DJIMavic
my_drone = DJIMavic(pre_calibrated=False)

def allowed_file(fname):
    return '.' in fname and fname.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/project/', methods=['GET', 'POST'])
def project():
    """
    GET : Query project list
    POST : Add a new project
    :return: project_list (GET), project_id (POST)
    """
    if request.method == 'GET':
        project_list = os.listdir(app.config['UPLOAD_FOLDER'])
        return json.dumps(project_list)
    if request.method == 'POST':
        if request.json['visualization_module'] == 'MAGO3D':
            # Create a new project on Mago3D
            res = mago3d.create_project(request.json['name'], request.json['project_type'],
                                        request.json['shooting_area'])
            # Mago3D assigns a new project ID to LDM
            project_id = str(res.json()['droneProjectId'])
        elif request.json['visualization_module'] == 'LOCAL':
            project_id = 'LOCAL_%s' % round(time.time())

        # Using the assigned ID, ldm makes a new folder to projects directory
        new_project_dir = os.path.join(app.config['UPLOAD_FOLDER'], project_id)
        os.mkdir(new_project_dir)
        os.mkdir(os.path.join(new_project_dir, 'rectified'))

        # LDM returns the project ID that Mago3D assigned
        return project_id


# 라이브 드론맵: 이미지 업로드, 기하보정 및 가시화
@app.route('/ldm_upload/<project_id_str>', methods=['POST'])
def ldm_upload(project_id_str):
    """
    POST : Input images to the image processing and object detection chain of LDM
    The image processing and object detection chain of LDM covers following procedures.
        1) Pre-processing: Metadata extraction, System calibration
        2) Object detection
        3) Individual orthophoto generation
    :param project_id_str: project_id which Mago3D/LOCAL assigned for each projects
    :return:
    """

    ############# Log for checking processing time #############
    f = open("log_processing_time.txt", "a")
    # Name | System Calibration | Inference | Rectify | Metadata | Mago3D
    start_time = time.time()

    if request.method == 'POST':
        # Initialize variables
        project_path = os.path.join(app.config['UPLOAD_FOLDER'], project_id_str)
        fname_dict = {
            'img': None,
            'img_rectified': None,
            'eo': None
        }

        # Check integrity of uploaded files
        for key in ['img', 'eo']:
            if key not in request.files:  # Key check
                return 'No %s part' % key
            file = request.files[key]
            if file.filename == '':  # Value check
                return 'No selected file'
            if file and allowed_file(file.filename):  # If the keys and corresponding values are OK
                fname_dict[key] = secure_filename(file.filename)
                file.save(os.path.join(project_path, fname_dict[key]))  # 클라이언트로부터 전송받은 파일을 저장한다.
            else:
                return 'Failed to save the uploaded files'

        ################################
        # IPOD chain 1: Pre-processing #
        ################################
        print("IPOD chain 1: Pre-processing")
        print(" * Read EOP")
        parsed_eo = my_drone.preprocess_eo_file(os.path.join(project_path, fname_dict['eo']))   # degrees
        if parsed_eo[2] - my_drone.ipod_params["ground_height"] <= height_threshold:
            print(" * The height is too low: ", parsed_eo[2] - my_drone.ipod_params["ground_height"], " m")
            return "The height of the image is too low"
        print(" * The height of the image: ", parsed_eo[2] - my_drone.ipod_params["ground_height"], " m")

        if not my_drone.pre_calibrated:
            print(' * System calibration...')
            opk = rpy_to_opk(parsed_eo[3:])
            parsed_eo[3:] = opk * np.pi / 180  # degree to radian
            if abs(opk[0]) > 0.175 or abs(opk[1]) > 0.175:
                print('Too much omega/phi will kill you')
                return 'Too much omega/phi will kill you'

        epsg = 3857
        converted_eo = geographic2plane(parsed_eo, epsg)
        R_CG = Rot3D(converted_eo).T

        print(" * Metadata extraction...")
        focal_length, orientation, _ = get_metadata(os.path.join(project_path, fname_dict["img"]),
                                                    "Linux")  # unit: m, _, ndarray
        img_type = 0

        preprocess_time = time.time()

        ##################################
        # IPOD chain 2: Object detection #
        ##################################
        print("IPOD chain 2: Object detection")
        imgencode = cv2.imread(os.path.join(project_path, fname_dict["img"]))

        # Restore the image based on orientation information
        imgencode_1 = restoreOrientation(imgencode, orientation)

        ####################################
        # Send the image to inference server
        print("start sending...")
        imgshape = json.dumps(imgencode.shape[:2]).encode('utf-8').ljust(16)
        stringData = imgencode_1.tostring()
        s.send(imgshape)
        s.send(stringData)

        # Receiving Bbox info
        data_len = s.recv(16)

        bbox_coords_bytes = s.recv(int(data_len))
        bbox_coords = json.loads(bbox_coords_bytes)
        print("received!")
        ####################################

        img_rows = imgencode_1.shape[0]
        img_cols = imgencode_1.shape[1]
        pixel_size = my_drone.ipod_params['sensor_width'] / img_cols

        obj_metadata = []
        for bbox in bbox_coords:
            bbox_world = transform_bbox(bbox, img_rows, img_cols, pixel_size,
                                        my_drone.ipod_params['focal_length'],
                                        converted_eo, R_CG, my_drone.ipod_params['ground_height'])

            obj_metadata.append(create_obj_metadata(bbox[4], bbox_world))

        # x1 = [603, 800, 289]
        # x2 = [708, 988, 392]
        # y1 = [776, 588, 1491]
        # y2 = [860, 947, 1572]
        # class_id = [3, 3, 3]

        inference_time = time.time()

        ##################################################
        # IPOD chain 3: Individual orthophoto generation #
        ##################################################
        fname_dict['img_rectified'] = fname_dict['img'].split('.')[0] + '.tif'
        bbox_wkt = rectify(
            project_path=project_path,
            img_fname=fname_dict['img'],
            img_rectified_fname=fname_dict['img_rectified'],
            eo=parsed_eo,
            ground_height=my_drone.ipod_params['ground_height'],
            sensor_width=my_drone.ipod_params['sensor_width']
        )
        rectify_time = time.time()

        uuid = "test1234"
        # Generate metadata for InnoMapViewer
        img_metadata = create_img_metadata_udp(
            uuid=uuid,
            path=project_path + "/" + fname_dict['img_rectified'],
            name=fname_dict['img'],
            img_type=img_type,
            tm_eo=[parsed_eo[0], parsed_eo[1]],
            img_boundary=bbox_wkt,
            objects=obj_metadata
        )
        metadata_time = time.time()

        img_metadata_info = json.dumps(img_metadata)
        #############################################
        # Send object information to web map viewer #
        #############################################
        fmt = '<4si' + str(len(img_metadata_info)) + 's'  # s: string, i: int
        data_to_send = pack(fmt, b"IPOD", len(img_metadata_info), img_metadata_info.encode())
        # s1.sendto(data_to_send, dest)

        transmission_time = time.time()

        cur_time = "%s\t%f\t%f\t%f\t%f\t%f\n" % (fname_dict['img'], preprocess_time - start_time,
                                                 inference_time - preprocess_time, rectify_time - inference_time,
                                                 metadata_time - rectify_time, transmission_time - metadata_time)
        f.write(cur_time)
        print(cur_time)

        return 'Image upload and IPOD chain complete'


if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=30011)
    # socket.close()
