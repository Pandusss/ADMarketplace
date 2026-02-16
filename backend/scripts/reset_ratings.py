import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy import update
from app.db.session import SessionLocal
from app.db.models.review import Review
from app.db.models.user import User
from app.db.models.channel import Channel
from app.db.models.campaign import Campaign

def reset_all_ratings():
    db = SessionLocal()
    try:
        print("Cleaning up reviews...")
        db.query(Review).delete()
        
        print("Resetting User ratings...")
        db.execute(
            update(User).values(
                rating_avg=0.0,
                rating_count=0,
                rating_advertiser_avg=0.0,
                rating_advertiser_count=0,
                rating_owner_avg=0.0,
                rating_owner_count=0
            )
        )
        
        print("Resetting Channel ratings...")
        db.execute(
            update(Channel).values(
                rating_avg=0.0,
                rating_count=0
            )
        )
        
        print("Resetting Campaign ratings...")
        db.execute(
            update(Campaign).values(
                rating_avg=0.0,
                rating_count=0
            )
        )
        
        db.commit()
        print("\033[92mDone! All ratings have been reset to 0.\033[0m")
    except Exception as e:
        db.rollback()
        print(f"\033[91mError during reset: {e}\033[0m")
    finally:
        db.close()

if __name__ == "__main__":
    reset_all_ratings()
