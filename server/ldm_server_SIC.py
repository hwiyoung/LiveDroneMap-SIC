import json
import os
import time
import cv2
import socket
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request
from werkzeug.utils import secure_filename

from config import config_flask, config_watchdog
from server.image_processing.img_metadata_generation import create_img_metadata_tcp, create_obj_metadata
from clients.webodm import WebODM
from clients.mago3d import Mago3D

from server.image_processing.orthophoto_generation.Orthophoto import rectify_SIC
from server.image_processing.orthophoto_generation.ExifData import get_metadata, restoreOrientation
from server.image_processing.orthophoto_generation.EoData import rpy_to_opk_smartphone, geographic2plane, \
                                                                 Rot3D, kappa_from_location_diff
from server.image_processing.orthophoto_generation.Boundary import transform_bbox

from struct import *

# socket for sending
TCP_IP = '192.168.0.24'
TCP_PORT = 5010

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.connect((TCP_IP, TCP_PORT))
print('connected! - inference')


def recvall(sock,headersize):
    buf = b''
    header = unpack('>H', sock.recv(headersize)) # length(4byte) + data
    count = header[0]
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf


#########################
# Client for map viewer #
#########################
TCP_IP1 = '192.168.0.5'
TCP_PORT1 = 57821

s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# dest = ("192.168.0.5", 57821)
s1.connect((TCP_IP1, TCP_PORT1))
print('connected! - viewer')

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

height_threshold = 50
omega_phi_threshold = np.pi / 180 * 50
epsg = 3857

