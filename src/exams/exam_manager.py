"""
Менеджер экзаменов и тестов
"""

import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from src.common.models import Exam, Question, ExamResult, QuestionType
from src.database.database import Database


logger = logging.getLogger(__name__)


class ExamManager:
    """Менеджер для создания и проведения экзаменов"""
    
    def __init__(self, database: Database):
        self.database = database
        self.active_exams: Dict[str, Exam] = {}  # exam_id -> Exam
        self.exam_results: Dict[str, Dict[str, ExamResult]] = {}  # exam_id -> {student_id -> ExamResult}
        
        logger.info("ExamManager создан")
    
    def create_exam(self, title: str, questions: List[Question], duration_minutes: int = 60) -> Exam:
        """Создать новый экзамен"""
        exam_id = str(uuid.uuid4())
        
        exam = Exam(
            id=exam_id,
            title=title,
            questions=questions,
            duration_minutes=duration_minutes,
            created_at=datetime.now()
        )
        
        # Сохраняем в БД
        self.database.save_exam(exam)
        
        logger.info(f"Экзамен создан: {title} ({len(questions)} вопросов, {duration_minutes} мин)")
        return exam
    
    def start_exam(self, exam_id: str, student_ids: List[str]) -> bool:
        """Начать экзамен для студентов"""
        exam = self.database.get_exam(exam_id)
        if not exam:
            logger.error(f"Экзамен не найден: {exam_id}")
            return False
        
        self.active_exams[exam_id] = exam
        self.exam_results[exam_id] = {}
        
        # Создаем результаты для каждого студента
        for student_id in student_ids:
            result = ExamResult(
                id=str(uuid.uuid4()),
                exam_id=exam_id,
                student_id=student_id,
                answers={},
                score=0.0,
                max_score=sum(q.points for q in exam.questions),
                submitted_at=None,
                checked=False
            )
            self.exam_results[exam_id][student_id] = result
        
        logger.info(f"Экзамен начат: {exam.title} для {len(student_ids)} студентов")
        return True
    
    def submit_answers(self, exam_id: str, student_id: str, answers: Dict[str, any]) -> bool:
        """Студент отправляет ответы"""
        if exam_id not in self.exam_results:
            logger.error(f"Активный экзамен не найден: {exam_id}")
            return False
        
        if student_id not in self.exam_results[exam_id]:
            logger.error(f"Результат для студента не найден: {student_id}")
            return False
        
        result = self.exam_results[exam_id][student_id]
        result.answers = answers
        result.submitted_at = datetime.now()
        
        # Автоматическая проверка
        self._auto_check_answers(exam_id, student_id)
        
        logger.info(f"Ответы получены от студента {student_id}")
        return True
    
    def _auto_check_answers(self, exam_id: str, student_id: str):
        """Автоматическая проверка ответов"""
        exam = self.active_exams.get(exam_id)
        result = self.exam_results[exam_id][student_id]
        
        if not exam:
            return
        
        score = 0.0
        
        for question in exam.questions:
            q_id = question.id
            student_answer = result.answers.get(q_id)
            
            if not student_answer:
                continue
            
            # Проверяем в зависимости от типа вопроса
            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                # Множественный выбор
                correct = set(question.correct_answers)
                given = set(student_answer if isinstance(student_answer, list) else [student_answer])
                
                if correct == given:
                    score += question.points
                    
            elif question.question_type == QuestionType.TRUE_FALSE:
                # Верно/Неверно
                if str(student_answer).lower() == str(question.correct_answers[0]).lower():
                    score += question.points
                    
            elif question.question_type == QuestionType.FILL_BLANK:
                # Заполнить пропуски
                correct = [ans.lower().strip() for ans in question.correct_answers]
                given = student_answer.lower().strip() if isinstance(student_answer, str) else ""
                
                if given in correct:
                    score += question.points
                    
            elif question.question_type == QuestionType.OPEN_ENDED:
                # Открытый вопрос - требует ручной проверки
                pass
        
        result.score = score
        result.checked = True
        
        logger.info(f"Автопроверка завершена: {student_id}, баллы: {score}/{result.max_score}")
    
    def get_exam_results(self, exam_id: str) -> List[ExamResult]:
        """Получить результаты экзамена"""
        if exam_id not in self.exam_results:
            return []
        
        return list(self.exam_results[exam_id].values())
    
    def get_student_result(self, exam_id: str, student_id: str) -> Optional[ExamResult]:
        """Получить результат конкретного студента"""
        if exam_id not in self.exam_results:
            return None
        
        return self.exam_results[exam_id].get(student_id)
    
    def update_result_score(self, exam_id: str, student_id: str, score: float, comments: str = ""):
        """Обновить оценку (для ручной проверки)"""
        result = self.get_student_result(exam_id, student_id)
        if result:
            result.score = score
            result.comments = comments
            result.checked = True
            
            logger.info(f"Оценка обновлена: {student_id}, {score} баллов")
    
    def end_exam(self, exam_id: str):
        """Завершить экзамен"""
        if exam_id in self.active_exams:
            del self.active_exams[exam_id]
            logger.info(f"Экзамен завершен: {exam_id}")
    
    def get_statistics(self, exam_id: str) -> Dict:
        """Получить статистику экзамена"""
        results = self.get_exam_results(exam_id)
        
        if not results:
            return {}
        
        scores = [r.score for r in results if r.submitted_at]
        max_scores = [r.max_score for r in results]
        
        if not scores:
            return {"submitted": 0, "total": len(results)}
        
        avg_score = sum(scores) / len(scores)
        avg_max = sum(max_scores) / len(max_scores)
        avg_percentage = (avg_score / avg_max * 100) if avg_max > 0 else 0
        
        return {
            "submitted": len(scores),
            "total": len(results),
            "average_score": avg_score,
            "average_max": avg_max,
            "average_percentage": avg_percentage,
            "min_score": min(scores),
            "max_score": max(scores)
        }


