-- Metabase queries for comparing Ace markets between bookmakers.
-- Flat schema: odds(tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date)
-- Focus: line differences and odds differences for Ace markets.

-- ============================================================================
-- 1. DETAILED ACE COMPARISON FOR ONE MATCH / DATE RANGE
-- ============================================================================
-- Use this as the main table in Metabase.
-- Parameters:
--   {{date_from}} optional date
--   {{date_to}} optional date
--   {{tournament}} optional text
--   {{player}} optional text

WITH ace_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        name,
        cat1,
        cat2,
        value,
        odd,
        bukmacher,
        CASE
            WHEN value ~ '([0-9]+([\.,][0-9]+)?)' THEN replace((regexp_match(value, '([0-9]+([\.,][0-9]+)?)'))[1], ',', '.')::numeric
            ELSE NULL
        END AS line_value,
        CASE
            WHEN value ILIKE 'Powyżej %' THEN 'over'
            WHEN value ILIKE 'Poniżej %' THEN 'under'
            ELSE 'other'
        END AS line_side
    FROM odds
    WHERE name = 'Ace'
      AND cat1 IN ('overall', 'player1', 'player2')
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
      [[AND (player1 ILIKE '%' || {{player}} || '%' OR player2 ILIKE '%' || {{player}} || '%')]]
), line_stats AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        cat1,
        value,
        COUNT(DISTINCT bukmacher) AS bookmakers_on_line,
        MAX(odd) AS best_odd,
        MIN(odd) AS worst_odd
    FROM ace_base
    GROUP BY date, tournament, player1, player2, cat1, value
)
SELECT
    b.date,
    b.tournament,
    b.player1,
    b.player2,
    b.cat1,
    CASE
        WHEN b.cat1 = 'overall' THEN 'Ace match total'
        WHEN b.cat1 = 'player1' THEN b.player1 || ' ace line'
        WHEN b.cat1 = 'player2' THEN b.player2 || ' ace line'
        ELSE b.cat1
    END AS market_label,
    b.value AS line_label,
    b.line_side,
    b.line_value,
    b.bukmacher,
    b.odd,
    ls.bookmakers_on_line,
    ROUND(ls.best_odd, 4) AS best_odd,
    ROUND(ls.worst_odd, 4) AS worst_odd,
    ROUND(ls.best_odd - ls.worst_odd, 4) AS odd_spread,
    RANK() OVER (
        PARTITION BY b.date, b.tournament, b.player1, b.player2, b.cat1, b.value
        ORDER BY b.odd DESC
    ) AS odds_rank
FROM ace_base b
JOIN line_stats ls
  ON ls.date = b.date
 AND ls.tournament = b.tournament
 AND ls.player1 = b.player1
 AND ls.player2 = b.player2
 AND ls.cat1 = b.cat1
 AND ls.value = b.value
ORDER BY b.date DESC, b.tournament, b.player1, b.player2, b.cat1, b.line_value NULLS LAST, b.odd DESC, b.bukmacher;

-- ============================================================================
-- 2. WHERE BOOKMAKERS DISAGREE ON THE ACE LINE
-- ============================================================================
-- Shows matches where the offered line differs between bookmakers.

WITH ace_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        cat1,
        value,
        odd,
        bukmacher,
        CASE
            WHEN value ~ '([0-9]+([\.,][0-9]+)?)' THEN replace((regexp_match(value, '([0-9]+([\.,][0-9]+)?)'))[1], ',', '.')::numeric
            ELSE NULL
        END AS line_value,
        CASE
            WHEN value ILIKE 'Powyżej %' THEN 'over'
            WHEN value ILIKE 'Poniżej %' THEN 'under'
            ELSE 'other'
        END AS line_side
    FROM odds
    WHERE name = 'Ace'
      AND cat1 IN ('overall', 'player1', 'player2')
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
)
SELECT
    date,
    tournament,
    player1,
    player2,
    cat1,
    line_side,
    MIN(line_value) AS lowest_line,
    MAX(line_value) AS highest_line,
    ROUND(MAX(line_value) - MIN(line_value), 1) AS line_span,
    COUNT(DISTINCT line_value) AS distinct_lines,
    COUNT(DISTINCT bukmacher) AS bookmakers,
    ROUND(MIN(odd), 4) AS worst_odd,
    ROUND(MAX(odd), 4) AS best_odd,
    ROUND(MAX(odd) - MIN(odd), 4) AS odd_spread,
    STRING_AGG(bukmacher || ': ' || value || ' @ ' || odd::text, ' | ' ORDER BY bukmacher) AS offers
