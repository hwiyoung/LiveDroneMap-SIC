import requests

class livedronemap:
    def __init__(self, url):
        self.url = url
        self.current_project = None

    def create_project(self, project_name):
        project_json = {
            'mode': 'create',
            'name':  project_name
        }
        r = requests.post(self.url + 'project/', json=project_json)
        return r

    def read_project(self):
        r = requests.get(self.url + 'project/')
        return r.json()

    def set_current_project(self, project_name):
        existing_projects = self.read_project()
        if project_name in existing_projects:
            self.current_project = project_name
        else:
            print('Project %s does not exist' % project_name)

    def ldm_upload(self, img_fname, eo_fname):
        if self.current_project is not None:
            files = {
                'img': open(img_fname, 'rb'),
                'eo': open(eo_fname, 'rb')
            }
            r = requests.post(self.url + 'ldm_upload/' + self.current_project, files=files)
            return r


if __name__ == '__main__':
    livedronemap = livedronemap('http://127.0.0.1:5000/')
    livedronemap.create_project('test2')
    livedronemap.set_current_project('test2')
    livedronemap.ldm_upload('2018-06-19_171528_sony.jpg', '2018-06-19_171528_insp.txt')