class QuestionBuilder:
    """Построитель вопросов для экзаменов"""
    
    @staticmethod
    def create_multiple_choice(text: str, options: List[str], correct: List[int], points: int = 1) -> Question:
        """Создать вопрос с множественным выбором"""
        q_id = str(uuid.uuid4())
        correct_answers = [options[i] for i in correct]
        
        return Question(
            id=q_id,
            text=text,
            question_type=QuestionType.MULTIPLE_CHOICE,
            options=options,
            correct_answers=correct_answers,
            points=points
        )
    
    @staticmethod
    def create_true_false(text: str, correct: bool, points: int = 1) -> Question:
        """Создать вопрос Верно/Неверно"""
        q_id = str(uuid.uuid4())
        
        return Question(
            id=q_id,
            text=text,
            question_type=QuestionType.TRUE_FALSE,
            options=["Верно", "Неверно"],
            correct_answers=["Верно" if correct else "Неверно"],
            points=points
        )
    
    @staticmethod
    def create_open_ended(text: str, points: int = 1) -> Question:
        """Создать открытый вопрос"""
        q_id = str(uuid.uuid4())
        
        return Question(
            id=q_id,
            text=text,
            question_type=QuestionType.OPEN_ENDED,
            options=[],
            correct_answers=[],
            points=points
        )
    
    @staticmethod
    def create_fill_blank(text: str, correct_answers: List[str], points: int = 1) -> Question:
        """Создать вопрос с заполнением пропусков"""
        q_id = str(uuid.uuid4())
        
        return Question(
            id=q_id,
            text=text,
            question_type=QuestionType.FILL_BLANK,
            options=[],
            correct_answers=correct_answers,
            points=points
        )


class PollManager:
    """Менеджер для быстрых опросов"""
    
    def __init__(self):
        self.active_poll: Optional[Dict] = None
        self.poll_answers: Dict[str, any] = {}  # student_id -> answer
        
        logger.info("PollManager создан")
    
    def start_poll(self, question: str, options: List[str], timeout: int = 30):
        """Начать опрос"""
        poll_id = str(uuid.uuid4())
        
        self.active_poll = {
            "id": poll_id,
            "question": question,
            "options": options,
            "timeout": timeout,
            "started_at": datetime.now()
        }
        self.poll_answers = {}
        
        logger.info(f"Опрос начат: {question}")
        return poll_id
    
    def submit_answer(self, student_id: str, answer: any):
        """Студент отправляет ответ"""
        if not self.active_poll:
            logger.warning("Нет активного опроса")
            return False
        
        self.poll_answers[student_id] = answer
        logger.info(f"Ответ получен от {student_id}")
        return True
    
    def get_results(self) -> Dict:
        """Получить результаты опроса"""
        if not self.active_poll:
            return {}
        
        # Подсчет ответов
        answer_counts = {}
        for answer in self.poll_answers.values():
            answer_counts[answer] = answer_counts.get(answer, 0) + 1
        
        return {
            "question": self.active_poll["question"],
            "options": self.active_poll["options"],
            "total_answers": len(self.poll_answers),
            "answer_counts": answer_counts
        }
    
    def end_poll(self):
        """Завершить опрос"""
        if self.active_poll:
            logger.info(f"Опрос завершен: {self.active_poll['question']}")
            self.active_poll = None
            self.poll_answers = {}

