import type { BBox } from '../api/images';

interface Props {
  bbox: BBox;
  imageWidth: number;
  imageHeight: number;
  displayWidth: number;
  displayHeight: number;
  label?: string;
}

export default function BBoxOverlay({ bbox, imageWidth, imageHeight, displayWidth, displayHeight, label }: Props) {
  const scaleX = displayWidth / imageWidth;
  const scaleY = displayHeight / imageHeight;

  return (
    <div
      style={{
        position: 'absolute',
        left: bbox.x * scaleX,
        top: bbox.y * scaleY,
        width: bbox.width * scaleX,
        height: bbox.height * scaleY,
        border: '2px solid #ff4d4f',
        background: 'rgba(255, 77, 79, 0.08)',
        pointerEvents: 'none',
        borderRadius: 2,
      }}
    >
      {label && (
        <span style={{
          position: 'absolute',
          top: -22,
          left: -2,
          background: '#ff4d4f',
          color: '#fff',
          fontSize: 11,
          padding: '2px 6px',
          borderRadius: '4px 4px 4px 0',
          whiteSpace: 'nowrap',
        }}>
          {label}
        </span>
      )}
    </div>
  );
}
