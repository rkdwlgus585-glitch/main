/** ResultPlaceholder — visual guide shown before first form submission. */
import { Sparkles } from "lucide-react";

interface ResultPlaceholderProps {
  title?: string;
  description?: string;
}

export function ResultPlaceholder({
  title = "AI 분석 결과가 여기에 표시됩니다",
  description = "위 양식을 작성하고 분석 버튼을 눌러 주세요.",
}: ResultPlaceholderProps) {
  return (
    <div className="calc-result-placeholder" aria-hidden="true">
      <div className="calc-result-placeholder-icon">
        <Sparkles size={28} />
      </div>
      <p className="calc-result-placeholder-title">{title}</p>
      <p className="calc-result-placeholder-desc">{description}</p>
    </div>
  );
}