from server.my_drones import GalaxyS10_SIC
my_drone = GalaxyS10_SIC(pre_calibrated=False)

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
        # os.mkdir(os.path.join(new_project_dir, 'rectified'))

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
        for key in ['img']:
            if key not in request.files:  # Key check
                return 'No %s part' % key
            file = request.files[key]
            if file.filename == '':  # Value check
                return 'No selected file'
            if file and allowed_file(file.filename):  # If the keys and corresponding values are OK
                fname_dict[key] = secure_filename(file.filename)
                file.save(os.path.join(project_path, fname_dict[key]))  # Save the file from client
            else:
                return 'Failed to save the uploaded files'

        ################################
        # IPOD chain 1: Pre-processing #
        ################################
        print("IPOD chain 1: Pre-processing")
        print(" * Metadata extraction...")
        focal_length, orientation, parsed_eo, before_lonlat, \
        uuid, task_id, maker = get_metadata(os.path.join(project_path, fname_dict["img"]),
                                            "Linux")  # unit: m, _, deg, deg, _, _, _
        img_type = int(os.path.splitext(os.path.join(project_path, fname_dict["img"]))[0][-1])

        # if parsed_eo[2] - my_drone.ipod_params["ground_height"] <= height_threshold:
        #     print("  * The height is too low: ", parsed_eo[2] - my_drone.ipod_params["ground_height"], " m")
        #     return "The height of the image is too low"

        if not my_drone.pre_calibrated:
            print(' * System calibration...')
            transformed_eo = geographic2plane(parsed_eo, epsg)

            # # Sensor
            # opk = rpy_to_opk_smartphone(transformed_eo[3:])
            # transformed_eo[3:] = opk * np.pi / 180  # degree to radian

            # Location
            before_xy = geographic2plane(before_lonlat, epsg)
            opk = np.empty(3)
            opk[0:2] = 0
            opk[-1] = kappa_from_location_diff(transformed_eo, before_xy)
            transformed_eo[3:] = opk * np.pi / 180  # degree to radian
            print(transformed_eo)

            # if abs(opk[0]) > omega_phi_threshold or abs(opk[1]) > omega_phi_threshold:
            #     print('Too much omega/phi will kill you')
            #     return 'Too much omega/phi will kill you'

        R_GC = Rot3D(transformed_eo)
        R_CG = R_GC.T

        preprocess_time = time.time()

        ##################################
        # IPOD chain 2: Object detection #
        ##################################
        print("IPOD chain 2: Object detection")
        img = cv2.imread(os.path.join(project_path, fname_dict["img"]))

        # Restore the image based on orientation information
        restored_img = restoreOrientation(img, orientation)

        ####################################
        # Send the image to inference server
        print(" * start sending...")
        # string_data = restored_img.tostring()
        # hei, wid, _ = restored_img.shape
        # header = pack('>2s2H', b'st', wid, hei)
        # s.send(header + string_data)
        string_data = cv2.imencode('.png', restored_img)[1].tobytes()
        string_data_size = pack('>I', len(string_data))
        s.send(b'st' + string_data_size + string_data)

        # Receiving Bbox info
        bbox_coords_bytes = recvall(s, 2)
        bbox_coords = json.loads(bbox_coords_bytes)
        # bbox_coords_bytes = s.recv(65534)
        # bbox_coords = json.loads(bbox_coords_bytes)
        print("  * received!")
        ####################################

        # bboxed_img = highlighting_bbox(imgencode, [x1, y1, x2, y2, cls_id])

        img_rows = restored_img.shape[0]
        img_cols = restored_img.shape[1]
        pixel_size = my_drone.ipod_params['sensor_width'] / img_cols

        print(" * Georeferencing boundary boxes...")
        obj_metadata = []
        for bbox in bbox_coords:
            bbox_world = transform_bbox(bbox, img_rows, img_cols, pixel_size,
                                        my_drone.ipod_params['focal_length'],
                                        transformed_eo, R_CG, my_drone.ipod_params['ground_height'])

            obj_metadata.append(create_obj_metadata(bbox[4], str(bbox), bbox_world))

        # x1 = [603, 800, 289]
        # x2 = [708, 988, 392]
        # y1 = [776, 588, 1491]
        # y2 = [860, 947, 1572]
        # class_id = [3, 3, 3]

        inference_time = time.time()

        ##################################################
        # IPOD chain 3: Individual orthophoto generation #
        ##################################################
        print("IPOD chain 3: Individual orthophoto generation")
        fname_dict['img_rectified'] = fname_dict['img'].split('.')[0] + '.png'
        bbox_wkt, orthophoto = rectify_SIC(
            output_path=config_watchdog.BaseConfig.DIRECTORY_FOR_OUTPUT,
            img_fname=fname_dict['img'],
            restored_image=restored_img,
            focal_length=focal_length,
            pixel_size=pixel_size/1000,
            eo=transformed_eo,
            R_GC=R_GC,
            ground_height=my_drone.ipod_params['ground_height'],
            epsg=epsg,
            img_type=img_type
        )
        # Write image to memory
        orthophoto_encode = cv2.imencode('.png', orthophoto)
        orthophoto_bytes = orthophoto_encode[1].tostring()

        rectify_time = time.time()

        # Generate metadata for InnoMapViewer
        img_metadata = create_img_metadata_tcp(
            uuid=uuid,
            task_id=task_id,
            name=fname_dict['img'],
            img_type=img_type,
            img_boundary=bbox_wkt,
            objects=obj_metadata
        )
        metadata_time = time.time()

        img_metadata_bytes = json.dumps(img_metadata).encode()
        #############################################
        # Send object information to web map viewer #
        #############################################
        full_length = len(img_metadata_bytes) + len(orthophoto_bytes)
        fmt = '<4siii' + str(len(img_metadata_bytes)) + 's' + str(len(orthophoto_bytes)) + 's'  # s: string, i: int
        data_to_send = pack(fmt, b"IPOD", full_length, len(img_metadata_bytes), len(orthophoto_bytes),
                            img_metadata_bytes, orthophoto_bytes)
        s1.send(data_to_send)

        transmission_time = time.time()

        cur_time = "%s\t%f\t%f\t%f\t%f\t%f\n" % (fname_dict['img'], preprocess_time - start_time,
                                                 inference_time - preprocess_time, rectify_time - inference_time,
                                                 metadata_time - rectify_time, transmission_time - metadata_time)
        f.write(cur_time)
        print("Name | Pre-processing | Object Detection | Orthophoto | Metadata | Transmission")
        print(cur_time)

        return 'Image upload and IPOD chain complete'


if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=30022)
    # socket.close()
