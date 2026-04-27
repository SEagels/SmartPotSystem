"""将缺少的注意力模块注入 ultralytics 包，使 best.pt 能够正常加载"""
import os
import torch
import torch.nn as nn
import ultralytics.nn as ultralytics_nn

nn_path = ultralytics_nn.__path__[0]
attn_pkg = os.path.join(nn_path, "attention")
os.makedirs(attn_pkg, exist_ok=True)

# 所有需要 stub 的类名
STUB_CLASSES = [
    "attention",
    "ParallelPolarizedSelfAttention",
    "SequentialPolarizedSelfAttention",
    "SimAM",
    "SpatialAttention",
    "ChannelAttention",
    "SEAttention",
    "CBAM",
    "CoordAtt",
    "BiLevelRoutingAttention",
    "EMA",
    "SimConv",
    "BiFPN_Concat3",
    "BiFPN_Concat2",
    "PConv",
    "C2f_EMA",
    "C2f_SimConv",
    "GhostModule",
    "TAM",
    "ShuffleNetV2",
    "C3",
    "C2f",
    "SPPF",
    "Detect",
    "Segment",
    "Pose",
    "Classify",
    "OBB",
    "RTDETRDecoder",
    "Concat",
    "RepConv",
    "ADown",
    "SPP",
    "Focus",
    "Bottleneck",
    "BottleneckCSP",
    "C3x",
    "GhostBottleneck",
    "HGBlock",
    "HGStem",
    "RepC3",
    "RepNCSPELAN4",
    "ELAN1",
    "AConv",
    "LightConv",
    "DWConv",
    "DWConvTranspose2d",
    "ConvTranspose",
    "DFL",
    "Proto",
    "TransformerEncoderLayer",
    "AIFI",
    "MLPBlock",
    "LayerNorm2d",
    "ReOrg",
    "ImagePoolingAttn",
    "PSAttention",
    "SPPELAN",
    "Silence",
    "RepVGGDW",
    "CBFuse",
    "C2fCIB",
    "C2fPSA",
    "SCDown",
    "C2PSA",
    "C2PSAv2",
    "PSABlock",
]

# 为 attention 包的 __init__.py 写入所有类
init_lines = ["import torch", "import torch.nn as nn"]
for cls_name in STUB_CLASSES:
    init_lines.append(f"""
class {cls_name}(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
    def forward(self, x):
        return x
""")

with open(os.path.join(attn_pkg, "__init__.py"), "w") as f:
    f.write("\n".join(init_lines))

# 为每个子模块创建对应的 .py 文件，每个文件包含全部 stub 类
# 因为模型 pickle 重建时可能从任意 attention 子模块路径查找任意类
_all_classes_code = "\n".join(init_lines)
for cls_name in STUB_CLASSES:
    with open(os.path.join(attn_pkg, f"{cls_name}.py"), "w") as f:
        f.write(_all_classes_code)

print(f"已在 {attn_pkg} 创建 {len(STUB_CLASSES)} 个注意力模块 stub")

import importlib
importlib.invalidate_caches()

best_pt_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "best.pt"
)
ckpt = torch.load(best_pt_path, map_location="cpu", weights_only=False)
print("best.pt 加载成功！")
print("checkpoint keys:", list(ckpt.keys()))

if "model" in ckpt:
    m = ckpt["model"]
    print("model type:", type(m).__name__)
    if hasattr(m, "names"):
        print("class names:", m.names)
    if hasattr(m, "nc"):
        print("nc:", m.nc)
