import cv2
from ultralytics import YOLO

VIDEO_PATH = "traffic.mp4"
MODEL_PATH = "yolo11n.pt"

CONFIDENCE = 0.40

VEHICLE_CLASSES = {
    2: "Saloon Car",
    7: "Truck"
}

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise FileNotFoundError(
        f"Could not open video: {VIDEO_PATH}"
    )

saloon_count = 0
truck_count = 0

counted_ids = set()

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

            x1, y1, x2, y2 = map(
                int,
                box
            )

            vehicle_type = VEHICLE_CLASSES.get(
                class_id
            )

            if track_id not in counted_ids:

                counted_ids.add(track_id)

                if vehicle_type == "Saloon Car":
                    saloon_count += 1

                elif vehicle_type == "Truck":
                    truck_count += 1

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"{vehicle_type} ID:{track_id}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    cv2.rectangle(
        frame,
        (10, 10),
        (300, 100),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        frame,
        f"Saloon Cars: {saloon_count}",
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Trucks: {truck_count}",
        (25, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "Saloon Cars and Trucks",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("================================")
print("VEHICLE COUNT")
print("================================")
print(f"Saloon Cars: {saloon_count}")
print(f"Trucks:      {truck_count}")
print("================================")