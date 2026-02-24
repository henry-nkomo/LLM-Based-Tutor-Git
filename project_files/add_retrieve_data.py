from .db_models import trackProgress
from . import db

class retrieveData():

    def get_skill_components(self, user_id):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        if progress:
            return progress.skills_component
        else:
            print(f"No progress record found for user_id: {user_id}")
            return None
    
    def update_skill_components(self, user_id, new_skills_component):
    # Define the canonical skill keys
        VALID_SKILLS = {
            'comprehending-text', 'summarisation', 'vocabulary'
        }
        
        # Sanitize the input dictionary
        sanitized_skills = {}
        
        for key, value in new_skills_component.items():
            # Skip invalid keys (None, empty string, "null", etc.)
            if key is None or key == "" or key == "null" or key not in VALID_SKILLS:
                print(f"WARNING: Skipping invalid skill key: {key}")
                continue
            
            # Ensure value is a valid number
            try:
                sanitized_value = float(value)
                # Optional: clamp values to reasonable range (e.g., 0-100)
                sanitized_value = max(0, min(100, sanitized_value))
                sanitized_skills[key] = sanitized_value
            except (TypeError, ValueError):
                print(f"WARNING: Invalid value for skill {key}: {value}, setting to 10")
                sanitized_skills[key] = 10.0
        
        # Ensure all required skills are present
        for skill in VALID_SKILLS:
            if skill not in sanitized_skills:
                print(f"WARNING: Missing skill {skill}, initializing to 10")
                sanitized_skills[skill] = 10.0
        
        # Now update the database
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        try:
            if progress:
                progress.skills_component = sanitized_skills
                db.session.commit()
                print(f"Successfully updated skills for user {user_id}: {sanitized_skills}")
            else:
                print(f"No progress record found for user_id: {user_id}")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating skill components for user_id {user_id}: {e}")

    def get_user_preferences(self, user_id):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        if progress:
            return progress.preferences
        else:
            print(f"No progress record found for user_id: {user_id}")
            return None
        
    def update_user_preferences(self, user_id, new_preferences):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        try:
            if progress:
                progress.preferences = new_preferences
                db.session.commit()
            else:
                print(f"No progress record found for user_id: {user_id}")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating preferences for user_id {user_id}: {e}")

    def get_report_summary(self, user_id):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        if progress:
            return progress.report_summary
        else:
            print(f"No progress record found for user_id: {user_id}")
            return None
    
    def update_report_summary(self, user_id, new_report):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        try:
            if progress:
                new_report =  progress.report_summary + new_report
                progress.report_summary = new_report
                db.session.commit()
            else:
                print(f"No progress record found for user_id: {user_id}")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating probabilities for user_id {user_id}: {e}")

    def get_progress(self, user_id):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        if progress:
            return progress.progress
        else:
            print(f"No progress record found for user_id: {user_id}")
            return None
    def update_progress(self, user_id, new_progress):
        progress = trackProgress.query.filter_by(user_id=user_id).first()
        try:
            if progress:
                progress.progress = new_progress
                db.session.commit()
            else:
                print(f"No progress record found for user_id: {user_id}")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating progress for user_id {user_id}: {e}")



