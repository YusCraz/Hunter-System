
"""
Hunter System — Milestone 2 API

Features:
- Persistent Hunter profile
- Daily quests
- Quest completion and XP
- Lifetime leveling
- Seasonal ranks
- Activity history
"""

from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.database import (
    initialize_database,
    get_player_by_id,
    save_quest_completion,
    get_completed_quests,
    get_activity_history,
    get_season_history,
    DuplicateQuestError,
)


# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================

TIMEZONE = ZoneInfo("America/Denver")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create missing database tables at server startup."""
    initialize_database()
    yield


app = FastAPI(
    title="Hunter System API",
    description="AI-powered self-improvement RPG",
    version="0.2.0",
    lifespan=lifespan
)


# ==========================================
# 2. DAILY QUEST DEFINITIONS
# ==========================================

QUEST_PLANS = {

    "light": [
        {
            "id": "read",
            "title": "Read 10 pages",
            "xp": 10
        },
        {
            "id": "code",
            "title": "Practice Python for 15 minutes",
            "xp": 20
        }
    ],

    "focus": [
        {
            "id": "read",
            "title": "Read 10 pages",
            "xp": 10
        },
        {
            "id": "code",
            "title": "Practice Python for 60 minutes",
            "xp": 35
        },
        {
            "id": "ai",
            "title": "Learn an AI concept",
            "xp": 20
        },
        {
            "id": "career",
            "title": "Work on your career",
            "xp": 15
        }
    ],

    "recovery": [
        {
            "id": "reflect",
            "title": "Review your progress",
            "xp": 10
        }
    ]
}


# ==========================================
# 3. DATE AND QUEST HELPERS
# ==========================================

def get_today():
    """Return today's date in Colorado."""
    return datetime.now(TIMEZONE).date()


def get_daily_plan():
    """Determine quest difficulty from weekday."""

    weekday = get_today().weekday()

    # Sunday: recovery
    if weekday == 6:
        return "recovery"

    # Tuesday and Thursday: focus
    if weekday in (1, 3):
        return "focus"

    # Other days: light
    return "light"


def find_quest(quest_id):
    """Find a quest in today's assigned plan."""

    plan = get_daily_plan()

    for quest in QUEST_PLANS[plan]:
        if quest["id"] == quest_id:
            return quest

    return None


# ==========================================
# 4. REQUEST MODELS
# ==========================================

class QuestCompletionRequest(BaseModel):
    quest_id: str


# ==========================================
# 5. API STATUS
# ==========================================

@app.get("/")
def home():
    return {
        "application": "Hunter System",
        "status": "online",
        "version": "0.2.0"
    }


# ==========================================
# 6. HUNTER PROFILE
# ==========================================

@app.get("/api/player")
@app.get("/hunter")
def get_player():
    """Retrieve the actual saved Hunter profile."""

    player = get_player_by_id(1, get_today())

    if player is None:
        raise HTTPException(
            status_code=404,
            detail="Hunter profile not found"
        )

    return player


# ==========================================
# 7. DAILY QUESTS
# ==========================================

@app.get("/api/quests/today")
def get_todays_quests():
    """Get today's quests and completion states."""

    today = get_today().isoformat()
    plan = get_daily_plan()

    completed = get_completed_quests(today)

    completed_ids = {
        record["quest_id"] for record in completed
    }

    quests = []

    for quest in QUEST_PLANS[plan]:
        quests.append({
            **quest,
            "completed": quest["id"] in completed_ids
        })

    return {
        "date": today,
        "difficulty": plan,
        "quests": quests
    }


# ==========================================
# 8. COMPLETE A QUEST
# ==========================================

@app.post("/api/quests/complete")
def complete_quest(request: QuestCompletionRequest):
    """
    Complete an eligible daily quest.

    XP is chosen by the backend, not the user.
    Database transaction prevents duplicate XP.
    """

    quest = find_quest(request.quest_id)

    if quest is None:
        raise HTTPException(
            status_code=404,
            detail="Quest not found in today's plan"
        )

    today = get_today().isoformat()

    try:
        updated_player = save_quest_completion(
            quest_id=quest["id"],
            xp_reward=quest["xp"],
            quest_date=today
        )

    except DuplicateQuestError:
        raise HTTPException(
            status_code=409,
            detail="Quest already completed today"
        )

    return {
        "message": "Quest completed successfully",
        "quest": quest["title"],
        "xp_earned": quest["xp"],
        "player": updated_player
    }


# ==========================================
# 9. COMPLETED QUESTS
# ==========================================

@app.get("/api/quests/completed")
def completed_quests():
    """Retrieve today's completed quests."""

    today = get_today().isoformat()

    completed = get_completed_quests(today)

    return {
        "date": today,
        "completed_quests": [
            row["quest_id"] for row in completed
        ],
        "total_completed": len(completed),
        "xp_earned_today": sum(
            row["xp_earned"] for row in completed
        )
    }


# ==========================================
# 10. ACTIVITY HISTORY
# ==========================================

@app.get("/api/history")
def activity_history():
    """Show all saved quest completion records."""

    return {
        "activities": get_activity_history()
    }


# ==========================================
# 11. SEASON HISTORY
# ==========================================

@app.get("/api/seasons/history")
def season_history():
    """Show previous season records."""

    # Synchronize season state first.
    get_player_by_id(1, get_today())

    return {
        "seasons": get_season_history()
    }
