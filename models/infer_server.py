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

# 模型加载（首启会下载权重）
MODEL_PATH = os.environ.get("MODEL_PATH", "yolov8n.pt")
# Load two models: COCO official model and an optional custom trained model
COCO_MODEL_PATH = os.environ.get("COCO_MODEL_PATH", MODEL_PATH)
CUSTOM_MODEL_PATH = os.environ.get(
    "CUSTOM_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "..", "runs", "detect", "elevator_sign_yolov8n", "weights", "best.pt"),
)

# Load models once at startup
try:
    coco_model = YOLO(COCO_MODEL_PATH)
except Exception:
    coco_model = YOLO(MODEL_PATH)

try:
    custom_model = YOLO(CUSTOM_MODEL_PATH)
except Exception:
    custom_model = None

# Per-model default confidence thresholds (can be overridden via env)
COCO_CONF_THRESH = float(os.environ.get("COCO_CONF_THRESH", "0.25"))
CUSTOM_CONF_THRESH = float(os.environ.get("CUSTOM_CONF_THRESH", "0.5"))


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

    # Run inference on COCO model and (optionally) the custom model, then merge results
    try:
        results_coco = coco_model.predict(img, verbose=False)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"coco infer failed: {e}")

    results_custom = None
    if custom_model is not None:
        try:
            results_custom = custom_model.predict(img, verbose=False)[0]
        except Exception:
            results_custom = None

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

    # extract separately and apply per-model thresholds
    dets_coco = extract(results_coco)
    dets_custom = extract(results_custom)

    # request-level threshold (acts as minimum on top of model defaults)
    req_conf = float(req.threshold)

    filtered_coco = [d for d in dets_coco if d.get("conf", 0.0) >= max(req_conf, COCO_CONF_THRESH)]
    filtered_custom = [d for d in dets_custom if d.get("conf", 0.0) >= max(req_conf, CUSTOM_CONF_THRESH)]

    dets = filtered_coco + filtered_custom

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

    # (annotated debug image saving removed)
    
    return {"found": found, "detections": detections}


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("infer_server:app", host=host, port=port, reload=False)
