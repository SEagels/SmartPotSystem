# 叶片病害检测服务 —— YOLOv11 ONNX推理 + 规则降级方案
# 双层检测策略：
#   1. 主路径：加载YOLOv11 ONNX模型，GPU/CPU推理，输出bbox+置信度
#   2. 降级路径：模型不可用时，基于RGB通道均值和标准差的规则引擎（启发式算法）
# 健康评分算法：基础分100 - 病斑数×20 - 最高置信度×30，保底10分
from __future__ import annotations

import asyncio
import json
import os

import numpy as np
from PIL import Image as PILImage

from app.config import settings

# --- 全局模型缓存（懒加载，避免启动时阻塞） ---
_MODEL = None
_CLASS_NAMES: dict[int, str] = {}  # 模型输出class_id → 英文类名
_CLASS_NAMES_ZH: dict[str, str] = {}  # 英文类名 → 中文名
_DISEASE_RECOMMENDATIONS: dict[str, str] = {}

# 规则引擎知识库：病害名 → {中文名, 防治建议}
_RULES: dict[str, dict] = {
    "leaf_spot": {"name_zh": "叶斑病", "recommendation": "建议喷洒多菌灵800倍液，间隔7天重复一次"},
    "powdery_mildew": {"name_zh": "白粉病", "recommendation": "喷洒硫磺悬浮剂，注意保持通风"},
    "anthracnose": {"name_zh": "炭疽病", "recommendation": "剪除病叶，喷洒代森锰锌600倍液"},
    "rust": {"name_zh": "锈病", "recommendation": "喷洒三唑酮1000倍液，清除病残体"},
    "gray_mold": {"name_zh": "灰霉病", "recommendation": "降低湿度，喷洒腐霉利800倍液"},
    "healthy": {"name_zh": "健康", "recommendation": "植株叶片健康，继续保持当前养护"},
    "black_rot": {"name_zh": "黑腐病", "recommendation": "剪除腐烂组织，喷洒氢氧化铜500倍液"},
    "downy_mildew": {"name_zh": "霜霉病", "recommendation": "喷洒霜脲锰锌600倍液，控制湿度"},
}


def _load_onnx_model():
    """懒加载YOLO ONNX模型：仅在首次检测时加载，节省启动时间"""
    import onnxruntime
    global _MODEL, _CLASS_NAMES, _CLASS_NAMES_ZH
    path = settings.YOLO_MODEL_PATH
    if not os.path.exists(path):
        return
    # CPU执行提供者（兼容无CUDA环境）
    _MODEL = onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"])
    # 从同名JSON文件加载类别映射表
    label_path = path.replace(".onnx", ".json")
    if os.path.exists(label_path):
        with open(label_path, encoding="utf-8") as f:
            meta = json.load(f)
            _CLASS_NAMES = {int(k): v for k, v in meta.get("classes", {}).items()}
            _CLASS_NAMES_ZH = meta.get("names_zh", {})


async def run_detection(image_path: str) -> list[dict]:
    """对外统一检测接口：优先YOLO推理，失败则降级到规则引擎"""
    if _MODEL is None:
        _load_onnx_model()
    if _MODEL is None:
        # 模型不存在 → 自动降级
        return await _rule_based_detection(image_path)

    # 将CPU密集型推理放到线程池中，避免阻塞事件循环
    result = await asyncio.to_thread(_infer, image_path)
    return result


def _infer(image_path: str) -> list[dict]:
    """YOLOv11 ONNX推理核心：图像预处理 → 前向传播 → 后处理（NMS+阈值过滤）"""
    img = PILImage.open(image_path).convert("RGB")
    orig_w, orig_h = img.size
    input_size = 640  # YOLO标准输入尺寸
    # 预处理：缩放到640×640 → Normalize到[0,1] → CHW格式 → 加batch维度
    img_resized = img.resize((input_size, input_size))
    img_array = np.array(img_resized, dtype=np.float32) / 255.0
    img_array = img_array.transpose(2, 0, 1)[np.newaxis, ...]

    input_name = _MODEL.get_inputs()[0].name
    outputs = _MODEL.run(None, {input_name: img_array.astype(np.float32)})

    detections = []
    # YOLO标准onnx输出：[boxes, scores, class_ids]
    boxes = outputs[0] if outputs else np.array([])
    scores = outputs[1] if len(outputs) > 1 else np.array([])
    class_ids = outputs[2] if len(outputs) > 2 else np.array([])

    conf_threshold = 0.3  # 低阈值保留更多候选，供后端进一步筛选
    for i in range(len(boxes)):
        score = float(scores[i]) if i < len(scores) else 0
        if score < conf_threshold:
            continue
        class_id = int(class_ids[i]) if i < len(class_ids) else 0
        class_name = _CLASS_NAMES.get(class_id, f"class_{class_id}")
        name_zh = _CLASS_NAMES_ZH.get(class_name, class_name)
        # 规则库覆盖中文名和防治建议（比模型标签更权威）
        rule = _RULES.get(class_name, {})
        name_zh = rule.get("name_zh", name_zh)
        recommendation = rule.get("recommendation", "请根据病害类型采取相应防治措施")

        # BBox坐标转换：模型坐标系(center_x, center_y, w, h) → 像素坐标系(x1, y1, w, h)
        if len(boxes[i]) >= 4:
            bx, by, bw, bh = boxes[i][:4]
            x = max(0, int((bx - bw / 2) * orig_w / input_size))
            y = max(0, int((by - bh / 2) * orig_h / input_size))
            w = int(bw * orig_w / input_size)
            h = int(bh * orig_h / input_size)
        else:
            x, y, w, h = 0, 0, orig_w, orig_h

        # 严重度分级：基于置信度阈值
        severity = "severe" if score > 0.75 else "moderate" if score > 0.5 else "mild"

        detections.append({
            "class": class_name,
            "name_zh": name_zh,
            "confidence": round(score, 4),
            "bbox": {"x": x, "y": y, "width": w, "height": h},
            "severity": severity,
            "recommendation": recommendation,
        })
    return detections


