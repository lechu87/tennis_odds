#!/usr/bin/env python3
"""Collect unknown player names from logs and suggest dictionary updates.

This script reads config/tennis_dictionary.json, scans log files for unknown player lines
emitted by the scrapers (e.g. "Name": ["Name"], or ["Name"]), and produces
a single markdown report with suggestions where aliases could be added.

It also performs a simple tournament-name audit from *_tennis*.json files to help
identify names that should be unified.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

UNKNOWN_PLAYER_RE = re.compile(r'^\s*"(?P<name>[^"]+)"\s*:\s*\[\s*"[^"]*"\s*\],\s*$')
UNKNOWN_PLAYER_BRACKET_RE = re.compile(r'^\s*\[\s*"(?P<name>[^"]+)"\s*\]\s*$')


@dataclass
class Suggestion:
    canonical: str
    score: float
    matched_alias: str


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9/ ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def surname_token(name: str) -> str:
    if ',' in name:
        left = name.split(',', 1)[0].strip()
        parts = [p for p in normalize_text(left).split() if p]
        return parts[-1] if parts else ""

    norm = normalize_text(name)
    parts = [p for p in re.split(r"[ /]", norm) if p]
    return parts[-1] if parts else ""


def name_variants(name: str) -> List[str]:
    raw = (name or '').strip()
    variants = set()

    direct = normalize_text(raw)
    if direct:
        variants.add(direct)
        variants.add(" ".join(sorted(direct.split())))

    if ',' in raw:
        left, right = raw.split(',', 1)
        left = left.strip()
        right = right.strip()
        if left and right:
            reordered = normalize_text(f"{right} {left}")
            if reordered:
                variants.add(reordered)
                variants.add(" ".join(sorted(reordered.split())))

    return [variant for variant in variants if variant]


def load_players_dictionary(path: Path) -> Dict[str, List[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    players = payload.get("players", {})
    if not isinstance(players, dict):
        raise ValueError("Invalid tennis dictionary format: 'players' must be an object")
    cleaned: Dict[str, List[str]] = {}
    for canonical, aliases in players.items():
        if isinstance(aliases, list):
            cleaned[canonical] = [str(a) for a in aliases]
        else:
            cleaned[canonical] = [str(aliases)]
    return cleaned


def expand_player_entries(players: Dict[str, List[str]]) -> List[Tuple[str, str, str]]:
    entries: List[Tuple[str, str, str]] = []
    for canonical, aliases in players.items():
        aliases_full = set(aliases)
        aliases_full.add(canonical)
        for alias in aliases_full:
            entries.append((canonical, alias, normalize_text(alias)))
    return entries


def parse_unknown_players(log_paths: Iterable[Path]) -> Tuple[Counter, Dict[str, set], Counter]:
    names = Counter()
    sources: Dict[str, set] = defaultdict(set)
    skipped_market_lines = Counter()

    for path in log_paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line in lines:
            line = line.rstrip("\n")
            m = UNKNOWN_PLAYER_RE.match(line)
            if m:
                name = m.group("name").strip()
                if name:
                    names[name] += 1
                    sources[name].add(path.name)
                continue

            m2 = UNKNOWN_PLAYER_BRACKET_RE.match(line)
            if m2:
                name = m2.group("name").strip()
                if name:
                    names[name] += 1
                    sources[name].add(path.name)
                continue

            if "Brak w słowniku:" in line:
                skipped_market_lines[path.name] += 1

    return names, sources, skipped_market_lines


def score_candidate(query: str, candidate_norm: str, candidate_alias: str) -> float:
    q_variants = name_variants(query)
    c_variants = name_variants(candidate_alias)
    if candidate_norm:
        c_variants.append(candidate_norm)

    if not q_variants or not c_variants:
        return 0.0

    best_pair = (q_variants[0], c_variants[0])
    ratio = 0.0
    for qv in q_variants:
        for cv in c_variants:
            current = difflib.SequenceMatcher(None, qv, cv).ratio()
            if current > ratio:
                ratio = current
                best_pair = (qv, cv)

    q_surname = surname_token(query)
    c_surname = surname_token(candidate_alias)
    if q_surname and c_surname and q_surname == c_surname:
        ratio += 0.15
    elif q_surname and c_surname and q_surname != c_surname:
        ratio -= 0.08

    # Initial + surname pattern, e.g. "Nys H" -> "Nys Hugo"
    q_parts = best_pair[0].split()
    c_parts = best_pair[1].split()
    if len(q_parts) >= 2 and len(c_parts) >= 2:
        if q_parts[0] == c_parts[0] and q_parts[1][:1] == c_parts[1][:1]:
            ratio += 0.08

    common_tokens = set(q_parts) & set(c_parts)
    if not common_tokens:
        ratio -= 0.08

    return min(ratio, 1.0)


def suggest_for_name(
    name: str,
    entries: Sequence[Tuple[str, str, str]],
    limit: int = 3,
    allow_doubles: bool = False,
) -> List[Suggestion]:
    scores: Dict[str, Suggestion] = {}
    for canonical, alias, alias_norm in entries:
        if not allow_doubles and ("/" in canonical or "/" in alias):
            continue
        score = score_candidate(name, alias_norm, alias)
        if score < 0.72:
            continue
        prev = scores.get(canonical)
        if prev is None or score > prev.score:
            scores[canonical] = Suggestion(canonical=canonical, score=score, matched_alias=alias)

    ranked = sorted(scores.values(), key=lambda x: (-x.score, x.canonical))
    return ranked[:limit]


def is_known_name(name: str, players: Dict[str, List[str]]) -> bool:
    if name in players:
        return True
    for aliases in players.values():
        if name in aliases:
            return True
    return False


def gather_tournaments(json_paths: Iterable[Path]) -> Counter:
    counts = Counter()
    for path in json_paths:
        if not path.exists() or not path.is_file():
            continue
        if path.name == "tennis_dictionary.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue

        items = payload if isinstance(payload, list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            tournament = item.get("tournament")
            if isinstance(tournament, str) and tournament.strip():
                counts[tournament.strip()] += 1
    return counts


def tournament_similarity_pairs(tournaments: Sequence[str], cutoff: float = 0.88, max_pairs: int = 40) -> List[Tuple[str, str, float]]:
    norm_to_raw = [(t, normalize_text(t)) for t in tournaments]
    pairs: List[Tuple[str, str, float]] = []
    for i in range(len(norm_to_raw)):
        a_raw, a_norm = norm_to_raw[i]
        if not a_norm:
            continue
        for j in range(i + 1, len(norm_to_raw)):
            b_raw, b_norm = norm_to_raw[j]
            if not b_norm:
                continue
            score = difflib.SequenceMatcher(None, a_norm, b_norm).ratio()
            if score >= cutoff and a_raw != b_raw:
                pairs.append((a_raw, b_raw, score))
    pairs.sort(key=lambda x: (-x[2], x[0], x[1]))
    return pairs[:max_pairs]


def format_suggestions(suggestions: Sequence[Suggestion]) -> str:
    if not suggestions:
        return "-"
    return "; ".join(f"{s.canonical} ({s.score:.2f}, via '{s.matched_alias}')" for s in suggestions)


def build_report(
    unknown_names: Counter,
    sources: Dict[str, set],
    skipped_market_lines: Counter,
    players: Dict[str, List[str]],
    entries: Sequence[Tuple[str, str, str]],
    tournament_counts: Counter,
) -> str:
    lines: List[str] = []
    lines.append("# Dictionary Update Suggestions")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Unknown-name entries found in logs: {sum(unknown_names.values())}")
    lines.append(f"- Distinct unknown names: {len(unknown_names)}")
    lines.append(f"- Market 'Brak w slowniku' lines (not player names): {sum(skipped_market_lines.values())}")
    lines.append("")

    lines.append("## Unknown Players From Logs")
    lines.append("")
    lines.append("| Unknown Name | Count | Known Already | Suggestions (canonical target) | Source Logs |")
    lines.append("|---|---:|:---:|---|---|")

    for name, count in unknown_names.most_common():
        known = is_known_name(name, players)
        if " / " in name:
            parts = [p.strip() for p in name.split("/") if p.strip()]
            part_suggestions = []
            for part in parts:
                sug = suggest_for_name(part, entries)
                part_suggestions.append(f"{part} -> {format_suggestions(sug)}")
            suggestions_text = " || ".join(part_suggestions) if part_suggestions else "-"
        else:
            suggestions_text = format_suggestions(suggest_for_name(name, entries, allow_doubles=False))

        source_text = ", ".join(sorted(sources.get(name, set())))
        lines.append(f"| {name} | {count} | {'yes' if known else 'no'} | {suggestions_text} | {source_text} |")

    if not unknown_names:
        lines.append("| - | - | - | - | - |")

    lines.append("")
    lines.append("## Tournament Name Audit")
    lines.append("")

    if tournament_counts:
        lines.append(f"- Distinct tournaments in scanned JSON files: {len(tournament_counts)}")
        lines.append("- Top 30 by frequency:")
        lines.append("")
        lines.append("| Tournament | Count |")
        lines.append("|---|---:|")
        for t, c in tournament_counts.most_common(30):
            lines.append(f"| {t} | {c} |")
        lines.append("")
        lines.append("- Near-duplicate candidates to consider unifying:")
        lines.append("")
        pairs = tournament_similarity_pairs(list(tournament_counts.keys()))
        if pairs:
            lines.append("| Tournament A | Tournament B | Similarity |")
            lines.append("|---|---|---:|")
            for a, b, score in pairs:
                lines.append(f"| {a} | {b} | {score:.2f} |")
        else:
            lines.append("No near-duplicate pairs found at current threshold.")
    else:
        lines.append("No tournament data found in scanned JSON files.")

    lines.append("")
    lines.append("## Notes")
    lines.append("- Lines with 'Brak w slowniku:' in logs are market-name mapping misses, not missing player dictionary entries.")
    lines.append("- Player dictionary misses are captured by lines like \"Name\": [\"Name\"], emitted by scraper code.")

    return "\n".join(lines) + "\n"


def existing_paths(patterns: Sequence[str], root: Path) -> List[Path]:
    out: List[Path] = []
    for pattern in patterns:
        out.extend(root.glob(pattern))
    uniq = sorted({p.resolve() for p in out if p.is_file()})
    return [Path(p) for p in uniq]


def load_dictionary_payload(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "players" not in payload or not isinstance(payload["players"], dict):
        raise ValueError("Invalid tennis dictionary format: missing 'players' object")
    return payload


def write_dictionary_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=3) + "\n", encoding="utf-8")


def generate_input_list_from_logs(
    log_paths: Sequence[Path],
    players: Dict[str, List[str]],
    output_path: Path,
) -> Tuple[int, int]:
    unknown_names, _, _ = parse_unknown_players(log_paths)
    lines: List[str] = []
    kept = 0
    for name, count in unknown_names.most_common():
        if is_known_name(name, players):
            continue
        lines.append(f"{name}\t{count}")
        kept += 1
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(unknown_names), kept


def parse_input_names(input_path: Path) -> List[str]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ordered: List[str] = []
    seen: Set[str] = set()

    for raw in input_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m = UNKNOWN_PLAYER_RE.match(line)
        if m:
            candidate = m.group("name").strip()
        else:
            m2 = UNKNOWN_PLAYER_BRACKET_RE.match(line)
            if m2:
                candidate = m2.group("name").strip()
            else:
                candidate = line.split("\t", 1)[0].strip()

        if candidate and candidate not in seen:
            ordered.append(candidate)
            seen.add(candidate)

    return ordered


def load_skipped(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()

    if isinstance(payload, list):
        return {str(x) for x in payload}
    if isinstance(payload, dict) and isinstance(payload.get("skipped"), list):
        return {str(x) for x in payload["skipped"]}
    return set()


def save_skipped(path: Path, skipped: Set[str]) -> None:
    payload = {"skipped": sorted(skipped)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_alias(players: Dict[str, List[str]], canonical: str, alias: str) -> bool:
    if canonical not in players:
        players[canonical] = [canonical]
    aliases = players[canonical]
    if alias in aliases:
        return False
    aliases.append(alias)
    return True


def interactive_update(
    payload: dict,
    input_names: List[str],
    skipped_path: Path,
    decisions_path: Path,
) -> None:
    players: Dict[str, List[str]] = payload["players"]
    skipped = load_skipped(skipped_path)
    entries = expand_player_entries(players)

    decisions: List[dict] = []
    queue = list(input_names)
    added_count = 0
    new_count = 0
    skipped_now = 0
    already_known = 0

    idx = 0
    while idx < len(queue):
        name = queue[idx].strip()
        idx += 1
        if not name:
            continue

        if name in skipped:
            continue

        if is_known_name(name, players):
            already_known += 1
            continue

        print("\n" + "=" * 80)
        print(f"[{idx}/{len(queue)}] {name}")

        if " / " in name:
            print("Wykryto parę graczy. Możesz rozbić na osobne nazwiska opcją 'd'.")

        suggestions = suggest_for_name(name, entries, limit=5, allow_doubles=False)
        if suggestions:
            print("Proponowane dopasowania:")
            for i, s in enumerate(suggestions, start=1):
                print(f"  {i}. {s.canonical} (score={s.score:.2f}, przez alias='{s.matched_alias}')")
        else:
            print("Brak sensownych sugestii.")

        print("Opcje:")
        print("  1..N  - dodaj jako alias do wskazanego kanonicznego wpisu")
        print("  n     - dodaj jako nowy osobny wpis")
        print("  e     - wpisz ręcznie nazwę kanoniczną, do której dopisać alias")
        print("  d     - rozbij wpis typu 'A / B' na osobne elementy")
        print("  s     - pomiń i zapamiętaj (nie pytaj ponownie)")
        print("  k     - pomiń teraz (bez zapamiętania)")
        print("  q     - zakończ i zapisz zmiany")

        choice = input("Wybór: ").strip().lower()

        if choice == "q":
            break
        if choice == "k":
            decisions.append({"name": name, "action": "skip_once"})
            continue
        if choice == "s":
            skipped.add(name)
            skipped_now += 1
            decisions.append({"name": name, "action": "skip_remember"})
            continue
        if choice == "d":
            if " / " in name:
                parts = [p.strip() for p in name.split("/") if p.strip()]
                if parts:
                    queue[idx:idx] = parts
                    decisions.append({"name": name, "action": "split", "parts": parts})
                    continue
            print("Nie udało się rozbić wpisu. Użyj innej opcji.")
            idx -= 1
            continue
        if choice == "n":
            if name not in players:
                players[name] = [name]
                new_count += 1
                entries = expand_player_entries(players)
            decisions.append({"name": name, "action": "add_new"})
            continue
        if choice == "e":
            target = input("Podaj nazwę kanoniczną: ").strip()
            if not target:
                print("Pusta nazwa kanoniczna. Spróbuj ponownie.")
                idx -= 1
                continue
            changed = add_alias(players, target, name)
            if changed:
                added_count += 1
                entries = expand_player_entries(players)
            decisions.append({"name": name, "action": "add_manual", "target": target, "changed": changed})
            continue

        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(suggestions):
                target = suggestions[num - 1].canonical
                changed = add_alias(players, target, name)
                if changed:
                    added_count += 1
                    entries = expand_player_entries(players)
                decisions.append({"name": name, "action": "add_suggested", "target": target, "changed": changed})
                continue

        print("Nieznana opcja. Powtórzę ten sam wpis.")
        idx -= 1

    save_skipped(skipped_path, skipped)
    decisions_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nPodsumowanie interaktywnego dodawania:")
    print(f"- Dodane aliasy: {added_count}")
    print(f"- Dodane nowe wpisy kanoniczne: {new_count}")
    print(f"- Pominięte i zapamiętane: {skipped_now}")
    print(f"- Już obecne w słowniku: {already_known}")
    print(f"- Zapis decyzji: {decisions_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest and apply player dictionary updates")
    parser.add_argument(
        "--dictionary",
        default="config/tennis_dictionary.json",
        help="Path to tennis dictionary JSON (default: config/tennis_dictionary.json)",
    )
    parser.add_argument(
        "--logs",
        nargs="*",
        default=["logs/*.log", "betclic_log", "bc_log*", "*_log", "logfile_*.log"],
        help="Glob patterns for log files to scan",
    )
    parser.add_argument(
        "--tournament-json",
        nargs="*",
        default=["*tennis*.json"],
        help="Glob patterns for JSON files used in tournament audit",
    )
    parser.add_argument(
        "--output",
        default="data/reports/dictionary_review.md",
        help="Output markdown report path (default: data/reports/dictionary_review.md)",
    )
    parser.add_argument(
        "--input-file",
        default="data/runtime/players_to_add.txt",
        help="Path to input list of names for interactive mode (default: data/runtime/players_to_add.txt)",
    )
    parser.add_argument(
        "--generate-input",
        action="store_true",
        help="Generate input file from logs (names + count) before other actions",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive confirmation flow and update dictionary",
    )
    parser.add_argument(
        "--skipped-file",
        default="data/runtime/players_skipped.json",
        help="File storing skipped names to remember (default: data/runtime/players_skipped.json)",
    )
    parser.add_argument(
        "--decisions-file",
        default="data/runtime/players_decisions.json",
        help="File storing interactive decisions (default: data/runtime/players_decisions.json)",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not generate markdown report",
    )
    args = parser.parse_args()

    root = Path.cwd()
    dictionary_path = Path(args.dictionary)
    if not dictionary_path.exists():
        raise FileNotFoundError(f"Dictionary file not found: {dictionary_path}")

    payload = load_dictionary_payload(dictionary_path)
    players = load_players_dictionary(dictionary_path)

    log_paths = existing_paths(args.logs, root)

    input_path = Path(args.input_file)
    skipped_path = Path(args.skipped_file)
    decisions_path = Path(args.decisions_file)

    if args.generate_input:
        total_raw, kept = generate_input_list_from_logs(log_paths, players, input_path)
        print(f"Input file generated: {input_path} (raw={total_raw}, kept={kept})")

    if args.interactive:
        input_names = parse_input_names(input_path)
        if not input_names:
            print(f"No names found in input file: {input_path}")
        else:
            interactive_update(
                payload=payload,
                input_names=input_names,
                skipped_path=skipped_path,
                decisions_path=decisions_path,
            )
            write_dictionary_payload(dictionary_path, payload)
            print(f"Dictionary updated: {dictionary_path}")

    if args.no_report:
        return 0

    # Refresh in case interactive mode modified the dictionary.
    players = load_players_dictionary(dictionary_path)
    entries = expand_player_entries(players)
    unknown_names, sources, skipped_market_lines = parse_unknown_players(log_paths)

    tournament_json_paths = existing_paths(args.tournament_json, root)
    tournament_counts = gather_tournaments(tournament_json_paths)

    report = build_report(
        unknown_names=unknown_names,
        sources=sources,
        skipped_market_lines=skipped_market_lines,
        players=players,
        entries=entries,
        tournament_counts=tournament_counts,
    )

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")

    print(f"Report written to: {output_path}")
    print(f"Scanned logs: {len(log_paths)}")
    print(f"Unknown distinct names: {len(unknown_names)}")
    print(f"Distinct tournaments: {len(tournament_counts)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
