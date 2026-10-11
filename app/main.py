"""
HUNTER SYSTEM — Backend V0.1

An AI-powered, Solo Leveling-inspired
self-improvement platform.

Current features:
- FastAPI backend
- Hunter profile
- Daily quest generation
- Work-aware difficulty
- XP rewards defined for quests

Coming later:
- User accounts and authentication
- SQLite / PostgreSQL database
- Permanent progress history
- XP and seasonal rankings
- Gym tracking
- AI coaching
- Evidation rewards estimates
"""




from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI

#makeing FastApi app

app = FastAPI(
    title = "Hunter System API",
    description = "Ai - powered self imporvement RPG",
    version = "0.1.0"
)

#Application settings   

#use colorado local timezone
#this ensure our quest follow local dates.
TIMEZONE = ZoneInfo("America/Denver")

#Tempeory hunter Profile

player = {
    "display_name" : "Hunter",
    "Level": 1,
    "rank": "E",
    "xp": 0,
    "season": 1
}

# 4. DAILY QUEST DEFINITIONS
# ==========================================

# Each quest is represented by a dictionary.
#
# id    = unique quest identifier
# title = task the player must complete
# xp    = experience points earned
#
# Different plans allow us to adjust difficulty
# based on the player's available time.

QUEST_PLANS = {
    #Light workload for busy workdays 
    "light":[
        {
            "id":"read",
            "title":"Read 10 pages",
            "xp": 10 
        },
        
        {
            "id": "code",
            "title":"Practice Python for 15 min",
            "xp": 20
        },
    ],
    
    "focus": [
        
        {
            "id": "read",
            "title":"Read 10 Pages",
             "xp": 10,
             
        },
        {
            "id":"code",
            "title":"Practice Python for 60 min",
            "xp":35
        },
        {
            "id":"career",
            "title": "Work on your career",
            "xp": 15
            
        }
        
        
        
    ],
    #recovery workload for sunday
    "recovery":[
        {
            "id":"reflect",
            "title":"Review your progress",
            "xp": 10
        }
    ]
}

#date Function
def get_today():
    """
    Return today's date in denver's timezone.
    example:
            2026-10-11
    """
    current_time = datetime.now(TIMEZONE)
    return current_time.date()


#6 Daily Difficulty Function
def get_daily_plan():
    """
    select today's quest difficult.
    
    python weekdays:
        Monday     = 0
        Tuesday    = 1
        Wednesday  = 2
        Thursday   = 3
        Friday     = 4
        Saturday   = 5
        Sunday     = 6
    
    This is only our Starting Schedule.
    Later, users will configure their own
    work hours, rest days and goal.
    """
    weekday = get_today().weekday()
    #sunday is recovery day.
    if weekday ==6:
        return "recovery"
    
    #thuesday and thursday have more
    #available time for focused quests 
   
    
    #Tuesday and thursday have more intense
    #avaliable time for focused quest
    if weekday in (1,3):
        return "focus"
    
    #pther weekdays use lighter quests.
    return "light"


# application status endpoint

@app.get("/")
def home():
    """
    GET /
    Returns basic application information.
    This tells us whether the API is running.
    """
    
    
    return{
        "application":"Hunter System",
        "status": "online",
        "version": "0.1.0"
        }
    
    #hunter profile endpoint
    
@app.get("/api/player")
def get_player():
    """
    GET/api/player
    
    Returns the temporary Hunter profile.
    
    FastAPI automatically converts our 
    Python dictionary in JSON
    """
    return player

# Daily Quest ENDPOINT
@app.get("/api/quests/today")
def get_todays_quest():
    """
    GET /api/quests/today
    
    steps:
    1. Check Today's weekday.
    2. Determine quest difficulty.
    3. Find the matching quest list.
    4. Return the quest as JSON.
    
    This endpoint does not save completed
    quests yet. That comes in Milestone 2
    
    
    """
    
    #Determine which quest plan applies
    plan = get_daily_plan()
    quests = QUEST_PLANS[plan]
    
    #Send the information to the browser
    return{
        "date": get_today().isoformat(),
        "difficulty": plan,
        "quests": quests
        
    }
    
    