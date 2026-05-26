from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageEnhance, ImageFilter, ImageOps, ImageStat

from app.services.storage_service import STORAGE_DIR


@dataclass(slots=True)
class ImagePreprocessResult:
    detection_path: str
    enhanced_url: str | None
    quality_score: float
    light_condition: str
    brightness: float
    contrast: float
    sharpness: float
    enhanced: bool


def _storage_ref_to_local_path(storage_ref: str) -> Path | None:
    if storage_ref.startswith("http://") or storage_ref.startswith("https://"):
        return None
    rel = storage_ref.replace("/static/images/", "", 1)
    path = (STORAGE_DIR / rel).resolve()
    root = STORAGE_DIR.resolve()
    if root not in path.parents and path != root:
        return None
    return path


def _local_path_to_static_url(path: Path) -> str:
    rel = path.resolve().relative_to(STORAGE_DIR.resolve()).as_posix()
    return f"/static/images/{rel}"


def _gamma_correct(image: PILImage.Image, gamma: float) -> PILImage.Image:
    table = [min(255, int(((i / 255.0) ** gamma) * 255)) for i in range(256)]
    return image.point(table * len(image.getbands()))


def _score_quality(brightness: float, contrast: float, sharpness: float) -> float:
    brightness_score = 1.0 - min(abs(brightness - 0.52) / 0.52, 1.0)
    contrast_score = min(contrast / 0.24, 1.0)
    sharpness_score = min(sharpness / 0.16, 1.0)
    score = brightness_score * 40 + contrast_score * 35 + sharpness_score * 25
    return round(max(0.0, min(100.0, score)), 1)


def _light_condition(brightness: float) -> str:
    if brightness < 0.25:
        return "dark"
    if brightness < 0.42:
        return "dim"
    if brightness > 0.82:
        return "bright"
    return "normal"


def _measure(image: PILImage.Image) -> tuple[float, float, float]:
    gray = ImageOps.grayscale(image)
    stat = ImageStat.Stat(gray)
    brightness = float(stat.mean[0] / 255.0)
    contrast = float(stat.stddev[0] / 255.0)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = float(ImageStat.Stat(edges).stddev[0] / 255.0)
    return brightness, contrast, sharpness


def _enhance(image: PILImage.Image, brightness: float, contrast: float) -> PILImage.Image:
    """Enhance luminance only to avoid RGB channel shifts and purple color casts."""
    base = image.filter(ImageFilter.MedianFilter(size=3)) if brightness < 0.30 else image
    y, cb, cr = base.convert("YCbCr").split()

    if brightness < 0.25:
        y = _gamma_correct(y, 0.58)
        y = ImageEnhance.Brightness(y).enhance(1.12)
    elif brightness < 0.35:
        y = _gamma_correct(y, 0.68)
        y = ImageEnhance.Brightness(y).enhance(1.06)
    elif brightness < 0.42:
        y = _gamma_correct(y, 0.82)

    y = ImageOps.autocontrast(y, cutoff=0.5)
    if contrast < 0.12:
        y = ImageEnhance.Contrast(y).enhance(1.22)
    elif contrast < 0.16:
        y = ImageEnhance.Contrast(y).enhance(1.12)

    enhanced = PILImage.merge("YCbCr", (y, cb, cr)).convert("RGB")
    return enhanced.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=6))


async def preprocess_image_for_detection(storage_ref: str) -> ImagePreprocessResult:
    """Analyze image quality and create an enhanced local JPEG for inference when needed."""
    local_path = _storage_ref_to_local_path(storage_ref)
    if local_path is None or not local_path.exists():
        return ImagePreprocessResult(
            detection_path=storage_ref,
            enhanced_url=None,
            quality_score=0.0,
            light_condition="unknown",
            brightness=0.0,
            contrast=0.0,
            sharpness=0.0,
            enhanced=False,
        )

    with PILImage.open(local_path) as raw:
        image = raw.convert("RGB")
        brightness, contrast, sharpness = _measure(image)
        quality_score = _score_quality(brightness, contrast, sharpness)
        light_condition = _light_condition(brightness)
        should_enhance = brightness < 0.42 or contrast < 0.16

        if not should_enhance:
            return ImagePreprocessResult(
                detection_path=str(local_path),
                enhanced_url=None,
                quality_score=quality_score,
                light_condition=light_condition,
                brightness=round(brightness, 4),
                contrast=round(contrast, 4),
                sharpness=round(sharpness, 4),
                enhanced=False,
            )

        enhanced = _enhance(image, brightness, contrast)
        enhanced_path = local_path.with_name(f"{local_path.stem}_enhanced{local_path.suffix or '.jpg'}")
        enhanced.save(enhanced_path, format="JPEG", quality=92, optimize=True)

        return ImagePreprocessResult(
            detection_path=str(enhanced_path),
            enhanced_url=_local_path_to_static_url(enhanced_path),
            quality_score=quality_score,
            light_condition=light_condition,
            brightness=round(brightness, 4),
            contrast=round(contrast, 4),
            sharpness=round(sharpness, 4),
            enhanced=True,
        )
