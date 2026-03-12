/** IndustrySelector — 191개 업종 검색 드롭다운 (카테고리 그룹) */
"use client";

import { useState, useMemo, useRef, useId } from "react";
import type { PermitIndustry, MajorCategory } from "@/lib/permit-types";
import { FormField } from "@/components/shared/form-field";
import { Search, ChevronDown } from "lucide-react";

interface IndustrySelectorProps {
  industries: PermitIndustry[];
  categories: MajorCategory[];
  selected: PermitIndustry | null;
  onSelect: (industry: PermitIndustry | null) => void;
}

export function IndustrySelector({ industries, categories, selected, onSelect }: IndustrySelectorProps) {
  const [query, setQuery] = useState(selected?.service_name ?? "");
  const [showDropdown, setShowDropdown] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const inputId = useId();

  const filteredIndustries = useMemo(() => {
    let list = industries;
    if (activeCategory) {
      list = list.filter((ind) => ind.major_code === activeCategory);
    }
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (ind) =>
          ind.service_name.toLowerCase().includes(q) ||
          ind.major_name.toLowerCase().includes(q),
      );
    }
    return list.slice(0, 20);
  }, [industries, query, activeCategory]);

  const handleSelect = (ind: PermitIndustry) => {
    setQuery(ind.service_name);
    setShowDropdown(false);
    onSelect(ind);
  };

  const handleInputChange = (val: string) => {
    setQuery(val);
    setShowDropdown(true);
    setHighlightIdx(-1);
    if (!val.trim()) onSelect(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || !filteredIndustries.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => Math.min(i + 1, filteredIndustries.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      handleSelect(filteredIndustries[highlightIdx]);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  };

  return (
    <div className="permit-industry-selector">
      <FormField label="업종 선택" htmlFor={inputId} required hint={`${industries.length}개 건설업 업종 중 선택`}>
        <div className="permit-combobox-wrap">
          <Search size={16} className="permit-combobox-icon" aria-hidden="true" />
          <input
            ref={inputRef}
            id={inputId}
            type="text"
            className="permit-combobox-input"
            role="combobox"
            aria-expanded={showDropdown}
            aria-controls={listId}
            aria-activedescendant={highlightIdx >= 0 ? `${listId}-${highlightIdx}` : undefined}
            autoComplete="off"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={() => setShowDropdown(true)}
            onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
            onKeyDown={handleKeyDown}
            placeholder="업종명 검색..."
          />
          <ChevronDown size={16} className="permit-combobox-chevron" aria-hidden="true" />
        </div>
      </FormField>

      {showDropdown && (
        <div className="permit-dropdown">
          {/* Category tabs */}
          <div className="permit-category-tabs" role="tablist" aria-label="업종 카테고리">
            <button
              type="button"
              role="tab"
              aria-selected={activeCategory === null}
              className={`permit-category-tab${activeCategory === null ? " permit-category-tab--active" : ""}`}
              onClick={() => setActiveCategory(null)}
            >
              전체
            </button>
            {categories.map((cat) => (
              <button
                key={cat.major_code}
                type="button"
                role="tab"
                aria-selected={activeCategory === cat.major_code}
                className={`permit-category-tab${activeCategory === cat.major_code ? " permit-category-tab--active" : ""}`}
                onClick={() => setActiveCategory(cat.major_code)}
              >
                {cat.major_name}
                <span className="permit-category-count">{cat.industry_count}</span>
              </button>
            ))}
          </div>

          {/* Industry list */}
          <ul id={listId} className="permit-industry-list" role="listbox">
            {filteredIndustries.length === 0 ? (
              <li className="permit-industry-empty">검색 결과가 없습니다</li>
            ) : (
              filteredIndustries.map((ind, i) => (
                <li
                  key={ind.service_code}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === highlightIdx}
                  className={`permit-industry-item${i === highlightIdx ? " permit-industry-item--active" : ""}${selected?.service_code === ind.service_code ? " permit-industry-item--selected" : ""}`}
                  onMouseDown={() => handleSelect(ind)}
                >
                  <span className="permit-industry-name">{ind.service_name}</span>
                  <span className="permit-industry-category">{ind.major_name}</span>
                  {ind.has_rule && <span className="permit-industry-rule-badge">기준 있음</span>}
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
