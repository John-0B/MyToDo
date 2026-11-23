import sys
import os
import traceback

# Записываем все ошибки в файл
def log_error(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_log = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        log_path = "/sdcard/Download/mytodo_error.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(error_log)
            f.write("\n" + "="*50 + "\n")
    except:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = log_error

# Настройки OpenGL ТОЛЬКО для Windows
if sys.platform == 'win32':
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

# Безопасный импорт yadisk
try:
    import yadisk
except ImportError:
    yadisk = None

import json
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
# --- Цвета ---
BG_COLOR = (0.17, 0.17, 0.17, 1)
FG_COLOR = (0.4, 0.85, 1, 1)
TREE_BG = (0.12, 0.12, 0.12, 1)
DONE_COLOR = (0.3, 0.69, 0.31, 1)
BTN_GREEN = (0.3, 0.69, 0.31, 1)
BTN_ORANGE = (1, 0.6, 0, 1)
BTN_RED = (0.96, 0.26, 0.21, 1)
BTN_BLUE = (0.13, 0.59, 0.95, 1)
BTN_PURPLE = (0.61, 0.15, 0.69, 1)
BTN_CYAN = (0, 0.75, 0.75, 1)
BTN_TEAL = (0, 0.5, 0.5, 1)
BTN_GRAY = (0.4, 0.4, 0.4, 1)
GOLD_COLOR = (1, 0.84, 0, 1)

# --- Пути (безопасные для Android) ---
def get_data_path(filename):
    try:
        app = App.get_running_app()
        if app and hasattr(app, 'user_data_dir') and app.user_data_dir:
            return os.path.join(app.user_data_dir, filename)
    except Exception:
        pass
    return filename  # Фоллбэк для ПК или до инициализации App

CONFIG_FILE_NAME = "config.json"
REMOTE_FILE_PATH = "app:/tree_tasks.json"
REMOTE_PRIORITY_PATH = "app:/priority.json"
LOCAL_FILE_NAME_BASE = "tree_tasks.json"
PRIORITY_FILE_BASE = "priority.json"


# --- Функции работы с данными ---
def load_config():
    path = get_data_path(CONFIG_FILE_NAME)
    if not os.path.exists(path):
        default_config = {"yandex_token": "ВСТАВЬТЕ_ВАШ_ТОКЕН_СЮДА"}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        raise FileNotFoundError(f"Файл config.json не найден. Шаблон создан по пути: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    if "yandex_token" not in config or config["yandex_token"] == "ВСТАВЬТЕ_ВАШ_ТОКЕН_СЮДА":
        raise ValueError(f"Токен не настроен в файле: {path}")
    return config["yandex_token"]


def load_tasks_local():
    path = get_data_path(LOCAL_FILE_NAME_BASE)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_tasks_local(tasks):
    path = get_data_path(LOCAL_FILE_NAME_BASE)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def load_priorities():
    path = get_data_path(PRIORITY_FILE_BASE)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("priorities", [])
        except:
            return []
    return []


def save_priorities(priorities):
    path = get_data_path(PRIORITY_FILE_BASE)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"priorities": priorities}, f, ensure_ascii=False, indent=2)


