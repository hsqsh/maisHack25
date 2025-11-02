from ultralytics import YOLO
from pathlib import Path

DATA_YAML = (Path(__file__).resolve().parent / "elevatorSigns-3" / "data.yaml")

def train_elevator_sign():
    model = YOLO('yolov8n.pt')  # 用 nano 版，训练快
    results = model.train(
        data=str(DATA_YAML),
        epochs=12,                # 稍多一点，提升泛化
        imgsz=640,
        batch=8,
        name='elevator_sign_yolov8n',
        degrees=15,        # 随机旋转±15°
        scale=0.5,         # 随机缩放0.5倍
        shear=5,           # 随机剪切±5°
        perspective=0.001, # 轻微透视变换
        flipud=0.2,        # 20%概率上下翻转
        fliplr=0.6,        # 60%概率左右翻转
        mosaic=True,       # 启用 mosaic 增强
        mixup=0.2,         # 20%概率 mixup
        hsv_h=0.02,        # 色调扰动
        hsv_s=0.7,         # 饱和度扰动
        hsv_v=0.4          # 亮度扰动
    )
    print("Training complete. Best weights:", results.best)

if __name__ == '__main__':
    train_elevator_sign()
