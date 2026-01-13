# volunteer_profile.py
import os
from datetime import datetime
import json

from backend.supabase_client import supabase, safe_supabase_write

class VolunteerProfile:
    def __init__(self, user_id, volunteer_id, assigned_region, status="Active", 
                 total_tasks_completed=0, ongoing_tasks=0, people_helped=0, 
                 food_delivered=0, emergency_cases=0, badges=None):
        self.user_id = user_id
        self.volunteer_id = volunteer_id
        self.assigned_region = assigned_region
        self.status = status
        self.total_tasks_completed = total_tasks_completed
        self.ongoing_tasks = ongoing_tasks
        self.people_helped = people_helped
        self.food_delivered = food_delivered
        self.emergency_cases = emergency_cases
        self.badges = badges if badges is not None else []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "volunteer_id": self.volunteer_id,
            "assigned_region": self.assigned_region,
            "status": self.status,
            "total_tasks_completed": self.total_tasks_completed,
            "ongoing_tasks": self.ongoing_tasks,
            "people_helped": self.people_helped,
            "food_delivered": self.food_delivered,
            "emergency_cases": self.emergency_cases,
            "badges": json.dumps(self.badges),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        badges = json.loads(data["badges"]) if data.get("badges") else []
        return cls(
            user_id=data["user_id"],
            volunteer_id=data["volunteer_id"],
            assigned_region=data["assigned_region"],
            status=data.get("status", "Active"),
            total_tasks_completed=data.get("total_tasks_completed", 0),
            ongoing_tasks=data.get("ongoing_tasks", 0),
            people_helped=data.get("people_helped", 0),
            food_delivered=data.get("food_delivered", 0),
            emergency_cases=data.get("emergency_cases", 0),
            badges=badges
        )

def create_volunteer_profile(volunteer_profile):
    """Insert a new volunteer profile into the database"""
    try:
        data = volunteer_profile.to_dict()
        res = safe_supabase_write(lambda: supabase.table("volunteer_profile").insert(data).execute(), "create volunteer profile")
        if not res.get('success'):
            print(f"Error creating volunteer profile: {res.get('error')}")
            return None
        d = res.get('data')
        if isinstance(d, list) and d:
            return d[0]
        return d
    except Exception as e:
        print(f"Error creating volunteer profile: {e}")
        return None

def get_volunteer_profile(volunteer_id):
    """Retrieve a volunteer profile by volunteer_id"""
    try:
        response = supabase.table("volunteer_profile").select("*").eq("volunteer_id", volunteer_id).execute()
        return VolunteerProfile.from_dict(response.data[0]) if response.data else None
    except Exception as e:
        print(f"Error retrieving volunteer profile: {e}")
        return None

def update_volunteer_profile(volunteer_id, updates):
    """Update a volunteer profile"""
    try:
        updates["updated_at"] = datetime.now().isoformat()
        if "badges" in updates and isinstance(updates["badges"], list):
            updates["badges"] = json.dumps(updates["badges"])
        res = safe_supabase_write(lambda: supabase.table("volunteer_profile").update(updates).eq("volunteer_id", volunteer_id).execute(), "update volunteer profile")
        if not res.get('success'):
            print(f"Error updating volunteer profile: {res.get('error')}")
            return None
        d = res.get('data')
        if isinstance(d, list) and d:
            return d[0]
        return d
    except Exception as e:
        print(f"Error updating volunteer profile: {e}")
        return None

def delete_volunteer_profile(volunteer_id):
    """Delete a volunteer profile"""
    try:
        res = safe_supabase_write(lambda: supabase.table("volunteer_profile").delete().eq("volunteer_id", volunteer_id).execute(), "delete volunteer profile")
        return res.get('success')
    except Exception as e:
        print(f"Error deleting volunteer profile: {e}")
        return False

# Example usage
if __name__ == "__main__":
    # Create a new volunteer profile
    new_volunteer = VolunteerProfile(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        volunteer_id="VOL-4821",
        assigned_region="Metro Central",
        status="Active",
        total_tasks_completed=127,
        ongoing_tasks=8,
        people_helped=342,
        food_delivered=1248,
        emergency_cases=14,
        badges=["First Responder", "Food Hero", "Community Champion"]
    )
    
    # Insert into database
    created_profile = create_volunteer_profile(new_volunteer)
    if created_profile:
        print("Volunteer profile created successfully!")
    
    # Retrieve a volunteer profile
    volunteer = get_volunteer_profile("VOL-4821")
    if volunteer:
        print(f"Retrieved volunteer: {volunteer.volunteer_id}")
    
    # Update a volunteer profile
    updates = {
        "total_tasks_completed": 130,
        "people_helped": 350,
        "badges": ["First Responder", "Food Hero", "Community Champion", "100 Tasks"]
    }
    updated_profile = update_volunteer_profile("VOL-4821", updates)
    if updated_profile:
        print("Volunteer profile updated successfully!")