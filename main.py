import sys
import os
import json
import requests
import traceback
from datetime import datetime

# Логирование ошибок в файл на телефоне
def log_error(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_log = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        log_path = "/sdcard/Download/mytodo_error.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(error_log + "\n" + "="*50 + "\n")
    except:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = log_error

if sys.platform == 'win32':
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
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

# --- Пути ---
def get_data_path(filename):
    try:
        app = App.get_running_app()
        if app and hasattr(app, 'user_data_dir') and app.user_data_dir:
            path = os.path.join(app.user_data_dir, filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return path
    except Exception:
        pass
    try:
        home = os.path.expanduser('~')
        path = os.path.join(home, '.mytodo', filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path
    except Exception:
        pass
    return filename

CONFIG_FILE_NAME = "config.json"
LOCAL_FILE_NAME_BASE = "tree_tasks.json"
PRIORITY_FILE_BASE = "priority.json"
REMOTE_TASKS_PATH = "app:/tree_tasks.json"
REMOTE_PRIORITY_PATH = "app:/priority.json"

# --- Яндекс.Диск через requests ---
def yd_get_upload_link(token, path):
    url = "https://cloud-api.yandex.ru/v1/disk/resources/upload"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": path, "overwrite": "true"}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()["href"]

def yd_upload_file(token, remote_path, local_path):
    href = yd_get_upload_link(token, remote_path)
    with open(local_path, 'rb') as f:
        r = requests.put(href, data=f, timeout=60)
        r.raise_for_status()

def yd_get_download_link(token, path):
    url = "https://cloud-api.yandex.ru/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": path}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()["href"]

def yd_download_file(token, remote_path, local_path):
    href = yd_get_download_link(token, remote_path)
    r = requests.get(href, timeout=60)
    r.raise_for_status()
    with open(local_path, 'wb') as f:
        f.write(r.content)

def yd_file_exists(token, path):
    url = "https://cloud-api.yandex.ru/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": path}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    return r.status_code == 200

# --- Работа с данными ---
def load_config():
    path = get_data_path(CONFIG_FILE_NAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        token = config.get("yandex_token", "")
        return token if token and token != "ВСТАВЬТЕ_ВАШ_ТОКЕН_СЮДА" else None
    except:
        return None

def save_config(token):
    path = get_data_path(CONFIG_FILE_NAME)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"yandex_token": token}, f, indent=4)

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
                return json.load(f).get("priorities", [])
        except:
            return []
    return []

def save_priorities(priorities):
    path = get_data_path(PRIORITY_FILE_BASE)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"priorities": priorities}, f, ensure_ascii=False, indent=2)

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
        return alphabet[index] if index < len(alphabet) else f"{alphabet[index // len(alphabet) - 1]}{alphabet[index % len(alphabet)]}"
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
    return ".".join([index_to_label(idx, is_root=(i==0)) for i, idx in enumerate(path)])

