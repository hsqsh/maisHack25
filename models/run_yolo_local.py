import argparse
import os
from ultralytics import YOLO
from PIL import Image
import cv2
import numpy as np

# Minimal local runner: no servers, no networking.
# Usage examples:
#   python models/run_yolo_local.py --image docs/test.jpg --target bottle --threshold 0.4
#   python models/run_yolo_local.py --webcam 0 --target person --threshold 0.4


def draw_boxes(img_bgr, detections):
    for det in detections:
        x1, y1, x2, y2 = map(int, det["box"])  # [x1,y1,x2,y2]
        label = f"{det['label']} {det['conf']*100:.0f}%"
        color = (0, 255, 136)
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img_bgr, (x1, y1 - th - 6), (x1 + tw + 6, y1), (0, 0, 0), -1)
        cv2.putText(img_bgr, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return img_bgr


def infer_on_pil(model, pil_img, target: str, threshold: float):
    results = model.predict(pil_img, verbose=False)[0]
    detections, found = [], False
    names = results.names
    boxes = getattr(results, "boxes", None)
    if boxes is not None and len(boxes) > 0:
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            if conf < threshold:
                continue
            label = names.get(cls_id, str(cls_id))
            x1, y1, x2, y2 = map(float, boxes.xyxy[i].tolist())
            detections.append({"label": label, "conf": conf, "box": [x1, y1, x2, y2]})
            if label.lower() == target.lower():
                found = True
    return found, detections


def run_image(model, image_path: str, target: str, threshold: float, save_path: str | None):
    pil_img = Image.open(image_path).convert("RGB")
    found, detections = infer_on_pil(model, pil_img, target, threshold)
    print({"found": found, "detections": detections})
    if save_path:
        # draw and save
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        img_bgr = draw_boxes(img_bgr, detections)
        cv2.imwrite(save_path, img_bgr)
        print(f"annotated saved to {save_path}")


def run_webcam(model, cam_index: int, target: str, threshold: float):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open webcam {cam_index}")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            found, detections = infer_on_pil(model, pil_img, target, threshold)
            vis = draw_boxes(frame.copy(), detections)
            if found:
                cv2.putText(vis, f"FOUND {target}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("YOLOv8 Local", vis)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Local YOLOv8 runner without any server")
    parser.add_argument("--model", default=os.environ.get("MODEL_PATH", "yolov8n.pt"))
    parser.add_argument("--target", default="bottle")
    parser.add_argument("--threshold", type=float, default=0.4)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--image", help="path to an input image")
    g.add_argument("--webcam", type=int, help="webcam index, e.g., 0")
    parser.add_argument("--save", help="path to save annotated image (image mode only)")
    args = parser.parse_args()

    model = YOLO(args.model)

    if args.image:
        run_image(model, args.image, args.target, args.threshold, args.save)
    else:
        run_webcam(model, args.webcam, args.target, args.threshold)


if __name__ == "__main__":
    main()
