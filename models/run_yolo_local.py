import argparse
import os
import time
import platform
from typing import List, Optional, Tuple

from ultralytics import YOLO
from PIL import Image
import cv2
import numpy as np
import signal

# Minimal local runner: no servers, no networking.
# Usage examples:
#   python models/run_yolo_local.py --image docs/test.jpg --target bottle --threshold 0.4
#   python models/run_yolo_local.py --webcam 0 --target person --threshold 0.4
#   python models/run_yolo_local.py --webcam -1 --target person --threshold 0.4 --no-display


def draw_boxes(img_bgr: np.ndarray, detections: List[dict]) -> np.ndarray:
    for det in detections:
        x1, y1, x2, y2 = map(int, det["box"])  # [x1,y1,x2,y2]
        label = f"{det['label']} {det['conf']*100:.0f}%"
        color = (0, 255, 136)
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img_bgr, (x1, y1 - th - 6), (x1 + tw + 6, y1), (0, 0, 0), -1)
        cv2.putText(img_bgr, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return img_bgr


def infer_on_pil(model: YOLO, pil_img: Image.Image, target: str, threshold: float) -> Tuple[bool, List[dict]]:
    # Use Ultralytics predict API; pass conf to reduce post-filter work
    results = model.predict(pil_img, verbose=False, conf=threshold)[0]
    detections, found = [], False
    names = results.names
    boxes = getattr(results, "boxes", None)
    if boxes is not None and len(boxes) > 0:
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            label = names.get(cls_id, str(cls_id))
            x1, y1, x2, y2 = map(float, boxes.xyxy[i].tolist())
            detections.append({"label": label, "conf": conf, "box": [x1, y1, x2, y2]})
            if label.lower() == target.lower():
                found = True
    return found, detections

def infer_on_pil_dual(pil_img: Image.Image, target: str, threshold: float, model_coco: YOLO, model_custom: YOLO) -> Tuple[bool, List[dict]]:
    # 先用 COCO 模型
    found_coco, det_coco = infer_on_pil(model_coco, pil_img, target, threshold)
    # 再用自定义模型
    found_custom, det_custom = infer_on_pil(model_custom, pil_img, target, threshold)
    # 合并结果
    found = found_coco or found_custom
    detections = det_coco + det_custom
    return found, detections


def run_image(image_path: str, target: str, threshold: float, save_path: Optional[str]):
    pil_img = Image.open(image_path).convert("RGB")
    # 加载两个模型
    model_coco = YOLO(os.path.join(os.path.dirname(__file__), "..", "yolov8n.pt"))
    model_custom = YOLO(os.path.join(os.path.dirname(__file__), "..", "runs", "detect", "elevator_sign_yolov8n", "weights", "best.pt"))
    found, detections = infer_on_pil_dual(pil_img, target, threshold, model_coco, model_custom)
    print({"found": found, "detections": detections})
    if save_path:
        # draw and save
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        img_bgr = draw_boxes(img_bgr, detections)
        cv2.imwrite(save_path, img_bgr)
        print(f"annotated saved to {save_path}")


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def try_open_camera(idx: int) -> Optional[cv2.VideoCapture]:
    """Try opening camera with a preferred backend on Windows (DirectShow).
    Returns cv2.VideoCapture if opened, else None.
    """
    cap = None
    if is_windows():
        # Prefer DirectShow on Windows for better device compatibility
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(idx)
    if cap is not None and cap.isOpened():
        return cap
    if cap is not None:
        cap.release()
    return None


def autoscan_camera(max_indices: int = 6) -> Tuple[int, cv2.VideoCapture]:
    """Scan camera indices [0..max_indices) and return the first available."""
    for idx in range(max_indices):
        cap = try_open_camera(idx)
        if cap is not None:
            return idx, cap
    raise RuntimeError(f"No available webcam found (scanned indices 0..{max_indices-1}).")


_STOP_REQUESTED = False


def _on_signal(signum, frame):
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def run_webcam(
    cam_index: int,
    target: str,
    threshold: float,
    no_display: bool = False,
    max_seconds: float = 0.0,
    max_frames: int = 0,
):
    # Auto-scan when cam_index == -1
    if cam_index == -1:
        print("[yolo-local] Auto-scanning webcams... (0-5)")
        idx, cap = autoscan_camera(6)
        print(f"[yolo-local] Using webcam index {idx}")
    else:
        cap = try_open_camera(cam_index)
        if cap is None:
            raise RuntimeError(f"Cannot open webcam {cam_index}")

    # 加载两个模型
    model_coco = YOLO(os.path.join(os.path.dirname(__file__), "..", "yolov8n.pt"))
    model_custom = YOLO(os.path.join(os.path.dirname(__file__), "..", "runs", "detect", "elevator_sign_yolov8n", "weights", "best.pt"))

    last_log = 0.0
    start_time = time.time()
    frame_count = 0
    window_name = "YOLOv8 Local"

    # Setup signal handlers to allow Ctrl+C exits
    try:
        signal.signal(signal.SIGINT, _on_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _on_signal)
    except Exception:
        pass  # not fatal on Windows/IDEs

    try:
        while True:
            if _STOP_REQUESTED:
                print("[yolo-local] Stop requested, exiting loop...")
                break

            # Time/frame limits for auto-exit
            if max_seconds > 0 and (time.time() - start_time) >= max_seconds:
                print(f"[yolo-local] Reached max_seconds={max_seconds}, exiting...")
                break
            if max_frames > 0 and frame_count >= max_frames:
                print(f"[yolo-local] Reached max_frames={max_frames}, exiting...")
                break

            ok, frame = cap.read()
            if not ok:
                break
            frame_count += 1
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            found, detections = infer_on_pil_dual(pil_img, target, threshold, model_coco, model_custom)
            if not no_display:
                vis = draw_boxes(frame.copy(), detections)
                if found:
                    cv2.putText(vis, f"FOUND {target}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                if frame_count == 1:
                    print("[yolo-local] Press 'q', ESC, Enter, or x in the window to quit. Ctrl+C also works.")
                cv2.imshow(window_name, vis)
                # Robust window closed check
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        print("[yolo-local] Window closed, exiting...")
                        break
                except Exception:
                    print("[yolo-local] Window property check failed, exiting...")
                    break
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q'), 13, ord('x')):  # ESC, q, Enter, x to quit
                    break
            # Throttled log when found
            if found and (time.time() - last_log) > 1.0:
                last_log = time.time()
                print(f"FOUND {target} @ {time.strftime('%H:%M:%S')}")
    finally:
        try:
            cap.release()
        except Exception:
            pass
        if not no_display:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Local YOLOv8 runner without any server")
    parser.add_argument("--target", default="bottle")
    parser.add_argument("--threshold", type=float, default=0.4)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--image", help="path to an input image")
    g.add_argument("--webcam", type=int, help="webcam index, e.g., 0; use -1 to auto-scan")
    parser.add_argument("--save", help="path to save annotated image (image mode only)")
    parser.add_argument("--no-display", action="store_true", help="Do not open any window; only print logs")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="Auto-quit after N seconds (0 = no limit)")
    parser.add_argument("--max-frames", type=int, default=0, help="Auto-quit after N frames (0 = no limit)")
    args = parser.parse_args()

    if args.image:
        run_image(args.image, args.target, args.threshold, args.save)
    else:
        run_webcam(
            args.webcam,
            args.target,
            args.threshold,
            no_display=args.no_display,
            max_seconds=args.max_seconds,
            max_frames=args.max_frames,
        )


if __name__ == "__main__":
    main()