# --- Виджет дела ---
class TaskItem(BoxLayout):
    def __init__(self, task, depth, app, expanded=False, **kwargs):
        super().__init__(**kwargs)
        self.task, self.depth, self.app = task, depth, app
        self.orientation, self.size_hint_y = 'vertical', None
        self.height = dp(95)  # Увеличили высоту
        self.padding = [dp(10) * (depth + 1), dp(5), dp(10), dp(5)]
        has_children = len(task.get('children', [])) > 0

        top_row = BoxLayout(size_hint_y=0.6, spacing=dp(3))
        if has_children:
            self.toggle_btn = Button(text="v" if expanded else ">", size_hint_x=None, width=dp(40), background_color=BTN_GRAY, color=(1,1,1,1), font_size=dp(16), bold=True)
            self.toggle_btn.bind(on_press=lambda inst: self.on_toggle_expand())
            top_row.add_widget(self.toggle_btn)
        else:
            top_row.add_widget(Label(size_hint_x=None, width=dp(40)))

        self.checkbox = CheckBox(active=task['done'], size_hint_x=None, width=dp(40), color=DONE_COLOR)
        self.checkbox.bind(active=self.on_checkbox_change)
        top_row.add_widget(self.checkbox)

        task_number = get_task_number(self.app.tasks, task['id'])
        display_name = f"{task_number}. {task['name']}"
        self.name_label = Label(
            text=display_name,
            halign='left', valign='middle',
            color=DONE_COLOR if task['done'] else FG_COLOR,
            font_size=dp(14),
            shorten=True,  # ВАЖНО: сокращает длинный текст
            shorten_from='right',
            max_lines=1,
            ellipsis_options={'color': FG_COLOR}
        )
        self.name_label.bind(size=self.name_label.setter('text_size'))
        top_row.add_widget(self.name_label)

        in_priority = task['id'] in self.app.priorities
        self.priority_btn = Button(text="S" if in_priority else "s", size_hint_x=None, width=dp(35), background_color=BTN_GRAY, color=GOLD_COLOR, font_size=dp(16), bold=True)
        self.priority_btn.bind(on_press=self.on_toggle_priority)
        top_row.add_widget(self.priority_btn)

        focus_btn = Button(text="F", size_hint_x=None, width=dp(35), background_color=BTN_GRAY, color=FG_COLOR, font_size=dp(14), bold=True)
        focus_btn.bind(on_press=lambda inst: self.app.focus_on_task(task['id']))
        top_row.add_widget(focus_btn)

        add_btn = Button(text="+", size_hint_x=None, width=dp(35), background_color=BTN_GREEN, color=(1,1,1,1), font_size=dp(18), bold=True)
        add_btn.bind(on_press=lambda inst: self.app.show_add_subtask_dialog(task['id']))
        top_row.add_widget(add_btn)
        self.add_widget(top_row)

        bottom_row = BoxLayout(size_hint_y=0.4, spacing=dp(3), padding=[dp(40), 0, 0, 0])
        for txt, color, action in [("Изм.", BTN_ORANGE, self.app.show_edit_dialog), ("Перен.", BTN_TEAL, self.app.show_move_dialog), ("Удал.", BTN_RED, self.app.show_delete_confirm)]:
            btn = Button(text=txt, background_color=color, color=(1,1,1,1), font_size=dp(11))
            btn.bind(on_press=lambda inst, a=action: a(task['id']))
            bottom_row.add_widget(btn)
        self.add_widget(bottom_row)

    def on_toggle_expand(self):
        self.app.expanded_tasks[self.task['id']] = not self.app.expanded_tasks.get(self.task['id'], False)
        self.toggle_btn.text = "v" if self.app.expanded_tasks[self.task['id']] else ">"
        self.app.refresh_tasks()

    def on_checkbox_change(self, instance, value):
        self.task['done'] = value
        save_tasks_local(self.app.tasks)
        self.name_label.color = DONE_COLOR if value else FG_COLOR
        if value and self.task['id'] in self.app.priorities:
            self.app.priorities.remove(self.task['id'])
            save_priorities(self.app.priorities)
        self.app.refresh_tasks()
        self.app.update_priority_button()

    def on_toggle_priority(self, instance):
        if self.task['id'] in self.app.priorities:
            self.app.priorities.remove(self.task['id'])
            instance.text = "s"
        else:
            self.app.priorities.append(self.task['id'])
            instance.text = "S"
        save_priorities(self.app.priorities)
        self.app.update_priority_button()

