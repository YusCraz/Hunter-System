
"""
Hunter System — Milestone 2
Permanent SQLite storage and progression.
"""

import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "hunter.db"
PLAYER_ID = 1
SEASON_LENGTH = 30


def utc_now():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    """Open SQLite with named columns and foreign keys."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create all required tables without erasing saved data."""

    with closing(get_connection()) as connection:
        with connection:

            # Existing player table from Part 1.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    total_xp INTEGER NOT NULL DEFAULT 0
                        CHECK(total_xp >= 0),
                    season INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            # One quest can be completed only once per day.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS quest_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    quest_id TEXT NOT NULL,
                    quest_date TEXT NOT NULL,
                    xp_earned INTEGER NOT NULL
                        CHECK(xp_earned >= 0),
                    completed_at TEXT NOT NULL,

                    FOREIGN KEY (player_id)
                        REFERENCES players(id),

                    UNIQUE(player_id, quest_date, quest_id)
                )
            """)

            # Separate seasonal XP from lifetime XP.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS season_progress (
                    player_id INTEGER PRIMARY KEY,
                    started_on TEXT NOT NULL,
                    season_xp INTEGER NOT NULL DEFAULT 0
                        CHECK(season_xp >= 0),

                    FOREIGN KEY (player_id)
                        REFERENCES players(id)
                )
            """)

            # Maintain a history of completed seasons.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS season_history (
                    player_id INTEGER NOT NULL,
                    season_number INTEGER NOT NULL,
                    started_on TEXT NOT NULL,
                    ended_on TEXT NOT NULL,
                    xp_earned INTEGER NOT NULL,

                    PRIMARY KEY (player_id, season_number),

                    FOREIGN KEY (player_id)
                        REFERENCES players(id)
                )
            """)

            # Initialize our local single-player profile.
            connection.execute("""
                INSERT OR IGNORE INTO players (
                    id, display_name, total_xp,
                    season, created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (PLAYER_ID, "Hunter", 0, 1, utc_now()))


def level_from_xp(total_xp):
    """
    Determine lifetime level.

    Level 1 -> 2 requires 100 XP.
    Level 2 -> 3 requires 200 additional XP.
    Level 3 -> 4 requires 300 additional XP.
    """
    level = 1
    remaining = total_xp

    while remaining >= level * 100:
        remaining -= level * 100
        level += 1

    return {
        "level": level,
        "xp_in_level": remaining,
        "xp_to_next_level": level * 100
    }


def rank_from_xp(season_xp):
    """Temporary, configurable seasonal rank thresholds."""

    if season_xp >= 4000:
        return "S"
    if season_xp >= 2000:
        return "A"
    if season_xp >= 1000:
        return "B"
    if season_xp >= 500:
        return "C"
    if season_xp >= 200:
        return "D"
    return "E"


