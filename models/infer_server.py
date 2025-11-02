from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image
import base64
import io
import os
import uvicorn


class DetectReq(BaseModel):
    image_b64: str
    target: str
    threshold: float = 0.4


app = FastAPI(title="Infer Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# 模型加载（首启会下载权重）
MODEL_PATH = os.environ.get("MODEL_PATH", "yolov8n.pt")
model = YOLO(MODEL_PATH)


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

    # Save the last received image for debugging (models/last_received.jpg)
    try:
        save_dir = os.path.dirname(__file__)
        save_path = os.path.join(save_dir, "last_received.jpg")
        with open(save_path, "wb") as f:
            f.write(img_bytes)
    except Exception:
        # non-fatal
        pass

    try:
        results = model.predict(img, verbose=False)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"infer failed: {e}")

    detections = []
    found = False
    names = results.names
    boxes = getattr(results, "boxes", None)

    if boxes is not None and len(boxes) > 0:
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            if conf < req.threshold:
                continue
            label = names.get(cls_id, str(cls_id))
            x1, y1, x2, y2 = map(float, boxes.xyxy[i].tolist())
            detections.append({"label": label, "conf": conf, "box": [x1, y1, x2, y2]})
            if label.lower() == req.target.lower():
                found = True

    return {"found": found, "detections": detections}


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("infer_server:app", host=host, port=port, reload=False)
