# -----------------------------
# Camera
# -----------------------------

CAMERA_DEVICE = (
    "/dev/v4l/by-id/"
    "usb-XC-TECH_2k_usb_Camera_Redeagle_20250820.1412-video-index0"
)

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480
PREVIEW_FPS = 30

CAPTURE_WIDTH = 2560
CAPTURE_HEIGHT = 1440


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# -----------------------------
# Logger
# -----------------------------

LOG_INTERVAL = 600
LOG_DIR = str((PROJECT_ROOT / "logs").resolve())


# -----------------------------
# Paths
# -----------------------------

IMAGE_DIR = str((PROJECT_ROOT / "images").resolve())
MICROSCOPE_IMAGE_DIR = str((PROJECT_ROOT / "micro_images").resolve())
DATA_DIR = str((PROJECT_ROOT / "data").resolve())
VIDEO_DIR = str((PROJECT_ROOT / "videos").resolve())