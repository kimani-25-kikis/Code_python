import cv2
import csv
import os
import easyocr
from datetime import datetime
from ultralytics import YOLO

VIDEO_PATH = "traffic.mp4"
VEHICLE_MODEL = "yolo11n.pt"
PLATE_MODEL = "license_plate.pt"

CONFIDENCE = 0.40
PLATE_CONFIDENCE = 0.35
LINE_POSITION = 0.60

VEHICLE_CLASSES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

vehicle_model = YOLO(VEHICLE_MODEL)
plate_model = YOLO(PLATE_MODEL)

reader = easyocr.Reader(["en"])

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise FileNotFoundError(
        f"Could not open video: {VIDEO_PATH}"
    )

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

if fps <= 0:
    fps = 30

counting_line_y = int(height * LINE_POSITION)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

out = cv2.VideoWriter(
    "vehicle_counted.mp4",
    fourcc,
    fps,
    (width, height)
)

vehicle_counts = {
    "Car": 0,
    "Motorcycle": 0,
    "Bus": 0,
    "Truck": 0
}

total_count = 0

previous_positions = {}
counted_ids = set()
plate_results = {}

csv_file = "vehicle_counts.csv"
csv_exists = os.path.exists(csv_file)

csv_output = open(
    csv_file,
    "a",
    newline="",
    encoding="utf-8"
)

csv_writer = csv.writer(csv_output)

if not csv_exists:
    csv_writer.writerow([
        "Timestamp",
        "Vehicle ID",
        "Vehicle Type",
        "License Plate",
        "Direction"
    ])

while True:

    ret, frame = cap.read()

    if not ret:
        break

    results = vehicle_model.track(
        frame,
        persist=True,
        conf=CONFIDENCE,
        classes=list(VEHICLE_CLASSES.keys()),
        tracker="bytetrack.yaml",
        verbose=False
    )

    if results[0].boxes.id is not None:

        boxes = results[0].boxes.xyxy.cpu().numpy()
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)

        for box, class_id, track_id in zip(
            boxes,
            class_ids,
            track_ids
        ):

            x1, y1, x2, y2 = map(int, box)

            vehicle_type = VEHICLE_CLASSES.get(
                class_id,
                "Unknown"
            )

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            previous_y = previous_positions.get(
                track_id,
                center_y
            )

            vehicle_crop = frame[
                max(0, y1):min(height, y2),
                max(0, x1):min(width, x2)
            ]

            if vehicle_crop.size > 0:

                plate_detections = plate_model(
                    vehicle_crop,
                    conf=PLATE_CONFIDENCE,
                    verbose=False
                )

                for plate_result in plate_detections:

                    if plate_result.boxes is None:
                        continue

                    for plate_box in plate_result.boxes.xyxy.cpu().numpy():

                        px1, py1, px2, py2 = map(
                            int,
                            plate_box
                        )

                        plate_crop = vehicle_crop[
                            max(0, py1):min(
                                vehicle_crop.shape[0],
                                py2
                            ),
                            max(0, px1):min(
                                vehicle_crop.shape[1],
                                px2
                            )
                        ]

                        if plate_crop.size == 0:
                            continue

                        gray = cv2.cvtColor(
                            plate_crop,
                            cv2.COLOR_BGR2GRAY
                        )

                        gray = cv2.resize(
                            gray,
                            None,
                            fx=2,
                            fy=2,
                            interpolation=cv2.INTER_CUBIC
                        )

                        text_results = reader.readtext(
                            gray,
                            detail=0
                        )

                        if text_results:

                            plate_text = "".join(
                                text_results
                            )

                            plate_text = (
                                plate_text
                                .upper()
                                .replace(" ", "")
                                .replace("-", "")
                            )

                            plate_results[
                                track_id
                            ] = plate_text

                        cv2.rectangle(
                            frame,
                            (
                                x1 + px1,
                                y1 + py1
                            ),
                            (
                                x1 + px2,
                                y1 + py2
                            ),
                            (255, 0, 255),
                            2
                        )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (0, 0, 255),
                -1
            )

            plate_text = plate_results.get(
                track_id,
                "Scanning..."
            )

            label = (
                f"{vehicle_type} "
                f"ID:{track_id} "
                f"Plate:{plate_text}"
            )

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2
            )

            crossed_line = (
                previous_y < counting_line_y
                and center_y >= counting_line_y
            )

            if (
                crossed_line
                and track_id not in counted_ids
            ):

                counted_ids.add(track_id)

                vehicle_counts[
                    vehicle_type
                ] += 1

                total_count += 1

                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                plate_text = plate_results.get(
                    track_id,
                    "Not detected"
                )

                csv_writer.writerow([
                    timestamp,
                    track_id,
                    vehicle_type,
                    plate_text,
                    "DOWN"
                ])

                csv_output.flush()

                print(
                    f"{vehicle_type} | "
                    f"ID: {track_id} | "
                    f"Plate: {plate_text}"
                )

            previous_positions[
                track_id
            ] = center_y

    cv2.line(
        frame,
        (0, counting_line_y),
        (width, counting_line_y),
        (255, 0, 0),
        3
    )

    cv2.putText(
        frame,
        "COUNTING LINE",
        (20, counting_line_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 0, 0),
        2
    )

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (10, 10),
        (350, 190),
        (0, 0, 0),
        -1
    )

    frame = cv2.addWeighted(
        overlay,
        0.65,
        frame,
        0.35,
        0
    )

    cv2.putText(
        frame,
        "VEHICLE COUNTER",
        (25, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Cars: {vehicle_counts['Car']}",
        (25, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Motorcycles: {vehicle_counts['Motorcycle']}",
        (25, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Buses: {vehicle_counts['Bus']}",
        (25, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Trucks: {vehicle_counts['Truck']}",
        (25, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"TOTAL: {total_count}",
        (width - 250, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 255),
        3
    )

    cv2.imshow(
        "Vehicle and License Plate Detection",
        frame
    )

    out.write(frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
out.release()
csv_output.close()
cv2.destroyAllWindows()

print("\nVehicle Counting Complete")
print(f"Cars: {vehicle_counts['Car']}")
print(f"Motorcycles: {vehicle_counts['Motorcycle']}")
print(f"Buses: {vehicle_counts['Bus']}")
print(f"Trucks: {vehicle_counts['Truck']}")
print(f"Total: {total_count}")