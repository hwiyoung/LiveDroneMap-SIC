import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config.config_watchdog import BaseConfig as Config
from clients.ldm_client import Livedronemap
from server.image_processing.exif_parser import extract_eo
import os
from watchdog.observers.polling import PollingObserver

image_list = []

ldm = Livedronemap(Config.LDM_ADDRESS)
project_id = ldm.create_project(Config.LDM_PROJECT_NAME)
ldm.set_current_project(project_id)

print('Current project ID: %s' % project_id)


def upload_data(image_fname):
    result = ldm.ldm_upload2(image_fname)
    print('response from LDM server:', result)


class Watcher:
    def __init__(self, directory_to_watch):
        # self.observer = Observer()
        self.observer = PollingObserver()
        self.directory_to_watch = directory_to_watch

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.directory_to_watch, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except:
            self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None
        elif event.event_type == 'created':
            file_name = event.src_path.split('\\')[-1]
            extension_name = event.src_path.split('.')[-1]
            print('A new file detected: %s' % file_name)
            print('extenstion: ', extension_name)
            if Config.IMAGE_FILE_EXT in extension_name:
                image_list.append(file_name)
                time.sleep(2)
                print('uploading data...')
                upload_data(event.src_path)
            else:
                print('Not allowed extension of an image')
            print('===========================================================')


if __name__ == '__main__':
    # filelist = [f for f in os.listdir(Config.DIRECTORY_TO_WATCH)]
    # for f in filelist:
    #     os.remove(Config.DIRECTORY_TO_WATCH + "/" + f)
    # print('Removal is done!')

    print(Config.DIRECTORY_TO_WATCH)

    w = Watcher(directory_to_watch=Config.DIRECTORY_TO_WATCH)
    w.run()
