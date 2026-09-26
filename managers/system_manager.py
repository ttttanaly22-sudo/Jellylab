import shutil


def get_storage():

    total, used, free = shutil.disk_usage("/")

    return {
        "total": round(total / (1024**3), 1),
        "used": round(used / (1024**3), 1),
        "free": round(free / (1024**3), 1)
    }