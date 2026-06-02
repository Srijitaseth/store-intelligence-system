import argparse
from ultralytics import YOLO


def debug_video(video_path):
    model = YOLO("yolov8n.pt")

    results = model.track(
        source=video_path,
        stream=True,
        persist=True,
        classes=[0],
        conf=0.25,
        tracker="bytetrack.yaml"
    )

    frame_count = 0
    frames_with_people = 0
    total_person_detections = 0
    frames_with_track_ids = 0

    for result in results:
        frame_count += 1

        if result.boxes is None or len(result.boxes) == 0:
            continue

        person_count_this_frame = len(result.boxes)
        total_person_detections += person_count_this_frame
        frames_with_people += 1

        has_track_id = False

        for box in result.boxes:
            if box.id is not None:
                has_track_id = True

        if has_track_id:
            frames_with_track_ids += 1

        if frame_count % 100 == 0:
            print(
                f"Frame {frame_count}: "
                f"persons={person_count_this_frame}, "
                f"has_track_id={has_track_id}"
            )

    print("========== DEBUG SUMMARY ==========")
    print(f"Total frames processed: {frame_count}")
    print(f"Frames with people: {frames_with_people}")
    print(f"Total person detections: {total_person_detections}")
    print(f"Frames with tracking IDs: {frames_with_track_ids}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)

    args = parser.parse_args()

    debug_video(args.video)