def sync_season(player_id=PLAYER_ID, today=None):
    """
    Ensure the player's season is up to date.

    Every 30 days:
    - Save the previous season's record.
    - Start a new season at Rank E.
    - Keep lifetime XP and lifetime level.
    """

    today = today or date.today()

    with closing(get_connection()) as connection:
        with connection:

            connection.execute("BEGIN IMMEDIATE")

            player = connection.execute("""
                SELECT season FROM players WHERE id = ?
            """, (player_id,)).fetchone()

            if player is None:
                raise ValueError("Player does not exist")

            progress = connection.execute("""
                SELECT started_on, season_xp
                FROM season_progress
                WHERE player_id = ?
            """, (player_id,)).fetchone()

            # First season starts when we first initialize progress.
            if progress is None:
                connection.execute("""
                    INSERT INTO season_progress (
                        player_id, started_on, season_xp
                    )
                    VALUES (?, ?, 0)
                """, (player_id, today.isoformat()))
                return

            started_on = date.fromisoformat(
                progress["started_on"]
            )

            # No season change needed yet.
            elapsed = (today - started_on).days
            if elapsed < SEASON_LENGTH:
                return

            # Handle one or more elapsed seasons.
            season_number = player["season"]
            season_xp = progress["season_xp"]

            while elapsed >= SEASON_LENGTH:

                next_start = date.fromordinal(
                    started_on.toordinal() + SEASON_LENGTH
                )

                connection.execute("""
                    INSERT OR IGNORE INTO season_history (
                        player_id, season_number,
                        started_on, ended_on, xp_earned
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    player_id,
                    season_number,
                    started_on.isoformat(),
                    next_start.isoformat(),
                    season_xp
                ))

                season_number += 1
                started_on = next_start
                season_xp = 0
                elapsed = (today - started_on).days

            connection.execute("""
                UPDATE players SET season = ?
                WHERE id = ?
            """, (season_number, player_id))

            connection.execute("""
                UPDATE season_progress
                SET started_on = ?, season_xp = 0
                WHERE player_id = ?
            """, (started_on.isoformat(), player_id))


def get_player_by_id(player_id=PLAYER_ID, today=None):
    """Load a persistent Hunter profile."""

    sync_season(player_id, today)

    with closing(get_connection()) as connection:

        row = connection.execute("""
            SELECT
                p.id,
                p.display_name,
                p.total_xp,
                p.season,
                s.started_on,
                s.season_xp
            FROM players AS p
            JOIN season_progress AS s
                ON p.id = s.player_id
            WHERE p.id = ?
        """, (player_id,)).fetchone()

        if row is None:
            return None

        result = dict(row)

        # Derive level from permanent lifetime XP.
        result.update(level_from_xp(result["total_xp"]))

        # Seasonal rank depends only on seasonal XP.
        result["rank"] = rank_from_xp(
            result["season_xp"]
        )

        return result


class DuplicateQuestError(Exception):
    """Raised when a quest has already been completed."""


def save_quest_completion(
    quest_id,
    xp_reward,
    quest_date,
    player_id=PLAYER_ID
):
    """
    Record completion and award XP atomically.

    Either both the quest and XP are saved,
    or neither is saved.
    """

    # Update seasonal state before awarding XP.
    sync_season(
        player_id,
        date.fromisoformat(quest_date)
    )

    with closing(get_connection()) as connection:

        try:
            with connection:

                # Lock writes before checking and updating XP.
                connection.execute("BEGIN IMMEDIATE")

                # The UNIQUE constraint blocks duplicate awards.
                connection.execute("""
                    INSERT INTO quest_completions (
                        player_id,
                        quest_id,
                        quest_date,
                        xp_earned,
                        completed_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    player_id,
                    quest_id,
                    quest_date,
                    xp_reward,
                    utc_now()
                ))

                # Add XP to permanent lifetime total.
                connection.execute("""
                    UPDATE players
                    SET total_xp = total_xp + ?
                    WHERE id = ?
                """, (xp_reward, player_id))

                # Add XP to the current season.
                connection.execute("""
                    UPDATE season_progress
                    SET season_xp = season_xp + ?
                    WHERE player_id = ?
                """, (xp_reward, player_id))

        except sqlite3.IntegrityError as error:
            if "UNIQUE constraint failed" in str(error):
                raise DuplicateQuestError(
                    "Quest already completed today"
                ) from error
            raise

    return get_player_by_id(
        player_id,
        date.fromisoformat(quest_date)
    )


def get_completed_quests(
    quest_date,
    player_id=PLAYER_ID
):
    """Retrieve quests completed on a given day."""

    with closing(get_connection()) as connection:

        rows = connection.execute("""
            SELECT quest_id, xp_earned, completed_at
            FROM quest_completions
            WHERE player_id = ? AND quest_date = ?
            ORDER BY completed_at, id
        """, (player_id, quest_date)).fetchall()

        return [dict(row) for row in rows]


def get_activity_history(player_id=PLAYER_ID):
    """Retrieve the complete saved quest history."""

    with closing(get_connection()) as connection:

        rows = connection.execute("""
            SELECT quest_id, quest_date,
                   xp_earned, completed_at
            FROM quest_completions
            WHERE player_id = ?
            ORDER BY quest_date DESC, id DESC
        """, (player_id,)).fetchall()

        return [dict(row) for row in rows]


def get_season_history(player_id=PLAYER_ID):
    """Retrieve previous 30-day seasons."""

    with closing(get_connection()) as connection:

        rows = connection.execute("""
            SELECT season_number, started_on,
                   ended_on, xp_earned
            FROM season_history
            WHERE player_id = ?
            ORDER BY season_number DESC
        """, (player_id,)).fetchall()

        return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_database()
    print("DATABASE CONNECTION SUCCESSFUL")
    print("Hunter:", get_player_by_id())
    print("Database:", DB_PATH)
