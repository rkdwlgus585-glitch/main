/** IndustrySelector — 191개 업종 검색 드롭다운 (카테고리 그룹) */
"use client";

import { useState, useEffect, useMemo, useRef, useId, useCallback } from "react";
import type { PermitIndustry, MajorCategory } from "@/lib/permit-types";
import { FormField } from "@/components/shared/form-field";
import { Search, ChevronDown, X } from "lucide-react";

interface IndustrySelectorProps {
  industries: PermitIndustry[];
  categories: MajorCategory[];
  selected: PermitIndustry | null;
  error?: string;
  onSelect: (industry: PermitIndustry | null) => void;
}

export function IndustrySelector({ industries, categories, selected, error, onSelect }: IndustrySelectorProps) {
  const [query, setQuery] = useState(selected?.service_name ?? "");
  useEffect(() => { setQuery(selected?.service_name ?? ""); }, [selected]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
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

  const handleSelect = useCallback((ind: PermitIndustry) => {
    setQuery(ind.service_name);
    setShowDropdown(false);
    onSelect(ind);
  }, [onSelect]);

  const handleInputChange = (val: string) => {
    setQuery(val);
    setShowDropdown(true);
    setHighlightIdx(-1);
    if (!val.trim()) onSelect(null);
  };

  /* Close dropdown on outside click — replaces fragile setTimeout onBlur */
  useEffect(() => {
    if (!showDropdown) return;
    const handlePointerDown = (e: PointerEvent) => {
      const input = inputRef.current;
      const dropdown = dropdownRef.current;
      const target = e.target as Node;
      if (input?.contains(target) || dropdown?.contains(target)) return;
      setShowDropdown(false);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [showDropdown]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!showDropdown) { setShowDropdown(true); return; }
      if (filteredIndustries.length) setHighlightIdx((i) => Math.min(i + 1, filteredIndustries.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (filteredIndustries.length) setHighlightIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      handleSelect(filteredIndustries[highlightIdx]);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      inputRef.current?.focus();
    }
  };

  /* Category tab keyboard nav (Left/Right arrows) */
  const allCategoryCodes = useMemo(() => [null, ...categories.map((c) => c.major_code)], [categories]);
  const handleCategoryKeyDown = useCallback((e: React.KeyboardEvent) => {
    const idx = allCategoryCodes.indexOf(activeCategory);
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const next = (idx + 1) % allCategoryCodes.length;
      setActiveCategory(allCategoryCodes[next]);
      setHighlightIdx(-1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const prev = (idx - 1 + allCategoryCodes.length) % allCategoryCodes.length;
      setActiveCategory(allCategoryCodes[prev]);
      setHighlightIdx(-1);
    }
  }, [activeCategory, allCategoryCodes]);

  return (
    <div className="permit-industry-selector">
      <FormField label="업종 선택" htmlFor={inputId} required hint={`${industries.length}개 건설업 업종 중 선택`} error={error}>
        <div className="permit-combobox-wrap">
          <Search size={16} className="permit-combobox-icon" aria-hidden="true" />
          <input
            ref={inputRef}
            id={inputId}
            type="text"
            className="permit-combobox-input"
            role="combobox"
            aria-expanded={showDropdown && filteredIndustries.length > 0}
            aria-controls={listId}
            aria-activedescendant={highlightIdx >= 0 ? `${listId}-${highlightIdx}` : undefined}
            aria-haspopup="listbox"
            aria-autocomplete="list"
            autoComplete="off"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={() => setShowDropdown(true)}
            onKeyDown={handleKeyDown}
            placeholder="업종명 검색..."
          />
          {query ? (
            <button
              type="button"
              className="calc-combobox-clear"
              onClick={() => { handleInputChange(""); inputRef.current?.focus(); }}
              aria-label="선택 초기화"
              tabIndex={-1}
            >
              <X size={14} aria-hidden="true" />
            </button>
          ) : (
            <ChevronDown size={16} className="permit-combobox-chevron" aria-hidden="true" />
          )}
        </div>
      </FormField>

      {showDropdown && (
        <div ref={dropdownRef} className="permit-dropdown" onPointerDown={(e) => e.preventDefault()}>
          {/* Category tabs */}
          <div className="permit-category-tabs" role="group" aria-label="업종 카테고리 필터" onKeyDown={handleCategoryKeyDown}>
            <button
              type="button"
              aria-pressed={activeCategory === null}
              tabIndex={activeCategory === null ? 0 : -1}
              className={`permit-category-tab${activeCategory === null ? " permit-category-tab--active" : ""}`}
              onClick={() => { setActiveCategory(null); setHighlightIdx(-1); }}
            >
              전체
            </button>
            {categories.map((cat) => (
              <button
                key={cat.major_code}
                type="button"
                aria-pressed={activeCategory === cat.major_code}
                tabIndex={activeCategory === cat.major_code ? 0 : -1}
                className={`permit-category-tab${activeCategory === cat.major_code ? " permit-category-tab--active" : ""}`}
                onClick={() => { setActiveCategory(cat.major_code); setHighlightIdx(-1); }}
              >
                {cat.major_name}
                <span className="permit-category-count">{cat.industry_count}</span>
              </button>
            ))}
          </div>

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
                  onPointerDown={() => handleSelect(ind)}
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
