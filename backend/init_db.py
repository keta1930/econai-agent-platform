from database import engine, SessionLocal, Base
from models import User, ModelConfig
from services.auth_service import hash_password
from config import DEFAULT_ADMIN_ID, DEFAULT_ADMIN_PASSWORD


def init_database():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Default admin
        if not db.query(User).filter(User.id == DEFAULT_ADMIN_ID).first():
            admin = User(
                id=DEFAULT_ADMIN_ID,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)

        # Default model config
        if not db.query(ModelConfig).filter(ModelConfig.name == "deepseek-chat").first():
            model = ModelConfig(
                name="deepseek-chat",
                api_key="sk-110d4fd6af1645558f56854349a9370f",
                base_url="https://api.deepseek.com/v1",
                adapter_type="openai",
                is_active=True,
            )
            db.add(model)

        db.commit()
    finally:
        db.close()
