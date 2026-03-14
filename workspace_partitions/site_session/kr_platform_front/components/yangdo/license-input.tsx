/** LicenseInput — 업종 자동완성 + quick chips */
"use client";

import { useState, useEffect, useRef, useId, useMemo, useCallback } from "react";
import type { LicenseProfileBundle, LicenseProfile } from "@/lib/yangdo-types";
import { FormField } from "@/components/shared/form-field";
import { ChipSelect } from "@/components/shared/chip-select";
import { Search, X } from "lucide-react";

interface LicenseInputProps {
  profiles: LicenseProfileBundle;
  selectedToken: string;
  licenseText: string;
  error?: string;
  onSelect: (text: string, token: string, profile?: LicenseProfile) => void;
}

export function LicenseInput({ profiles, selectedToken, licenseText, error, onSelect }: LicenseInputProps) {
  const [query, setQuery] = useState(licenseText);
  useEffect(() => { setQuery(licenseText); }, [licenseText]);
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

  const suggestionsRef = useRef<HTMLUListElement>(null);

  const handleSelect = useCallback((token: string) => {
    const profile = profiles.profiles[token];
    const display = profile?.display_name ?? token;
    setQuery(display);
    setShowSuggestions(false);
    onSelect(display, token, profile);
  }, [profiles.profiles, onSelect]);

  const handleInputChange = (val: string) => {
    setQuery(val);
    setShowSuggestions(true);
    setHighlightIdx(-1);
    if (!val.trim()) onSelect("", "", undefined);
  };

  /* Close suggestions on outside click — replaces fragile setTimeout onBlur */
  useEffect(() => {
    if (!showSuggestions) return;
    const handlePointerDown = (e: PointerEvent) => {
      const input = inputRef.current;
      const list = suggestionsRef.current;
      const target = e.target as Node;
      if (input?.contains(target) || list?.contains(target)) return;
      setShowSuggestions(false);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [showSuggestions]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!showSuggestions && query.trim()) { setShowSuggestions(true); return; }
      if (suggestions.length) setHighlightIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (suggestions.length) setHighlightIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      handleSelect(suggestions[highlightIdx].token);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="yangdo-license-input">
      <FormField label="업종 선택" htmlFor={inputId} required hint="예: 토목건축공사업, 전기공사업" error={error}>
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
            aria-haspopup="listbox"
            aria-autocomplete="list"
            autoComplete="off"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={() => { if (query.trim()) setShowSuggestions(true); }}
            onKeyDown={handleKeyDown}
            placeholder="업종명 입력..."
          />
          {query && (
            <button
              type="button"
              className="calc-combobox-clear"
              onClick={() => { handleInputChange(""); inputRef.current?.focus(); }}
              aria-label="선택 초기화"
              tabIndex={-1}
            >
              <X size={14} aria-hidden="true" />
            </button>
          )}
          {showSuggestions && suggestions.length > 0 && (
            <ul ref={suggestionsRef} id={listId} className="yangdo-suggestions" role="listbox" onPointerDown={(e) => e.preventDefault()}>
              {suggestions.map((s, i) => (
                <li
                  key={s.token}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === highlightIdx}
                  className={`yangdo-suggestion${i === highlightIdx ? " yangdo-suggestion--active" : ""}`}
                  onPointerDown={() => handleSelect(s.token)}
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