def update_task_timestamp(tasks, task_id, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    for task in tasks:
        if task['id'] == task_id:
            task['last_modified'] = timestamp
            return True
        if update_task_timestamp(task['children'], task_id, timestamp):
            task['last_modified'] = timestamp
            return True
    return False


def find_task(tasks, task_id):
    for task in tasks:
        if task['id'] == task_id:
            return task
        found = find_task(task['children'], task_id)
        if found:
            return found
    return None


def remove_task(tasks, task_id):
    for i, task in enumerate(tasks):
        if task['id'] == task_id:
            return tasks.pop(i)
        removed = remove_task(task['children'], task_id)
        if removed:
            return removed
    return None


def index_to_label(index, is_root=True):
    alphabet = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    if is_root:
        if index < len(alphabet):
            return alphabet[index]
        else:
            first = alphabet[index // len(alphabet) - 1]
            second = alphabet[index % len(alphabet)]
            return f"{first}{second}"
    else:
        return str(index + 1)


def get_task_number(tasks, task_id):
    def find_path(tasks, target_id, current_path):
        for i, task in enumerate(tasks):
            if task['id'] == target_id:
                return current_path + [i]
            result = find_path(task['children'], target_id, current_path + [i])
            if result:
                return result
        return None

    path = find_path(tasks, task_id, [])
    if not path:
        return ""

    result = []
    for i, idx in enumerate(path):
        if i == 0:
            result.append(index_to_label(idx, is_root=True))
        else:
            result.append(index_to_label(idx, is_root=False))

    return ".".join(result)


# --- Виджет одного дела ---
class TaskItem(BoxLayout):
    def __init__(self, task, depth, app, expanded=False, **kwargs):
        super().__init__(**kwargs)
        self.task = task
        self.depth = depth
        self.app = app
        self.expanded = expanded
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(75)
        self.padding = [dp(10) * (depth + 1), dp(5), dp(10), dp(5)]

        has_children = len(task.get('children', [])) > 0

        top_row = BoxLayout(size_hint_y=0.55, spacing=dp(3))

        if has_children:
            self.toggle_btn = Button(
                text="v" if expanded else ">",
                size_hint_x=None,
                width=dp(40),
                background_color=BTN_GRAY,
                color=(1, 1, 1, 1),
                font_size=dp(16),
                bold=True
            )
            self.toggle_btn.bind(on_press=self.on_toggle_expand)
            top_row.add_widget(self.toggle_btn)
        else:
            spacer = Label(size_hint_x=None, width=dp(40))
            top_row.add_widget(spacer)

        self.checkbox = CheckBox(
            active=task['done'],
            size_hint_x=None,
            width=dp(40),
            color=DONE_COLOR
        )
        self.checkbox.bind(active=self.on_checkbox_change)
        top_row.add_widget(self.checkbox)

        task_number = get_task_number(self.app.tasks, task['id'])
        display_name = f"{task_number}. {task['name']}"
        self.name_label = Label(
            text=display_name,
            halign='left',
            valign='middle',
            color=DONE_COLOR if task['done'] else FG_COLOR,
            font_size=dp(14)
        )
        self.name_label.bind(size=self.name_label.setter('text_size'))
        top_row.add_widget(self.name_label)

        in_priority = task['id'] in self.app.priorities
        self.priority_btn = Button(
            text="S" if in_priority else "s",
            size_hint_x=None,
            width=dp(35),
            background_color=BTN_GRAY,
            color=GOLD_COLOR,
            font_size=dp(16),
            bold=True
        )
        self.priority_btn.bind(on_press=self.on_toggle_priority)
        top_row.add_widget(self.priority_btn)

        focus_btn = Button(
            text="F",
            size_hint_x=None,
            width=dp(35),
            background_color=BTN_GRAY,
            color=FG_COLOR,
            font_size=dp(14),
            bold=True
        )
        focus_btn.bind(on_press=self.on_focus)
        top_row.add_widget(focus_btn)

        add_btn = Button(
            text="+",
            size_hint_x=None,
            width=dp(35),
            background_color=BTN_GREEN,
            color=(1, 1, 1, 1),
            font_size=dp(18),
            bold=True
        )
        add_btn.bind(on_press=self.on_add_subtask)
        top_row.add_widget(add_btn)

        self.add_widget(top_row)

        bottom_row = BoxLayout(size_hint_y=0.45, spacing=dp(3), padding=[dp(40), 0, 0, 0])

        edit_btn = Button(text="Изм.", background_color=BTN_ORANGE, color=(1, 1, 1, 1), font_size=dp(11))
        edit_btn.bind(on_press=self.on_edit)
        bottom_row.add_widget(edit_btn)

        move_btn = Button(text="Перен.", background_color=BTN_TEAL, color=(1, 1, 1, 1), font_size=dp(11))
        move_btn.bind(on_press=self.on_move)
        bottom_row.add_widget(move_btn)

        delete_btn = Button(text="Удал.", background_color=BTN_RED, color=(1, 1, 1, 1), font_size=dp(11))
        delete_btn.bind(on_press=self.on_delete)
        bottom_row.add_widget(delete_btn)

        self.add_widget(bottom_row)

    def on_toggle_expand(self, instance):
        current_state = self.app.expanded_tasks.get(self.task['id'], False)
        self.app.expanded_tasks[self.task['id']] = not current_state
        instance.text = "v" if self.app.expanded_tasks[self.task['id']] else ">"
        self.app.refresh_tasks()

    def on_checkbox_change(self, instance, value):
        self.task['done'] = value
        update_task_timestamp(self.app.tasks, self.task['id'])
        save_tasks_local(self.app.tasks)
        self.name_label.color = DONE_COLOR if value else FG_COLOR

        if value and self.task['id'] in self.app.priorities:
            self.app.priorities.remove(self.task['id'])
            save_priorities(self.app.priorities)

        self.app.refresh_tasks()
        self.app.update_priority_button()

    def on_toggle_priority(self, instance):
        task_id = self.task['id']
        if task_id in self.app.priorities:
            self.app.priorities.remove(task_id)
            instance.text = "s"
        else:
            self.app.priorities.append(task_id)
            instance.text = "S"
        save_priorities(self.app.priorities)
        self.app.update_priority_button()

    def on_focus(self, instance):
        self.app.focus_on_task(self.task['id'])

    def on_add_subtask(self, instance):
        self.app.show_add_subtask_dialog(self.task['id'])

    def on_edit(self, instance):
        self.app.show_edit_dialog(self.task['id'])

    def on_move(self, instance):
        self.app.show_move_dialog(self.task['id'])

    def on_delete(self, instance):
        self.app.show_delete_confirm(self.task['id'])


# --- Виджет дела в списке приоритетов ---
class PriorityItem(BoxLayout):
    def __init__(self, task, position, total, app, **kwargs):
        super().__init__(**kwargs)
        self.task = task
        self.position = position
        self.total = total
        self.app = app
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [dp(5), dp(3), dp(5), dp(3)]
        self.spacing = dp(3)

        pos_label = Label(text=f"{position}.", color=GOLD_COLOR, font_size=dp(14), bold=True, size_hint_x=None, width=dp(35))
        self.add_widget(pos_label)

        task_number = get_task_number(self.app.tasks, task['id'])
        name_label = Label(text=f"{task_number}. {task['name']}", color=FG_COLOR, font_size=dp(13), halign='left')
        name_label.bind(size=name_label.setter('text_size'))
        self.add_widget(name_label)

        up_btn = Button(text="^", size_hint_x=None, width=dp(40), background_color=BTN_GRAY, color=FG_COLOR, font_size=dp(16), bold=True)
        up_btn.bind(on_press=self.on_move_up)
        if position == 1:
            up_btn.disabled = True
            up_btn.color = (0.3, 0.3, 0.3, 1)
        self.add_widget(up_btn)

        down_btn = Button(text="v", size_hint_x=None, width=dp(40), background_color=BTN_GRAY, color=FG_COLOR, font_size=dp(16), bold=True)
        down_btn.bind(on_press=self.on_move_down)
        if position == total:
            down_btn.disabled = True
            down_btn.color = (0.3, 0.3, 0.3, 1)
        self.add_widget(down_btn)

        done_btn = Button(text="D", size_hint_x=None, width=dp(40), background_color=BTN_GRAY, color=DONE_COLOR, font_size=dp(14), bold=True)
        done_btn.bind(on_press=self.on_mark_done)
        self.add_widget(done_btn)

        remove_btn = Button(text="X", size_hint_x=None, width=dp(40), background_color=BTN_GRAY, color=BTN_RED, font_size=dp(16), bold=True)
        remove_btn.bind(on_press=self.on_remove)
        self.add_widget(remove_btn)

    def on_move_up(self, instance):
        idx = self.position - 1
        if idx > 0:
            self.app.priorities[idx], self.app.priorities[idx - 1] = self.app.priorities[idx - 1], self.app.priorities[idx]
            save_priorities(self.app.priorities)
            self.app.refresh_priority_screen()

    def on_move_down(self, instance):
        idx = self.position - 1
        if idx < len(self.app.priorities) - 1:
            self.app.priorities[idx], self.app.priorities[idx + 1] = self.app.priorities[idx + 1], self.app.priorities[idx]
            save_priorities(self.app.priorities)
            self.app.refresh_priority_screen()

    def on_mark_done(self, instance):
        task_id = self.task['id']
        task = find_task(self.app.tasks, task_id)
        if task:
            task['done'] = True
            update_task_timestamp(self.app.tasks, task_id)
            if task_id in self.app.priorities:
                self.app.priorities.remove(task_id)
            save_priorities(self.app.priorities)
            save_tasks_local(self.app.tasks)
            self.app.refresh_priority_screen()
            self.app.refresh_tasks()
            self.app.update_priority_button()

    def on_remove(self, instance):
        task_id = self.task['id']
        if task_id in self.app.priorities:
            self.app.priorities.remove(task_id)
            save_priorities(self.app.priorities)
            self.app.refresh_priority_screen()
            self.app.refresh_tasks()
            self.app.update_priority_button()


# --- Главный экран ---
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'main'

        layout = BoxLayout(orientation='vertical', padding=[dp(10), dp(10), dp(10), dp(10)], spacing=dp(5))
        self.add_widget(layout)

        header = Label(text="Мои дела", size_hint_y=None, height=dp(40), font_size=dp(22), bold=True, color=FG_COLOR)
        layout.add_widget(header)

        self.sync_label = Label(text="Загрузка...", size_hint_y=None, height=dp(25), font_size=dp(11), color=(0.7, 0.7, 0.7, 1))
        layout.add_widget(self.sync_label)

        self.focus_panel = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5), padding=[dp(5), 0, dp(5), 0])
        self.focus_panel.opacity = 0
        self.focus_label = Label(text="", color=GOLD_COLOR, font_size=dp(12), bold=True, halign='left')
        self.focus_label.bind(size=self.focus_label.setter('text_size'))
        self.focus_panel.add_widget(self.focus_label)

        clear_focus_btn = Button(text="< Все дела", size_hint_x=None, width=dp(100), background_color=BTN_BLUE, color=(1, 1, 1, 1), font_size=dp(12))
        clear_focus_btn.bind(on_press=self.on_clear_focus)
        self.focus_panel.add_widget(clear_focus_btn)
        layout.add_widget(self.focus_panel)

        self.scroll = ScrollView(size_hint_y=1)
        self.tasks_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        self.tasks_container.bind(minimum_height=self.tasks_container.setter('height'))
        self.scroll.add_widget(self.tasks_container)
        layout.add_widget(self.scroll)

        btn_row1 = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        add_btn = Button(text="+ Создать", background_color=BTN_GREEN, color=(1, 1, 1, 1), font_size=dp(13), bold=True)
        add_btn.bind(on_press=self.on_add_task)
        btn_row1.add_widget(add_btn)

        self.priority_btn = Button(text="S Приоритеты (0)", background_color=BTN_GRAY, color=GOLD_COLOR, font_size=dp(13), bold=True)
        self.priority_btn.bind(on_press=self.on_show_priorities)
        btn_row1.add_widget(self.priority_btn)
        layout.add_widget(btn_row1)

        btn_row2 = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        download_btn = Button(text="< Из облака", background_color=BTN_CYAN, color=(1, 1, 1, 1), font_size=dp(13), bold=True)
        download_btn.bind(on_press=self.on_download)
        btn_row2.add_widget(download_btn)

        sync_btn = Button(text="> В облако", background_color=BTN_PURPLE, color=(1, 1, 1, 1), font_size=dp(13), bold=True)
        sync_btn.bind(on_press=self.on_sync)
        btn_row2.add_widget(sync_btn)
        layout.add_widget(btn_row2)

    def on_add_task(self, instance):
        App.get_running_app().show_add_task_dialog()

    def on_show_priorities(self, instance):
        App.get_running_app().show_priority_screen()

    def on_download(self, instance):
        App.get_running_app().download_from_cloud()

    def on_sync(self, instance):
        App.get_running_app().manual_sync()

    def on_clear_focus(self, instance):
        App.get_running_app().clear_focus()


