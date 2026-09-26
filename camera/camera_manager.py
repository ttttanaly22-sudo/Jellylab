import cv2
import time
import threading
from pathlib import Path
from datetime import datetime

from config import (
    CAMERA_DEVICE,
    PREVIEW_WIDTH,
    PREVIEW_HEIGHT,
    CAPTURE_WIDTH,
    CAPTURE_HEIGHT,
    IMAGE_DIR
)


class CameraManager:

    def __init__(self):

        self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            raise RuntimeError("camera open failed")

        self.lock = threading.RLock()
        self.restarting = False

        self.set_preview()

    # -----------------------------
    # preview
    # -----------------------------

    def set_preview(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_HEIGHT)

    def set_capture(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

    def read(self):

        with self.lock:

            if self.restarting:
                return False, None

            success, frame = self.cap.read()

            if success:
                return True, frame

        # ここはロック外（重要）
        print("recovering camera...")
        self.reconnect()

        return False, None

    def get_jpeg(self):

        success, frame = self.read()

        if not success:
            return None

        _, jpeg = cv2.imencode(".jpg", frame)
        return jpeg.tobytes()

    # -----------------------------
    # capture
    # -----------------------------

    def capture(self, label="", output_dir=IMAGE_DIR):

        with self.lock:

            if self.restarting:
                return None

            self.set_capture()

            time.sleep(0.2)

            for _ in range(3):
                self.cap.read()

            success, frame = self.cap.read()

            self.set_preview()

        if not success:
            return None

        prefix = ""
        if label != "":
            prefix = label + "_"
            cv2.putText(
                frame,
                label,
                (30,70),
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0,0,255),
                4,
                cv2.LINE_AA
            )

        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = directory / (prefix + stamp + ".jpg")


        success = cv2.imwrite(
            str(filename),
            frame
        )


        if not success:
            print("image save failed")
            return None


        # サイズ確認
        if filename.stat().st_size == 0:
            print("empty image file")
            filename.unlink()
            return None
        return filename
    
    def reconnect(self):

        with self.lock:

            self.restarting = True

            try:
                self.cap.release()
            except:
                pass

            time.sleep(1)

            self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                self.restarting = False
                return False

            self.set_preview()

            self.restarting = False

            return True