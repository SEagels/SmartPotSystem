"""诊断 best.pt 模型中哪些注意力模块被实际使用，以及参数加载状态"""
from __future__ import annotations

import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn

import ultralytics.nn as ultralytics_nn

attn_pkg = os.path.join(ultralytics_nn.__path__[0], "attention")
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

MODEL_PATH = os.path.join("models", "best.pt")
print(f"加载模型: {MODEL_PATH}")

from ultralytics import YOLO

model = YOLO(MODEL_PATH)
torch_model = model.model

print("\n" + "=" * 60)
print("模型中的注意力模块（当前 stub 模式）")
print("=" * 60)

found_attn = {}
for name, module in torch_model.named_modules():
    cls_name = type(module).__name__
    if cls_name in STUB_CLASSES:
        param_count = sum(p.numel() for p in module.parameters())
        mod_file = type(module).__module__
        is_stub = "attention" in mod_file
        found_attn[name] = {
            "class": cls_name, "params": param_count,
            "is_stub": is_stub, "module_file": mod_file,
        }

if found_attn:
    print(f"找到 {len(found_attn)} 个注意力模块实例：\n")
    total_params = 0
    for n, info in sorted(found_attn.items()):
        marker = "⚠ STUB (直通层，forward 不做计算)" if info["is_stub"] else "真实实现"
        print(f"  {n}")
        print(f"    类型: {info['class']}  参数: {info['params']:,}  {marker}")
        total_params += info["params"]
    print(f"\n  注意力模块总参数量: {total_params:,}")
else:
    print("未找到注意力模块")

print("\n" + "=" * 60)
print("Checkpoint 原生结构")
print("=" * 60)

ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
if "model" in ckpt:
    ckpt_model = ckpt["model"]
    print(f"类型: {type(ckpt_model).__name__}")
    for name, module in ckpt_model.named_modules():
        cls_name = type(module).__name__
        if cls_name in STUB_CLASSES:
            pc = sum(p.numel() for p in module.parameters())
            print(f"  {name}: {cls_name} ({pc:,} params)")

print("\n" + "=" * 60)
print("结论")
print("=" * 60)

if found_attn and any(i["is_stub"] and i["params"] > 0 for i in found_attn.values()):
    print("关键发现: 注意力模块有参数但 forward() 是直通")
    print("  → 注意力权重已加载但未参与计算")
    print("  → 需从训练环境导出 ONNX 固化计算图")
elif found_attn and all(i["params"] == 0 for i in found_attn.values()):
    print("注意力模块无参数（如 SimAM 基于统计量）")
    print("  → stub 跳过了统计注意力计算，仍有损失")
else:
    print("未发现明显 stub 问题，差异可能来自其他原因")
