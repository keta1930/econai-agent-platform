import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.user import User
from models.roster import StudentRoster


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def register_student(db: Session, student_id: str, password: str) -> User:
    roster_entry = (
        db.query(StudentRoster)
        .filter(StudentRoster.student_id == student_id)
        .first()
    )
    if not roster_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号不在名单中",
        )

    existing = db.query(User).filter(User.id == student_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学号已注册",
        )

    user = User(
        id=student_id,
        password_hash=hash_password(password),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, user_id: str, password: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return user
