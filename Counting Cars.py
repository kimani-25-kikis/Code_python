import cv2
from ultralytics import YOLO
from datetime import datetime
import csv
import os

VIDEO_PATH = "traffic.mp4"
MODEL_PATH = "yolo11n.pt"
CONFIDENCE = 0.40
LINE_POSITION = 0.60

VEHICLE_CLASSES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise FileNotFoundError(f"Could not open video: {VIDEO_PATH}")

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
        "Direction"
    ])

while True:
    ret, frame = cap.read()

    if not ret:
        break

    results = model.track(
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

            label = f"{vehicle_type} ID:{track_id}"

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

            crossed_line = (
                previous_y < counting_line_y
                and center_y >= counting_line_y
            )

            if crossed_line and track_id not in counted_ids:
                counted_ids.add(track_id)
                vehicle_counts[vehicle_type] += 1
                total_count += 1

                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                csv_writer.writerow([
                    timestamp,
                    track_id,
                    vehicle_type,
                    "DOWN"
                ])

                csv_output.flush()

            previous_positions[track_id] = center_y

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
        (330, 180),
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
        f"Cars:        {vehicle_counts['Car']}",
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
        f"Buses:       {vehicle_counts['Bus']}",
        (25, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Trucks:      {vehicle_counts['Truck']}",
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
        "Advanced Vehicle Counter",
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