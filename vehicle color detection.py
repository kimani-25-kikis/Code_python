import cv2
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "traffic.mp4"
MODEL_PATH = "yolo11n.pt"

CONFIDENCE = 0.40

VEHICLE_CLASSES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise FileNotFoundError(
        f"Could not open video: {VIDEO_PATH}"
    )


def detect_color(image):

    if image.size == 0:
        return "Unknown"

    image = cv2.resize(
        image,
        (100, 100)
    )

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )

    pixels = hsv.reshape(-1, 3)

    h = pixels[:, 0]
    s = pixels[:, 1]
    v = pixels[:, 2]

    valid = (
        (s > 40) &
        (v > 40)
    )

    h = h[valid]
    s = s[valid]
    v = v[valid]

    if len(h) == 0:
        return "Black"

    average_saturation = np.mean(s)
    average_value = np.mean(v)

    if average_value < 60:
        return "Black"

    if average_value > 190 and average_saturation < 50:
        return "White"

    if average_saturation < 60:
        if average_value < 130:
            return "Gray"
        return "Silver"

    red = (
        (h < 10) |
        (h > 170)
    )

    orange = (
        (h >= 10) &
        (h < 20)
    )

    yellow = (
        (h >= 20) &
        (h < 35)
    )

    green = (
        (h >= 35) &
        (h < 85)
    )

    blue = (
        (h >= 85) &
        (h < 130)
    )

    purple = (
        (h >= 130) &
        (h < 160)
    )

    pink = (
        (h >= 160) &
        (h <= 170)
    )

    color_counts = {
        "Red": np.sum(red),
        "Orange": np.sum(orange),
        "Yellow": np.sum(yellow),
        "Green": np.sum(green),
        "Blue": np.sum(blue),
        "Purple": np.sum(purple),
        "Pink": np.sum(pink)
    }

    return max(
        color_counts,
        key=color_counts.get
    )


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

            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            vehicle = frame[
                y1:y2,
                x1:x2
            ]

            color = detect_color(
                vehicle
            )

            vehicle_type = VEHICLE_CLASSES.get(
                class_id,
                "Unknown"
            )

            label = (
                f"{vehicle_type} "
                f"ID:{track_id} "
                f"Color:{color}"
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
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

    cv2.imshow(
        "Vehicle Color Detection",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()

cv2.destroyAllWindows()