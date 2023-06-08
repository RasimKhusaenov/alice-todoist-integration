import json

from todoist.scenes import SCENES, DEFAULT_SCENE
from todoist.request import Request


def handler(event, context):
    print('Incoming request: ' + json.dumps(event))
    request = Request(event)
    current_scene_id = request.session.get('scene')
    if current_scene_id is None:
        return DEFAULT_SCENE().reply(request)
    current_scene = SCENES.get(current_scene_id, DEFAULT_SCENE)()
    next_scene = current_scene.move(request)
    if next_scene is not None:
        print(f'Moving from scene {current_scene.id()} to {next_scene.id()}')
        return next_scene.reply(request)
    else:
        print(f'Failed to parse user request at scene {current_scene.id()}')
        return current_scene.fallback(request)
