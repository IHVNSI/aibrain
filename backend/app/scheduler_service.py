"""Task scheduling service for automating agent actions."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any
import json
import os
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()


class ScheduledTask(Base):
    """Database model for scheduled tasks."""
    __tablename__ = 'scheduled_tasks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)  # 'email_check', 'email_respond', 'sql_query', etc.
    natural_language_instruction = Column(Text, nullable=False)
    
    # Scheduling config (JSON)
    schedule_config = Column(Text, nullable=False)  # JSON: {"type": "cron", "cron_expr": "0 10 * * *"}
    
    # Task config (JSON)
    task_config = Column(Text, nullable=False)  # JSON: {"email_folder": "INBOX", "filter": "..."}
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)  # Admin user ID


class TaskScheduler:
    """Schedule and manage automated tasks with natural language support."""
    
    def __init__(self, db_url: Optional[str] = None, app=None):
        """
        Initialize task scheduler.
        
        Args:
            db_url: SQLAlchemy database URL (uses ADMIN_DB_URL if not provided)
            app: Flask app instance (optional, but required for db access in handlers)
        """
        if db_url is None:
            db_url = os.getenv('ADMIN_DB_URL', 'sqlite:///brainr.db')
        
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.app = app  # Store Flask app reference for app context in handlers
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Initialize APScheduler
        self.scheduler = BackgroundScheduler()
        self.task_handlers: Dict[str, Callable] = {}
        
        logger.info("✓ Task Scheduler initialized")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        Register a handler for a task type.
        
        Args:
            task_type: Type of task (e.g., 'email_check', 'email_respond')
            handler: Callable that handles the task
        """
        self.task_handlers[task_type] = handler
        logger.info(f"✓ Registered handler for task type: {task_type}")
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("✓ Task scheduler started")
            self._load_active_tasks()
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✓ Task scheduler stopped")
    
    def _load_active_tasks(self):
        """Load and schedule all active tasks from database."""
        session = self.SessionLocal()
        try:
            tasks = session.query(ScheduledTask).filter_by(is_active=True).all()
            
            for task in tasks:
                self._add_scheduler_job(task)
                logger.info(f"✓ Loaded scheduled task: {task.name}")
        finally:
            session.close()
    
    def _add_scheduler_job(self, task: ScheduledTask):
        """Add job to APScheduler."""
        try:
            schedule_config = json.loads(task.schedule_config)
            task_config = json.loads(task.task_config)
            
            trigger = self._parse_schedule_config(schedule_config)
            handler = self.task_handlers.get(task.task_type)
            
            if not handler:
                logger.warning(f"No handler registered for task type: {task.task_type}")
                return
            
            # Create job with handler
            job = self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task, task_config],
                id=f"task_{task.id}",
                replace_existing=True,
                name=task.name
            )
            
            logger.info(f"✓ Scheduled job: {task.name} (next run: {job.next_run_time})")
        except Exception as e:
            logger.error(f"Error adding scheduler job: {e}")
    
    def _parse_schedule_config(self, config: Dict[str, Any]):
        """Parse schedule configuration to APScheduler trigger."""
        schedule_type = config.get('type', 'cron')
        
        if schedule_type == 'cron':
            # Cron expression (e.g., "0 10 * * *" for 10 AM daily)
            cron_expr = config.get('cron_expr', '0 * * * *')
            return CronTrigger.from_crontab(cron_expr)
        
        elif schedule_type == 'interval':
            # Interval (e.g., every 30 minutes)
            minutes = config.get('minutes', 30)
            return IntervalTrigger(minutes=minutes)
        
        elif schedule_type == 'on_event':
            # Event-based (e.g., "whenever new email arrives")
            # For now, use polling interval as fallback
            return IntervalTrigger(minutes=5)
        
        else:
            logger.warning(f"Unknown schedule type: {schedule_type}, defaulting to hourly")
            return CronTrigger.from_crontab('0 * * * *')
    
    def _execute_task(self, task: ScheduledTask, task_config: Dict[str, Any]):
        """Execute a scheduled task within Flask app context if available."""
        logger.info(f"Executing task: {task.name}")
        
        try:
            handler = self.task_handlers.get(task.task_type)
            if handler:
                # Execute handler within Flask app context if available
                if self.app:
                    with self.app.app_context():
                        result = handler(task, task_config)
                else:
                    result = handler(task, task_config)
                
                # Update last_run
                session = self.SessionLocal()
                try:
                    db_task = session.query(ScheduledTask).filter_by(id=task.id).first()
                    if db_task:
                        db_task.last_run = datetime.utcnow()
                        session.commit()
                        logger.info(f"✓ Task completed: {task.name}")
                finally:
                    session.close()
                
                return result
        except Exception as e:
            logger.error(f"Error executing task {task.name}: {e}", exc_info=True)
    
    def create_task(
        self,
        name: str,
        task_type: str,
        natural_language_instruction: str,
        schedule_config: Dict[str, Any],
        task_config: Dict[str, Any],
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Optional[ScheduledTask]:
        """
        Create and schedule a new task.
        
        Args:
            name: Task name (unique)
            task_type: Type of task (e.g., 'email_check')
            natural_language_instruction: Natural language description
            schedule_config: Schedule config dict (e.g., {"type": "cron", "cron_expr": "0 10 * * *"})
            task_config: Task-specific config
            description: Optional description
            created_by: Admin user ID
        
        Returns:
            ScheduledTask or None if error
        """
        session = self.SessionLocal()
        try:
            # Check if task already exists
            existing = session.query(ScheduledTask).filter_by(name=name).first()
            if existing:
                logger.warning(f"Task {name} already exists")
                return None
            
            task = ScheduledTask(
                name=name,
                description=description,
                task_type=task_type,
                natural_language_instruction=natural_language_instruction,
                schedule_config=json.dumps(schedule_config),
                task_config=json.dumps(task_config),
                created_by=created_by,
            )
            
            session.add(task)
            session.commit()
            
            # Add to scheduler
            self._add_scheduler_job(task)
            
            logger.info(f"✓ Created task: {name}")
            return task
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
        finally:
            session.close()
    
    def update_task(self, task_id: int, **kwargs) -> Optional[ScheduledTask]:
        """Update an existing task."""
        session = self.SessionLocal()
        try:
            task = session.query(ScheduledTask).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"Task {task_id} not found")
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(task, key):
                    if key in ('schedule_config', 'task_config'):
                        setattr(task, key, json.dumps(value) if isinstance(value, dict) else value)
                    else:
                        setattr(task, key, value)
            
            task.updated_at = datetime.utcnow()
            session.commit()
            
            # Re-schedule if active
            if task.is_active:
                self._add_scheduler_job(task)
            
            logger.info(f"✓ Updated task: {task.name}")
            return task
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return None
        finally:
            session.close()
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        session = self.SessionLocal()
        try:
            task = session.query(ScheduledTask).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Remove from scheduler
            self.scheduler.remove_job(f"task_{task.id}")
            
            # Delete from database
            session.delete(task)
            session.commit()
            
            logger.info(f"✓ Deleted task: {task.name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
        finally:
            session.close()
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        session = self.SessionLocal()
        try:
            tasks = session.query(ScheduledTask).all()
            return [
                {
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'task_type': task.task_type,
                    'natural_language_instruction': task.natural_language_instruction,
                    'is_active': task.is_active,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'created_by': task.created_by,
                }
                for task in tasks
            ]
        finally:
            session.close()
    
    def enable_task(self, task_id: int) -> bool:
        """Enable a task."""
        return self.update_task(task_id, is_active=True) is not None
    
    def disable_task(self, task_id: int) -> bool:
        """Disable a task."""
        return self.update_task(task_id, is_active=False) is not None


# Natural language to cron parser
def parse_natural_language_schedule(instruction: str) -> Optional[Dict[str, Any]]:
    """
    Parse natural language instruction to schedule config.
    
    Examples:
    - "at 10 AM" → {"type": "cron", "cron_expr": "0 10 * * *"}
    - "every 30 minutes" → {"type": "interval", "minutes": 30}
    - "whenever new email arrives" → {"type": "on_event"}
    - "every day at 9 AM" → {"type": "cron", "cron_expr": "0 9 * * *"}
    - "every hour" → {"type": "interval", "minutes": 60}
    """
    instruction = instruction.lower().strip()
    
    # Time-based patterns
    if " am" in instruction or " pm" in instruction:
        # Extract time
        import re
        match = re.search(r'(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm)', instruction)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            am_pm = match.group(3)
            
            # Convert to 24-hour format
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
            
            return {"type": "cron", "cron_expr": f"{minute} {hour} * * *"}
    
    # Interval-based patterns
    if "every" in instruction:
        import re
        if "hour" in instruction:
            return {"type": "interval", "minutes": 60}
        elif "30 minute" in instruction or "thirty minute" in instruction:
            return {"type": "interval", "minutes": 30}
        elif "minute" in instruction:
            match = re.search(r'every (\d+)\s*minute', instruction)
            if match:
                return {"type": "interval", "minutes": int(match.group(1))}
            return {"type": "interval", "minutes": 1}
        elif "day" in instruction:
            return {"type": "cron", "cron_expr": "0 0 * * *"}
        elif "week" in instruction:
            return {"type": "cron", "cron_expr": "0 0 * * 0"}
    
    # Event-based patterns
    if "whenever" in instruction or "when" in instruction:
        if "new email" in instruction or "email arrives" in instruction:
            return {"type": "on_event", "event": "new_email"}
        elif "message" in instruction:
            return {"type": "on_event", "event": "new_message"}
    
    # Default: every hour
    logger.warning(f"Could not parse schedule instruction: {instruction}, defaulting to hourly")
    return {"type": "interval", "minutes": 60}
