import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# 使用脚本所在目录作为基准，避免绝对路径在不同机器/账号失效
BASE = Path(__file__).resolve().parent
SRC_DIR = BASE / 'elevatorSigns-3' / 'train' / 'images'
DST_DIR = SRC_DIR.parent / 'images_gray'

DST_DIR.mkdir(parents=True, exist_ok=True)

for fname in tqdm(os.listdir(SRC_DIR)):
    if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
        img = Image.open(SRC_DIR / fname).convert('L')  # 转灰度
        img.save(DST_DIR / fname)

print(f'已批量生成灰度图片到 {DST_DIR}')
