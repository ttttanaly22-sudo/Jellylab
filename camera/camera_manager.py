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
    IMAGE_DIR,
    VIDEO_DIR
)


class CameraManager:

    @staticmethod
    def resolve_output_dir(output_dir):
        directory = Path(output_dir)
        if directory.is_absolute():
            return directory
        return (Path(__file__).resolve().parent.parent / directory).resolve()

    def __init__(self):

        self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            raise RuntimeError("camera open failed")

        self.lock = threading.RLock()
        self.restarting = False
        self.recording_stop_event = None
        self.recording_thread = None
        self.recording_output = None
        self.recording_started_at = None
        self.recording_active = False

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

        print("recovering camera...")
        self.reconnect()

        return False, None

    def open_capture(self):

        cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
        if not cap.isOpened():
            return None

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_HEIGHT)
        return cap

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

        directory = self.resolve_output_dir(output_dir)
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

    def record_video(self, duration=3, output_dir="videos", fps=20, stop_event=None):
        temp_filename = None
        final_filename = None
        writer = None

        try:
            print("record start", flush=True)
            directory = self.resolve_output_dir(output_dir)
            directory.mkdir(parents=True, exist_ok=True)

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 一時ファイル（mp4v）
            temp_filename = directory / f"micro_video_{stamp}_temp.mp4"

            # 最終ファイル（H.264）
            final_filename = directory / f"micro_video_{stamp}.mp4"

            # 現在のカメラをそのまま使用する
            # 2つ目のVideoCaptureは開かない
            with self.lock:
                if self.restarting:
                    return None

                self.set_preview()
                time.sleep(0.2)

                # 古いフレームを少し捨てる
                for _ in range(3):
                    self.cap.read()

                success, frame = self.cap.read()

            if not success or frame is None:
                print("video recording: first frame read failed")
                return None

            height, width = frame.shape[:2]

            writer = cv2.VideoWriter(
                str(temp_filename),
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (width, height)
            )

            if not writer.isOpened():
                print("video recording: VideoWriter open failed")
                return None

            start = time.time()
            deadline = start + max(0.0, min(float(duration), 120.0))

            while True:
                if stop_event is not None and stop_event.is_set():
                    break

                if time.time() >= deadline:
                    break

                success, frame = self.read()

                if success and frame is not None:
                    writer.write(frame)

            writer.release()
            writer = None
            print("writer release", flush=True)

            # 一時ファイル確認
            if not temp_filename.exists() or temp_filename.stat().st_size == 0:
                print("video recording: temporary file is empty")

                if temp_filename.exists():
                    temp_filename.unlink()

                return None

            print(f"video recording: recorded {temp_filename}")

            # mp4v → H.264
            import subprocess
            thread = threading.Thread(
                target=self.convert_video_async,
                args=(temp_filename, final_filename),
                daemon=True
            )

            thread.start()

            print(
                f"video recording complete: {temp_filename}",
                flush=True
            )

            return temp_filename

        finally:
            if writer is not None:
                writer.release()

    def convert_video_async(self, temp_filename, final_filename):

        import subprocess

        try:
            print("ffmpeg start", flush=True)

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", str(temp_filename),
                    "-c:v", "libx264",
                    "-crf", "23",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(final_filename)
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )

            print("ffmpeg end", flush=True)

            if result.returncode != 0:

                print("ffmpeg conversion failed")
                print(result.stderr)

                return

            if temp_filename.exists():
                temp_filename.unlink()

            print(
                f"video converted: {final_filename}",
                flush=True
            )

        except Exception as e:

            print(
                f"video convert exception: {e}",
                flush=True
            )

    def start_recording(self, duration=120, output_dir="videos", fps=20):

        if self.recording_active:
            return self.recording_output

        self.recording_started_at = time.time()
        self.recording_active = True
        self.recording_stop_event = threading.Event()
        self.recording_output = None

        def worker():
            try:
                self.recording_output = self.record_video(
                    duration=duration,
                    output_dir=output_dir,
                    fps=fps,
                    stop_event=self.recording_stop_event
                )
            finally:
                self.recording_active = False

        self.recording_thread = threading.Thread(target=worker, daemon=True)
        self.recording_thread.start()
        return None

    def stop_recording(self):

        if getattr(self, "recording_stop_event", None) is not None:
            self.recording_stop_event.set()

        thread = getattr(self, "recording_thread", None)
        if thread is not None:
            thread.join(timeout=30)

        filename = getattr(self, "recording_output", None)

        if filename is None and self.recording_started_at is not None:
            videos_dir = self.resolve_output_dir(VIDEO_DIR)
            if videos_dir.exists():
                candidates = sorted(
                    videos_dir.glob("micro_video_*.mp4"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                for candidate in candidates:
                    if candidate.stat().st_mtime >= self.recording_started_at:
                        filename = candidate
                        self.recording_output = candidate
                        break

        self.recording_thread = None
        self.recording_stop_event = None
        self.recording_started_at = None
        self.recording_active = False
        self.recording_output = filename
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