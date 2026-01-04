"""
Модуль управления классом и контроля студентов
"""

import logging
from typing import List, Dict, Optional
from src.common.models import Student, Group
from src.common.constants import StudentStatus
import uuid


logger = logging.getLogger(__name__)


class ClassroomControl:
    """Контроллер управления классом"""
    
    def __init__(self, server):
        self.server = server  # TeacherServer instance
        self.groups: Dict[str, Group] = {}
        
        logger.info("ClassroomControl создан")
    
    # ========== УПРАВЛЕНИЕ ГРУППАМИ ==========
    
    def create_group(self, name: str, student_ids: List[str], leader_id: Optional[str] = None) -> Group:
        """Создать группу студентов"""
        group_id = str(uuid.uuid4())
        
        group = Group(
            id=group_id,
            name=name,
            leader_id=leader_id,
            student_ids=student_ids
        )
        
        self.groups[group_id] = group
        
        # Обновляем группы у студентов
        for student_id in student_ids:
            if student_id in self.server.students:
                self.server.students[student_id].group_id = group_id
        
        logger.info(f"Группа создана: {name} ({len(student_ids)} студентов)")
        return group
    
    def create_random_groups(self, group_size: int) -> List[Group]:
        """Создать случайные группы"""
        import random
        
        # Получаем всех онлайн студентов
        students = [s for s in self.server.get_students() if s.status == StudentStatus.ONLINE]
        random.shuffle(students)
        
        groups = []
        for i in range(0, len(students), group_size):
            group_students = students[i:i+group_size]
            student_ids = [s.id for s in group_students]
            
            group = self.create_group(
                name=f"Группа {len(groups) + 1}",
                student_ids=student_ids,
                leader_id=student_ids[0] if student_ids else None
            )
            groups.append(group)
        
        logger.info(f"Создано {len(groups)} случайных групп")
        return groups
    
    def disband_all_groups(self):
        """Распустить все группы"""
        for student in self.server.get_students():
            student.group_id = None
        
        self.groups.clear()
        logger.info("Все группы распущены")
    
    def get_group_students(self, group_id: str) -> List[Student]:
        """Получить студентов группы"""
        if group_id not in self.groups:
            return []
        
        group = self.groups[group_id]
        students = []
        
        for student_id in group.student_ids:
            if student_id in self.server.students:
                students.append(self.server.students[student_id])
        
        return students
    
    # ========== БЛОКИРОВКА И КОНТРОЛЬ ==========
    
    def lock_screen(self, student_ids: List[str], message: str = "Экран заблокирован"):
        """Заблокировать экраны студентов"""
        from src.common.constants import MessageType
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.LOCK_SCREEN, {"message": message})
            
            if student_id in self.server.students:
                self.server.students[student_id].status = StudentStatus.SCREEN_LOCKED
        
        logger.info(f"Экраны заблокированы: {len(student_ids)} студентов")
    
    def unlock_screen(self, student_ids: List[str]):
        """Разблокировать экраны студентов"""
        from src.common.constants import MessageType
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.UNLOCK_SCREEN, {})
            
            if student_id in self.server.students:
                self.server.students[student_id].status = StudentStatus.ONLINE
        
        logger.info(f"Экраны разблокированы: {len(student_ids)} студентов")
    
    def lock_all_screens(self, message: str = "Экран заблокирован"):
        """Заблокировать экраны всех студентов"""
        student_ids = [s.id for s in self.server.get_students()]
        self.lock_screen(student_ids, message)
    
    def unlock_all_screens(self):
        """Разблокировать экраны всех студентов"""
        student_ids = [s.id for s in self.server.get_students()]
        self.unlock_screen(student_ids)
    
    def lock_input(self, student_ids: List[str]):
        """Заблокировать ввод (клавиатура/мышь) у студентов"""
        from src.common.constants import MessageType
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.LOCK_INPUT, {})
        
        logger.info(f"Ввод заблокирован: {len(student_ids)} студентов")
    
    def unlock_input(self, student_ids: List[str]):
        """Разблокировать ввод у студентов"""
        from src.common.constants import MessageType
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.UNLOCK_INPUT, {})
        
        logger.info(f"Ввод разблокирован: {len(student_ids)} студентов")
    
    def lock_all_input(self):
        """Заблокировать ввод у всех студентов"""
        student_ids = [s.id for s in self.server.get_students()]
        self.lock_input(student_ids)
    
    def unlock_all_input(self):
        """Разблокировать ввод у всех студентов"""
        student_ids = [s.id for s in self.server.get_students()]
        self.unlock_input(student_ids)
    
    # ========== УПРАВЛЕНИЕ ПРИЛОЖЕНИЯМИ ==========
    
    def block_application(self, student_ids: List[str], app_name: str):
        """Заблокировать приложение"""
        from src.common.constants import MessageType
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.BLOCK_APP, {"app_name": app_name})
        
        logger.info(f"Приложение {app_name} заблокировано для {len(student_ids)} студентов")
    
    def unblock_application(self, student_ids: List[str], app_name: str):
        """Разблокировать приложение"""
        from src.common.constants import MessageType
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.UNBLOCK_APP, {"app_name": app_name})
        
        logger.info(f"Приложение {app_name} разблокировано для {len(student_ids)} студентов")
    
    # ========== УДАЛЕННЫЕ КОМАНДЫ ==========
    
    def send_remote_command(self, student_ids: List[str], command: str, params: Dict = None):
        """Отправить удаленную команду"""
        from src.common.constants import MessageType
        
        params = params or {}
        
        for student_id in student_ids:
            self.server.send_to_student(student_id, MessageType.REMOTE_COMMAND, {
                "command": command,
                "params": params
            })
        
        logger.info(f"Команда {command} отправлена {len(student_ids)} студентам")
    
    def shutdown_computers(self, student_ids: List[str]):
        """Выключить компьютеры студентов"""
        self.send_remote_command(student_ids, "shutdown")
        logger.info(f"Команда выключения отправлена {len(student_ids)} студентам")
    
    def restart_computers(self, student_ids: List[str]):
        """Перезагрузить компьютеры студентов"""
        self.send_remote_command(student_ids, "restart")
        logger.info(f"Команда перезагрузки отправлена {len(student_ids)} студентам")
    
    # ========== НАБЛЮДЕНИЕ ==========
    
    def start_monitoring(self, student_id: str):
        """Начать наблюдение за студентом"""
        from src.common.constants import MessageType
        
        self.server.send_to_student(student_id, MessageType.DEMO_START, {
            "type": "monitor"
        })
        
        logger.info(f"Наблюдение за студентом {student_id} начато")
    
    def stop_monitoring(self, student_id: str):
        """Остановить наблюдение"""
        from src.common.constants import MessageType
        
        self.server.send_to_student(student_id, MessageType.DEMO_STOP, {})
        
        logger.info(f"Наблюдение за студентом {student_id} остановлено")
    
    def start_demo(self, student_id: str, broadcast_to_all: bool = False):
        """Начать демонстрацию студента"""
        from src.common.constants import MessageType
        
        self.server.send_to_student(student_id, MessageType.DEMO_START, {
            "type": "demo",
            "broadcast": broadcast_to_all
        })
        
        logger.info(f"Демонстрация студента {student_id} начата")
    
    # ========== СООБЩЕНИЯ ==========
    
    def send_message_to_student(self, student_id: str, message: str):
        """Отправить сообщение студенту"""
        from src.common.constants import MessageType
        
        self.server.send_to_student(student_id, MessageType.CHAT_MESSAGE, {
            "sender_id": "teacher",
            "sender_name": "Преподаватель",
            "content": message,
            "recipient_id": student_id
        })
        
        logger.info(f"Сообщение отправлено студенту {student_id}")
    
    def send_message_to_all(self, message: str):
        """Отправить сообщение всем студентам"""
        from src.common.constants import MessageType
        
        self.server.broadcast_to_all(MessageType.CHAT_MESSAGE, {
            "sender_id": "teacher",
            "sender_name": "Преподаватель",
            "content": message
        })
        
        logger.info("Сообщение отправлено всем студентам")
    
    def send_message_to_group(self, group_id: str, message: str):
        """Отправить сообщение группе"""
        from src.common.constants import MessageType
        
        if group_id not in self.groups:
            logger.warning(f"Группа не найдена: {group_id}")
            return
        
        group = self.groups[group_id]
        
        for student_id in group.student_ids:
            self.server.send_to_student(student_id, MessageType.CHAT_MESSAGE, {
                "sender_id": "teacher",
                "sender_name": "Преподаватель",
                "content": message,
                "group_id": group_id
            })
        
        logger.info(f"Сообщение отправлено группе {group.name}")
    
    # ========== СТАТИСТИКА ==========
    
    def get_classroom_stats(self) -> Dict:
        """Получить статистику класса"""
        students = self.server.get_students()
        
        total = len(students)
        online = sum(1 for s in students if s.status == StudentStatus.ONLINE)
        offline = total - online
        
        # Статусы
        status_counts = {}
        for s in students:
            status_counts[s.status] = status_counts.get(s.status, 0) + 1
        
        return {
            "total_students": total,
            "online": online,
            "offline": offline,
            "groups": len(self.groups),
            "status_counts": status_counts
        }
    
    def get_student_activity(self, student_id: str) -> Dict:
        """Получить активность студента"""
        if student_id not in self.server.students:
            return {}
        
        student = self.server.students[student_id]
        
        return {
            "student_id": student_id,
            "name": student.name,
            "status": student.status,
            "group_id": student.group_id,
            "last_seen": student.last_seen
        }


class WebAccessControl:
    """Контроль доступа к веб-сайтам"""
    
    def __init__(self):
        self.mode = "full_access"  # full_access, whitelist, blacklist
        self.whitelist: List[str] = []
        self.blacklist: List[str] = []
        
        logger.info("WebAccessControl создан")
    
    def set_full_access(self):
        """Полный доступ"""
        self.mode = "full_access"
        logger.info("Режим: полный доступ")
    
    def set_whitelist_mode(self, allowed_sites: List[str]):
        """Режим белого списка"""
        self.mode = "whitelist"
        self.whitelist = allowed_sites
        logger.info(f"Режим белого списка: {len(allowed_sites)} сайтов")
    
    def set_blacklist_mode(self, blocked_sites: List[str]):
        """Режим черного списка"""
        self.mode = "blacklist"
        self.blacklist = blocked_sites
        logger.info(f"Режим черного списка: {len(blocked_sites)} сайтов")
    
    def is_allowed(self, url: str) -> bool:
        """Проверить, разрешен ли URL"""
        if self.mode == "full_access":
            return True
        
        elif self.mode == "whitelist":
            return any(site in url for site in self.whitelist)
        
        elif self.mode == "blacklist":
            return not any(site in url for site in self.blacklist)
        
        return True

