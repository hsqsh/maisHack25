from roboflow import Roboflow

# 用你的 Roboflow API Key
rf = Roboflow(api_key="J4oKSy5NP0X9LmkzVyTV")
# elevator signs 项目名和版本号
project = rf.workspace().project("elevatorsigns-oarrx")
version = project.version(3)  # 可根据需要换成你想要的版本号
# 下载为 YOLOv8 格式
version.download("yolov8")

print("数据集下载完成，已解压到 elevatorsigns-3/ 目录")
