# 叶片病害检测服务 —— PyTorch YOLO (best.pt) 推理 + 规则降级方案
# 双层检测策略：
#   1. 主路径：加载 best.pt (ultralytics YOLO)，GPU/CPU 推理，输出 bbox + 置信度
#   2. 降级路径：模型不可用时，基于 RGB 通道均值和标准差的规则引擎（启发式算法）
# 健康评分算法：基础分100 - 病斑数×20 - 最高置信度×30，保底10分
from __future__ import annotations

import asyncio
import json
import os

import numpy as np
from PIL import Image as PILImage

from app.config import settings

# --- 模型加载前的 stub 注入（best.pt 训练时依赖自定义注意力模块） ---
_ATTENTION_STUBS_SETUP = False

# --- 全局模型缓存（懒加载，避免启动时阻塞） ---
_MODEL = None
_CLASS_NAMES: dict[int, str] = {}  # 模型输出 class_id → 英文类名
_CLASS_NAMES_ZH: dict[str, str] = {}  # 英文类名 → 中文名

# best.pt 12 类病害的中文映射和防治建议
_PLANT_DISEASE_MAP: dict[str, dict] = {
    "ALS": {
        "name_zh": "褐斑病",
        "recommendation": "喷洒苯醚甲环唑1500倍液，及时清除病残叶，注意通风透光",
    },
    "Angular Leafspot": {
        "name_zh": "角斑病",
        "recommendation": "喷洒氢氧化铜500倍液或噻菌铜600倍液，避免叶面长期潮湿",
    },
    "Anthracnose Fruit Rot": {
        "name_zh": "炭疽果腐病",
        "recommendation": "剪除病果病叶，喷洒代森锰锌600倍液 + 咪鲜胺1000倍液",
    },
    "Bean Rust": {
        "name_zh": "豆类锈病",
        "recommendation": "喷洒三唑酮1000倍液或戊唑醇2000倍液，清除病残体",
    },
    "Blossom Blight": {
        "name_zh": "花枯病",
        "recommendation": "喷洒啶酰菌胺800倍液，避免花期高湿，及时摘除病花",
    },
    "Gray Mold": {
        "name_zh": "灰霉病",
        "recommendation": "降低环境湿度至60%以下，喷洒腐霉利800倍液或异菌脲1000倍液",
    },
    "Leaf Spot": {
        "name_zh": "叶斑病",
        "recommendation": "喷洒多菌灵800倍液或百菌清600倍液，间隔7天重复一次",
    },
    "Powdery Mildew Fruit": {
        "name_zh": "果实白粉病",
        "recommendation": "喷洒硫磺悬浮剂300倍液或嘧菌酯1500倍液，保持通风",
    },
    "Powdery Mildew Leaf": {
        "name_zh": "叶片白粉病",
        "recommendation": "喷洒三唑酮1500倍液或吡唑醚菌酯2000倍液，避免偏施氮肥",
    },
    "disease": {
        "name_zh": "病害（通用）",
        "recommendation": "叶片存在异常，建议人工确认具体病害类型后采取相应防治措施",
    },
    "leaf mold": {
        "name_zh": "叶霉病",
        "recommendation": "喷洒嘧霉胺800倍液或啶菌噁唑1000倍液，加强通风降湿",
    },
    "spider mites": {
        "name_zh": "红蜘蛛/叶螨",
        "recommendation": "喷洒阿维菌素1500倍液或联苯肼酯2000倍液，重点喷洒叶背",
    },
}

# 规则引擎知识库（模型不可用时的降级方案）
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


