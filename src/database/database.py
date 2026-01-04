"""
База данных для хранения информации
"""

import sqlite3
import os
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.common.utils import get_app_dir, ensure_dir
from src.common.models import Student, Group, Exam, ExamResult, AudioCourse


logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = os.path.join(get_app_dir(), "data")
            ensure_dir(data_dir)
            db_path = os.path.join(data_dir, "classroom.db")
        
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
        logger.info(f"База данных: {db_path}")
    
    def connect(self) -> bool:
        """Подключиться к БД"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info("Подключение к БД установлено")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return False
    
    def init_tables(self):
        """Инициализировать таблицы"""
        try:
            cursor = self.conn.cursor()
            
            # Таблица студентов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    ip_address TEXT,
                    status TEXT DEFAULT 'offline',
                    group_id TEXT,
                    last_seen TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица групп
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    leader_id TEXT,
                    student_ids TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица экзаменов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exams (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    questions TEXT NOT NULL,
                    duration_minutes INTEGER DEFAULT 60,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица результатов экзаменов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_results (
                    id TEXT PRIMARY KEY,
                    exam_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    answers TEXT NOT NULL,
                    score REAL DEFAULT 0,
                    max_score REAL DEFAULT 0,
                    submitted_at TEXT,
                    checked INTEGER DEFAULT 0,
                    comments TEXT,
                    FOREIGN KEY (exam_id) REFERENCES exams (id),
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            """)
            
            # Таблица аудиокурсов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audio_courses (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    audio_file TEXT NOT NULL,
                    duration REAL DEFAULT 0,
                    segments TEXT,
                    subtitles TEXT,
                    bookmarks TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица записей уроков
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lesson_recordings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    duration REAL DEFAULT 0,
                    size INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица посещаемости
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time_in TEXT,
                    time_out TEXT,
                    duration INTEGER DEFAULT 0,
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            """)
            
            # Таблица настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            self.conn.commit()
            logger.info("Таблицы инициализированы")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации таблиц: {e}")
    
    def close(self):
        """Закрыть соединение"""
        if self.conn:
            self.conn.close()
            logger.info("Соединение с БД закрыто")
    
    # ========== СТУДЕНТЫ ==========
    
    def save_student(self, student: Student):
        """Сохранить студента"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO students 
                (id, name, ip_address, status, group_id, last_seen, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                student.id,
                student.name,
                student.ip_address,
                student.status,
                student.group_id,
                student.last_seen.isoformat() if student.last_seen else None,
                json.dumps(student.metadata)
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения студента: {e}")
    
    def get_student(self, student_id: str) -> Optional[Student]:
        """Получить студента по ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            
            if row:
                return Student(
                    id=row['id'],
                    name=row['name'],
                    ip_address=row['ip_address'],
                    status=row['status'],
                    group_id=row['group_id'],
                    last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения студента: {e}")
            return None
    
    def get_all_students(self) -> List[Student]:
        """Получить всех студентов"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY name")
            rows = cursor.fetchall()
            
            students = []
            for row in rows:
                student = Student(
                    id=row['id'],
                    name=row['name'],
                    ip_address=row['ip_address'],
                    status=row['status'],
                    group_id=row['group_id'],
                    last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                students.append(student)
            
            return students
            
        except Exception as e:
            logger.error(f"Ошибка получения студентов: {e}")
            return []
    
    def delete_student(self, student_id: str):
        """Удалить студента"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка удаления студента: {e}")
    
    # ========== ГРУППЫ ==========
    
    def save_group(self, group: Group):
        """Сохранить группу"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO groups 
                (id, name, leader_id, student_ids, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                group.id,
                group.name,
                group.leader_id,
                json.dumps(group.student_ids),
                group.created_at.isoformat()
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения группы: {e}")
    
    def get_group(self, group_id: str) -> Optional[Group]:
        """Получить группу по ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            
            if row:
                return Group(
                    id=row['id'],
                    name=row['name'],
                    leader_id=row['leader_id'],
                    student_ids=json.loads(row['student_ids']) if row['student_ids'] else [],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения группы: {e}")
            return None
    
    def get_all_groups(self) -> List[Group]:
        """Получить все группы"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM groups ORDER BY name")
            rows = cursor.fetchall()
            
            groups = []
            for row in rows:
                group = Group(
                    id=row['id'],
                    name=row['name'],
                    leader_id=row['leader_id'],
                    student_ids=json.loads(row['student_ids']) if row['student_ids'] else [],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
                groups.append(group)
            
            return groups
            
        except Exception as e:
            logger.error(f"Ошибка получения групп: {e}")
            return []
    
    # ========== ЭКЗАМЕНЫ ==========
    
    def save_exam(self, exam: Exam):
        """Сохранить экзамен"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO exams 
                (id, title, questions, duration_minutes, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                exam.id,
                exam.title,
                json.dumps([q.to_dict() for q in exam.questions]),
                exam.duration_minutes,
                exam.created_at.isoformat()
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения экзамена: {e}")
    
    def get_exam(self, exam_id: str) -> Optional[Exam]:
        """Получить экзамен по ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
            row = cursor.fetchone()
            
            if row:
                from src.common.models import Question, QuestionType
                questions_data = json.loads(row['questions'])
                questions = [
                    Question(
                        id=q['id'],
                        text=q['text'],
                        question_type=QuestionType(q['question_type']),
                        options=q.get('options', []),
                        correct_answers=q.get('correct_answers', []),
                        points=q.get('points', 1)
                    )
                    for q in questions_data
                ]
                
                return Exam(
                    id=row['id'],
                    title=row['title'],
                    questions=questions,
                    duration_minutes=row['duration_minutes'],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения экзамена: {e}")
            return None
    
    # ========== НАСТРОЙКИ ==========
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Получить настройку"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                try:
                    return json.loads(row['value'])
                except:
                    return row['value']
            return default
            
        except Exception as e:
            logger.error(f"Ошибка получения настройки: {e}")
            return default
    
    def set_setting(self, key: str, value: Any):
        """Установить настройку"""
        try:
            cursor = self.conn.cursor()
            value_str = json.dumps(value) if not isinstance(value, str) else value
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, (key, value_str))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка установки настройки: {e}")

