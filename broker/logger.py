import logging
from typing import Union, TypeVar, Any, Callable

from broker.config import LOGGER_FILE, LOGGER_FORMAT

logging.basicConfig(level=logging.INFO,
                    filename=LOGGER_FILE,
                    format=LOGGER_FORMAT,
                    )
ErrType = TypeVar("ErrType", bound=Exception)


def logger(raise_e: bool = False) -> Callable:
    """
    Декоратор для логирования.

    Вызывает декорируемую функцию и если в ней возбуждается ошибка, записывает
    эту информацию в файл.

    Args:
        raise_e: bool (если True, то после отлавливания ошибки она будет
        повторно возбуждена).

    Returns:
        Callable: вложенная функция
    """

    def _logger(func: Callable) -> Callable:
        """
        Внутренняя функция декоратора.

        Args:
            func: Callable (декорируемая функция)

        Returns:
            Callable: вложенная функция
        """

        def wrapper(*args, **kwargs) -> Union[Any, ErrType]:
            """
            Внутренняя функция декоратора.

            Returns:
                Union[Any, ErrType]:
                    Any: результат работы декорируемой функции
                    ErrType: возникшая в декорируемой функции ошибка
            """
            try:
                res = func(*args, **kwargs)
                return res
            except BaseException as e:
                if not isinstance(e, KeyboardInterrupt):
                    logging.error('Error!', exc_info=True)
                if raise_e and isinstance(raise_e, bool):
                    raise e

        return wrapper

    if not isinstance(raise_e, bool):
        return _logger(raise_e)
    return _logger