FROM ace_base
WHERE line_value IS NOT NULL
GROUP BY date, tournament, player1, player2, cat1, line_side
HAVING COUNT(DISTINCT line_value) > 1 OR (MAX(odd) - MIN(odd)) >= 0.15
ORDER BY line_span DESC NULLS LAST, odd_spread DESC, bookmakers DESC, tournament, player1, player2, cat1, line_side;

-- ============================================================================
-- 3. BOOKMAKER SUMMARY FOR ACE MARKETS
-- ============================================================================
-- Quick comparison: who posts higher ace lines / better odds more often.

WITH ace_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        cat1,
        value,
        odd,
        bukmacher,
        CASE
            WHEN value ~ '([0-9]+([\.,][0-9]+)?)' THEN replace((regexp_match(value, '([0-9]+([\.,][0-9]+)?)'))[1], ',', '.')::numeric
            ELSE NULL
        END AS line_value
    FROM odds
    WHERE name = 'Ace'
      AND cat1 IN ('overall', 'player1', 'player2')
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
)
SELECT
    bukmacher,
    COUNT(*) AS rows_count,
    COUNT(DISTINCT date || '|' || tournament || '|' || player1 || '|' || player2) AS matches_count,
    COUNT(DISTINCT value) AS distinct_ace_lines,
    ROUND(AVG(line_value)::numeric, 2) AS avg_line,
    ROUND(MIN(line_value)::numeric, 2) AS min_line,
    ROUND(MAX(line_value)::numeric, 2) AS max_line,
    ROUND(AVG(odd)::numeric, 4) AS avg_odd,
    ROUND(MIN(odd)::numeric, 4) AS min_odd,
    ROUND(MAX(odd)::numeric, 4) AS max_odd,
    ROUND(MAX(odd) - MIN(odd), 4) AS odd_range
FROM ace_base
GROUP BY bukmacher
ORDER BY matches_count DESC, avg_line DESC, avg_odd DESC;

-- ============================================================================
-- 4. BIGGEST ACE DISAGREEMENTS
-- ============================================================================
-- Fast Metabase table for spotting the most interesting gaps.

WITH ace_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        cat1,
        value,
        odd,
        bukmacher,
        CASE
            WHEN value ~ '([0-9]+([\.,][0-9]+)?)' THEN replace((regexp_match(value, '([0-9]+([\.,][0-9]+)?)'))[1], ',', '.')::numeric
            ELSE NULL
        END AS line_value,
        CASE
            WHEN value ILIKE 'Powyżej %' THEN 'over'
            WHEN value ILIKE 'Poniżej %' THEN 'under'
            ELSE 'other'
        END AS line_side
    FROM odds
    WHERE name = 'Ace'
      AND cat1 IN ('overall', 'player1', 'player2')
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
      [[AND (player1 ILIKE '%' || {{player}} || '%' OR player2 ILIKE '%' || {{player}} || '%')]]
), ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY date, tournament, player1, player2, cat1, value
            ORDER BY odd DESC, bukmacher
        ) AS rn_best,
        ROW_NUMBER() OVER (
            PARTITION BY date, tournament, player1, player2, cat1, value
            ORDER BY odd ASC, bukmacher
        ) AS rn_worst
    FROM ace_base
), stats AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        cat1,
        value,
        line_value,
        line_side,
        COUNT(DISTINCT bukmacher) AS bookmakers,
        MAX(odd) AS best_odd,
        MIN(odd) AS worst_odd
    FROM ace_base
    GROUP BY date, tournament, player1, player2, cat1, value, line_value, line_side
)
SELECT
    s.date,
    s.tournament,
    s.player1,
    s.player2,
    s.cat1,
    CASE
        WHEN s.cat1 = 'overall' THEN 'Ace match total'
        WHEN s.cat1 = 'player1' THEN s.player1 || ' ace line'
        WHEN s.cat1 = 'player2' THEN s.player2 || ' ace line'
        ELSE s.cat1
    END AS market_label,
    s.value AS line_label,
    s.line_side,
    s.line_value,
    s.bookmakers,
    ROUND(s.best_odd, 4) AS best_odd,
    best_bookmaker.bukmacher AS best_bookmaker,
    ROUND(s.worst_odd, 4) AS worst_odd,
    worst_bookmaker.bukmacher AS worst_bookmaker,
    ROUND(s.best_odd - s.worst_odd, 4) AS odd_spread,
    ROUND((s.best_odd - s.worst_odd) / NULLIF(s.worst_odd, 0) * 100, 2) AS odd_spread_pct
