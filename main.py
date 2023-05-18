import os

from celery.result import AsyncResult
from flask import Flask, request, jsonify, send_file
from flask.views import MethodView
from celery import Celery
from werkzeug.security import safe_join
import redis

from upscale.upscale import upscale


redis_client = redis.Redis(host='db-redis')  # для храния данных "task_id": "путь к обработанному файлу"

app_name = 'app'
app = Flask(app_name)

celery_app = Celery(
    'app',
    backend=os.getenv('BACKEND'),
    broker=os.getenv('BROKER')
)

app.config['UPLOAD_FOLDER'] = 'initial_files'
app.config['RESULT_FOLDER'] = 'result_files'
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']  # для валидации расширения входного файла
BASEDIR = os.getcwd()

celery_app.conf.update(app.config)


class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery_app.Task = ContextTask


@celery_app.task(name='tasks.upscale_task')
def upscale_photo(input_path: str, output_path: str):
    """
    Возвращает обработанное изображение
    :param input_path: путь к изображению для апскейла
    :param output_path:  путь к выходному файлу
    """
    res = upscale(input_path, output_path)

    return res


class Upscaler(MethodView):

    def get(self, task_id):
        """
        Проверка готовности выполнения celery-задачи по идентификатору
        :param task_id: идентификатор celery-задачи
        :return: статус задачи и ссылку на обработанный файл, если задача выполнена
        """
        result_filename = str(redis_client.get(task_id)).rstrip("'").lstrip("b'")
        task = AsyncResult(task_id, app=celery_app)

        try:
            safe_path = safe_join(app.config["RESULT_FOLDER"], result_filename)

            return jsonify(
                {'status': task.status, 'link': f'{send_file(safe_path, as_attachment=True)}'
                 })

        except FileNotFoundError:

            return jsonify({
                'status': task.status, 'link': 'ссылка еще формируется, подождите...'
            })

    def post(self):
        """
        Отправка изображения на апскейл
        :return: идентификатор задачи для проверки выполнения
        """
        path_definition = self.path_definition_and_save_image('image_for_upscale')
        task = upscale_photo.delay(path_definition[0], path_definition[1])
        redis_client.mset({f'{task.id}': f'{path_definition[1].split("/")[-1]}'})

        return jsonify(
            {'task_id': task.id}
        )

    def path_definition_and_save_image(self, initial_photo):
        """
        Сохранение изображения
        :param initial_photo: изображение для апскейла
        :return: путь к сохраненному изображению для апскейла, путь к выходному файлу
        """
        image = request.files.get(initial_photo)
        extension = image.filename.split('.')[-1]

        if extension in ALLOWED_EXTENSIONS:  # валидация
            image_basename = image.filename.split('.')[-2]
            path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            image.save(path)
            result_path = os.path.join(
                app.config['RESULT_FOLDER'], f'{image_basename}_UPSCALED.{extension}')

            return path, result_path

        else:
            raise NameError


def get_file(file):
    """
    Возвращает обработанный файл ???
    :param file: название обработанного файла ?
    :return: ??
    """
    return jsonify({
        'result':
            f"file:///{os.getenv('HOSTNAME')}:5000{os.path.join(BASEDIR, app.config['RESULT_FOLDER'], file)}",
        'result_path': f"{os.path.join(BASEDIR, app.config['RESULT_FOLDER'], file)}"
    })


app.add_url_rule('/upscale', view_func=Upscaler.as_view('upscale'), methods=['POST'])
app.add_url_rule('/tasks/<task_id>', view_func=Upscaler.as_view('upscale_status'), methods=['GET'])
app.add_url_rule('/processed/<file>', view_func=get_file, methods=['GET'])

if __name__ == '__main__':
    app.run(host=os.getenv('HOSTNAME'))
