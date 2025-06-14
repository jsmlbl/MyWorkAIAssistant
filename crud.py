from sqlalchemy.orm import Session
from models import Task, Attachment
from schemas import TaskCreate, TaskUpdate
import datetime

# 任务相关

def create_task(db: Session, task: TaskCreate):
    db_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        tags=task.tags
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Task).offset(skip).limit(limit).all()

def update_task(db: Session, task_id: int, task: TaskUpdate):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        return None
    for var, value in vars(task).items():
        if value is not None:
            setattr(db_task, var, value)
    if task.status == 'completed' and not db_task.completed_at:
        db_task.completed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task

# 附件相关

def create_attachment(db: Session, filename: str, filepath: str, filetype: str, task_id: int):
    db_attachment = Attachment(
        filename=filename,
        filepath=filepath,
        filetype=filetype,
        task_id=task_id
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment

def get_attachments_by_task(db: Session, task_id: int):
    return db.query(Attachment).filter(Attachment.task_id == task_id).all() 