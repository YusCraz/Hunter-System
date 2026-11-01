schedule = {
    "monday": "workout",
    "tuesday": "workout",
    "wednesday": "rest",
    "thursday": "workout",
    "friday": "workout",
    "saturday": "workout",
    "sunday": "rest"
}




def validate_gym_schedule(schedule):
    # check if the inout is a dict or not
    if not isinstance(schedule,dict):
        return False
    
    #define the save valid days.
    weekdays = {
        "monday","tuesday","wednesday",
        "thursday","friday","saturday", "sunday"
        
    }
    
    # chcek that all 7 days are present
    if set(schedule.keys()) != weekdays:
        return False
    
    # chcek that every value is either workout or rest
    for activity in schedule.values():
        if activity not in ("workout","rest"):
            return False
    
    #count workout days.
    workout_days = list(schedule.values()).count("workout")
    
    # a valud schedule must have 5 working days
    if workout_days != 5:
        return False
    
    #all chcek
    return True

def get_workout_for_day(workout_plan, day):
    
    if not isinstance(workout_plan,dict) or not isinstance (day,str):
        return None 
    

    normalized_day = day.strip().lower()
    
    if normalized_day not in workout_plan:
        return None
    
    workout = workout_plan.get(normalized_day)

    if workout == None:
        return None
    
    return workout 
    
def get_exercises_for_day(exercise_plan, day):
    if not isinstance(exercise_plan, dict) or not isinstance(day, str):
        
        return []
    
    normalize_day = day.strip().lower()
    
    if normalize_day not in exercise_plan:
        
        return []
    
    exercises = exercise_plan.get(normalize_day,[])
    
    if not isinstance(exercise_plan, dict):
        
        return []
    
    return [exercises]

    


if __name__ == "__main__":
    exercise_plan = {
    "monday": ["Chest Press", "Lat Pulldown"],
    "tuesday": ["Squat", "Leg Extension"],
    "wednesday": [],
    "sunday": []
}

print(get_exercises_for_day(exercise_plan, " MONDAY "))
print(get_exercises_for_day(exercise_plan, "wednesday"))
print(get_exercises_for_day(exercise_plan, "holiday"))

print(validate_gym_schedule(schedule))
print(get_workout_for_day(schedule, " TUESDAY "))



