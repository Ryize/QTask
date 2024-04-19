"""
Модуль работы с задачами.

Содержит два класса - задачи и менеджер задач.
"""
import json
import random
import socket
import threading
import time

import requests

from broker.config import TIMEOUT
from errors import ValidateError


class Task:
    """
    Класс задачи.

    Содержит данные задачи.

    Fields:
        title: str (название задачи)
        address_type: str (тип подключения)
        address_link: str (адрес, куда будет отправляться запрос)
        settings_time: str (время задержки перед отправкой запроса)
        settings_data: str (передаваемые данные)
    """
    title: str
    address_type: str
    address_link: str
    settings_time: str
    settings_data: str

    def __init__(self, data: dict):
        """
        Принимает данные в dict и переводит в значения полей класса.

        Перед установкой полей, данные сначала проверяются на корректность
        формата.

        Args:
            data: dict (словарь с данными)
        """
        title = data.get('title')
        address = data.get('address')
        settings = data.get('settings')

        if not (title and isinstance(address, dict) and isinstance(settings,
                                                                   dict)):
            raise ValidateError('Missing key title or address or settings')
        if not (address.get('type') and address.get('link')):
            raise ValidateError('Missing key type or link in address')
        if not settings.get('time'):
            raise ValidateError('Missing key time in settings')

        self.title = title
        self.address_type = address.get('type')
        self.address_link = address.get('link')
        self.settings_time = settings.get('time') + time.time()
        self.settings_data = settings.get('data', {})

    def __repr__(self):
        return f'Задача: {self.title}'

    def __str__(self):
        return f'Задача: {self.title}'


class TaskManager:
    """
    Оркеструет задачами.

    Позволяет добавить, удалить, получить задачи. При вызове manage будет
    автоматическое отслеживание и вызов необходимых задач.

    Fields:
        __tasks: Iterable (список с задачами)
    """
    __tasks: list = []

    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    ]

    def append_task(self, task: Task) -> None:
        """
        Добавление задачи в __tasks.

        Args:
            task: Task (объект задачи)
        """
        self.__tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """
        Удаление задачи из __tasks.

        Args:
            task: Task (объект задачи)
        """
        self.__tasks.remove(task)

    def get_tasks(self) -> list:
        """
        Получение списка активных задач.

        Args:
            list[Task]: список задач
        """
        return self.__tasks

    def manage(self) -> None:
        """
        Обрабатывает задачи.

        В отдельном потоке (демоне) запускает бесконечный цикл с обработкой
        задачи.
        """
        thread = threading.Thread(target=self._manage)
        thread.setDaemon(daemonic=True)
        thread.start()

    def _manage(self) -> None:
        """
        Запускает бесконечный цикл и по времени отправляет запрос.

        В цикле проверяет все задачи, и если задержка прошла, то отправляет
        запрос, по указанному типу (http, socket).
        """
        while True:
            for task in self.__tasks:
                if not task.settings_time <= time.time():
                    continue
                if task.address_type == 'http':
                    self.__send_http(task)
                elif task.address_type == 'socket':
                    self.__send_socket(task)
            time.sleep(TIMEOUT)

    def __send_socket(self, task: Task) -> None:
        """
        Отправка данных по сокету.

        Отправляет данные на указанный сокет.

        Args:
            task: Task (объект задачи)
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            HOST = task.address_link.split(':')[0]
            PORT = task.address_link.split(':')[1]
            s.connect((HOST, int(PORT)))
            data = json.dumps(task.settings_data)
            s.send(bytes(data, 'utf8'))
        self.remove_task(task)

    def __send_http(self, task: Task) -> None:
        """
        Отправка данных по HTTP.

        Отправляет HTTP запрос с указанными в задаче параметрами.
        Поддерживает автоматическую установку headers (или ручную передачи в
        Task).

        Args:
            task: Task (объект задачи)
        """
        if task.settings_data:
            data: dict = task.settings_data
            headers = data.get('headers', {})
            if headers == 'auto':
                headers = self._get_random_user_agent()
            requests.get(task.address_link, data=data, headers=headers)
        else:
            requests.get(task.address_link)
        self.remove_task(task)

    def _get_random_user_agent(self) -> dict:
        """
        Получение случайного User Agent.

        Возвращает случайный User Agent из поля класса (user_agents).

        Returns:
            dict: Словарь в формате ['User-Agent'] = value
        """
        user_agent = random.choice(self.user_agents)
        return {'User-Agent': user_agent}

    def __new__(cls) -> 'TaskManager':
        """
        Singleton, так как менеджер в программе подразумевается 1.

        Работает через дополнительное поле __instance.
        """
        if not hasattr(cls, 'instance'):
            cls.__instance = super().__new__(cls)

        return cls.__instance
