from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Attachment, Task
from schemas import TaskCreate, TaskUpdate, TaskOut
import crud
import os
from fastapi.responses import FileResponse
import requests

# TiDB数据库连接配置
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@192.168.5.124:4000/myassistant"
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表（如未创建）
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 依赖项：获取数据库会话

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# AI生成任务接口
@app.post("/ai_generate_tasks/")
def ai_generate_tasks(prompt: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    输入一句话，调用DeepSeek API，AI自动拆解为多个任务并写入数据库。
    """
    # 1. 调用DeepSeek API（此处用占位符，需替换为你的API Key和真实接口）
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"  # 请替换为你的Key
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    # 你可以根据DeepSeek的API格式调整messages内容
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个任务拆解助手，请将用户输入的目标拆解为简明的任务列表，返回JSON数组，每个任务包含title和description。"},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        ai_content = resp.json()["choices"][0]["message"]["content"]
        # 假设AI返回内容为JSON数组字符串
        import json
        tasks = json.loads(ai_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI生成任务失败: {e}")
    # 2. 写入数据库
    created_tasks = []
    for t in tasks:
        task_obj = crud.create_task(db, TaskCreate(title=t.get("title", "AI任务"), description=t.get("description", "")))
        created_tasks.append(task_obj)
    return {"tasks": [ {"id": t.id, "title": t.title, "description": t.description} for t in created_tasks ]}

# 任务API
@app.post("/tasks/", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(db, task)

@app.get("/tasks/", response_model=list[TaskOut])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_tasks(db, skip=skip, limit=limit)

@app.get("/tasks/{task_id}", response_model=TaskOut)
def read_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    db_task = crud.update_task(db, task_id, task)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.delete_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}

# 附件上传API
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/tasks/{task_id}/attachments/")
def upload_attachment(task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    attachment = crud.create_attachment(
        db,
        filename=file.filename,
        filepath=file_location,
        filetype=file.content_type,
        task_id=task_id
    )
    return {"filename": file.filename, "id": attachment.id}

@app.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path=attachment.filepath, filename=attachment.filename)

@app.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    # 删除本地文件
    if os.path.exists(attachment.filepath):
        os.remove(attachment.filepath)
    db.delete(attachment)
    db.commit()
    return {"ok": True} 