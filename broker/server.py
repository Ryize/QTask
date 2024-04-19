"""
Основная часть проекта.

Реализует прослушивание сокета, добавление задачи, сериализацию/десериализацию.

-------------------------------------------------------------------------------
Суть проекта: реализация процесса работающего в фоне (демона), который будет
получать данные с сокета. Данные имеют структуру:
    data: dict (словарь с данными. Формат:
        dict['title'] - название задачи
        dict['address'] - вложенный словарь с настройками подключения
            dict['address']['type'] - тип подключения (http/socket)
            dict['address']['link'] - адрес подключения.
                При type = http, link должен начинаться с http/https.
                При type = socket, link должен быть в формате сокеты
                    (0.0.0.0:5000)
        dict['settings'] - данные запроса
            dict['settings']['time'] - время, через которое будет отправлен
                запрос.
            dict['settings']['data'] - данные для отправки. Будут
                сериализовываться.
По этим данным будет создаваться задача (Task) и через указанный промежуток
времени будет отправляться запрос (на сокеты или HTTP). Мониторинг задач
выполняется многопоточным менеджером.
Проект позволит автоматизироваться отложенную отправку запросов и не нагружать
код и систему разрабатываемого проекта. Не имеет дополнительных зависимостей.

Реализовано:
1) Поднятие и работа сервера;
2) Прослушивание запросов с указанного сокета;
3) Многопоточный вызов функции обработчика запроса;
4) Класс задачи (с проверкой переданных данных);
5) Класс менеджера задач (вызов задачи по расписанию, добавление/удаление/просмотр);
6) Логирование;
7) Просмотр активных задач;
8) Поддержка headers в http запросах (в том числе случайных).

В планах. TODO:
1) Добавить отправку запросов по любому HTTP методу;
2) Добавить возможность отправки UDP запроса;
3) Отправка данных в каналы;
4) Интерфейс (Objective C/PyCocoa?);
"""
import socket
import json
import threading

from broker.config import DEBUG, HOST, PORT
from broker.managers.task import Task, TaskManager
from broker.logger import logger
from errors import ValidateError

task_manager = TaskManager()
task_manager.manage()


@logger(raise_e=True)
def add_task(data: dict) -> None:
    """
    Создаёт и сохраняет задачу.

    Создаёт объект Task, далее сохраняя объект в TaskManager (создаётся в
    global). После выводит список задач в консоль.

    Args:
        data: dict (словарь с данными. Формат:
            dict['title'] - название задачи
            dict['address'] - вложенный словарь с настройками подключения
                dict['address']['type'] - тип подключения (http/socket)
                dict['address']['link'] - адрес подключения.
                    При type = http, link должен начинаться с http/https.
                    При type = socket, link должен быть в формате сокеты
                        (0.0.0.0:5000)
            dict['settings'] - данные запроса
                dict['settings']['time'] - время, через которое будет отправлен
                    запрос.
                dict['settings']['data'] - данные для отправки. Будут
                    сериализовываться.
        )
    """
    task = Task(data)
    task_manager.append_task(task)
    if DEBUG:
        print('Задача добавлена!')
        print('Список задач:', *task_manager.get_tasks(), sep='\n- ')


@logger(raise_e=True)
def handle_request(conn: socket.socket) -> None:
    """
    Обработчик запроса.

    После прихода запроса, читает данные с сокета (по 1024б) и переводит в
    utf-8. Далее десериализирует с помощью json.loads.
    Может принять бесконечное кол-во данных, так как работает на бесконечно
    цикле.

    Args:
        conn: socket (объект запроса пользователя)
    """
    res_data = ''
    while True:
        data = conn.recv(1024)
        if not data:
            break
        res_data += data.decode()
    try:
        data_json = json.loads(res_data)
        add_task(data_json)
    except json.JSONDecodeError:
        print('Ошибка: Некорректный формат JSON')
    except ValidateError as exc:
        print(exc)


@logger
def main() -> None:
    """
    Запуск сервера.

    Подключается к сокету, слушает и при получении запроса вызывает
    обработчик запроса. Декоратор нейтрализует любые ошибки, и при их
    возникновении записывает в лог файл.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))

    server_socket.listen(10)
    print('Сервер запущен и ожидает подключений...')

    while True:
        conn, client_address = server_socket.accept()
        print(f'Подключение от {client_address}')

        thread = threading.Thread(target=handle_request, args=(conn,))
        thread.start()


if __name__ == '__main__':
    main()
