import arrow


def create_img_metadata(drone_project_id, data_type, file_name, detected_objects, drone_id, drone_name, parsed_eo):
    img_metadata = {
        "drone_project_id": drone_project_id,
        "data_type": data_type,
        "file_name": file_name,
        "detected_objects": detected_objects,
        "drone": {
            "drone_id": drone_id,
            "drone_name": drone_name,
            "latitude": parsed_eo[1],
            "longitude": parsed_eo[0],
            "altitude": parsed_eo[2],
            "roll": round(parsed_eo[3], 3),
            "pitch": round(parsed_eo[4], 3),
            "yaw": round(parsed_eo[5], 3),
            "insert_date": arrow.utcnow().format('YYYYMMDDHHmmss')
        },
        # TODO: EXIF 데이터에서 시간 추출 (지금은 그냥 현재시각으로)
        "shooting_date": arrow.utcnow().format('YYYYMMDDHHmmss')
    }

    return img_metadata


def create_img_metadata_udp(uuid, path, name, tm_eo, img_boundary, objects):
    """
    Create a metadata of an orthophoto for udp transmission
    :param uuid: uuid of the image | String
    :param path: A path of a generated orthophoto | String
    :param name: A name of the original image | String
    :param tm_eo: EOP of the image | np.array
    :param img_boundary: Boundary of the orthophoto | String in wkt
    :param objects: JSON object? array? of the detected object ... from create_obj_metadata
    :return: JSON object of the orthophoto ... python dictionary
    """
    img_metadata = {
        "uid": uuid,    # String
        "path": path,  # String
        "img_name": name,  # String
        "img_position": [tm_eo[0], tm_eo[1]],  # Array
        "img_boundary": img_boundary,  # WKT ... String
        "objects": objects
    }

    return img_metadata


def create_obj_metadata(object_type, boundary):
    """
    Create a metadata of **each** detected object
    :param object_type: Type of the object | int
    :param boundary: Boundary of the object in GCS - shape: 2(x, y) x points | np.array
    :return: JSON object of each detected object ... python dictionary
    """
    obj_metadata = {
        "obj_type": object_type
    }

    object_boundary = "POLYGON (("
    for i in range(boundary.shape[1]):
        object_boundary = object_boundary + str(boundary[0, i]) + " " + str(boundary[1, i]) + ", "
    object_boundary = object_boundary + str(boundary[0, 0]) + " " + str(boundary[1, 0]) + "))"
    # print("object_boundary: ", object_boundary)

    obj_metadata["obj_boundary"] = object_boundary  # string in wkt
    # print("obj_metadata: " ,obj_metadata)

    return obj_metadata
