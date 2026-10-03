from flask import (
    Flask,
    Response,
    send_file,
    render_template,
    jsonify,
    request,
    redirect
)

from pathlib import Path
from datetime import datetime

from managers.sensor_manager import get_status
from managers.logger_manager import start_logger
from camera.camera_manager import CameraManager
from managers.system_manager import get_storage
from managers.image_manager import get_image_count
from config import IMAGE_DIR as CONFIG_IMAGE_DIR, MICROSCOPE_IMAGE_DIR, VIDEO_DIR


app = Flask(__name__)

VIDEO_OUTPUT_DIR = Path(VIDEO_DIR)

MAX_VIDEO_DURATION = 120.0

camera = CameraManager()


def get_video_status(filename):
    status_reader = getattr(camera, "get_video_conversion_status", None)
    if status_reader is None:
        return "unknown"
    return status_reader(filename)


def can_serve_video(filename):
    if filename.endswith("_temp.mp4"):
        return False
    return get_video_status(filename) not in {"pending", "failed"}


# -----------------------------
# Camera stream
# -----------------------------

def generate():

    while True:

        jpeg = camera.get_jpeg()

        if jpeg is None:
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + jpeg +
            b'\r\n'
        )



@app.route("/")
def home():

    return render_template("home.html")


@app.route("/jellylab")
def jellylab():

    status = get_status()

    return render_template(
        "index.html",
        temperature=status["temperature"],
        lux=status["lux"]
    )


@app.route("/preview")
def preview():

    return redirect("/microscope", code=302)