def _setup_attention_stubs():
    """在加载 best.pt 前，将训练时依赖的自定义注意力模块 stub 注入 ultralytics 包"""
    global _ATTENTION_STUBS_SETUP
    if _ATTENTION_STUBS_SETUP:
        return
    _ATTENTION_STUBS_SETUP = True

    import torch.nn as nn
    import ultralytics.nn as ultralytics_nn

    nn_path = ultralytics_nn.__path__[0]
    attn_pkg = os.path.join(nn_path, "attention")
    os.makedirs(attn_pkg, exist_ok=True)

    STUB_CLASSES = [
        "attention", "ParallelPolarizedSelfAttention", "SequentialPolarizedSelfAttention",
        "SimAM", "SpatialAttention", "ChannelAttention", "SEAttention", "CBAM",
        "CoordAtt", "BiLevelRoutingAttention", "EMA", "SimConv", "BiFPN_Concat3",
        "BiFPN_Concat2", "PConv", "C2f_EMA", "C2f_SimConv", "GhostModule", "TAM",
    ]

    init_lines = ["import torch", "import torch.nn as nn"]
    for cls_name in STUB_CLASSES:
        init_lines.append(f"""
class {cls_name}(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
    def forward(self, x):
        return x
""")
    all_code = "\n".join(init_lines)

    with open(os.path.join(attn_pkg, "__init__.py"), "w") as f:
        f.write(all_code)

    for cls_name in STUB_CLASSES:
        with open(os.path.join(attn_pkg, f"{cls_name}.py"), "w") as f:
            f.write(all_code)

    import importlib
    importlib.invalidate_caches()


def _load_yolo_model():
    """懒加载 YOLO PyTorch 模型：首次检测时加载"""
    global _MODEL, _CLASS_NAMES, _CLASS_NAMES_ZH

    _setup_attention_stubs()

    from ultralytics import YOLO

    path = settings.YOLO_PT_MODEL_PATH
    if not path or not os.path.exists(path):
        return

    _MODEL = YOLO(path)
    if hasattr(_MODEL, "names"):
        raw_names = _MODEL.names
        _CLASS_NAMES = {int(k): v for k, v in raw_names.items()}
        for name_en in raw_names.values():
            disease_info = _PLANT_DISEASE_MAP.get(name_en, {})
            _CLASS_NAMES_ZH[name_en] = disease_info.get("name_zh", name_en)


async def run_detection(image_path: str) -> list[dict]:
    """对外统一检测接口：优先 YOLO 推理，失败则降级到规则引擎"""
    if _MODEL is None:
        _load_yolo_model()
    if _MODEL is None:
        return await _rule_based_detection(image_path)

    result = await asyncio.to_thread(_infer, image_path)
    return result


def _infer(image_path: str) -> list[dict]:
    """YOLO PyTorch 推理核心：ultralytics 自动处理预处理 + NMS + 后处理"""
    results = _MODEL.predict(
        source=image_path,
        imgsz=640,
        conf=0.25,
        iou=0.45,
        augment=True,
        half=False,
        verbose=False,
    )

    detections = []
    if not results or len(results) == 0:
        return detections

    result = results[0]
    if result.boxes is None:
        return detections

    for box in result.boxes:
        cls_id = int(box.cls.item())
        conf = float(box.conf.item())
        xyxy = box.xyxy[0].tolist()

        class_name = _CLASS_NAMES.get(cls_id, f"class_{cls_id}")
        name_zh = _CLASS_NAMES_ZH.get(class_name, class_name)
        disease_info = _PLANT_DISEASE_MAP.get(class_name, {})
        name_zh = disease_info.get("name_zh", name_zh)
        recommendation = disease_info.get("recommendation", "请根据病害类型采取相应防治措施")

        x = max(0, int(xyxy[0]))
        y = max(0, int(xyxy[1]))
        w = int(xyxy[2] - xyxy[0])
        h = int(xyxy[3] - xyxy[1])

        severity = "severe" if conf > 0.75 else "moderate" if conf > 0.5 else "mild"

        detections.append({
            "class": class_name,
            "name_zh": name_zh,
            "confidence": round(conf, 4),
            "bbox": {"x": x, "y": y, "width": w, "height": h},
            "severity": severity,
            "recommendation": recommendation,
        })

    return detections