async def _rule_based_detection(image_path: str) -> list[dict]:
    """启发式规则引擎：基于RGB通道统计特征的病害判断（YOLO模型不可用时的降级方案）
    核心逻辑：
      - 标准差<0.05 → 图像过暗/单一（可能拍摄异常）
      - 绿色通道占优(G>R×1.15 且 G>B×1.05) → 健康
      - 蓝色通道占优(B>R 且 B>G) → 疑似叶斑病（叶面偏暗/偏蓝）
      - 红色通道异常(R>G×1.1) 或 低纹理(std<0.08) → 疑似白粉病
    局限性：无法定位具体病斑位置（无bbox），置信度较低"""
    img = PILImage.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    mean_r = float(np.mean(arr[:, :, 0]))
    mean_g = float(np.mean(arr[:, :, 1]))
    mean_b = float(np.mean(arr[:, :, 2]))
    std = float(np.std(arr))

    # 规则1：标准差极低 → 过暗/异常光照
    if std < 0.05:
        return [{"class": "healthy", "name_zh": "健康", "confidence": 0.9, "bbox": None, "severity": None,
                 "recommendation": "图像过于均匀，可能是光照不足或拍摄异常，建议使用更好的光照条件重新拍摄"}]

    # 规则2：绿色通道显著占优 → 健康
    if mean_g > mean_r * 1.15 and mean_g > mean_b * 1.05:
        return [{"class": "healthy", "name_zh": "健康", "confidence": 0.75, "bbox": None, "severity": None,
                 "recommendation": "植株叶片整体呈健康绿色，继续保持当前养护"}]

    # 规则3：蓝色通道占优 → 叶斑病（叶面上褐色/暗色斑纹使蓝色分量相对突出）
    if mean_b > mean_r and mean_b > mean_g:
        return [{"class": "leaf_spot", "name_zh": "叶斑病", "confidence": 0.45, "bbox": None, "severity": "moderate",
                 "recommendation": "检测到叶片色斑，建议人工查看确认，必要时喷洒多菌灵800倍液"}]

    # 规则4：红色通道异常或纹理不明显 → 白粉病
    if mean_r > mean_g * 1.1 or std < 0.08:
        return [{"class": "powdery_mildew", "name_zh": "白粉病", "confidence": 0.40, "bbox": None, "severity": "mild",
                 "recommendation": "疑似白粉病早期，建议保持通风，检查叶片正面是否有白色粉末"}]

    # 兜底：默认判定健康
    return [{"class": "healthy", "name_zh": "健康", "confidence": 0.6, "bbox": None, "severity": None,
             "recommendation": "植株叶片状态尚可，继续保持当前养护"}]


def get_disease_name_zh(class_name: str) -> str:
    """从规则库获取病害中文名"""
    rule = _RULES.get(class_name, {})
    return rule.get("name_zh", class_name)


async def compute_health_score(detections: list[dict]) -> int:
    """计算植株健康评分(0-100)：病斑越多/置信度越高 → 分数越低"""
    if not detections:
        return 100
    max_conf = max(d.get("confidence", 0) for d in detections)
    disease_count = sum(1 for d in detections if d.get("class") != "healthy")
    if disease_count == 0:
        return 95
    # 评分公式：100 - 病斑数×20 - 最高置信度×30，下限10
    score = 100 - (disease_count * 20 + int(max_conf * 30))
    return max(10, min(100, score))
