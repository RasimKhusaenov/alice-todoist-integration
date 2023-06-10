import enum
import inspect
import sys
import os
from abc import ABC, abstractmethod
from typing import Optional

from todoist import intents
from todoist.request import Request
from todoist.state import STATE_RESPONSE_KEY

from todoist_api_python.api import TodoistAPI

api = TodoistAPI(os.environ.get('TODOIST_APP_TOKEN'))


class TaskFilter(enum.Enum):
    TODAY = 'today'
    TOMORROW = 'tomorrow'

    @classmethod
    def from_request(cls, request: Request, intent_name: str):
        time_from_intent = request.intents[intent_name].get('slots', {}).get('time', {}).get('value')
        current_filter = time_from_intent or request.session.get('time', {}).get('value')
        if current_filter == 'today':
            return cls.TODAY
        elif current_filter == 'tomorrow':
            return cls.TOMORROW


class TaskPosition(enum.Enum):
    @classmethod
    def from_request(cls, request: Request):
        slot = request.session.get('position', {}).get('value', 0)

        return slot


def move_to_position(request: Request):
    position = TaskPosition.from_request(request)

    return position


class Scene(ABC):

    @classmethod
    def id(cls):
        return cls.__name__

    """Генерация ответа сцены"""
    @abstractmethod
    def reply(self, request):
        raise NotImplementedError()

    """Проверка перехода к новой сцене"""
    def move(self, request: Request):
        next_scene = self.handle_local_intents(request)
        if next_scene is None:
            next_scene = self.handle_global_intents(request)
        return next_scene

    @abstractmethod
    def handle_global_intents(self, request: Request):
        raise NotImplementedError()

    @abstractmethod
    def handle_local_intents(self, request: Request) -> Optional[str]:
        raise NotImplementedError()

    def fallback(self, request: Request):
        return self.make_response('Извините, я вас не поняла. Пожалуйста, попробуйте переформулировать вопрос.')

    def make_response(self, text, tts=None, card=None, state=None, buttons=None, directives=None):
        response = {
            'text': text,
            'tts': tts if tts is not None else text,
        }
        if card is not None:
            response['card'] = card
        if buttons is not None:
            response['buttons'] = buttons
        if directives is not None:
            response['directives'] = directives
        webhook_response = {
            'response': response,
            'version': '1.0',
            STATE_RESPONSE_KEY: {
                'scene': self.id(),
            },
        }
        if state is not None:
            webhook_response[STATE_RESPONSE_KEY].update(state)
        return webhook_response


class TodoistScene(Scene):
    def handle_global_intents(self, request):
        if intents.GET_NEAREST_TASKS in request.intents:
            return TasksList()


class Welcome(TodoistScene):
    def reply(self, request: Request):
        text = 'Привет! Я помогу управлять вашими задачами в Todoist.'
        tts = 'Привет! Я помогу управлять вашими задачами в Tod+oist.'
        return self.make_response(text, tts=tts)

    def handle_local_intents(self, request: Request):
        pass


class TasksList(TodoistScene):
    def reply(self, request: Request):
        current_filter = TaskFilter.from_request(request, intents.GET_NEAREST_TASKS).value
        tasks = api.get_tasks(filter=current_filter)
        tasks_count = len(tasks)

        texts = [f"Сейчас у вас {tasks_count} задач в списке."]

        for index, task in enumerate(tasks):
            position = index + 1
            texts.append(f"Задача №{position}: {task.content}.")

        text = " ".join(texts)

        return self.make_response(text)

    def handle_local_intents(self, request: Request):
        pass


def _list_scenes():
    current_module = sys.modules[__name__]
    scenes = []
    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, Scene):
            scenes.append(obj)
    return scenes


SCENES = {
    scene.id(): scene for scene in _list_scenes()
}

DEFAULT_SCENE = Welcome
