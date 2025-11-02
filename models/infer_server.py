from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image, ImageDraw
import base64
import io
import os
import uvicorn
import cv2
import numpy as np


class DetectReq(BaseModel):
    image_b64: str
    target: str
    threshold: float = 0.25  # Lower default threshold for better detection


app = FastAPI(title="Infer Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

import os
# Explicitly load COCO and custom model from fixed paths
COCO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "yolov8n.pt")
CUSTOM_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "runs", "detect", "elevator_sign_yolov8n", "weights", "best.pt")

try:
    coco_model = YOLO(COCO_MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load COCO model from {COCO_MODEL_PATH}: {e}")
try:
    custom_model = YOLO(CUSTOM_MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load custom model from {CUSTOM_MODEL_PATH}: {e}")

# Per-model default confidence thresholds (can be overridden via env)
COCO_CONF_THRESH = float(os.environ.get("COCO_CONF_THRESH", "0.25"))
CUSTOM_CONF_THRESH = float(os.environ.get("CUSTOM_CONF_THRESH", "0.25"))


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/detect")
def detect(req: DetectReq):
    try:
        img_bytes = base64.b64decode(req.image_b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid image_b64")

    # (debug image saving removed)

    req_conf = float(req.threshold)
    target_lower = req.target.lower().strip()

    results_coco = None
    results_custom = None

    # Only use COCO model for non-elevator targets
    if target_lower != "elevator":
        coco_conf = max(req_conf, COCO_CONF_THRESH)
        try:
            results_coco = coco_model.predict(img, verbose=False, conf=coco_conf)[0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"coco infer failed: {e}")
    
    # Always use custom model for elevator target
    if target_lower == "elevator":
        custom_conf = max(req_conf, CUSTOM_CONF_THRESH)
        try:
            results_custom = custom_model.predict(img, verbose=False, conf=custom_conf)[0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"custom model infer failed: {e}")

    def extract(results):
        out = []
        if results is None:
            return out
        names = results.names
        boxes = getattr(results, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return out
        for i in range(len(boxes)):
            try:
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                x1, y1, x2, y2 = map(float, boxes.xyxy[i].tolist())
                label = names.get(cls_id, str(cls_id))
                out.append({"label": label, "conf": conf, "box": [x1, y1, x2, y2]})
            except Exception:
                continue
        return out

    # Extract detections from the appropriate model based on target
    detections = []
    if target_lower == "elevator":
        detections = extract(results_custom)  # Only use custom model for elevators
    else:
        detections = extract(results_coco)    # Only use COCO model for other targets

    # Apply confidence threshold based on which model was used
    threshold = max(req_conf, CUSTOM_CONF_THRESH if target_lower == "elevator" else COCO_CONF_THRESH)
    filtered_dets = [d for d in detections if d.get("conf", 0.0) >= threshold]
    dets = filtered_dets

    # simple duplicate suppression: keep highest-confidence detection for same label with IoU > 0.5
    def iou(boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interW = max(0.0, xB - xA)
        interH = max(0.0, yB - yA)
        interArea = interW * interH
        boxAArea = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
        boxBArea = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])
        denom = boxAArea + boxBArea - interArea
        if denom <= 0:
            return 0.0
        return interArea / denom

    dets.sort(key=lambda x: x.get("conf", 0.0), reverse=True)
    kept = []
    iou_thresh = 0.5
    for d in dets:
        box = d["box"]
        label = d["label"].lower()
        dup = False
        for k in kept:
            if k["label"].lower() == label and iou(k["box"], box) > iou_thresh:
                dup = True
                break
        if not dup:
            kept.append(d)

    detections = kept
    found = any(det["label"].lower() == req.target.lower() for det in detections)

    # 生成带框预览图片
    preview_img = img.copy()
    draw = ImageDraw.Draw(preview_img)
    for det in detections:
        box = det["box"]
        label = det["label"]
        conf = det["conf"]
        x1, y1, x2, y2 = box
        # 画框
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
        # 画标签
        draw.text((x1, y1 - 12), f"{label} {conf:.2f}", fill="red")
    # 转 PNG base64
    print("[detect] returning preview_b64", flush=True)
    buf = io.BytesIO()
    preview_img.save(buf, format="PNG")
    preview_b64 = base64.b64encode(buf.getvalue()).decode()
    return {
        "found": found,
        "detections": detections,
        "preview_b64": preview_b64,
        "backend_version": "with_preview"
    }


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("infer_server:app", host=host, port=port, reload=False)
