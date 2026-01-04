"""
Контроль веб-доступа
Версия 1.0

Управление доступом к веб-сайтам:
- Режим полного доступа
- Белый список (только разрешённые)
- Чёрный список (запрещённые)
"""

import logging
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


logger = logging.getLogger(__name__)


class WebAccessMode(Enum):
    """Режим веб-доступа"""
    FULL_ACCESS = "full_access"
    WHITELIST = "whitelist"
    BLACKLIST = "blacklist"
    NO_ACCESS = "no_access"


@dataclass
class WebControlConfig:
    """Конфигурация веб-контроля"""
    mode: str = "full_access"
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)
    
    # Предустановленные списки
    educational_sites: List[str] = field(default_factory=lambda: [
        "wikipedia.org",
        "google.com",
        "google.ru",
        "youtube.com",  # Для образовательного контента
        "stackoverflow.com",
        "github.com",
        "docs.python.org",
        "w3schools.com",
        "khanacademy.org",
        "coursera.org",
        "edx.org",
        "academia.edu",
        "scholar.google.com",
        "translate.google.com",
        "deepl.com",
    ])
    
    social_sites: List[str] = field(default_factory=lambda: [
        "vk.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "telegram.org",
        "whatsapp.com",
        "discord.com",
        "reddit.com",
    ])
    
    gaming_sites: List[str] = field(default_factory=lambda: [
        "twitch.tv",
        "steam.com",
        "steampowered.com",
        "epicgames.com",
        "roblox.com",
        "minecraft.net",
    ])
    
    entertainment_sites: List[str] = field(default_factory=lambda: [
        "netflix.com",
        "hulu.com",
        "kinopoisk.ru",
        "ivi.ru",
    ])
    
    def to_dict(self) -> Dict:
        """Преобразовать в словарь для передачи"""
        return {
            'mode': self.mode,
            'whitelist': self.whitelist,
            'blacklist': self.blacklist
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WebControlConfig':
        """Создать из словаря"""
        return cls(
            mode=data.get('mode', 'full_access'),
            whitelist=data.get('whitelist', []),
            blacklist=data.get('blacklist', [])
        )


class WebAccessController:
    """Контроллер веб-доступа (серверная сторона)"""
    
    def __init__(self):
        self.config = WebControlConfig()
        logger.info("WebAccessController создан")
    
    def set_full_access(self):
        """Установить полный доступ"""
        self.config.mode = WebAccessMode.FULL_ACCESS.value
        logger.info("Веб-доступ: полный")
    
    def set_no_access(self):
        """Заблокировать весь интернет"""
        self.config.mode = WebAccessMode.NO_ACCESS.value
        logger.info("Веб-доступ: заблокирован")
    
    def set_whitelist(self, sites: List[str]):
        """Установить белый список"""
        self.config.mode = WebAccessMode.WHITELIST.value
        self.config.whitelist = sites
        logger.info(f"Веб-доступ: белый список ({len(sites)} сайтов)")
    
    def set_blacklist(self, sites: List[str]):
        """Установить чёрный список"""
        self.config.mode = WebAccessMode.BLACKLIST.value
        self.config.blacklist = sites
        logger.info(f"Веб-доступ: чёрный список ({len(sites)} сайтов)")
    
    def set_educational_only(self):
        """Только образовательные сайты"""
        self.set_whitelist(self.config.educational_sites.copy())
    
    def block_social(self):
        """Заблокировать соц. сети"""
        blocked = (
            self.config.social_sites + 
            self.config.gaming_sites + 
            self.config.entertainment_sites
        )
        self.set_blacklist(blocked)
    
    def add_to_whitelist(self, site: str):
        """Добавить в белый список"""
        if site not in self.config.whitelist:
            self.config.whitelist.append(site)
    
    def add_to_blacklist(self, site: str):
        """Добавить в чёрный список"""
        if site not in self.config.blacklist:
            self.config.blacklist.append(site)
    
    def remove_from_whitelist(self, site: str):
        """Удалить из белого списка"""
        if site in self.config.whitelist:
            self.config.whitelist.remove(site)
    
    def remove_from_blacklist(self, site: str):
        """Удалить из чёрного списка"""
        if site in self.config.blacklist:
            self.config.blacklist.remove(site)
    
    def get_config(self) -> Dict:
        """Получить конфигурацию для отправки"""
        return self.config.to_dict()
    
    def is_allowed(self, url: str) -> bool:
        """Проверить, разрешён ли URL"""
        mode = self.config.mode
        
        if mode == WebAccessMode.FULL_ACCESS.value:
            return True
        
        if mode == WebAccessMode.NO_ACCESS.value:
            return False
        
        # Извлекаем домен из URL
        domain = self._extract_domain(url)
        
        if mode == WebAccessMode.WHITELIST.value:
            return any(allowed in domain for allowed in self.config.whitelist)
        
        if mode == WebAccessMode.BLACKLIST.value:
            return not any(blocked in domain for blocked in self.config.blacklist)
        
        return True
    
    def _extract_domain(self, url: str) -> str:
        """Извлечь домен из URL"""
        url = url.lower()
        
        # Удаляем протокол
        if "://" in url:
            url = url.split("://", 1)[1]
        
        # Удаляем путь
        if "/" in url:
            url = url.split("/", 1)[0]
        
        # Удаляем порт
        if ":" in url:
            url = url.split(":", 1)[0]
        
        return url


class WebControlClient:
    """Клиент веб-контроля (на стороне студента)"""
    
    def __init__(self):
        self.config = WebControlConfig()
        self.enabled = False
        
        logger.info("WebControlClient создан")
    
    def apply_config(self, config_data: Dict):
        """Применить полученную конфигурацию"""
        self.config = WebControlConfig.from_dict(config_data)
        self.enabled = True
        
        logger.info(f"Веб-контроль применён: режим={self.config.mode}")
    
    def disable(self):
        """Отключить веб-контроль"""
        self.enabled = False
        self.config.mode = WebAccessMode.FULL_ACCESS.value
        logger.info("Веб-контроль отключён")
    
    def is_url_allowed(self, url: str) -> bool:
        """Проверить, разрешён ли URL"""
        if not self.enabled:
            return True
        
        mode = self.config.mode
        
        if mode == WebAccessMode.FULL_ACCESS.value:
            return True
        
        if mode == WebAccessMode.NO_ACCESS.value:
            return False
        
        domain = self._extract_domain(url)
        
        if mode == WebAccessMode.WHITELIST.value:
            allowed = any(site in domain for site in self.config.whitelist)
            if not allowed:
                logger.info(f"URL заблокирован (не в whitelist): {url}")
            return allowed
        
        if mode == WebAccessMode.BLACKLIST.value:
            blocked = any(site in domain for site in self.config.blacklist)
            if blocked:
                logger.info(f"URL заблокирован (в blacklist): {url}")
            return not blocked
        
        return True
    
    def _extract_domain(self, url: str) -> str:
        """Извлечь домен"""
        url = url.lower()
        if "://" in url:
            url = url.split("://", 1)[1]
        if "/" in url:
            url = url.split("/", 1)[0]
        if ":" in url:
            url = url.split(":", 1)[0]
        return url
    
    def get_mode_description(self) -> str:
        """Получить описание текущего режима"""
        mode = self.config.mode
        
        if mode == WebAccessMode.FULL_ACCESS.value:
            return "Полный доступ к интернету"
        elif mode == WebAccessMode.NO_ACCESS.value:
            return "Интернет заблокирован"
        elif mode == WebAccessMode.WHITELIST.value:
            count = len(self.config.whitelist)
            return f"Доступ только к {count} сайтам"
        elif mode == WebAccessMode.BLACKLIST.value:
            count = len(self.config.blacklist)
            return f"Заблокировано {count} сайтов"
        
        return "Неизвестный режим"


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест веб-контроля...")
    
    # Сервер
    controller = WebAccessController()
    
    # Тест белого списка
    controller.set_educational_only()
    print(f"Режим: {controller.config.mode}")
    print(f"Whitelist: {controller.config.whitelist[:5]}...")
    
    # Проверка URL
    test_urls = [
        "https://wikipedia.org/wiki/Python",
        "https://vk.com",
        "https://google.com/search?q=test",
        "https://tiktok.com",
    ]
    
    for url in test_urls:
        allowed = controller.is_allowed(url)
        print(f"  {url}: {'✅' if allowed else '❌'}")
    
    # Клиент
    print("\nКлиент:")
    client = WebControlClient()
    client.apply_config(controller.get_config())
    
    print(f"Режим: {client.get_mode_description()}")
    
    for url in test_urls:
        allowed = client.is_url_allowed(url)
        print(f"  {url}: {'✅' if allowed else '❌'}")
    
    print("\nТест завершён!")




