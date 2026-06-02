import argparse
from ultralytics import YOLO
from pipeline.zones import get_zone_for_point


def debug_zone_match(video_path):
    model = YOLO("yolov8n.pt")

    zones = {
        "ENTRY_ZONE": [0, 0, 1920, 350],
        "MAIN_FLOOR": [0, 350, 1200, 1080],
        "BILLING": [1200, 350, 1920, 1080]
    }

    results = model.track(
        source=video_path,
        stream=True,
        persist=True,
        classes=[0],
        conf=0.25,
        tracker="bytetrack.yaml"
    )

    printed = 0

    for frame_number, result in enumerate(results, start=1):
        if result.boxes is None or len(result.boxes) == 0:
            continue

        for box in result.boxes:
            if box.id is None:
                continue

            track_id = int(box.id[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            zone = get_zone_for_point(center_x, center_y, zones)

            print(
                f"frame={frame_number}, "
                f"track_id={track_id}, "
                f"center_x={center_x}, center_y={center_y}, "
                f"matched_zone={zone}"
            )

            printed += 1

            if printed >= 20:
                return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)

    args = parser.parse_args()
    debug_zone_match(args.video)