# --- Экран приоритетов ---
class PriorityScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'priority'

        layout = BoxLayout(orientation='vertical', padding=[dp(10), dp(10), dp(10), dp(10)], spacing=dp(5))
        self.add_widget(layout)

        header = Label(text="S Приоритеты", size_hint_y=None, height=dp(40), font_size=dp(20), bold=True, color=GOLD_COLOR)
        layout.add_widget(header)

        self.status_label = Label(text="Всего: 0", size_hint_y=None, height=dp(25), font_size=dp(11), color=(0.7, 0.7, 0.7, 1))
        layout.add_widget(self.status_label)

        self.scroll = ScrollView(size_hint_y=1)
        self.list_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        self.scroll.add_widget(self.list_container)
        layout.add_widget(self.scroll)

        back_btn = Button(text="< Назад к делам", size_hint_y=None, height=dp(45), background_color=BTN_BLUE, color=(1, 1, 1, 1), font_size=dp(14), bold=True)
        back_btn.bind(on_press=lambda inst: setattr(App.get_running_app().root, 'current', 'main'))
        layout.add_widget(back_btn)


# --- Главное приложение ---
class TodoApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks = []
        self.next_id = 1
        self.yandex_disk = None
        self.expanded_tasks = {}
        self.priorities = []
        self.focused_task_id = None

    def build(self):
        Window.clearcolor = BG_COLOR

        if yadisk is None:
            return Label(text="Ошибка: библиотека yadisk не найдена.\nДобавьте 'yadisk' в requirements в buildozer.spec", color=(1, 0, 0, 1), halign='center')

        try:
            token = load_config()
            self.yandex_disk = yadisk.YaDisk(token=token)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Ошибка:\n{e}"))
            return Label(text="Ошибка конфигурации", color=(1, 0, 0, 1), halign='center')

        self.tasks = load_tasks_local()
        self.priorities = load_priorities()
        if self.tasks:
            self.next_id = max(t['id'] for t in self.flatten_tasks(self.tasks)) + 1

        sm = ScreenManager()
        self.main_screen = MainScreen()
        self.priority_screen = PriorityScreen()
        sm.add_widget(self.main_screen)
        sm.add_widget(self.priority_screen)

        Clock.schedule_once(lambda dt: self.sync_on_startup(), 0.5)
        Clock.schedule_once(lambda dt: self.refresh_tasks(), 0.3)

        return sm

    def flatten_tasks(self, tasks):
        result = []
        for task in tasks:
            result.append(task)
            result.extend(self.flatten_tasks(task['children']))
        return result

    def refresh_tasks(self):
        if not hasattr(self, 'main_screen') or not self.main_screen:
            return

        self.main_screen.tasks_container.clear_widgets()

        if self.focused_task_id is not None:
            focused_task = find_task(self.tasks, self.focused_task_id)
            if focused_task:
                expanded = self.expanded_tasks.get(focused_task['id'], True)
                item = TaskItem(focused_task, 0, self, expanded=expanded)
                self.main_screen.tasks_container.add_widget(item)
                if expanded:
                    self.add_children_recursive(focused_task, 1)
        else:
            for task in self.tasks:
                expanded = self.expanded_tasks.get(task['id'], False)
                item = TaskItem(task, 0, self, expanded=expanded)
                self.main_screen.tasks_container.add_widget(item)
                if expanded:
                    self.add_children_recursive(task, 1)

        self.update_priority_button()

    def add_children_recursive(self, parent_task, depth):
        for child in parent_task.get('children', []):
            expanded = self.expanded_tasks.get(child['id'], False)
            item = TaskItem(child, depth, self, expanded=expanded)
            self.main_screen.tasks_container.add_widget(item)
            if expanded:
                self.add_children_recursive(child, depth + 1)

    def update_priority_button(self):
        if hasattr(self, 'main_screen') and self.main_screen:
            count = len([p for p in self.priorities if find_task(self.tasks, p) and not find_task(self.tasks, p)['done']])
            self.main_screen.priority_btn.text = f"S Приоритеты ({count})"

    def sync_on_startup(self):
        try:
            if self.yandex_disk.exists(REMOTE_FILE_PATH):
                temp_file = get_data_path("temp_sync.json")
                self.yandex_disk.download(REMOTE_FILE_PATH, temp_file)
                with open(temp_file, 'r', encoding='utf-8') as f:
                    remote_tasks = json.load(f)
                os.remove(temp_file)

                if not self.tasks:
                    self.tasks = remote_tasks
                    self.next_id = max(t['id'] for t in self.flatten_tasks(self.tasks)) + 1
                    self.refresh_tasks()
                    self.main_screen.sync_label.text = "Загружено из облака"
                    self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)
                else:
                    self.main_screen.sync_label.text = f"Локально: {len(self.tasks)} дел"
                    self.main_screen.sync_label.color = (0.7, 0.7, 0.7, 1)
            else:
                self.main_screen.sync_label.text = "Файла в облаке нет"
                self.main_screen.sync_label.color = (1, 0.7, 0, 1)

            self._sync_priorities_from_cloud()
        except Exception as e:
            self.main_screen.sync_label.text = f"Ошибка: {str(e)[:50]}"
            self.main_screen.sync_label.color = (1, 0.3, 0.3, 1)

    def _sync_priorities_from_cloud(self):
        try:
            if self.yandex_disk.exists(REMOTE_PRIORITY_PATH):
                temp_file = get_data_path("temp_priority.json")
                self.yandex_disk.download(REMOTE_PRIORITY_PATH, temp_file)
                with open(temp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                os.remove(temp_file)
                cloud_priorities = data.get("priorities", [])
                if not self.priorities:
                    self.priorities = cloud_priorities
                    save_priorities(self.priorities)
                    self.refresh_tasks()
        except Exception as e:
            print(f"Не удалось загрузить приоритеты: {e}")

    def download_from_cloud(self):
        try:
            if not self.yandex_disk.exists(REMOTE_FILE_PATH):
                self.show_error("Файл не найден на Яндекс.Диске")
                return

            temp_file = get_data_path("temp_sync.json")
            self.yandex_disk.download(REMOTE_FILE_PATH, temp_file)
            with open(temp_file, 'r', encoding='utf-8') as f:
                remote_tasks = json.load(f)
            os.remove(temp_file)

            self.tasks = remote_tasks
            self.next_id = max(t['id'] for t in self.flatten_tasks(self.tasks)) + 1
            save_tasks_local(self.tasks)
            self.refresh_tasks()

            if self.yandex_disk.exists(REMOTE_PRIORITY_PATH):
                temp_file = get_data_path("temp_priority.json")
                self.yandex_disk.download(REMOTE_PRIORITY_PATH, temp_file)
                with open(temp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                os.remove(temp_file)
                self.priorities = data.get("priorities", [])
                save_priorities(self.priorities)

            self.main_screen.sync_label.text = f"Загружено: {len(self.tasks)} дел"
            self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)
            self.show_info("Успех", f"Загружено {len(self.tasks)} дел из облака!")

        except Exception as e:
            self.show_error(f"Не удалось загрузить:\n{e}")

    def manual_sync(self):
        try:
            save_tasks_local(self.tasks)
            self.yandex_disk.upload(get_data_path(LOCAL_FILE_NAME_BASE), REMOTE_FILE_PATH, overwrite=True)
            save_priorities(self.priorities)
            self.yandex_disk.upload(get_data_path(PRIORITY_FILE_BASE), REMOTE_PRIORITY_PATH, overwrite=True)
            self.main_screen.sync_label.text = f"Загружено: {datetime.now().strftime('%H:%M')}"
            self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)
            self.show_info("Синхронизация", f"Загружено на Яндекс.Диск:\n• Дела: {len(self.tasks)} шт.\n• Приоритеты: {len(self.priorities)} шт.")
        except Exception as e:
            self.main_screen.sync_label.text = "Ошибка загрузки"
            self.main_screen.sync_label.color = (1, 0.3, 0.3, 1)
            self.show_error(f"Не удалось загрузить:\n{e}")

    def focus_on_task(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task:
            return
        self.focused_task_id = task_id
        self._expand_all_children(task_id)
        self.expanded_tasks[task_id] = True
        self.main_screen.focus_label.text = f"F Фокус: {task['name']}"
        self.main_screen.focus_panel.opacity = 1
        self.refresh_tasks()

    def clear_focus(self):
        self.focused_task_id = None
        self.expanded_tasks = {}
        self.main_screen.focus_panel.opacity = 0
        self.refresh_tasks()

    def _expand_all_children(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task:
            return
        self.expanded_tasks[task_id] = True
        for child in task.get('children', []):
            self._expand_all_children(child['id'])

    def show_priority_screen(self):
        self.refresh_priority_screen()
        self.root.current = 'priority'

    def refresh_priority_screen(self):
        self.priority_screen.list_container.clear_widgets()

        valid = []
        for task_id in self.priorities:
            task = find_task(self.tasks, task_id)
            if task and not task['done']:
                valid.append(task_id)
            elif task and task['done'] and task_id in self.priorities:
                self.priorities.remove(task_id)

        if valid != self.priorities:
            self.priorities = valid
            save_priorities(self.priorities)

        self.priority_screen.status_label.text = f"Всего в приоритете: {len(self.priorities)}"

        if not self.priorities:
            empty = Label(text="Список пуст\nНажмите s рядом с делом", color=(0.4, 0.4, 0.4, 1), font_size=dp(14), halign='center', size_hint_y=None, height=dp(100))
            empty.bind(size=empty.setter('text_size'))
            self.priority_screen.list_container.add_widget(empty)
            return

        for idx, task_id in enumerate(self.priorities):
            task = find_task(self.tasks, task_id)
            if task:
                item = PriorityItem(task, idx + 1, len(self.priorities), self)
                self.priority_screen.list_container.add_widget(item)

    def show_add_task_dialog(self):
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text="Новое дело:", font_size=dp(18), color=FG_COLOR)
        layout.add_widget(label)
        input_field = TextInput(hint_text="Введите название", multiline=False, font_size=dp(16), background_color=TREE_BG, foreground_color=FG_COLOR)
        layout.add_widget(input_field)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = Button(text="Сохранить", background_color=BTN_GREEN, color=(1, 1, 1, 1))
        save_btn.bind(on_press=lambda inst: self.save_new_task(input_field.text, popup))
        btn_row.add_widget(save_btn)
        cancel_btn = Button(text="Отмена", background_color=BTN_RED, color=(1, 1, 1, 1))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()
        Clock.schedule_once(lambda dt: setattr(input_field, 'focus', True), 0.1)

    def save_new_task(self, name, popup):
        name = name.strip()
        if not name:
            return
        new_task = {'id': self.next_id, 'name': name, 'done': False, 'children': [], 'last_modified': datetime.now().isoformat()}
        self.next_id += 1
        if self.focused_task_id is not None:
            parent = find_task(self.tasks, self.focused_task_id)
            if parent:
                parent['children'].append(new_task)
                self.expanded_tasks[self.focused_task_id] = True
        else:
            self.tasks.append(new_task)
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        popup.dismiss()

    def show_add_subtask_dialog(self, parent_id):
        parent = find_task(self.tasks, parent_id)
        if not parent:
            return
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text=f"Поддело для \"{parent['name']}\":", font_size=dp(16), color=FG_COLOR)
        layout.add_widget(label)
        input_field = TextInput(hint_text="Название поддела", multiline=False, font_size=dp(16), background_color=TREE_BG, foreground_color=FG_COLOR)
        layout.add_widget(input_field)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = Button(text="Сохранить", background_color=BTN_GREEN, color=(1, 1, 1, 1))
        save_btn.bind(on_press=lambda inst: self.save_subtask(input_field.text, parent_id, popup))
        btn_row.add_widget(save_btn)
        cancel_btn = Button(text="Отмена", background_color=BTN_RED, color=(1, 1, 1, 1))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()
        Clock.schedule_once(lambda dt: setattr(input_field, 'focus', True), 0.1)

    def save_subtask(self, name, parent_id, popup):
        name = name.strip()
        if not name:
            return
        parent = find_task(self.tasks, parent_id)
        if not parent:
            return
        new_task = {'id': self.next_id, 'name': name, 'done': False, 'children': [], 'last_modified': datetime.now().isoformat()}
        self.next_id += 1
        parent['children'].append(new_task)
        update_task_timestamp(self.tasks, parent_id)
        self.expanded_tasks[parent_id] = True
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        popup.dismiss()

    def show_edit_dialog(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task:
            return
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text="Редактировать дело:", font_size=dp(18), color=FG_COLOR)
        layout.add_widget(label)
        input_field = TextInput(text=task['name'], multiline=False, font_size=dp(16), background_color=TREE_BG, foreground_color=FG_COLOR)
        layout.add_widget(input_field)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = Button(text="Сохранить", background_color=BTN_GREEN, color=(1, 1, 1, 1))
        save_btn.bind(on_press=lambda inst: self.save_edit(input_field.text, task_id, popup))
        btn_row.add_widget(save_btn)
        cancel_btn = Button(text="Отмена", background_color=BTN_RED, color=(1, 1, 1, 1))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()

    def save_edit(self, new_name, task_id, popup):
        new_name = new_name.strip()
        if not new_name:
            return
        task = find_task(self.tasks, task_id)
        if not task:
            return
        task['name'] = new_name
        update_task_timestamp(self.tasks, task_id)
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        popup.dismiss()

    def show_delete_confirm(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task:
            return
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text=f"Удалить \"{task['name']}\" и все поддела?", font_size=dp(16), color=FG_COLOR, halign='center')
        label.bind(size=label.setter('text_size'))
        layout.add_widget(label)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        yes_btn = Button(text="Да, удалить", background_color=BTN_RED, color=(1, 1, 1, 1))
        yes_btn.bind(on_press=lambda inst: self.confirm_delete(task_id, popup))
        btn_row.add_widget(yes_btn)
        no_btn = Button(text="Отмена", background_color=BTN_BLUE, color=(1, 1, 1, 1))
        no_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(no_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()

    def confirm_delete(self, task_id, popup):
        remove_task(self.tasks, task_id)
        if task_id in self.expanded_tasks:
            del self.expanded_tasks[task_id]
        if task_id in self.priorities:
            self.priorities.remove(task_id)
            save_priorities(self.priorities)
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        self.update_priority_button()
        popup.dismiss()

    def show_move_dialog(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task:
            return
        popup = ModalView(size_hint=(0.95, 0.8))
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        label = Label(text=f"Куда перенести \"{task['name']}\"?", font_size=dp(16), color=FG_COLOR, size_hint_y=None, height=dp(40))
        layout.add_widget(label)
        scroll = ScrollView(size_hint_y=1)
        list_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        list_container.bind(minimum_height=list_container.setter('height'))
        root_btn = Button(text="-- Корень -- (главный экран)", size_hint_y=None, height=dp(45), background_color=BTN_BLUE, color=(1, 1, 1, 1), font_size=dp(14))
        root_btn.bind(on_press=lambda inst: self.do_move(task_id, -1, popup))
        list_container.add_widget(root_btn)

        def get_all_with_numbers(tasks, parent_number="", depth=0):
            result = []
            for i, t in enumerate(tasks):
                if parent_number:
                    number = f"{parent_number}.{i + 1}"
                else:
                    number = index_to_label(i, is_root=True)
                indent = "  " * depth
                display = f"{indent}{number}. {t['name']}"
                result.append((t['id'], display, number))
                subtasks = get_all_with_numbers(t['children'], number, depth + 1)
                result.extend(subtasks)
            return result

        all_tasks = get_all_with_numbers(self.tasks)
        for tid, display, number in all_tasks:
            if tid != task_id:
                btn = Button(text=display, size_hint_y=None, height=dp(45), background_color=BTN_GRAY, color=(1, 1, 1, 1), font_size=dp(13), halign='left')
                btn.bind(on_press=lambda inst, t_id=tid: self.do_move(task_id, t_id, popup))
                list_container.add_widget(btn)

        scroll.add_widget(list_container)
        layout.add_widget(scroll)
        cancel_btn = Button(text="Отмена", size_hint_y=None, height=dp(45), background_color=BTN_RED, color=(1, 1, 1, 1), font_size=dp(14))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        layout.add_widget(cancel_btn)
        popup.add_widget(layout)
        popup.open()

    def do_move(self, task_id, new_parent_id, popup):
        task = find_task(self.tasks, task_id)
        if not task:
            return
        if new_parent_id != -1:
            def is_descendant(t, target_id):
                for child in t['children']:
                    if child['id'] == target_id:
                        return True
                    if is_descendant(child, target_id):
                        return True
                return False
            if is_descendant(task, new_parent_id):
                self.show_error("Нельзя перенести дело внутрь его поддела!")
                return
        removed = remove_task(self.tasks, task_id)
        if new_parent_id == -1:
            self.tasks.append(removed)
        else:
            parent = find_task(self.tasks, new_parent_id)
            if parent:
                parent['children'].append(removed)
                self.expanded_tasks[new_parent_id] = True
        update_task_timestamp(self.tasks, removed['id'])
        save_tasks_local(self.tasks)
        popup.dismiss()
        self.refresh_tasks()
        self.main_screen.sync_label.text = f"Перенесено: {removed['name']}"
        self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)

    def show_error(self, message):
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text=message, color=(1, 0.3, 0.3, 1), font_size=dp(16))
        layout.add_widget(label)
        btn = Button(text="OK", background_color=BTN_RED, color=(1, 1, 1, 1), size_hint_y=None, height=dp(50))
        btn.bind(on_press=lambda inst: popup.dismiss())
        layout.add_widget(btn)
        popup.add_widget(layout)
        popup.open()

    def show_info(self, title, message):
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text=message, color=FG_COLOR, font_size=dp(16))
        layout.add_widget(label)
        btn = Button(text="OK", background_color=BTN_BLUE, color=(1, 1, 1, 1), size_hint_y=None, height=dp(50))
        btn.bind(on_press=lambda inst: popup.dismiss())
        layout.add_widget(btn)
        popup.add_widget(layout)
        popup.open()


if __name__ == "__main__":
    TodoApp().run()
