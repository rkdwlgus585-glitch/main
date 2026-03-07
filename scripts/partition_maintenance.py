#!/usr/bin/env python3
"""Maintain workspace partitions for calculator/site session artifacts.

Usage examples:
  py -3 scripts/partition_maintenance.py --status
  py -3 scripts/partition_maintenance.py --sync --restore-missing --relocate-site-temp --status
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "workspace_partitions" / "partition_map.json"
SITE_TMP_DIR = ROOT / "workspace_partitions" / "site_session" / "tmp"


@dataclass
class MappingEntry:
    source: Path
    partition: Path


def _load_entries() -> Dict[str, List[MappingEntry]]:
    if not MAP_PATH.exists():
        raise FileNotFoundError(f"partition map not found: {MAP_PATH}")
    data = json.loads(MAP_PATH.read_text(encoding="utf-8-sig"))
    out: Dict[str, List[MappingEntry]] = {}
    for bucket, items in data.items():
        entries: List[MappingEntry] = []
        for raw in items:
            src = ROOT / str(raw["source"])
            dst = ROOT / str(raw["partition"])
            entries.append(MappingEntry(source=src, partition=dst))
        out[bucket] = entries
    return out


def _copy(src: Path, dst: Path, dry_run: bool) -> str:
    if not src.exists():
        return "missing-source"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        src_stat = src.stat()
        dst_stat = dst.stat()
        if src_stat.st_size == dst_stat.st_size and int(src_stat.st_mtime) == int(dst_stat.st_mtime):
            return "unchanged"
    if dry_run:
        return "would-copy"
    shutil.copy2(src, dst)
    return "copied"


def _move(src: Path, dst: Path, dry_run: bool) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return "would-move"
    if dst.exists():
        dst.unlink()
    shutil.move(str(src), str(dst))
    return "moved"


def sync_to_partition(entries: Iterable[MappingEntry], dry_run: bool) -> Dict[str, int]:
    result = {"copied": 0, "unchanged": 0, "missing-source": 0, "would-copy": 0}
    for e in entries:
        state = _copy(e.source, e.partition, dry_run=dry_run)
        if state not in result:
            result[state] = 0
        result[state] += 1
    return result


def restore_missing(entries: Iterable[MappingEntry], dry_run: bool) -> Dict[str, int]:
    result = {"restored": 0, "skipped": 0, "would-restore": 0}
    for e in entries:
        if e.source.exists():
            result["skipped"] += 1
            continue
        if not e.partition.exists():
            result["skipped"] += 1
            continue
        e.source.parent.mkdir(parents=True, exist_ok=True)
        if dry_run:
            result["would-restore"] += 1
            continue
        shutil.copy2(e.partition, e.source)
        result["restored"] += 1
    return result


def relocate_site_tmp(dry_run: bool) -> Dict[str, int]:
    SITE_TMP_DIR.mkdir(parents=True, exist_ok=True)
    files = [p for p in ROOT.glob("tmp_*") if p.is_file()]
    moved = 0
    skipped = 0
    for src in files:
        dst = SITE_TMP_DIR / src.name
        state = _move(src, dst, dry_run=dry_run)
        if state in {"moved", "would-move"}:
            moved += 1
        else:
            skipped += 1
    return {"candidate": len(files), "moved": moved, "skipped": skipped}


def status(entries_map: Dict[str, List[MappingEntry]]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    out["root_tmp_files"] = len([p for p in ROOT.glob("tmp_*") if p.is_file()])
    out["site_tmp_files"] = len(list(SITE_TMP_DIR.glob("tmp_*"))) if SITE_TMP_DIR.exists() else 0
    buckets: Dict[str, Dict[str, int]] = {}
    for bucket, entries in entries_map.items():
        src_ok = sum(1 for e in entries if e.source.exists())
        dst_ok = sum(1 for e in entries if e.partition.exists())
        buckets[bucket] = {
            "mapped": len(entries),
            "source_exists": src_ok,
            "partition_exists": dst_ok,
        }
    out["buckets"] = buckets
    return out


def _flatten(entries_map: Dict[str, List[MappingEntry]]) -> List[MappingEntry]:
    out: List[MappingEntry] = []
    for entries in entries_map.values():
        out.extend(entries)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain workspace partitions")
    parser.add_argument("--sync", action="store_true", help="copy source files to partition paths")
    parser.add_argument("--restore-missing", action="store_true", help="restore missing source files from partition")
    parser.add_argument("--relocate-site-temp", action="store_true", help="move root tmp_* files into site partition tmp")
    parser.add_argument("--status", action="store_true", help="print partition status JSON")
    parser.add_argument("--dry-run", action="store_true", help="show actions without modifying files")
    args = parser.parse_args()

    entries_map = _load_entries()
    all_entries = _flatten(entries_map)
    touched = False

    if not any([args.sync, args.restore_missing, args.relocate_site_temp, args.status]):
        args.sync = True
        args.restore_missing = True
        args.relocate_site_temp = True
        args.status = True

    report: Dict[str, object] = {}

    if args.sync:
        report["sync"] = sync_to_partition(all_entries, dry_run=args.dry_run)
        touched = True
    if args.restore_missing:
        report["restore_missing"] = restore_missing(all_entries, dry_run=args.dry_run)
        touched = True
    if args.relocate_site_temp:
        report["relocate_site_temp"] = relocate_site_tmp(dry_run=args.dry_run)
        touched = True
    if args.status or touched:
        report["status"] = status(entries_map)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

