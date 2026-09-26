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
from config import MICROSCOPE_IMAGE_DIR


app = Flask(__name__)


camera = CameraManager()


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


@app.route("/microscope")
def microscope():

    return render_template("microscope.html")


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

    return send_file(
        filename,
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=filename.name
    )


@app.route("/micro_images/<filename>")
def serve_micro_image(filename):

    return send_file(
        Path(MICROSCOPE_IMAGE_DIR) / filename
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

IMAGE_DIR = Path("images")


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

