import argparse
import os
import json
from datetime import datetime, timedelta, timezone

from ultralytics import YOLO

from pipeline.emit import create_event, write_event
from pipeline.zones import get_zone_for_point


def iso_time_from_frame(start_time, frame_number, fps):
    seconds = frame_number / fps
    event_time = start_time + timedelta(seconds=seconds)
    return event_time.isoformat().replace("+00:00", "Z")


def load_camera_config(camera_id, config_path="data/camera_zones.json"):
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    if camera_id not in config:
        raise ValueError(f"No camera zone config found for camera_id: {camera_id}")

    camera_config = config[camera_id]

    return camera_config["entry_line_y"], camera_config["zones"]


def process_video(video_path, output_path, store_id, camera_id):
    model = YOLO("yolov8n.pt")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.exists(output_path):
        os.remove(output_path)

    open(output_path, "w", encoding="utf-8").close()

    start_time = datetime(2026, 3, 3, 14, 0, 0, tzinfo=timezone.utc)
    fps = 15

    entry_line_y, zones = load_camera_config(camera_id)

    previous_y_by_track = {}
    current_zone_by_track = {}
    session_seq_by_track = {}
    last_entry_exit_frame_by_track = {}
    zone_enter_frame_by_track = {}
    last_dwell_emit_frame_by_track = {}
    billing_join_emitted_by_track = set()

    results = model.track(
        source=video_path,
        stream=True,
        persist=True,
        classes=[0],
        conf=0.35,
        tracker="bytetrack.yaml"
    )

    frame_number = 0

    for result in results:
        frame_number += 1
        timestamp = iso_time_from_frame(start_time, frame_number, fps)

        if result.boxes is None:
            continue

        current_billing_tracks = set()

        for box in result.boxes:
            if box.id is None:
                continue

            track_id = int(box.id[0])
            visitor_id = f"VIS_{track_id}"

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            if track_id not in session_seq_by_track:
                session_seq_by_track[track_id] = 1

            previous_y = previous_y_by_track.get(track_id)

            if previous_y is not None:
                last_event_frame = last_entry_exit_frame_by_track.get(track_id, -9999)
                cooldown_frames = 45
                can_emit_entry_exit = frame_number - last_event_frame >= cooldown_frames

                if can_emit_entry_exit:
                    if previous_y < entry_line_y and center_y >= entry_line_y:
                        event = create_event(
                            store_id=store_id,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type="ENTRY",
                            timestamp=timestamp,
                            confidence=confidence,
                            session_seq=session_seq_by_track[track_id]
                        )
                        write_event(output_path, event)

                        session_seq_by_track[track_id] += 1
                        last_entry_exit_frame_by_track[track_id] = frame_number

                    elif previous_y >= entry_line_y and center_y < entry_line_y:
                        event = create_event(
                            store_id=store_id,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type="EXIT",
                            timestamp=timestamp,
                            confidence=confidence,
                            session_seq=session_seq_by_track[track_id]
                        )
                        write_event(output_path, event)

                        session_seq_by_track[track_id] += 1
                        last_entry_exit_frame_by_track[track_id] = frame_number

            previous_y_by_track[track_id] = center_y

            new_zone = get_zone_for_point(center_x, center_y, zones)
            old_zone = current_zone_by_track.get(track_id)

            if new_zone == "BILLING":
                current_billing_tracks.add(track_id)

            if new_zone is not None:
                zone_key = f"{track_id}_{new_zone}"

                if zone_key not in zone_enter_frame_by_track:
                    zone_enter_frame_by_track[zone_key] = frame_number

                dwell_frames = frame_number - zone_enter_frame_by_track[zone_key]
                dwell_seconds = dwell_frames / fps
                last_dwell_frame = last_dwell_emit_frame_by_track.get(zone_key, -9999)

                if dwell_seconds >= 30 and frame_number - last_dwell_frame >= int(30 * fps):
                    dwell_event = create_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_DWELL",
                        timestamp=timestamp,
                        zone_id=new_zone,
                        dwell_ms=int(dwell_seconds * 1000),
                        confidence=confidence,
                        sku_zone=new_zone,
                        session_seq=session_seq_by_track[track_id]
                    )
                    write_event(output_path, dwell_event)

                    session_seq_by_track[track_id] += 1
                    last_dwell_emit_frame_by_track[zone_key] = frame_number

            if new_zone != old_zone:
                if old_zone is not None:
                    old_zone_key = f"{track_id}_{old_zone}"

                    zone_enter_frame_by_track.pop(old_zone_key, None)
                    last_dwell_emit_frame_by_track.pop(old_zone_key, None)

                    event = create_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_EXIT",
                        timestamp=timestamp,
                        zone_id=old_zone,
                        confidence=confidence,
                        session_seq=session_seq_by_track[track_id]
                    )
                    write_event(output_path, event)

                    session_seq_by_track[track_id] += 1

                if new_zone is not None:
                    new_zone_key = f"{track_id}_{new_zone}"
                    zone_enter_frame_by_track[new_zone_key] = frame_number

                    event = create_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_ENTER",
                        timestamp=timestamp,
                        zone_id=new_zone,
                        confidence=confidence,
                        queue_depth=None,
                        sku_zone=new_zone,
                        session_seq=session_seq_by_track[track_id]
                    )
                    write_event(output_path, event)

                    session_seq_by_track[track_id] += 1

                    if new_zone == "BILLING" and track_id not in billing_join_emitted_by_track:
                        queue_depth = len(current_billing_tracks)

                        event = create_event(
                            store_id=store_id,
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type="BILLING_QUEUE_JOIN",
                            timestamp=timestamp,
                            zone_id="BILLING",
                            confidence=confidence,
                            queue_depth=queue_depth,
                            sku_zone="BILLING",
                            session_seq=session_seq_by_track[track_id]
                        )
                        write_event(output_path, event)

                        session_seq_by_track[track_id] += 1
                        billing_join_emitted_by_track.add(track_id)

                current_zone_by_track[track_id] = new_zone

    print(f"Events written to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--video", required=True)
    parser.add_argument("--output", default="data/generated_events.jsonl")
    parser.add_argument("--store-id", default="STORE_BLR_002")
    parser.add_argument("--camera-id", default="CAM_ENTRY_01")

    args = parser.parse_args()

    process_video(
        video_path=args.video,
        output_path=args.output,
        store_id=args.store_id,
        camera_id=args.camera_id
    )