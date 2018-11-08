import requests
import json
import nanotime


class Mago3D:
    def __init__(self, url, user_id, api_key):
        self.url = url
        self.user_id = user_id
        self.headers = None
        self.api_key = api_key

        self.set_headers()
        self.get_token()

    def set_headers(self, token='', role='ADMIN', algorithm='sha', type='jwt,mac'):
        current_time = int(nanotime.now())
        headers_content = "user_id=%s" \
                          "&api_key=%s" \
                          "&token=%s" \
                          "&role=%s" \
                          "&algorithm=%s" \
                          "&type=%s" \
                          "&timestamp=%s" % (self.user_id, self.api_key, token, role, algorithm, type, current_time)
        self.headers = {'live_drone_map': headers_content}

    def get_token(self, auto_set_headers=True):
        res = requests.post(url=self.url + 'authentication/tokens/', headers=self.headers)
        token = res.json()['token']
        if auto_set_headers:
            self.set_headers(token=token)
        return token

    def create_project(self, drone_project_name, drone_project_type, shooting_area):
        data = {
            "drone_id": 1,
            "drone_project_name": drone_project_name,
            "drone_project_type": drone_project_type,
            "shooting_area": shooting_area,
            "shooting_upper_left_latitude": 37.1,
            "shooting_upper_left_longitude": 132.23,
            "shooting_upper_right_latitude": 37.2,
            "shooting_upper_right_longitude": 132.24,
            "shooting_lower_right_latitude": 37.3,
            "shooting_lower_right_longitude": 132.25,
            "shooting_lower_left_latitude": 37.4,
            "shooting_lower_left_longitude": 132.26,
            "location": "POINT (128.382757714281 34.7651373676212)",
            "shooting_date": "20180929203800",  # TODO: 현재시각
            "description": "시뮬레이션 프로젝트"
        }
        res = requests.post(url=self.url + 'drone-projects/', headers=self.headers, data=data)
        return res

    def upload(self, img_fname, img_metadata):
        data = {'file_meta': json.dumps(img_metadata)}
        files = {
            'file': open(img_fname, 'rb')
        }
        res = requests.post(url=self.url + 'transfer-data/', headers=self.headers, files=files, data=data)
        return res

    def set_simulation_id(self, simulation_id, drone_project_id, status='2'):
        simulation_json = {
            'simulation_log_id': simulation_id,
            'drone_project_id': drone_project_id,
            'status': status
        }
        r = requests.post(url=self.url + 'simulations/%s' % simulation_id, json=simulation_json)
        return r.text

    def conclude_simulation(self, drone_project_id):
        data = {
            'drone_project_id': drone_project_id,
            'status': '4'
        }
        r = requests.post(url=self.url + 'drone-projects/%s' % drone_project_id, json=data)
        return r.text


if __name__ == '__main__':
    mago3d = Mago3D('http://seoul.gaia3d.com:30080/', 'ldm_uos', '54fe3dcd-f814-447a-a476-96e216dd774e')
    res = mago3d.conclude_simulation('129')
    print(res)