FROM stats s
LEFT JOIN ranked best_bookmaker
  ON best_bookmaker.date = s.date
 AND best_bookmaker.tournament = s.tournament
 AND best_bookmaker.player1 = s.player1
 AND best_bookmaker.player2 = s.player2
 AND best_bookmaker.cat1 = s.cat1
 AND best_bookmaker.value = s.value
 AND best_bookmaker.rn_best = 1
LEFT JOIN ranked worst_bookmaker
  ON worst_bookmaker.date = s.date
 AND worst_bookmaker.tournament = s.tournament
 AND worst_bookmaker.player1 = s.player1
 AND worst_bookmaker.player2 = s.player2
 AND worst_bookmaker.cat1 = s.cat1
 AND worst_bookmaker.value = s.value
 AND worst_bookmaker.rn_worst = 1
WHERE s.line_value IS NOT NULL
ORDER BY odd_spread DESC, odd_spread_pct DESC, s.bookmakers DESC, s.date DESC, s.tournament, s.player1, s.player2, s.cat1, s.line_value;

-- ============================================================================
-- 5. ACE PIVOT - BOOKMAKERS IN COLUMNS
-- ============================================================================
-- One row per aligned Ace line. Betfan integers are normalized to half-lines.
-- Columns are the bookmakers, so missing offers stay NULL.
-- Parameters:
--   {{date_from}} optional date
--   {{date_to}} optional date
--   {{tournament}} optional text
--   {{player}} optional text

WITH ace_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        cat1,
        value,
        odd,
        bukmacher,
        CASE
            WHEN value ~ '([0-9]+([\.,][0-9]+)?)' THEN replace((regexp_match(value, '([0-9]+([\.,][0-9]+)?)'))[1], ',', '.')::numeric
            ELSE NULL
        END AS raw_line_value,
        CASE
            WHEN bukmacher = 'betfan'
             AND value ~ '^[0-9]+$'
             AND value <> '0'
            THEN replace(value, ',', '.')::numeric - 0.5
            WHEN value ~ '([0-9]+([\.,][0-9]+)?)' THEN replace((regexp_match(value, '([0-9]+([\.,][0-9]+)?)'))[1], ',', '.')::numeric
            ELSE NULL
        END AS norm_line_value,
        CASE
            WHEN value ILIKE 'Powyżej %' THEN 'over'
            WHEN value ILIKE 'Poniżej %' THEN 'under'
            ELSE 'other'
        END AS line_side
    FROM odds
    WHERE name = 'Ace'
      AND cat1 IN ('overall', 'player1', 'player2')
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
      [[AND (player1 ILIKE '%' || {{player}} || '%' OR player2 ILIKE '%' || {{player}} || '%')]]
)
SELECT
    date,
    tournament,
    player1,
    player2,
    cat1,
    CASE
        WHEN cat1 = 'overall' THEN 'Ace match total'
        WHEN cat1 = 'player1' THEN player1 || ' ace line'
        WHEN cat1 = 'player2' THEN player2 || ' ace line'
        ELSE cat1
    END AS market_label,
    line_side,
    norm_line_value,
    COUNT(DISTINCT bukmacher) AS bookmakers_on_line,
    MAX(odd) AS best_odd,
    MIN(odd) AS worst_odd,
    ROUND(MAX(odd) - MIN(odd), 4) AS odd_spread,
    MAX(odd) FILTER (WHERE bukmacher = 'betclic') AS betclic,
    MAX(odd) FILTER (WHERE bukmacher = 'betfan') AS betfan,
    MAX(odd) FILTER (WHERE bukmacher = 'iforbet') AS iforbet,
    MAX(odd) FILTER (WHERE bukmacher = 'etoto') AS etoto,
    MAX(odd) FILTER (WHERE bukmacher = 'totalbet') AS totalbet,
    MAX(odd) FILTER (WHERE bukmacher = 'lvbet') AS lvbet,
    MAX(odd) FILTER (WHERE bukmacher = 'fortuna') AS fortuna,
    MAX(odd) FILTER (WHERE bukmacher = 'sts') AS sts,
    MAX(odd) FILTER (WHERE bukmacher = 'forbet') AS forbet,
    STRING_AGG(DISTINCT bukmacher, ', ' ORDER BY bukmacher) AS present_bookmakers,
    STRING_AGG(bukmacher || ': ' || value || ' @ ' || odd::text, ' | ' ORDER BY bukmacher) AS offers
