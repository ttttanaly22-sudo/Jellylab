import sys
import types
import unittest
from pathlib import Path

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
        pass

    def get_jpeg(self):
        return b'fake-jpeg'

    def capture(self, label=''):
        return ROOT / 'images' / 'sample.jpg'

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


if __name__ == '__main__':
    unittest.main()
