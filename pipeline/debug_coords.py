import argparse
from ultralytics import YOLO


def debug_coords(video_path):
    model = YOLO("yolov8n.pt")

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

            print(
                f"frame={frame_number}, "
                f"track_id={track_id}, "
                f"x1={int(x1)}, y1={int(y1)}, x2={int(x2)}, y2={int(y2)}, "
                f"center_x={center_x}, center_y={center_y}"
            )

            printed += 1

            if printed >= 20:
                return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)

    args = parser.parse_args()

    debug_coords(args.video)