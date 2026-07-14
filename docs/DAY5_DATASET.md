# Day5 数据集说明：PCB 缺陷检测数据集

## 1. 数据集方向

本项目选择题目为：

```text
P12：PCB 缺陷检测系统
```

项目方向从通用目标检测平台切换为 PCB 工业质检场景。后续模型训练、检测任务、检测结果分析和智能体问答均围绕 PCB 缺陷检测展开。

---

## 2. 数据集来源

本项目使用 PCB 缺陷检测数据集，该数据集包含 PCB 图像以及对应的 YOLO 格式标注文件。

数据集特点如下：

```text
任务类型：目标检测
标注格式：YOLO TXT
缺陷类别：6 类
数据划分：train / val / test
```

本数据集已经是 YOLO 标注格式，因此当前项目不需要进行 VOC、COCO 或 LabelMe 到 YOLO 的格式转换。

---

## 3. 本地数据集路径

原始下载数据位于：

```text
datasets/raw/pcb-defect-dataset
```

整理后的正式训练数据位于：

```text
datasets/pcb_defect
```

正式数据集结构如下：

```text
datasets/pcb_defect/
├── train/
│   ├── images/
│   └── labels/
├── val/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml
```

其中：

```text
images/     存放 PCB 图像
labels/     存放 YOLO TXT 标注文件
data.yaml   YOLOv11 训练配置文件
```

---

## 4. 数据集数量统计

当前数据集数量如下：

```text
train images: 8534
train labels: 8534

val images: 1066
val labels: 1066

test images: 1068
test labels: 1068
```

总图片数量为：

```text
8534 + 1066 + 1068 = 10668 张
```

数据集数量远超过 Day5 要求的至少 100 张图像，满足后续 YOLOv11 模型训练需求。

---

## 5. PCB 缺陷类别

本项目使用的数据集包含 6 类 PCB 缺陷。

类别编号如下：

```text
0 mouse_bite        鼠咬
1 spur              毛刺
2 missing_hole      缺孔
3 short             短路
4 open_circuit      开路
5 spurious_copper   多余铜
```

该类别顺序必须与 `data.yaml` 和 YOLO 标注文件中的 `class_id` 保持一致。

后续模型训练、推理结果解析、前端检测结果展示和智能体分析，都必须使用这一类别顺序。

---

## 6. YOLO 标注格式说明

YOLO 目标检测标注采用 TXT 格式。

每一张图片对应一个同名 `.txt` 标注文件。

例如：

```text
train/images/xxx.jpg
train/labels/xxx.txt
```

YOLO 标注文件中，每一行代表一个目标框，格式为：

```text
class_id x_center y_center width height
```

其中：

```text
class_id   类别编号，从 0 开始
x_center   目标框中心点 x 坐标，已归一化
y_center   目标框中心点 y 坐标，已归一化
width      目标框宽度，已归一化
height     目标框高度，已归一化
```

后四个坐标值均应位于 0 到 1 之间。

例如：

```text
3 0.512500 0.438333 0.065000 0.073333
```

表示该图像中存在一个类别编号为 `3` 的缺陷目标，也就是 `short` 短路缺陷。

---

## 7. data.yaml 配置

本项目正式使用的 `data.yaml` 内容如下：

```yaml
path: D:/实习/rsod-agent-platform/datasets/pcb_defect
train: train/images
val: val/images
test: test/images

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
```

该文件用于后续 YOLOv11 模型训练。

后续训练命令中会指定：

```powershell
yolo detect train data=datasets/pcb_defect/data.yaml model=yolo11n.pt epochs=50 imgsz=640
```

Day5 阶段只完成数据集准备，暂不进行正式模型训练。

---

## 8. 数据集检查脚本

项目中新增数据集检查脚本：

```text
scripts/check_yolo_dataset.py
```

运行方式：

```powershell
python scripts/check_yolo_dataset.py
```

该脚本用于检查：

```text
1. images 和 labels 数量是否一致
2. 图片是否缺少对应 txt 标注
3. txt 标注是否有多余文件
4. 每一行标注字段数量是否为 5
5. class_id 是否在合法范围内
6. 坐标是否在 0 到 1 之间
7. width 和 height 是否大于 0
```

数据集检查脚本可以保证后续 YOLOv11 训练前，数据集目录结构和标注格式基本正确。

---

## 9. 格式转换说明

Day5 中学习了 YOLO、VOC、COCO、LabelMe 等常见目标检测标注格式。

本项目当前使用的数据集已经是 YOLO TXT 格式，因此本阶段不需要实际执行格式转换。

如果后续更换数据集，可能需要实现：

```text
VOC XML       → YOLO TXT
COCO JSON     → YOLO TXT
LabelMe JSON  → YOLO TXT
```

当前阶段的重点是对已有 YOLO 数据集进行目录整理、类别确认、`data.yaml` 生成和数据合法性检查。

---

## 10. 数据集检查结果

当前数据集已经完成数量检查，结果如下：

```text
train images: 8534
train labels: 8534

val images: 1066
val labels: 1066

test images: 1068
test labels: 1068
```

检查结果说明：

```text
1. train、val、test 三个数据划分均存在
2. 每个划分下均包含 images 和 labels
3. 图片数量与标签数量一一对应
4. 数据集总图片数量为 10668 张
5. 数据量满足 Day5 要求
```

---

## 11. Git 提交说明

数据集图片和标签数量较多，不提交到 GitHub。

不应提交：

```text
datasets/raw/
datasets/pcb_defect/train/
datasets/pcb_defect/val/
datasets/pcb_defect/test/
```

可以提交：

```text
docs/DAY5_DATASET.md
scripts/check_yolo_dataset.py
README.md
datasets/pcb_defect/data.yaml
```

其中 `datasets/pcb_defect/data.yaml` 文件较小，可以提交，用于说明数据集结构和类别配置。

---

## 12. Day5 阶段结论

截至 Day5，项目已经完成 PCB 缺陷检测数据集准备工作：

```text
已确定 P12 PCB 缺陷检测方向
已下载 PCB 缺陷检测 YOLO 数据集
已整理正式数据集目录 datasets/pcb_defect
已生成 YOLOv11 训练配置文件 data.yaml
已确认 train / val / test 数据划分
已确认 images 与 labels 一一对应
已确定 6 类 PCB 缺陷类别
已完成数据集合法性检查脚本
```

后续 Day6 可以开始进行 YOLOv11 模型训练。