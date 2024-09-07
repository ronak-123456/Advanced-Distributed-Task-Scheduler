# Core Service: task_manager.py
import logging
import os
import asyncio
from datetime import datetime, timedelta

import aiohttp
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/taskdb")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    status = Column(String)
    priority = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user_id = Column(Integer)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Security functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def authenticate_user(db, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# ML Service: priority_predictor.py
import joblib
from sklearn.ensemble import RandomForestRegressor

class PriorityPredictor:
    def __init__(self):
        self.model = joblib.load('priority_model.joblib')

    def predict_priority(self, task_features):
        return self.model.predict([task_features])[0]

# Task assignment service
async def assign_task(task_id: int, task_name: str, priority: float):
    worker_nodes = ["http://worker1:8001", "http://worker2:8002", "http://worker3:8003"]
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(session.post(f"{worker}/execute", json={
                "task_id": task_id, "name": task_name, "priority": priority
            })) for worker in worker_nodes
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for response in responses:
            if isinstance(response, aiohttp.ClientResponse) and response.status == 200:
                return
        raise HTTPException(status_code=503, detail="No available workers")

# API endpoints
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/tasks")
async def create_task(task: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    priority_predictor = PriorityPredictor()
    task_features = [len(task['name']), len(task['description']), current_user.id]  # Simplified features
    priority = priority_predictor.predict_priority(task_features)
    
    db_task = Task(
        name=task['name'], description=task['description'],
        status="pending", priority=priority, user_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    asyncio.create_task(assign_task(db_task.id, db_task.name, db_task.priority))
    
    return {"task_id": db_task.id, "priority": priority}

@app.get("/tasks/{task_id}")
async def get_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}/complete")
async def complete_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.commit()
    return {"message": "Task completed successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Worker Node: worker.py
from fastapi import FastAPI, BackgroundTasks
import asyncio
import random

worker_app = FastAPI()

async def execute_task(task_id: int, name: str, priority: float):
    # Simulate task execution
    execution_time = random.uniform(1, 10) * (1 / priority)  # Higher priority tasks execute faster
    await asyncio.sleep(execution_time)
    print(f"Task {task_id}: {name} completed in {execution_time:.2f} seconds")

@worker_app.post("/execute")
async def execute(task: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(execute_task, task['task_id'], task['name'], task['priority'])
    return {"message": "Task accepted for execution"}

if __name__ == "__main__":
    uvicorn.run(worker_app, host="0.0.0.0", port=8001)  # Different port for each worker

# Docker Compose file: docker-compose.yml
version: '3'
services:
  taskmanager:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
  worker1:
    build: .
    command: python worker.py
    ports:
      - "8001:8001"
  worker2:
    build: .
    command: python worker.py
    ports:
      - "8002:8002"
  worker3:
    build: .
    command: python worker.py
    ports:
      - "8003:8003"
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: taskdb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
