/** LicenseInput — 업종 자동완성 + quick chips */
"use client";

import { useState, useRef, useId, useMemo } from "react";
import type { LicenseProfileBundle, LicenseProfile } from "@/lib/yangdo-types";
import { FormField } from "@/components/shared/form-field";
import { ChipSelect } from "@/components/shared/chip-select";
import { Search } from "lucide-react";

interface LicenseInputProps {
  profiles: LicenseProfileBundle;
  selectedToken: string;
  licenseText: string;
  onSelect: (text: string, token: string, profile?: LicenseProfile) => void;
}

export function LicenseInput({ profiles, selectedToken, licenseText, onSelect }: LicenseInputProps) {
  const [query, setQuery] = useState(licenseText);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const inputId = useId();

  const allTokens = useMemo(
    () => Object.values(profiles.profiles).sort((a, b) => b.sample_count - a.sample_count),
    [profiles.profiles],
  );

  const suggestions = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    return allTokens.filter((p) => p.display_name.toLowerCase().includes(q)).slice(0, 8);
  }, [query, allTokens]);

  const quickChips = useMemo(
    () => profiles.quick_tokens.map((t) => ({ value: t.token, label: t.display_name, count: t.sample_count })),
    [profiles.quick_tokens],
  );

  const handleSelect = (token: string) => {
    const profile = profiles.profiles[token];
    const display = profile?.display_name ?? token;
    setQuery(display);
    setShowSuggestions(false);
    onSelect(display, token, profile);
  };

  const handleInputChange = (val: string) => {
    setQuery(val);
    setShowSuggestions(true);
    setHighlightIdx(-1);
    if (!val.trim()) onSelect("", "", undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || !suggestions.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      handleSelect(suggestions[highlightIdx].token);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  return (
    <div className="yangdo-license-input">
      <FormField label="업종 선택" htmlFor={inputId} required hint="예: 토목건축공사업, 전기공사업">
        <div className="yangdo-combobox-wrap">
          <Search size={16} className="yangdo-combobox-icon" aria-hidden="true" />
          <input
            ref={inputRef}
            id={inputId}
            type="text"
            className="yangdo-combobox-input"
            role="combobox"
            aria-expanded={showSuggestions && suggestions.length > 0}
            aria-controls={listId}
            aria-activedescendant={highlightIdx >= 0 ? `${listId}-${highlightIdx}` : undefined}
            autoComplete="off"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={() => { if (query.trim()) setShowSuggestions(true); }}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onKeyDown={handleKeyDown}
            placeholder="업종명 입력..."
          />
          {showSuggestions && suggestions.length > 0 && (
            <ul id={listId} className="yangdo-suggestions" role="listbox">
              {suggestions.map((s, i) => (
                <li
                  key={s.token}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === highlightIdx}
                  className={`yangdo-suggestion${i === highlightIdx ? " yangdo-suggestion--active" : ""}`}
                  onMouseDown={() => handleSelect(s.token)}
                >
                  <span>{s.display_name}</span>
                  <span className="yangdo-suggestion-count">{s.sample_count}건</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </FormField>
      <ChipSelect
        options={quickChips}
        selected={selectedToken}
        onSelect={handleSelect}
        label="인기 업종 빠른 선택"
      />
    </div>
  );
}
