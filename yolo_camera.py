import cv2
import json
from datetime import datetime
from ultralytics import YOLO
import numpy as np
import screeninfo

# --- Configuration ---
CONFIDENCE_THRESHOLD = 0.6 # Yolo needs a confidence of 60% to detect the confirm the object
RED_ZONE = {"x1": 200, "y1": 150, "x2": 450, "y2": 350}
MODEL_PATH = "yolov8n.pt" # YOLO model

# Load YOLO model
model = YOLO(MODEL_PATH)

# Initialize camera
cap = cv2.VideoCapture(0)
object_in_zone = False
alert_active = False
cleared_printed = True  # prevents CLEARED spam

# --- Camera info ---
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
fps  = cap.get(cv2.CAP_PROP_FPS)
print(f"[INFO] Camera default resolution: {width} x {height}")
print(f"[INFO] Default FPS: {fps}")

print("[INFO] Starting YOLO Red-Zone Monitor...")
print("[INFO] Press 'q' to quit.")

# --- Create adjustable window ---
WIN_NAME = "YOLO Red Zone"
cv2.namedWindow("YOLO Red Zone", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("YOLO Red Zone", cv2.WND_PROP_TOPMOST, 1)  # pop-up on top
cv2.moveWindow("YOLO Red Zone", 100, 80)  # where it appears
cv2.resizeWindow("YOLO Red Zone", 640, 480)  # initial window size (keeps quality sharp)

# Get screen resolution to center the live feed
monitor = screeninfo.get_monitors()[0]
screen_w, screen_h = monitor.width, monitor.height
target_w, target_h = 640, 480

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame.")
        break

    height, width = frame.shape[:2]

    # Draw red zone
    cv2.rectangle(frame,
                  (RED_ZONE["x1"], RED_ZONE["y1"]),
                  (RED_ZONE["x2"], RED_ZONE["y2"]),
                  (0, 0, 255), 3)

    # Run YOLO
    results = model(frame, verbose=False)
    detections_in_zone = []

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if conf < CONFIDENCE_THRESHOLD:
                continue

            # Object center
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Inside red zone?
            inside_zone = (
                RED_ZONE["x1"] <= cx <= RED_ZONE["x2"]
                and RED_ZONE["y1"] <= cy <= RED_ZONE["y2"]
            )

            # Yellow normally, green if inside red zone
            color = (0, 255, 255) if not inside_zone else (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.circle(frame, (cx, cy), 4, color, -1)

            if inside_zone:
                detections_in_zone.append({
                    "name": label,
                    "confidence": round(conf, 2),
                    "timestamp": timestamp,
                    "coords": (x1, y1, x2, y2)
                })

    object_in_zone = len(detections_in_zone) > 0

    # --- Red-zone entry/exit logic with coordinate and timestamp logging ---
    if object_in_zone:
        if not alert_active:
            alert_active = True
            cleared_printed = False
            t = datetime.now()

            # Entry log with full coordinate info
            alert = {
                "event": "Object ENTERED red zone",
                "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
                "objects": [{
                    "name": d["name"],
                    "confidence": d["confidence"],
                    "coords": d["coords"]
                } for d in detections_in_zone]
            }

            with open("yolo_redzone_log.txt", "a") as f:
                f.write(json.dumps(alert) + "\n")

            snap = f"redzone_capture_{t.strftime('%H%M%S')}.jpg"
            cv2.imwrite(snap, frame)
            print(f"[ALERT] Object entered red zone! Snapshot saved: {snap}")

    else:
        if alert_active:  # means object just left the zone
            t = datetime.now()

            # Exit log
            exit_event = {
                "event": "Object LEFT red zone",
                "timestamp": t.strftime("%Y-%m-%d %H:%M:%S")
            }

            with open("yolo_redzone_log.txt", "a") as f:
                f.write(json.dumps(exit_event) + "\n")

            print("[CLEARED] Object left red zone.")
            alert_active = False


    # Overlay info
    cv2.rectangle(frame, (0, 0), (width, 25), (0, 0, 0), -1)
    cv2.putText(frame, f"YOLO Red Zone Active - {datetime.now().strftime('%H:%M:%S')} (Press 'q' to quit)",
                (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # --- Create black background to center 640x480 feed ---
    canvas = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
    x_offset = (screen_w - target_w) // 2
    y_offset = (screen_h - target_h) // 2
    canvas[y_offset:y_offset + target_h, x_offset:x_offset + target_w] = cv2.resize(frame, (target_w, target_h))

    # Show live feed (resizable window)
    # ----- Letterbox center the 640x480 feed inside the current window -----
    target_w, target_h = 640, 480

    # Current window rectangle (x, y, w, h)
    _, _, win_w, win_h = cv2.getWindowImageRect(WIN_NAME)

    # Safety in case the window is minimized or returns 0
    win_w = max(win_w, 1)
    win_h = max(win_h, 1)

    # Create a black canvas matching the *current window* size
    canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)

    # If the window is smaller than 640x480, scale the preview down to fit;
    # otherwise keep it exactly 640x480.
    if win_w < target_w or win_h < target_h:
        scale = min(win_w / target_w, win_h / target_h)
        disp_w = max(1, int(target_w * scale))
        disp_h = max(1, int(target_h * scale))
    else:
        disp_w, disp_h = target_w, target_h

    preview = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_NEAREST)

    # Center the preview inside the window
    x0 = (win_w - disp_w) // 2
    y0 = (win_h - disp_h) // 2
    canvas[y0:y0+disp_h, x0:x0+disp_w] = preview

    cv2.imshow(WIN_NAME, canvas)


    # Quit key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
