import sys
import threading
import types
import unittest
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

fake_sensor_manager = types.ModuleType('managers.sensor_manager')
fake_sensor_manager.get_status = lambda: {'temperature': 21.5, 'lux': 41.0}

fake_logger_manager = types.ModuleType('managers.logger_manager')
fake_logger_manager.start_logger = lambda: None

fake_system_manager = types.ModuleType('managers.system_manager')
fake_system_manager.get_storage = lambda: 88.0

fake_image_manager = types.ModuleType('managers.image_manager')
fake_image_manager.get_image_count = lambda: 5

class DummyCamera:
    def __init__(self):
        self.resolution = 'preview'
        self.recording_stop_event = None
        self.recording_thread = None
        self.recording_output = None

    def get_jpeg(self):
        return b'fake-jpeg'

    def set_preview(self):
        self.resolution = 'preview'

    def set_capture(self):
        self.resolution = 'capture'

    def capture(self, label='', output_dir='images'):
        return ROOT / 'images' / 'sample.jpg'

    def start_recording(self, duration=120, output_dir='videos', fps=20):
        self.recording_stop_event = threading.Event()
        self.recording_output = None
        return None

    def stop_recording(self):
        if self.recording_stop_event is not None:
            self.recording_stop_event.set()
        filename = ROOT / 'videos' / 'video_test.mp4'
        filename.parent.mkdir(exist_ok=True)
        filename.write_bytes(b'fake-video')
        self.recording_output = filename
        self.recording_stop_event = None
        return filename

fake_camera_module = types.ModuleType('camera.camera_manager')
fake_camera_module.CameraManager = DummyCamera

sys.modules.setdefault('managers', types.ModuleType('managers'))
sys.modules['managers.sensor_manager'] = fake_sensor_manager
sys.modules['managers.logger_manager'] = fake_logger_manager
sys.modules['managers.system_manager'] = fake_system_manager
sys.modules['managers.image_manager'] = fake_image_manager

sys.modules.setdefault('camera', types.ModuleType('camera'))
sys.modules['camera.camera_manager'] = fake_camera_module

import app as app_module


class AppRouteTests(unittest.TestCase):
    def test_home_page_shows_mode_selection(self):
        client = app_module.app.test_client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('JellyLab', text)
        self.assertIn('顕微鏡', text)

    def test_jellylab_route_is_available(self):
        client = app_module.app.test_client()
        response = client.get('/jellylab')
        self.assertEqual(response.status_code, 200)

    def test_microscope_page_has_preview_controls(self):
        client = app_module.app.test_client()
        response = client.get('/microscope')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('Preview', text)
        self.assertNotIn('解像度', text)
        self.assertIn('保存', text)

    def test_microscope_page_links_home_only(self):
        client = app_module.app.test_client()
        response = client.get('/microscope')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('/', text)
        self.assertNotIn('/timeline/unknown', text)

    def test_timeline_links_back_to_jellylab_and_micro_scope(self):
        client = app_module.app.test_client()
        response = client.get('/timeline/unknown')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('/jellylab', text)
        self.assertIn('/microscope', text)

    def test_microscope_capture_uses_json_download_flow(self):
        client = app_module.app.test_client()
        response = client.get('/microscope')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('downloadCapture', text)
        self.assertNotIn('action="/microscope/capture" method="post"', text)

    def test_microscope_capture_without_resolution_setting(self):
        sample = ROOT / 'images' / 'sample.jpg'
        sample.parent.mkdir(exist_ok=True)
        sample.write_bytes(b'fake-image')

        client = app_module.app.test_client()
        response = client.post('/microscope/capture')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response.content_type)

    def test_microscope_page_lists_saved_files(self):
        saved_dir = ROOT / 'micro_images'
        saved_dir.mkdir(exist_ok=True)
        saved_image = saved_dir / 'saved_preview.jpg'
        saved_image.write_bytes(b'fake-image')

        client = app_module.app.test_client()
        response = client.get('/microscope')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('保存ファイル一覧', text)
        self.assertIn('saved_preview.jpg', text)

    def test_microscope_page_has_video_capture_button(self):
        client = app_module.app.test_client()
        response = client.get('/microscope')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('動画撮影', text)

    def test_video_route_serves_video_file(self):
        video_dir = ROOT / 'videos'
        video_dir.mkdir(exist_ok=True)
        sample_video = video_dir / 'sample.mp4'
        sample_video.write_bytes(b'fake-video')

        client = app_module.app.test_client()
        response = client.get('/videos/sample.mp4')
        self.assertEqual(response.status_code, 200)
        self.assertIn('video/mp4', response.content_type)

    def test_video_stop_route_returns_filename(self):
        client = app_module.app.test_client()
        response = client.post('/microscope/video_stop')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['ok'])
        self.assertIn('video_test.mp4', str(body.get('filename') or ''))

    def test_config_paths_are_project_root_absolute(self):
        self.assertTrue(Path(config.IMAGE_DIR).is_absolute())
        self.assertTrue(Path(config.MICROSCOPE_IMAGE_DIR).is_absolute())
        self.assertTrue(Path(config.LOG_DIR).is_absolute())
        self.assertTrue(Path(config.DATA_DIR).is_absolute())


if __name__ == '__main__':
    unittest.main()
