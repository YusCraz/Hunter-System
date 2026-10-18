"""
HUNTER SYSTEM -- DATABASE MODULE

Milestone 2: Permanent Progress

This module is responsible for:
1. Connecting to the SQLite database.
2. Creating database tables.
3. Creating the initial Hunter profile.

Later, it will also store separate user accounts.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# ==============================
# 1. DATABASE LOCATION
# ==============================

# Find the project root directory.
BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite will store data in this file.
DB_PATH = BASE_DIR / "hunter.db"


# ==============================
# 2. DATABASE CONNECTION
# ==============================

def get_connection():
    """
    Open a connection to our SQLite database.
    """

    connection = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    # Allow accessing columns by name.
    connection.row_factory = sqlite3.Row

    # Enforce foreign-key relationships.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==============================
# 3. INITIALIZE DATABASE
# ==============================

def initialize_database():
    """
    Create database tables if they don't exist.

    Existing tables and records are preserved.
    """

    with get_connection() as connection:

        # Table 1: Hunter profiles
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

        # Table 2: Completed quests
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

        # Check whether our first player exists.
        player = connection.execute("""
            SELECT id
            FROM players
            WHERE id = 1
        """).fetchone()

        # Create the Hunter only if it doesn't exist.
        if player is None:

            now = datetime.now(timezone.utc).isoformat()

            connection.execute("""
                INSERT INTO players (
                    id,
                    display_name,
                    total_xp,
                    season,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (1, "Hunter", 0, 1, now))

        # Save all changes.
        connection.commit()

#==========================
#4 RETERIEVE HUNTER PROFILE
#===========================


def get_player_by_id(player_id: int):
    """
    Retrieve a player from our sqlite database.
    Args:
        player_id: The ID of the player to retrieve
        
    Returns:
        A dictionary containing the player's data,
        or None if the player doesn't exist.
    """
    
    #Connect to SQLite.
    with get_connection() as connection:
        #? is a placeholder for the player ID.
        #this safely passes values into SQL
        
        player = connection.execute(
            """
            SELECT id, display_name, total_xp, season
            FROM players
            WHERE id = ?
            
            """,
            (player_id,)
        ).fetchone()

        #Return None if the player wasn't food
        if player is None:
            return None
        
        #Convert sqlite3.row into a regular dictionary.
        return dict(player)
        
        
        


# ==============================
# 5. LOCAL DATABASE TEST
# ==============================

if __name__ == "__main__":

    # Create the database tables.
    initialize_database()

    # Retrieve the saved Hunter profile.
    with get_connection() as connection:

        player = connection.execute("""
            SELECT *
            FROM players
            WHERE id = 1
        """).fetchone()

        print("DATABASE CONNECTION SUCCESSFUL")
        print("Hunter:", player["display_name"])
        print("Total XP:", player["total_xp"])
        print("Season:", player["season"])
        print("Database:", DB_PATH)

