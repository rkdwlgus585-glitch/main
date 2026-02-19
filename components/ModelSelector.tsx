'use client';

import { MODELS, ModelId } from '@/types';

interface Props {
  value: ModelId;
  onChange: (model: ModelId) => void;
  disabled?: boolean;
}

export default function ModelSelector({ value, onChange, disabled }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as ModelId)}
      disabled={disabled}
      className="bg-gray-700 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500 disabled:opacity-50 cursor-pointer"
    >
      {MODELS.map((m) => (
        <option key={m.id} value={m.id}>
          {m.name} — {m.description}
        </option>
      ))}
    </select>
  );
}
