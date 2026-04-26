import { Tag } from 'antd';
import { DISEASE_NAME_MAP } from '../utils/constants';

interface Props {
  diseaseClass: string;
  confidence: number;
}

export default function DiseaseBadge({ diseaseClass, confidence }: Props) {
  const name = DISEASE_NAME_MAP[diseaseClass] ?? diseaseClass;
  const color = confidence >= 0.8 ? 'red' : confidence >= 0.6 ? 'orange' : 'gold';

  return (
    <Tag color={color}>
      {name} {(confidence * 100).toFixed(0)}%
    </Tag>
  );
}