FROM ace_base
WHERE norm_line_value IS NOT NULL
GROUP BY date, tournament, player1, player2, cat1, line_side, norm_line_value
ORDER BY date DESC, tournament, player1, player2, cat1, norm_line_value, line_side;

-- ============================================================================
-- 6. PRACTICAL VALUE SCANNER (ALL MARKETS, PIVOT-READY)
-- ============================================================================
-- Finds rows where one bookmaker is clearly above the rest.
-- Parameters:
--   {{date_from}} optional date
--   {{date_to}} optional date
--   {{tournament}} optional text
--   {{market_name}} optional text (e.g. score, win, Gem)
--   {{min_books}} optional number (recommended 3)
--   {{min_spread_pct}} optional number (recommended 6)
--   {{min_odd}} optional number (recommended 1.2)
--   {{max_odd}} optional number (recommended 8)

WITH base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        name,
        cat1,
        cat2,
        value,
        bukmacher,
        odd,
        COALESCE(NULLIF(TRIM(value), ''), NULLIF(TRIM(cat2), '')) AS outcome_label
    FROM odds
    WHERE odd IS NOT NULL
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
      [[AND name = {{market_name}}]]
), agg AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        name,
        cat1,
        cat2,
        value,
        outcome_label,
        COUNT(DISTINCT bukmacher) AS books,
        MAX(odd) AS best_odd,
        MIN(odd) AS worst_odd,
        AVG(odd) AS avg_odd,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY odd) AS med_odd,
        (ARRAY_AGG(bukmacher ORDER BY odd DESC))[1] AS best_bookmaker,
        (ARRAY_AGG(bukmacher ORDER BY odd ASC))[1] AS worst_bookmaker
    FROM base
    GROUP BY date, tournament, player1, player2, name, cat1, cat2, value, outcome_label
)
SELECT
    date,
    tournament,
    player1,
    player2,
    name,
    cat1,
    cat2,
    value,
    outcome_label,
    books,
    ROUND(best_odd, 4) AS best_odd,
    best_bookmaker,
    ROUND(avg_odd, 4) AS avg_odd,
    ROUND(med_odd, 4) AS med_odd,
    ROUND(worst_odd, 4) AS worst_odd,
    worst_bookmaker,
    ROUND(best_odd - worst_odd, 4) AS spread_abs,
    ROUND((best_odd - worst_odd) / NULLIF(worst_odd, 0) * 100, 2) AS spread_pct,
    ROUND((best_odd - avg_odd) / NULLIF(avg_odd, 0) * 100, 2) AS edge_vs_avg_pct,
    ROUND((best_odd - med_odd) / NULLIF(med_odd, 0) * 100, 2) AS edge_vs_median_pct,
    MAX(odd) FILTER (WHERE bukmacher = 'betclic') AS betclic,
    MAX(odd) FILTER (WHERE bukmacher = 'betfan') AS betfan,
    MAX(odd) FILTER (WHERE bukmacher = 'iforbet') AS iforbet,
    MAX(odd) FILTER (WHERE bukmacher = 'etoto') AS etoto,
    MAX(odd) FILTER (WHERE bukmacher = 'totalbet') AS totalbet,
    MAX(odd) FILTER (WHERE bukmacher = 'lvbet') AS lvbet,
    STRING_AGG(bukmacher || ': ' || odd::text, ' | ' ORDER BY bukmacher) AS offers
FROM base b
JOIN agg a USING (date, tournament, player1, player2, name, cat1, cat2, value, outcome_label)
GROUP BY
    date, tournament, player1, player2, name, cat1, cat2, value, outcome_label,
    books, best_odd, best_bookmaker, avg_odd, med_odd, worst_odd, worst_bookmaker
HAVING books >= 3
    AND best_odd BETWEEN 1.2 AND 8.0
    AND (best_odd - worst_odd) / NULLIF(worst_odd, 0) * 100 >= 6
    [[AND books >= {{min_books}}]]
    [[AND best_odd >= {{min_odd}}]]
    [[AND best_odd <= {{max_odd}}]]
    [[AND (best_odd - worst_odd) / NULLIF(worst_odd, 0) * 100 >= {{min_spread_pct}}]]
ORDER BY edge_vs_avg_pct DESC, spread_pct DESC, best_odd DESC;

