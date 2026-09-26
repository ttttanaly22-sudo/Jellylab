from pathlib import Path

from config import IMAGE_DIR


DISHES = ["1", "2", "3", "4"]
POLYPS = ["A", "B", "C", "D", "E","R"]


def get_image_count():

    counts = {}

    # 1A ～ 4E + 1R~4R を作成
    for dish in DISHES:
        for polyp in POLYPS:
            counts[dish + polyp] = 0

    # 未分類
    counts["unknown"] = 0

    # DEL済み
    counts["deleted"] = 0


    path = Path(IMAGE_DIR)

    if not path.exists():
        return counts


    for file in path.glob("*.jpg"):

        name = file.name


        # -----------------------------
        # DEL画像
        # -----------------------------
        if name.startswith("DEL_"):

            counts["deleted"] += 1
            continue


        stem = file.stem


        # -----------------------------
        # prefixあり
        #
        # 例:
        # 1A_20260712_103000
        # -----------------------------
        if (
            len(stem) >= 3
            and stem[0] in DISHES
            and stem[1] in POLYPS
            and stem[2] == "_"
        ):

            prefix = stem[:2]

            counts[prefix] += 1


        # -----------------------------
        # prefixなし
        #
        # 例:
        # 20260712_103000
        # -----------------------------
        else:

            counts["unknown"] += 1


    return counts