# --- Виджет приоритета ---
class PriorityItem(BoxLayout):
    def __init__(self, task, position, total, app, **kwargs):
        super().__init__(**kwargs)
        self.task, self.position, self.total, self.app = task, position, total, app
        self.orientation, self.size_hint_y, self.height = 'horizontal', None, dp(50)
        self.padding, self.spacing = [dp(5), dp(3), dp(5), dp(3)], dp(3)

        self.add_widget(Label(text=f"{position}.", color=GOLD_COLOR, font_size=dp(14), bold=True, size_hint_x=None, width=dp(35)))
        name_label = Label(text=f"{get_task_number(self.app.tasks, task['id'])}. {task['name']}", color=FG_COLOR, font_size=dp(13), halign='left', shorten=True, shorten_from='right', max_lines=1)
        name_label.bind(size=name_label.setter('text_size'))
        self.add_widget(name_label)

        for txt, color, action, disabled in [
            ("^", FG_COLOR, self.on_move_up, position == 1),
            ("v", FG_COLOR, self.on_move_down, position == total),
            ("D", DONE_COLOR, self.on_mark_done, False),
            ("X", BTN_RED, self.on_remove, False)
        ]:
            btn = Button(text=txt, size_hint_x=None, width=dp(40), background_color=BTN_GRAY, color=(0.3,0.3,0.3,1) if disabled else color, font_size=dp(16), bold=True, disabled=disabled)
            btn.bind(on_press=lambda inst, a=action: a())
            self.add_widget(btn)

    def on_move_up(self):
        if self.position > 1:
            idx = self.position - 1
            self.app.priorities[idx], self.app.priorities[idx-1] = self.app.priorities[idx-1], self.app.priorities[idx]
            save_priorities(self.app.priorities)
            self.app.refresh_priority_screen()

    def on_move_down(self):
        if self.position < self.total:
            idx = self.position - 1
            self.app.priorities[idx], self.app.priorities[idx+1] = self.app.priorities[idx+1], self.app.priorities[idx]
            save_priorities(self.app.priorities)
            self.app.refresh_priority_screen()

    def on_mark_done(self):
        task = find_task(self.app.tasks, self.task['id'])
        if task:
            task['done'] = True
            if self.task['id'] in self.app.priorities:
                self.app.priorities.remove(self.task['id'])
            save_priorities(self.app.priorities)
            save_tasks_local(self.app.tasks)
            self.app.refresh_priority_screen()
            self.app.refresh_tasks()
            self.app.update_priority_button()

    def on_remove(self):
        if self.task['id'] in self.app.priorities:
            self.app.priorities.remove(self.task['id'])
            save_priorities(self.app.priorities)
            self.app.refresh_priority_screen()
            self.app.refresh_tasks()
            self.app.update_priority_button()

# --- Главный экран ---
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'main'
        layout = BoxLayout(orientation='vertical', padding=[dp(10)]*4, spacing=dp(5))
        self.add_widget(layout)

        layout.add_widget(Label(text="Мои дела", size_hint_y=None, height=dp(40), font_size=dp(22), bold=True, color=FG_COLOR))
        self.sync_label = Label(text="Проверка облака...", size_hint_y=None, height=dp(25), font_size=dp(11), color=(0.7, 0.7, 0.7, 1))
        layout.add_widget(self.sync_label)

        self.focus_panel = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5), padding=[dp(5), 0, dp(5), 0], opacity=0)
        self.focus_label = Label(text="", color=GOLD_COLOR, font_size=dp(12), bold=True, halign='left')
        self.focus_label.bind(size=self.focus_label.setter('text_size'))
        self.focus_panel.add_widget(self.focus_label)
        clear_btn = Button(text="< Все дела", size_hint_x=None, width=dp(100), background_color=BTN_BLUE, color=(1,1,1,1), font_size=dp(12))
        clear_btn.bind(on_press=lambda inst: App.get_running_app().clear_focus())
        self.focus_panel.add_widget(clear_btn)
        layout.add_widget(self.focus_panel)

        self.scroll = ScrollView(size_hint_y=1)
        self.tasks_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        self.tasks_container.bind(minimum_height=self.tasks_container.setter('height'))
        self.scroll.add_widget(self.tasks_container)
        layout.add_widget(self.scroll)

        btn_row1 = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        add_btn = Button(text="+ Создать", background_color=BTN_GREEN, color=(1,1,1,1), font_size=dp(13), bold=True)
        add_btn.bind(on_press=lambda inst: App.get_running_app().show_add_task_dialog())
        btn_row1.add_widget(add_btn)
        self.priority_btn = Button(text="S Приоритеты (0)", background_color=BTN_GRAY, color=GOLD_COLOR, font_size=dp(13), bold=True)
        self.priority_btn.bind(on_press=lambda inst: App.get_running_app().show_priority_screen())
        btn_row1.add_widget(self.priority_btn)
        layout.add_widget(btn_row1)

        # Кнопки синхронизации
        btn_row2 = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        download_btn = Button(text="⬇ Из облака", background_color=BTN_CYAN, color=(1,1,1,1), font_size=dp(13), bold=True)
        download_btn.bind(on_press=lambda inst: App.get_running_app().sync_from_cloud())
        btn_row2.add_widget(download_btn)
        upload_btn = Button(text="⬆ В облако", background_color=BTN_PURPLE, color=(1,1,1,1), font_size=dp(13), bold=True)
        upload_btn.bind(on_press=lambda inst: App.get_running_app().sync_to_cloud())
        btn_row2.add_widget(upload_btn)
        layout.add_widget(btn_row2)

        # Кнопка настройки токена
        token_btn = Button(text="⚙ Токен", size_hint_y=None, height=dp(35), background_color=BTN_GRAY, color=(0.7, 0.7, 0.7, 1), font_size=dp(11))
        token_btn.bind(on_press=lambda inst: App.get_running_app().show_token_dialog())
        layout.add_widget(token_btn)