@app.route("/microscope")
def microscope():

    image_dir = Path(MICROSCOPE_IMAGE_DIR)
    image_dir.mkdir(parents=True, exist_ok=True)

    video_dir = Path(VIDEO_DIR)
    video_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        image_dir.glob("*.jpg"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    videos = sorted(
        (
            path for path in video_dir.glob("*.mp4")
            if can_serve_video(path.name)
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    return render_template(
        "microscope.html",
        images=images,
        videos=videos
    )


@app.route("/microscope/capture", methods=["POST"])
def microscope_capture():

    filename = camera.capture(output_dir=MICROSCOPE_IMAGE_DIR)

    if filename is None:
        return jsonify(
            {
                "ok": False,
                "message": "保存に失敗しました"
            }
        ), 500

    return jsonify(
        {
            "ok": True,
            "filename": filename.name
        }
    )


@app.route("/microscope/video_capture", methods=["POST"])
def microscope_video_capture():

    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    action = (payload.get("action") or request.form.get("action") or "start").strip().lower()

    if action == "stop":
        filename = camera.stop_recording()
        return jsonify(
            {
                "ok": True,
                "recording": False,
                "filename": filename.name if filename is not None else None
            }
        )

    if camera.recording_stop_event is not None and camera.recording_stop_event.is_set() is False:
        return jsonify({"ok": True, "recording": True})

    duration = request.form.get("duration", str(MAX_VIDEO_DURATION))

    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = MAX_VIDEO_DURATION

    duration = max(1.0, min(duration, MAX_VIDEO_DURATION))

    camera.start_recording(duration=duration, output_dir=VIDEO_OUTPUT_DIR)

    return jsonify(
        {
            "ok": True,
            "recording": True,
            "duration": duration
        }
    )


@app.route("/microscope/video_stop", methods=["POST"])
def microscope_video_stop():

    filename = camera.stop_recording()

    return jsonify(
        {
            "ok": True,
            "recording": False,
            "filename": filename.name if filename is not None else None
        }
    )


@app.route("/video_status/<filename>")
def video_status(filename):
    if filename.endswith("_temp.mp4"):
        return jsonify({"status": "unavailable"}), 404

    status = get_video_status(filename)
    if status == "unknown" and (VIDEO_OUTPUT_DIR / filename).is_file():
        status = "ready"

    return jsonify({"status": status})


@app.route("/micro_images/<filename>")
def serve_micro_image(filename):

    return send_file(
        Path(MICROSCOPE_IMAGE_DIR) / filename
    )


@app.route("/videos/<filename>")
def serve_video(filename):

    if not can_serve_video(filename):
        return jsonify({"error": "video is not ready"}), 404

    return send_file(
        VIDEO_OUTPUT_DIR / filename,
        mimetype="video/mp4"
    )

@app.route("/video_download/<filename>")
def download_video(filename):

    if not can_serve_video(filename):
        return jsonify({"error": "video is not ready"}), 404

    return send_file(
        VIDEO_OUTPUT_DIR / filename,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=filename
    )


@app.route("/video")
def video():

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )



@app.route("/capture")
def capture():

    label = request.args.get("label", "")

    filename = camera.capture(label)

    if filename is None:
        return jsonify(
            {
                "ok":False,
                "message":"逕ｻ蜒丈ｿ晏ｭ倥↓螟ｱ謨励＠縺ｾ縺励◆"
            }
        ),500

    return jsonify(
        {
            "ok":True,
            "filename":filename.name
        }
    )


@app.route("/status")
def status_route():

    status = get_status()

    status.update(
        {
            "storage": get_storage(),
            "images": get_image_count()
        }
    )

    return jsonify(status)



# -----------------------------
# Image
# -----------------------------

IMAGE_DIR = (Path(__file__).resolve().parent / CONFIG_IMAGE_DIR).resolve()


TIMELINE_PREFIXES = [
    f"{dish}{polyp}"
    for dish in ["1", "2", "3", "4"]
    for polyp in ["A", "B", "C", "D", "E", "R"]
]


@app.route("/images/<filename>")
def serve_image(filename):

    return send_file(
        IMAGE_DIR / filename
    )



# -----------------------------
# Timeline
# -----------------------------

@app.route("/timeline/<prefix>")
def timeline(prefix):

    images = []

    for file in IMAGE_DIR.glob("*.jpg"):

        name = file.name
        stem = file.stem

        is_deleted = name.startswith("DEL_")

        # -------------------------
        # deleted filter
        # -------------------------

        if prefix == "deleted":

            if not is_deleted:
                continue

        else:

            # 騾壼ｸｸ繧ｿ繧､繝繝ｩ繧､繝ｳ縺ｧ縺ｯDEL貂医∩繧帝勁螟・
            if is_deleted:
                continue

            # -------------------------
            # prefix filter
            # -------------------------

            if prefix != "unknown":

                if not name.startswith(prefix + "_"):
                    continue

            else:

                if (
                    len(stem) >= 3
                    and stem[0] in ["1", "2", "3", "4"]
                    and stem[1] in ["A", "B", "C", "D", "E", "R"]
                    and stem[2] == "_"
                ):
                    continue

        # -------------------------
        # datetime
        # -------------------------

        dt = None

        try:

            parts = stem.split("_")

            if len(parts) >= 2:

                dt = datetime.strptime(
                    parts[-2] + "_" + parts[-1],
                    "%Y%m%d_%H%M%S"
                )

        except ValueError:
            pass

        if dt:

            display_time = dt.strftime(
                "%Y/%m/%d %H:%M"
            )

        else:

            display_time = name

        # DEL_1A_... 縺ｮ蝣ｴ蜷医ｂ蜈・げ繝ｫ繝ｼ繝励ｒ蜿門ｾ・
        original_name = name

        if is_deleted:
            original_name = name[4:]

        original_stem = Path(original_name).stem

        image_prefix = ""

        if (
            len(original_stem) >= 3
            and original_stem[0] in ["1", "2", "3", "4"]
            and original_stem[1] in ["A", "B", "C", "D", "E", "R"]
            and original_stem[2] == "_"
        ):
            image_prefix = original_stem[:2]

        images.append(
            {
                "name": name,
                "path": "/images/" + name,
                "time": display_time,
                "prefix": image_prefix,
                "deleted": is_deleted
            }
        )

    # 譌･莉倥ｒ豁｣縺励￥譁ｰ縺励＞鬆・↓荳ｦ縺ｹ繧・
    images.sort(
        key=lambda x: x["time"],
        reverse=True
    )

    # -------------------------
    # Timeline navigation
    # -------------------------

    next_prefix = None

    if prefix in TIMELINE_PREFIXES:

        current_index = TIMELINE_PREFIXES.index(prefix)

        if current_index < len(TIMELINE_PREFIXES) - 1:
            next_prefix = TIMELINE_PREFIXES[current_index + 1]


    return render_template(
        "timeline.html",
        prefix=prefix,
        images=images,
        next_prefix=next_prefix
    )


# -----------------------------
# Move group
# -----------------------------

@app.route("/image/move", methods=["POST"])
def move_image():

    filename = request.form.get("filename")
    prefix = request.form.get("prefix")


    if not filename or not prefix:

        return jsonify(
            {
                "result":"error"
            }
        ),400



    old_path = IMAGE_DIR / filename


    if not old_path.exists():

        return jsonify(
            {
                "result":"not found"
            }
        ),404



    stem = old_path.stem
    suffix = old_path.suffix


    parts = stem.split("_")


    if len(parts) >= 3:

        new_name = (
            prefix
            + "_"
            + parts[-2]
            + "_"
            + parts[-1]
            + suffix
        )

    else:

        new_name = (
            prefix
            + "_"
            + stem
            + suffix
        )



    new_path = IMAGE_DIR / new_name



    if new_path.exists():

        return jsonify(
            {
                "result":"exists"
            }
        ),400



    old_path.rename(new_path)


    return jsonify(
        {
            "result":"ok"
        }
    )



# -----------------------------
# Delete
# -----------------------------

@app.route("/image/delete", methods=["POST"])
def delete_image():

    filename = request.form.get("filename")


    if not filename:

        return jsonify(
            {
                "result":"error"
            }
        ),400



    old_path = IMAGE_DIR / filename


    if not old_path.exists():

        return jsonify(
            {
                "result":"not found"
            }
        ),404



    new_path = IMAGE_DIR / (
        "DEL_" + filename
    )


    old_path.rename(new_path)


    return jsonify(
        {
            "result":"ok"
        }
    )
    
# -----------------------------
# restore
# -----------------------------

@app.route("/image/restore", methods=["POST"])
def restore_image():

    filename = request.form.get("filename")

    if not filename:

        return jsonify(
            {
                "result": "error"
            }
        ), 400

    if not filename.startswith("DEL_"):

        return jsonify(
            {
                "result": "not deleted"
            }
        ), 400

    old_path = IMAGE_DIR / filename

    if not old_path.exists():

        return jsonify(
            {
                "result": "not found"
            }
        ), 404

    restored_name = filename[4:]

    new_path = IMAGE_DIR / restored_name

    if new_path.exists():

        return jsonify(
            {
                "result": "exists"
            }
        ), 400

    old_path.rename(new_path)

    return jsonify(
        {
            "result": "ok"
        }
    )

# -----------------------------
# main
# -----------------------------

if __name__ == "__main__":

    start_logger()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