-- ============================================================================
-- 7. WIN PIVOT (BOOKMAKERS SIDE-BY-SIDE)
-- ============================================================================
-- Dedicated monitor for match winner market.
-- Parameters:
--   {{date_from}} optional date
--   {{date_to}} optional date
--   {{tournament}} optional text
--   {{player}} optional text

WITH win_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        COALESCE(NULLIF(TRIM(value), ''), NULLIF(TRIM(cat2), '')) AS outcome,
        bukmacher,
        odd
    FROM odds
    WHERE name = 'win'
      AND cat1 = 'overall'
      AND odd IS NOT NULL
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
      [[AND (player1 ILIKE '%' || {{player}} || '%' OR player2 ILIKE '%' || {{player}} || '%')]]
)
SELECT
    date,
    tournament,
    player1,
    player2,
    outcome,
    COUNT(DISTINCT bukmacher) AS books,
    MAX(odd) AS best_odd,
    MIN(odd) AS worst_odd,
    ROUND(MAX(odd) - MIN(odd), 4) AS spread_abs,
    ROUND((MAX(odd) - MIN(odd)) / NULLIF(MIN(odd), 0) * 100, 2) AS spread_pct,
    MAX(odd) FILTER (WHERE bukmacher = 'betclic') AS betclic,
    MAX(odd) FILTER (WHERE bukmacher = 'betfan') AS betfan,
    MAX(odd) FILTER (WHERE bukmacher = 'iforbet') AS iforbet,
    MAX(odd) FILTER (WHERE bukmacher = 'etoto') AS etoto,
    MAX(odd) FILTER (WHERE bukmacher = 'totalbet') AS totalbet,
    MAX(odd) FILTER (WHERE bukmacher = 'lvbet') AS lvbet,
    STRING_AGG(bukmacher || ': ' || odd::text, ' | ' ORDER BY bukmacher) AS offers
FROM win_base
WHERE outcome IS NOT NULL
GROUP BY date, tournament, player1, player2, outcome
ORDER BY date DESC, tournament, player1, player2, outcome;

-- ============================================================================
-- 8. WIN SUREBET / ARB MONITOR
-- ============================================================================
-- For 2-way winner market only.
-- arb_index_pct < 100 means theoretical arbitrage exists.
-- Parameters:
--   {{date_from}} optional date
--   {{date_to}} optional date
--   {{tournament}} optional text

WITH win_base AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        COALESCE(NULLIF(TRIM(value), ''), NULLIF(TRIM(cat2), '')) AS outcome,
        bukmacher,
        odd
    FROM odds
    WHERE name = 'win'
      AND cat1 = 'overall'
      AND odd IS NOT NULL
      [[AND date >= {{date_from}}]]
      [[AND date <= {{date_to}}]]
      [[AND tournament = {{tournament}}]]
), best_per_outcome AS (
    SELECT
        date,
        tournament,
        player1,
        player2,
        outcome,
        MAX(odd) AS best_odd,
        (ARRAY_AGG(bukmacher ORDER BY odd DESC))[1] AS best_bookmaker
    FROM win_base
    WHERE outcome IS NOT NULL
    GROUP BY date, tournament, player1, player2, outcome
), paired AS (
    SELECT
        a.date,
        a.tournament,
        a.player1,
        a.player2,
        a.best_odd AS odd_player1,
        a.best_bookmaker AS book_player1,
        b.best_odd AS odd_player2,
        b.best_bookmaker AS book_player2,
        (1.0 / a.best_odd + 1.0 / b.best_odd) AS arb_index
    FROM best_per_outcome a
    JOIN best_per_outcome b
      ON a.date = b.date
     AND a.tournament = b.tournament
     AND a.player1 = b.player1
     AND a.player2 = b.player2
     AND a.outcome = a.player1
     AND b.outcome = a.player2
)
SELECT
    date,
    tournament,
    player1,
    player2,
    ROUND(odd_player1, 4) AS odd_player1,
    book_player1,
    ROUND(odd_player2, 4) AS odd_player2,
    book_player2,
    ROUND(arb_index * 100, 2) AS arb_index_pct,
    ROUND(((1 / arb_index) - 1) * 100, 2) AS theoretical_margin_pct,
    CASE
        WHEN arb_index < 1 THEN 'surebet'
        WHEN arb_index < 1.02 THEN 'near_surebet'
        ELSE 'no_arb'
    END AS arb_flag
FROM paired
ORDER BY arb_index ASC, date DESC, tournament, player1, player2;