# --- Экран приоритетов ---
class PriorityScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'priority'
        layout = BoxLayout(orientation='vertical', padding=[dp(10)]*4, spacing=dp(5))
        self.add_widget(layout)
        layout.add_widget(Label(text="S Приоритеты", size_hint_y=None, height=dp(40), font_size=dp(20), bold=True, color=GOLD_COLOR))
        self.status_label = Label(text="Всего: 0", size_hint_y=None, height=dp(25), font_size=dp(11), color=(0.7, 0.7, 0.7, 1))
        layout.add_widget(self.status_label)
        self.scroll = ScrollView(size_hint_y=1)
        self.list_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        self.scroll.add_widget(self.list_container)
        layout.add_widget(self.scroll)
        back_btn = Button(text="< Назад к делам", size_hint_y=None, height=dp(45), background_color=BTN_BLUE, color=(1,1,1,1), font_size=dp(14), bold=True)
        back_btn.bind(on_press=lambda inst: setattr(App.get_running_app().root, 'current', 'main'))
        layout.add_widget(back_btn)

# --- Приложение ---
class TodoApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks, self.next_id, self.expanded_tasks, self.priorities, self.focused_task_id = [], 1, {}, [], None
        self.yandex_token = None

    def build(self):
        Window.clearcolor = BG_COLOR
        try:
            self.tasks = load_tasks_local()
            self.priorities = load_priorities()
            if self.tasks:
                self.next_id = max(t['id'] for t in self.flatten_tasks(self.tasks)) + 1
        except Exception:
            self.tasks, self.priorities = [], []

        self.yandex_token = load_config()

        sm = ScreenManager()
        self.main_screen = MainScreen()
        self.priority_screen = PriorityScreen()
        sm.add_widget(self.main_screen)
        sm.add_widget(self.priority_screen)

        if not self.yandex_token:
            self.main_screen.sync_label.text = "Токен не настроен (нажмите ⚙ Токен)"
            self.main_screen.sync_label.color = (1, 0.7, 0, 1)
            Clock.schedule_once(lambda dt: self.show_token_dialog(), 0.5)
        else:
            self.main_screen.sync_label.text = "Готов к синхронизации"
            self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)

        Clock.schedule_once(lambda dt: self.refresh_tasks(), 0.3)
        return sm

    def flatten_tasks(self, tasks):
        result = []
        for task in tasks:
            result.append(task)
            result.extend(self.flatten_tasks(task['children']))
        return result

    def refresh_tasks(self):
        if not hasattr(self, 'main_screen') or not self.main_screen: return
        self.main_screen.tasks_container.clear_widgets()
        if self.focused_task_id is not None:
            focused = find_task(self.tasks, self.focused_task_id)
            if focused:
                exp = self.expanded_tasks.get(focused['id'], True)
                self.main_screen.tasks_container.add_widget(TaskItem(focused, 0, self, expanded=exp))
                if exp: self.add_children_recursive(focused, 1)
        else:
            for task in self.tasks:
                exp = self.expanded_tasks.get(task['id'], False)
                self.main_screen.tasks_container.add_widget(TaskItem(task, 0, self, expanded=exp))
                if exp: self.add_children_recursive(task, 1)
        self.update_priority_button()

    def add_children_recursive(self, parent_task, depth):
        for child in parent_task.get('children', []):
            exp = self.expanded_tasks.get(child['id'], False)
            self.main_screen.tasks_container.add_widget(TaskItem(child, depth, self, expanded=exp))
            if exp: self.add_children_recursive(child, depth + 1)

    def update_priority_button(self):
        if hasattr(self, 'main_screen') and self.main_screen:
            count = len([p for p in self.priorities if find_task(self.tasks, p) and not find_task(self.tasks, p)['done']])
            self.main_screen.priority_btn.text = f"S Приоритеты ({count})"

    def focus_on_task(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task: return
        self.focused_task_id = task_id
        self._expand_all(task_id)
        self.expanded_tasks[task_id] = True
        self.main_screen.focus_label.text = f"F Фокус: {task['name']}"
        self.main_screen.focus_panel.opacity = 1
        self.refresh_tasks()

    def clear_focus(self):
        self.focused_task_id = None
        self.expanded_tasks = {}
        self.main_screen.focus_panel.opacity = 0
        self.refresh_tasks()

    def _expand_all(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task: return
        self.expanded_tasks[task_id] = True
        for child in task.get('children', []): self._expand_all(child['id'])

    def show_priority_screen(self):
        self.refresh_priority_screen()
        self.root.current = 'priority'

    def refresh_priority_screen(self):
        self.priority_screen.list_container.clear_widgets()
        valid = [p for p in self.priorities if find_task(self.tasks, p) and not find_task(self.tasks, p)['done']]
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
            if task: self.priority_screen.list_container.add_widget(PriorityItem(task, idx + 1, len(self.priorities), self))

    # --- Диалоги ввода ---
    def _show_input_popup(self, title, hint, save_action, default_text=""):
        popup = ModalView(size_hint=(0.9, 0.35))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        layout.add_widget(Label(text=title, font_size=dp(18), color=FG_COLOR, size_hint_y=None, height=dp(30)))
        input_field = TextInput(text=default_text, hint_text=hint, multiline=False, font_size=dp(16), background_color=TREE_BG, foreground_color=FG_COLOR)
        layout.add_widget(input_field)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = Button(text="Сохранить", background_color=BTN_GREEN, color=(1,1,1,1))
        save_btn.bind(on_press=lambda inst: save_action(input_field.text.strip(), popup))
        btn_row.add_widget(save_btn)
        cancel_btn = Button(text="Отмена", background_color=BTN_RED, color=(1,1,1,1))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()
        Clock.schedule_once(lambda dt: setattr(input_field, 'focus', True), 0.1)

    def show_add_task_dialog(self):
        self._show_input_popup("Новое дело:", "Введите название", self.save_new_task)

    def show_add_subtask_dialog(self, parent_id):
        parent = find_task(self.tasks, parent_id)
        if parent: self._show_input_popup(f"Поддело для \"{parent['name']}\":", "Название поддела", lambda name, pop: self.save_subtask(name, parent_id, pop))

    def save_new_task(self, name, popup):
        if not name: return
        new_task = {'id': self.next_id, 'name': name, 'done': False, 'children': [], 'last_modified': datetime.now().isoformat()}
        self.next_id += 1
        if self.focused_task_id:
            parent = find_task(self.tasks, self.focused_task_id)
            if parent:
                parent['children'].append(new_task)
                self.expanded_tasks[self.focused_task_id] = True
        else:
            self.tasks.append(new_task)
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        popup.dismiss()

    def save_subtask(self, name, parent_id, popup):
        if not name: return
        parent = find_task(self.tasks, parent_id)
        if not parent: return
        new_task = {'id': self.next_id, 'name': name, 'done': False, 'children': [], 'last_modified': datetime.now().isoformat()}
        self.next_id += 1
        parent['children'].append(new_task)
        self.expanded_tasks[parent_id] = True
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        popup.dismiss()

    def show_edit_dialog(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task: return
        self._show_input_popup("Редактировать дело:", "Новое название", lambda name, pop: self.save_edit(name, task_id, pop), task['name'])

    def save_edit(self, new_name, task_id, popup):
        if not new_name: return
        task = find_task(self.tasks, task_id)
        if task:
            task['name'] = new_name
            save_tasks_local(self.tasks)
            self.refresh_tasks()
        popup.dismiss()

    def show_delete_confirm(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task: return
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        label = Label(text=f"Удалить \"{task['name']}\" и все поддела?", font_size=dp(16), color=FG_COLOR, halign='center')
        label.bind(size=label.setter('text_size'))
        layout.add_widget(label)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        yes_btn = Button(text="Да, удалить", background_color=BTN_RED, color=(1,1,1,1))
        yes_btn.bind(on_press=lambda inst: self.confirm_delete(task_id, popup))
        btn_row.add_widget(yes_btn)
        no_btn = Button(text="Отмена", background_color=BTN_BLUE, color=(1,1,1,1))
        no_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(no_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()

    def confirm_delete(self, task_id, popup):
        remove_task(self.tasks, task_id)
        self.expanded_tasks.pop(task_id, None)
        if task_id in self.priorities:
            self.priorities.remove(task_id)
            save_priorities(self.priorities)
        save_tasks_local(self.tasks)
        self.refresh_tasks()
        self.update_priority_button()
        popup.dismiss()

    def show_move_dialog(self, task_id):
        task = find_task(self.tasks, task_id)
        if not task: return
        popup = ModalView(size_hint=(0.95, 0.8))
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        layout.add_widget(Label(text=f"Куда перенести \"{task['name']}\"?", font_size=dp(16), color=FG_COLOR, size_hint_y=None, height=dp(40)))
        scroll = ScrollView(size_hint_y=1)
        list_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        list_container.bind(minimum_height=list_container.setter('height'))
        root_btn = Button(text="-- Корень -- (главный экран)", size_hint_y=None, height=dp(45), background_color=BTN_BLUE, color=(1,1,1,1), font_size=dp(14))
        root_btn.bind(on_press=lambda inst: self.do_move(task_id, -1, popup))
        list_container.add_widget(root_btn)

        def get_all(tasks, parent_num="", depth=0):
            res = []
            for i, t in enumerate(tasks):
                num = f"{parent_num}.{i+1}" if parent_num else index_to_label(i, True)
                res.append((t['id'], f"{'  '*depth}{num}. {t['name']}"))
                res.extend(get_all(t['children'], num, depth+1))
            return res

        for tid, display in get_all(self.tasks):
            if tid != task_id:
                btn = Button(text=display, size_hint_y=None, height=dp(45), background_color=BTN_GRAY, color=(1,1,1,1), font_size=dp(13), halign='left')
                btn.bind(on_press=lambda inst, t_id=tid: self.do_move(task_id, t_id, popup))
                list_container.add_widget(btn)

        scroll.add_widget(list_container)
        layout.add_widget(scroll)
        cancel_btn = Button(text="Отмена", size_hint_y=None, height=dp(45), background_color=BTN_RED, color=(1,1,1,1), font_size=dp(14))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        layout.add_widget(cancel_btn)
        popup.add_widget(layout)
        popup.open()

    def do_move(self, task_id, new_parent_id, popup):
        task = find_task(self.tasks, task_id)
        if not task: return
        if new_parent_id != -1:
            def is_desc(t, target):
                for c in t['children']:
                    if c['id'] == target or is_desc(c, target): return True
                return False
            if is_desc(task, new_parent_id):
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
        save_tasks_local(self.tasks)
        popup.dismiss()
        self.refresh_tasks()
        self.main_screen.sync_label.text = f"Перенесено: {removed['name']}"
        self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)

    # --- Токен ---
    def show_token_dialog(self):
        popup = ModalView(size_hint=(0.92, 0.55))
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        layout.add_widget(Label(text="Токен Яндекс.Диска", font_size=dp(17), color=GOLD_COLOR, size_hint_y=None, height=dp(35)))
        hint = Label(
            text="1. Зайдите на oauth.yandex.ru\n2. Создайте приложение\n3. Выберите 'Доступ к Яндекс.Диску'\n4. Скопируйте токен и вставьте сюда",
            font_size=dp(11), color=(0.7, 0.7, 0.7, 1), halign='left', size_hint_y=None, height=dp(80)
        )
        hint.bind(size=hint.setter('text_size'))
        layout.add_widget(hint)
        input_field = TextInput(
            hint_text="Вставьте токен",
            multiline=False, font_size=dp(14),
            background_color=TREE_BG, foreground_color=FG_COLOR,
            size_hint_y=None, height=dp(45)
        )
        if self.yandex_token:
            input_field.text = self.yandex_token
        layout.add_widget(input_field)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = Button(text="Сохранить", background_color=BTN_GREEN, color=(1,1,1,1))
        save_btn.bind(on_press=lambda inst: self.save_token(input_field.text.strip(), popup))
        btn_row.add_widget(save_btn)
        cancel_btn = Button(text="Отмена", background_color=BTN_GRAY, color=(1,1,1,1))
        cancel_btn.bind(on_press=lambda inst: popup.dismiss())
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)
        popup.add_widget(layout)
        popup.open()

    def save_token(self, token, popup):
        if not token:
            self.show_error("Токен не может быть пустым")
            return
        try:
            save_config(token)
            self.yandex_token = token
            self.main_screen.sync_label.text = "Токен сохранён ✓"
            self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)
            popup.dismiss()
            self.show_info("Готово", "Токен сохранён. Теперь можно синхронизировать дела с облаком.")
        except Exception as e:
            self.show_error(f"Ошибка сохранения:\n{e}")

    # --- Синхронизация ---
    def sync_to_cloud(self):
        if not self.yandex_token:
            self.show_error("Сначала настройте токен (кнопка ⚙ Токен)")
            return
        try:
            self.main_screen.sync_label.text = "Загрузка в облако..."
            self.main_screen.sync_label.color = (1, 0.7, 0, 1)
            save_tasks_local(self.tasks)
            save_priorities(self.priorities)
            yd_upload_file(self.yandex_token, REMOTE_TASKS_PATH, get_data_path(LOCAL_FILE_NAME_BASE))
            yd_upload_file(self.yandex_token, REMOTE_PRIORITY_PATH, get_data_path(PRIORITY_FILE_BASE))
            self.main_screen.sync_label.text = f"✓ Загружено: {datetime.now().strftime('%H:%M')}"
            self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)
            self.show_info("Успех", f"Загружено в облако:\n• Дела: {len(self.tasks)}\n• Приоритеты: {len(self.priorities)}")
        except Exception as e:
            self.main_screen.sync_label.text = "Ошибка загрузки"
            self.main_screen.sync_label.color = (1, 0.3, 0.3, 1)
            self.show_error(f"Не удалось загрузить:\n{e}")

    def sync_from_cloud(self):
        if not self.yandex_token:
            self.show_error("Сначала настройте токен (кнопка ⚙ Токен)")
            return
        try:
            self.main_screen.sync_label.text = "Загрузка из облака..."
            self.main_screen.sync_label.color = (1, 0.7, 0, 1)
            temp_tasks = get_data_path("temp_tasks.json")
            temp_priority = get_data_path("temp_priority.json")
            yd_download_file(self.yandex_token, REMOTE_TASKS_PATH, temp_tasks)
            with open(temp_tasks, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
            os.remove(temp_tasks)
            if yd_file_exists(self.yandex_token, REMOTE_PRIORITY_PATH):
                yd_download_file(self.yandex_token, REMOTE_PRIORITY_PATH, temp_priority)
                with open(temp_priority, 'r', encoding='utf-8') as f:
                    self.priorities = json.load(f).get("priorities", [])
                os.remove(temp_priority)
            else:
                self.priorities = []
            save_tasks_local(self.tasks)
            save_priorities(self.priorities)
            if self.tasks:
                self.next_id = max(t['id'] for t in self.flatten_tasks(self.tasks)) + 1
            self.refresh_tasks()
            self.update_priority_button()
            self.main_screen.sync_label.text = f"✓ Загружено: {len(self.tasks)} дел"
            self.main_screen.sync_label.color = (0.3, 1, 0.3, 1)
            self.show_info("Успех", f"Загружено из облака:\n• Дела: {len(self.tasks)}\n• Приоритеты: {len(self.priorities)}")
        except Exception as e:
            self.main_screen.sync_label.text = "Ошибка загрузки"
            self.main_screen.sync_label.color = (1, 0.3, 0.3, 1)
            self.show_error(f"Не удалось загрузить:\n{e}")

    def show_error(self, message):
        popup = ModalView(size_hint=(0.9, 0.3))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        layout.add_widget(Label(text=message, color=(1, 0.3, 0.3, 1), font_size=dp(16), halign='center'))
        btn = Button(text="OK", background_color=BTN_RED, color=(1,1,1,1), size_hint_y=None, height=dp(50))
        btn.bind(on_press=lambda inst: popup.dismiss())
        layout.add_widget(btn)
        popup.add_widget(layout)
        popup.open()

    def show_info(self, title, message):
        popup = ModalView(size_hint=(0.9, 0.35))
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        layout.add_widget(Label(text=title, color=GOLD_COLOR, font_size=dp(18), bold=True, size_hint_y=None, height=dp(30)))
        layout.add_widget(Label(text=message, color=FG_COLOR, font_size=dp(14), halign='center'))
        btn = Button(text="OK", background_color=BTN_BLUE, color=(1,1,1,1), size_hint_y=None, height=dp(50))
        btn.bind(on_press=lambda inst: popup.dismiss())
        layout.add_widget(btn)
        popup.add_widget(layout)
        popup.open()

if __name__ == "__main__":
    TodoApp().run()