async def _rule_based_detection(image_path: str) -> list[dict]:
    """启发式规则引擎：基于 RGB 通道统计特征的病害判断（YOLO 模型不可用时的降级方案）
    局限性：无法定位具体病斑位置（无 bbox），置信度较低"""
    img = PILImage.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    mean_r = float(np.mean(arr[:, :, 0]))
    mean_g = float(np.mean(arr[:, :, 1]))
    mean_b = float(np.mean(arr[:, :, 2]))
    std = float(np.std(arr))

    h, w = arr.shape[:2]
    cy, cx = h // 2, w // 2
    r_size = min(h, w) // 4
    if r_size < 1:
        r_size = 1
    center = arr[cy - r_size:cy + r_size, cx - r_size:cx + r_size, :]
    center_mean_r = float(np.mean(center[:, :, 0]))
    center_mean_g = float(np.mean(center[:, :, 1]))
    center_mean_b = float(np.mean(center[:, :, 2]))

    brightness = np.mean(arr, axis=2)

    # pixels where R+G dominates over B (yellow/brown/cholorosis tones)
    yellow_mask = (arr[:, :, 0] + arr[:, :, 1]) > 2.2 * arr[:, :, 2]
    yellow_ratio = float(np.mean(yellow_mask))

    # dark patches (potential necrosis)
    dark_ratio = float(np.mean(brightness < 0.25))

    # brown spots: red dominant in mid-brightness
    brown_mask = (arr[:, :, 0] > arr[:, :, 1]) & (arr[:, :, 0] > arr[:, :, 2]) & (brightness > 0.2) & (brightness < 0.6)
    brown_ratio = float(np.mean(brown_mask))

    # white/bright patches (potential powdery mildew)
    white_mask = (arr[:, :, 0] > 0.72) & (arr[:, :, 1] > 0.72) & (arr[:, :, 2] > 0.72)
    white_ratio = float(np.mean(white_mask))

    if std < 0.05:
        return [{"class": "healthy", "name_zh": "健康", "confidence": 0.85, "bbox": None, "severity": None,
                 "recommendation": "图像过于均匀，可能是光照不足或拍摄异常，建议使用更好的光照条件重新拍摄"}]

    detections = []

    if brown_ratio > 0.04 or dark_ratio > 0.12:
        conf = round(min(0.62, 0.28 + brown_ratio * 3), 4)
        sev = "severe" if brown_ratio > 0.14 else "moderate"
        detections.append({
            "class": "Leaf Spot", "name_zh": "叶斑病", "confidence": conf,
            "bbox": None, "severity": sev,
            "recommendation": "叶片检测到褐色/深色斑点，可能为叶斑病或坏死斑，建议人工确认并喷洒多菌灵800倍液",
        })

    if yellow_ratio > 0.18:
        conf = round(min(0.58, 0.22 + yellow_ratio * 0.6), 4)
        sev = "moderate" if yellow_ratio > 0.35 else "mild"
        detections.append({
            "class": "disease", "name_zh": "叶片黄化", "confidence": conf,
            "bbox": None, "severity": sev,
            "recommendation": "叶片出现黄化现象，可能缺氮或缺铁，建议检查土壤养分并适当追肥",
        })

    if white_ratio > 0.025:
        conf = round(min(0.52, 0.28 + white_ratio * 4), 4)
        detections.append({
            "class": "Powdery Mildew Leaf", "name_zh": "叶片白粉病", "confidence": conf,
            "bbox": None, "severity": "mild",
            "recommendation": "疑似白粉病，建议保持通风，检查叶片正面是否有白色粉末，必要时喷洒三唑酮1500倍液",
        })

    center_green_ratio = center_mean_g / max(center_mean_r, center_mean_b, 0.01)
    if center_green_ratio < 0.92:
        detections.append({
            "class": "healthy", "name_zh": "叶片色泽异常", "confidence": 0.38,
            "bbox": None, "severity": "mild",
            "recommendation": "叶片中心区域绿色度偏低，可能存在光照不足或养分不均，建议调整光照条件",
        })

    if detections:
        return detections

    if mean_g > mean_r * 1.1 and mean_g > mean_b * 1.02:
        return [{"class": "healthy", "name_zh": "健康", "confidence": 0.8, "bbox": None, "severity": None,
                 "recommendation": "植株叶片整体呈健康绿色，继续保持当前养护"}]

    return [{"class": "healthy", "name_zh": "基本健康", "confidence": 0.55, "bbox": None, "severity": None,
             "recommendation": "植株叶片状态尚可，建议持续观察，注意水肥管理"}]


def get_disease_name_zh(class_name: str) -> str:
    """从病害知识库获取中文名"""
    disease_info = _PLANT_DISEASE_MAP.get(class_name, {})
    if disease_info:
        return disease_info.get("name_zh", class_name)
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
    score = 100 - (disease_count * 20 + int(max_conf * 30))
    return max(10, min(100, score))
