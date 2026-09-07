from __future__ import annotations

import asyncio
import csv
import json
import importlib.util
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import dotenv_values
from requests_oauthlib import OAuth1Session
from telegram import Bot

from PySide6.QtCore import QThread, Qt, Signal, QSize, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR / '.env'
HISTORY_PATH = APP_DIR / 'publication_history.json'
LEGACY_CSV_PATH = APP_DIR / 'publish_log.csv'
TAG_TEMPLATES_PATH = APP_DIR / 'tag_templates.json'
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}


@dataclass
class AppConfig:
    ai_enabled: bool = False
    ollama_model: str = 'qwen3-vl:4b'
    caption_language: str = 'ru'
    caption_style: str = 'коротко, живо, естественно, слегка игриво; без канцелярита'
    ready_dir: str = 'READY'
    posted_dir: str = 'POSTED'
    auto_move_after_publish: bool = True
    append_tags_to_social_caption: bool = False

    telegram_enabled: bool = True
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''

    x_enabled: bool = False
    x_consumer_key: str = ''
    x_consumer_secret: str = ''
    x_access_token: str = ''
    x_access_token_secret: str = ''
    x_username: str = ''

    vk_enabled: bool = False
    vk_access_token: str = ''
    vk_owner_id: str = ''
    vk_group_id: str = ''
    vk_api_version: str = '5.199'
    vk_from_group: bool = True

    e621_enabled: bool = False
    e621_username: str = ''
    e621_api_key: str = ''
    e621_default_rating: str = 's'

    deviantart_enabled: bool = False
    deviantart_client_id: str = ''
    deviantart_client_secret: str = ''
    deviantart_access_token: str = ''
    deviantart_refresh_token: str = ''

    @classmethod
    def load(cls) -> 'AppConfig':
        if not ENV_PATH.exists():
            return cls()
        values = dotenv_values(ENV_PATH)

        def get(key: str, default: str = '') -> str:
            return str(values.get(key, default) or default).strip()

        def to_bool(key: str, default: bool) -> bool:
            return str(values.get(key, 'true' if default else 'false')).strip().lower() in {
                '1', 'true', 'yes', 'y', 'on'
            }

        return cls(
            ai_enabled=to_bool('AI_ENABLED', False),
            ollama_model=get('OLLAMA_MODEL', 'qwen3-vl:4b'),
            caption_language=get('CAPTION_LANGUAGE', 'ru'),
            caption_style=get('CAPTION_STYLE', 'коротко, живо, естественно, слегка игриво; без канцелярита'),
            ready_dir=get('READY_DIR', 'READY'),
            posted_dir=get('POSTED_DIR', 'POSTED'),
            auto_move_after_publish=to_bool('AUTO_MOVE_AFTER_PUBLISH', True),
            append_tags_to_social_caption=to_bool('APPEND_TAGS_TO_SOCIAL_CAPTION', False),
            telegram_enabled=to_bool('TELEGRAM_ENABLED', True),
            telegram_bot_token=get('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=get('TELEGRAM_CHAT_ID'),
            x_enabled=to_bool('X_ENABLED', False),
            x_consumer_key=get('X_CONSUMER_KEY'),
            x_consumer_secret=get('X_CONSUMER_SECRET'),
            x_access_token=get('X_ACCESS_TOKEN'),
            x_access_token_secret=get('X_ACCESS_TOKEN_SECRET'),
            x_username=get('X_USERNAME'),
            vk_enabled=to_bool('VK_ENABLED', False),
            vk_access_token=get('VK_ACCESS_TOKEN'),
            vk_owner_id=get('VK_OWNER_ID'),
            vk_group_id=get('VK_GROUP_ID'),
            vk_api_version=get('VK_API_VERSION', '5.199'),
            vk_from_group=to_bool('VK_FROM_GROUP', True),
            e621_enabled=to_bool('E621_ENABLED', False),
            e621_username=get('E621_USERNAME'),
            e621_api_key=get('E621_API_KEY'),
            e621_default_rating=get('E621_DEFAULT_RATING', 's'),
            deviantart_enabled=to_bool('DEVIANTART_ENABLED', False),
            deviantart_client_id=get('DEVIANTART_CLIENT_ID'),
            deviantart_client_secret=get('DEVIANTART_CLIENT_SECRET'),
            deviantart_access_token=get('DEVIANTART_ACCESS_TOKEN'),
            deviantart_refresh_token=get('DEVIANTART_REFRESH_TOKEN'),
        )

    def save(self) -> None:
        lines = [
            f"AI_ENABLED={'true' if self.ai_enabled else 'false'}",
            f'OLLAMA_MODEL={self.ollama_model}',
            f'CAPTION_LANGUAGE={self.caption_language}',
            f'CAPTION_STYLE={self.caption_style}',
            f'READY_DIR={self.ready_dir}',
            f'POSTED_DIR={self.posted_dir}',
            f"AUTO_MOVE_AFTER_PUBLISH={'true' if self.auto_move_after_publish else 'false'}",
            f"APPEND_TAGS_TO_SOCIAL_CAPTION={'true' if self.append_tags_to_social_caption else 'false'}",
            f"TELEGRAM_ENABLED={'true' if self.telegram_enabled else 'false'}",
            f'TELEGRAM_BOT_TOKEN={self.telegram_bot_token}',
            f'TELEGRAM_CHAT_ID={self.telegram_chat_id}',
            f"X_ENABLED={'true' if self.x_enabled else 'false'}",
            f'X_CONSUMER_KEY={self.x_consumer_key}',
            f'X_CONSUMER_SECRET={self.x_consumer_secret}',
            f'X_ACCESS_TOKEN={self.x_access_token}',
            f'X_ACCESS_TOKEN_SECRET={self.x_access_token_secret}',
            f'X_USERNAME={self.x_username}',
            f"VK_ENABLED={'true' if self.vk_enabled else 'false'}",
            f'VK_ACCESS_TOKEN={self.vk_access_token}',
            f'VK_OWNER_ID={self.vk_owner_id}',
            f'VK_GROUP_ID={self.vk_group_id}',
            f'VK_API_VERSION={self.vk_api_version}',
            f"VK_FROM_GROUP={'true' if self.vk_from_group else 'false'}",
            f"E621_ENABLED={'true' if self.e621_enabled else 'false'}",
            f'E621_USERNAME={self.e621_username}',
            f'E621_API_KEY={self.e621_api_key}',
            f'E621_DEFAULT_RATING={self.e621_default_rating}',
            f"DEVIANTART_ENABLED={'true' if self.deviantart_enabled else 'false'}",
            f'DEVIANTART_CLIENT_ID={self.deviantart_client_id}',
            f'DEVIANTART_CLIENT_SECRET={self.deviantart_client_secret}',
            f'DEVIANTART_ACCESS_TOKEN={self.deviantart_access_token}',
            f'DEVIANTART_REFRESH_TOKEN={self.deviantart_refresh_token}',
        ]
        ENV_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    @property
    def ready_path(self) -> Path:
        p = Path(self.ready_dir)
        if not p.is_absolute():
            p = APP_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def posted_path(self) -> Path:
        p = Path(self.posted_dir)
        if not p.is_absolute():
            p = APP_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p


@dataclass
class HistoryEntry:
    timestamp: str
    platform: str
    status: str
    image_path: str
    display_name: str
    caption: str = ''
    tags: str = ''
    notes: str = ''
    remote_id: str = ''
    url: str = ''
    moved_to: str = ''
    extra: dict[str, Any] | None = None


@dataclass
class TagTemplate:
    name: str
    tags: str


class TagTemplateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.templates: list[TagTemplate] = []
        self.load()
        if not self.templates:
            self.templates = [
                TagTemplate('Ulyana basic', 'female, anthro, furry, ulyana'),
                TagTemplate('Male basic', 'male, anthro, furry'),
            ]
            self.save()

    def load(self) -> None:
        if not self.path.exists():
            self.templates = []
            return
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            self.templates = [TagTemplate(**item) for item in data]
        except Exception:
            self.templates = []

    def save(self) -> None:
        self.path.write_text(
            json.dumps([t.__dict__ for t in self.templates], ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    def add_or_update(self, name: str, tags: str) -> None:
        name = name.strip()
        tags = tags.strip()
        if not name:
            raise ValueError('Имя шаблона пустое.')
        for template in self.templates:
            if template.name.lower() == name.lower():
                template.name = name
                template.tags = tags
                self.save()
                return
        self.templates.append(TagTemplate(name, tags))
        self.templates.sort(key=lambda t: t.name.lower())
        self.save()

    def delete(self, name: str) -> None:
        self.templates = [t for t in self.templates if t.name != name]
        self.save()

    def get(self, name: str) -> Optional[TagTemplate]:
        for t in self.templates:
            if t.name == name:
                return t
        return None


class PublicationHistory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: list[HistoryEntry] = []
        self.load()
        self.import_legacy_csv_if_needed()

    def load(self) -> None:
        if not self.path.exists():
            self.entries = []
            return
        data = json.loads(self.path.read_text(encoding='utf-8'))
        self.entries = [HistoryEntry(**item) for item in data]

    def save(self) -> None:
        self.path.write_text(
            json.dumps([asdict(e) for e in self.entries], ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    def add(self, entry: HistoryEntry) -> None:
        self.entries.insert(0, entry)
        self.save()

    def import_legacy_csv_if_needed(self) -> None:
        if self.entries or not LEGACY_CSV_PATH.exists():
            return
        imported = []
        try:
            with LEGACY_CSV_PATH.open('r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    imported.append(HistoryEntry(
                        timestamp=row.get('published_at', ''),
                        platform=row.get('platform', 'telegram'),
                        status='legacy-import',
                        image_path=row.get('filename', ''),
                        display_name=row.get('filename', ''),
                        remote_id=str(row.get('message_id', '')),
                        extra={'legacy': True},
                    ))
        except Exception:
            return
        if imported:
            self.entries = list(reversed(imported))
            self.entries.reverse()
            self.save()


def list_images(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    return sorted(
        [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda p: p.stat().st_mtime,
    )


def get_ollama_chat():
    try:
        from ollama import chat
        return chat
    except ImportError as exc:
        raise RuntimeError(
            'AI-модуль Ollama не установлен. Программа может работать без ИИ. '
            'Чтобы включить AI Assistance, установи зависимости из requirements-ai.txt.'
        ) from exc


def conservative_notes_block(notes: str) -> str:
    notes = notes.strip()
    return 'Пользователь не дал дополнительных подсказок. Не выдумывай детали.' if not notes else f'Дополнительные подсказки от автора:\n{notes}'


def generate_caption(image_path: Path, config: AppConfig, notes: str) -> str:
    prompt = f"""
Ты помощник художника. Нужно придумать подпись к ЕГО СОБСТВЕННОМУ рисунку для публикации.

Проанализируй изображение и соблюдай строгую осторожность:
- если не уверен в виде персонажа, поле, сюжете или эмоции — НЕ выдумывай;
- не называй вид слишком конкретно без уверенности;
- не приписывай персонажу настроение, если оно не читается;
- лучше коротко и нейтрально, чем уверенно и неверно.

{conservative_notes_block(notes)}

Сформируй ТОЛЬКО готовую подпись.
Требования:
- язык: {config.caption_language}
- стиль: {config.caption_style}
- 1-3 коротких абзаца
- максимум 500 символов
- не описывай картинку сухим списком
- не упоминай ИИ, нейросети или автоматизацию
- не добавляй вступление вроде "Вот подпись:"
""".strip()
    chat = get_ollama_chat()
    response = chat(model=config.ollama_model, messages=[{'role': 'user', 'content': prompt, 'images': [str(image_path)]}])
    text = (response.message.content or '').strip()
    if not text:
        raise RuntimeError('Ollama вернула пустую подпись.')
    return text[:900]


def generate_tags(image_path: Path, config: AppConfig, notes: str) -> str:
    prompt = f"""
Ты помощник художника. Нужно подобрать теги к рисунку.

Правила:
- если не уверен в детали — не включай её;
- не выдумывай имена персонажей;
- максимум 18 тегов;
- делай теги краткими;
- лучше общие теги, чем ошибочные;
- верни только одну строку тегов, разделённых запятыми.

{conservative_notes_block(notes)}
Язык тегов: английский.
""".strip()
    chat = get_ollama_chat()
    response = chat(model=config.ollama_model, messages=[{'role': 'user', 'content': prompt, 'images': [str(image_path)]}])
    text = (response.message.content or '').strip()
    if not text:
        raise RuntimeError('Ollama вернула пустые теги.')
    text = ', '.join([part.strip(' -•\t') for line in text.splitlines() for part in line.split(',') if part.strip()])
    return text[:600]


def compose_social_text(caption: str, tags: str, append_tags: bool) -> str:
    caption, tags = caption.strip(), tags.strip()
    if not append_tags or not tags:
        return caption
    hashtags = []
    for raw in tags.replace(';', ',').split(','):
        t = raw.strip().replace(' ', '_')
        if not t:
            continue
        if not t.startswith('#'):
            t = '#' + t
        hashtags.append(t)
    return caption if not hashtags else caption + '\n\n' + ' '.join(hashtags[:15])


async def publish_to_telegram(image_path: Path, text: str, bot_token: str, chat_id: str) -> dict[str, Any]:
    send_as_document = image_path.stat().st_size >= 9_500_000
    async with Bot(token=bot_token) as bot:
        with image_path.open('rb') as file_obj:
            if send_as_document:
                message = await bot.send_document(chat_id=chat_id, document=file_obj, caption=text, filename=image_path.name, read_timeout=120, write_timeout=120, connect_timeout=30)
            else:
                message = await bot.send_photo(chat_id=chat_id, photo=file_obj, caption=text, filename=image_path.name, read_timeout=120, write_timeout=120, connect_timeout=30)
    url = f'https://t.me/{chat_id[1:]}/{message.message_id}' if isinstance(chat_id, str) and chat_id.startswith('@') else ''
    return {'remote_id': str(message.message_id), 'url': url}


def publish_to_x(image_path: Path, text: str, consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str, username: str) -> dict[str, Any]:
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret, resource_owner_key=access_token, resource_owner_secret=access_token_secret)
    with image_path.open('rb') as f:
        upload_resp = oauth.post('https://upload.twitter.com/1.1/media/upload.json', files={'media': f}, timeout=120)
    upload_resp.raise_for_status()
    media_id = upload_resp.json().get('media_id_string')
    if not media_id:
        raise RuntimeError(f'Не удалось получить media_id: {upload_resp.text}')
    post_resp = oauth.post('https://api.x.com/2/tweets', json={'text': text, 'media': {'media_ids': [media_id]}}, timeout=120)
    post_resp.raise_for_status()
    data = post_resp.json()
    tweet_id = data.get('data', {}).get('id')
    if not tweet_id:
        raise RuntimeError(f'Не удалось получить id поста: {data}')
    url = f'https://x.com/{username}/status/{tweet_id}' if username else ''
    return {'remote_id': str(tweet_id), 'url': url}


def vk_api_call(method: str, token: str, version: str, **params) -> dict[str, Any]:
    resp = requests.post(f'https://api.vk.com/method/{method}', data={'access_token': token, 'v': version, **params}, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(str(data['error']))
    return data['response']


def publish_to_vk(image_path: Path, text: str, access_token: str, owner_id: str, group_id: str, version: str, from_group: bool) -> dict[str, Any]:
    upload_params = {'group_id': group_id.strip()} if group_id.strip() else {}
    upload_server = vk_api_call('photos.getWallUploadServer', access_token, version, **upload_params)
    with image_path.open('rb') as f:
        upload_resp = requests.post(upload_server['upload_url'], files={'photo': f}, timeout=120)
    upload_resp.raise_for_status()
    upload_data = upload_resp.json()
    save_params = {'photo': upload_data['photo'], 'server': upload_data['server'], 'hash': upload_data['hash']}
    if group_id.strip():
        save_params['group_id'] = group_id.strip()
    saved = vk_api_call('photos.saveWallPhoto', access_token, version, **save_params)
    if not saved:
        raise RuntimeError('VK не вернул сохранённую фотографию.')
    item = saved[0]
    attachment = f"photo{item['owner_id']}_{item['id']}"
    post_params = {'owner_id': owner_id.strip(), 'attachments': attachment, 'message': text}
    if group_id.strip() and from_group:
        post_params['from_group'] = 1
    post = vk_api_call('wall.post', access_token, version, **post_params)
    post_id = post['post_id']
    return {'remote_id': str(post_id), 'url': f"https://vk.com/wall{owner_id.strip()}_{post_id}"}


def move_to_posted(image_path: Path, posted_dir: Path) -> Path:
    destination = posted_dir / image_path.name
    if destination.exists():
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        destination = posted_dir / f'{image_path.stem}_{stamp}{image_path.suffix}'
    shutil.move(str(image_path), str(destination))
    return destination


class ContentWorker(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, image_path: Path, config: AppConfig, notes: str, mode: str) -> None:
        super().__init__()
        self.image_path = image_path
        self.config = config
        self.notes = notes
        self.mode = mode

    def run(self) -> None:
        try:
            result = {}
            if self.mode in {'caption', 'both'}:
                result['caption'] = generate_caption(self.image_path, self.config, self.notes)
            if self.mode in {'tags', 'both'}:
                result['tags'] = generate_tags(self.image_path, self.config, self.notes)
            self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class PublishWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, image_path: Path, caption: str, tags: str, notes: str, config: AppConfig, platforms: list[str]) -> None:
        super().__init__()
        self.image_path = image_path
        self.caption = caption
        self.tags = tags
        self.notes = notes
        self.config = config
        self.platforms = platforms

    def run(self) -> None:
        try:
            results = []
            text = compose_social_text(self.caption, self.tags, self.config.append_tags_to_social_caption)
            for platform in self.platforms:
                if platform == 'telegram':
                    if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
                        raise RuntimeError('Telegram не настроен.')
                    published = asyncio.run(publish_to_telegram(self.image_path, text, self.config.telegram_bot_token, self.config.telegram_chat_id))
                    results.append({'platform': 'telegram', 'status': 'published', **published})
                elif platform == 'x':
                    if not all([self.config.x_consumer_key, self.config.x_consumer_secret, self.config.x_access_token, self.config.x_access_token_secret]):
                        raise RuntimeError('X не настроен.')
                    published = publish_to_x(self.image_path, text, self.config.x_consumer_key, self.config.x_consumer_secret, self.config.x_access_token, self.config.x_access_token_secret, self.config.x_username)
                    results.append({'platform': 'x', 'status': 'published', **published})
                elif platform == 'vk':
                    if not self.config.vk_access_token or not self.config.vk_owner_id:
                        raise RuntimeError('VK не настроен.')
                    published = publish_to_vk(self.image_path, text, self.config.vk_access_token, self.config.vk_owner_id, self.config.vk_group_id, self.config.vk_api_version, self.config.vk_from_group)
                    results.append({'platform': 'vk', 'status': 'published', **published})
                elif platform == 'e621':
                    results.append({'platform': 'e621', 'status': 'planned', 'remote_id': '', 'url': '', 'message': 'Заготовка UI и настроек добавлена, но загрузка в e621 пока не реализована.'})
                elif platform == 'deviantart':
                    results.append({'platform': 'deviantart', 'status': 'planned', 'remote_id': '', 'url': '', 'message': 'Заготовка UI и настроек добавлена, но публикация в DeviantArt пока не реализована.'})
            self.finished_ok.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class ImageDropLabel(QLabel):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Keep the preview useful, but do not force the whole window to stay tall.
        self.setMinimumSize(QSize(140, 100))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setWordWrap(True)
        self.setText('Перетащи рисунок сюда\nили нажми «Открыть файл»')

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = Path(urls[0].toLocalFile())
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                self.file_dropped.emit(str(path))
                event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Art Publisher Agent+')

        # The window must remain freely resizable even on small displays.
        # Start at a comfortable size relative to the usable desktop instead
        # of forcing a fixed 1380x900 window.
        self.setMinimumSize(560, 360)
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            start_width = min(1180, max(760, int(available.width() * 0.86)))
            start_height = min(760, max(520, int(available.height() * 0.80)))
            self.resize(start_width, start_height)
        else:
            self.resize(1100, 700)

        self.config = AppConfig.load()
        self.history = PublicationHistory(HISTORY_PATH)
        self.tag_templates = TagTemplateStore(TAG_TEMPLATES_PATH)
        self.current_image_path: Optional[Path] = None
        self._content_worker: Optional[ContentWorker] = None
        self._publish_worker: Optional[PublishWorker] = None

        self._build_ui()
        self._load_settings_into_form()
        self._refresh_status_labels()
        self.refresh_history_list()
        self.refresh_file_lists()
        self.refresh_tag_template_list()

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setMinimumSize(0, 0)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs.addTab(self._build_publish_tab(), 'Публикация')
        self.tabs.addTab(self._build_files_tab(), 'Файлы READY/POSTED')
        self.tabs.addTab(self._build_settings_tab(), 'Настройки')
        self.tabs.addTab(self._build_history_tab(), 'История')
        self.setCentralWidget(self.tabs)

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage('Готово')

        menu = self.menuBar()
        file_menu = menu.addMenu('Файл')

        open_action = QAction('Открыть изображение', self)
        open_action.triggered.connect(self.choose_image_file)
        file_menu.addAction(open_action)

        load_ready_action = QAction('Загрузить следующую из READY', self)
        load_ready_action.triggered.connect(self.load_next_from_ready)
        file_menu.addAction(load_ready_action)

        save_settings_action = QAction('Сохранить настройки', self)
        save_settings_action.triggered.connect(self.save_settings)
        file_menu.addAction(save_settings_action)

    def _build_publish_tab(self) -> QWidget:
        page = QWidget()
        page.setMinimumSize(0, 0)
        page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setMinimumSize(0, 0)
        layout.addWidget(splitter, 1)

        # LEFT: preview area can freely shrink with the window.
        left_panel = QWidget()
        left_panel.setMinimumSize(0, 0)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 6, 6, 6)

        self.preview_label = ImageDropLabel()
        self.preview_label.file_dropped.connect(self.load_image)
        left_layout.addWidget(self.preview_label, 1)

        self.file_name_label = QLabel('Файл: —')
        self.file_name_label.setWordWrap(True)
        left_layout.addWidget(self.file_name_label)

        self.file_path_label = QLabel('Путь: —')
        self.file_path_label.setWordWrap(True)
        left_layout.addWidget(self.file_path_label)

        left_buttons = QHBoxLayout()
        self.open_button = QPushButton('Открыть файл')
        self.open_button.clicked.connect(self.choose_image_file)
        left_buttons.addWidget(self.open_button)

        self.load_ready_button = QPushButton('Следующая из READY')
        self.load_ready_button.clicked.connect(self.load_next_from_ready)
        left_buttons.addWidget(self.load_ready_button)

        left_layout.addLayout(left_buttons)
        splitter.addWidget(left_panel)

        # RIGHT: keep controls at a sane height.  When the main window becomes
        # shorter, this pane scrolls vertically instead of Qt crushing widgets
        # until labels/editors overlap each other.
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setMinimumSize(0, 0)
        right_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_panel = QWidget()
        right_panel.setMinimumWidth(0)
        # This is intentional: below this height the scroll area takes over.
        # It prevents QTextEdit/QGroupBox layouts from being compressed into
        # each other on small displays.
        right_panel.setMinimumHeight(790)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        status_box = QGroupBox('Статус')
        status_box.setMinimumHeight(92)
        status_layout = QGridLayout(status_box)
        self.telegram_status_label = QLabel('Telegram: ?')
        self.x_status_label = QLabel('X: ?')
        self.vk_status_label = QLabel('VK: ?')
        self.ai_status_label = QLabel('AI: ?')
        status_layout.addWidget(self.telegram_status_label, 0, 0)
        status_layout.addWidget(self.x_status_label, 0, 1)
        status_layout.addWidget(self.vk_status_label, 1, 0)
        status_layout.addWidget(self.ai_status_label, 1, 1)
        right_layout.addWidget(status_box)

        self.notes_box = QGroupBox('Подсказки для ИИ (опционально)')
        self.notes_box.setMinimumHeight(116)
        notes_layout = QVBoxLayout(self.notes_box)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            'Например:\n'
            '- это мой персонаж-енот\n'
            '- настроение: самодовольное\n'
            '- это не волк, а собака\n'
            '- не делай романтических выводов'
        )
        self.notes_edit.setMinimumHeight(70)
        self.notes_edit.setMaximumHeight(95)
        notes_layout.addWidget(self.notes_edit)
        right_layout.addWidget(self.notes_box)

        content_box = QGroupBox('Текст публикации')
        content_box.setMinimumHeight(365)
        content_layout = QVBoxLayout(content_box)
        content_layout.setSpacing(5)

        caption_label = QLabel('Подпись')
        content_layout.addWidget(caption_label)
        self.caption_edit = QTextEdit()
        self.caption_edit.setPlaceholderText('Здесь будет подпись...')
        self.caption_edit.setMinimumHeight(90)
        self.caption_edit.setMaximumHeight(135)
        content_layout.addWidget(self.caption_edit)

        tags_label = QLabel('Теги')
        content_layout.addWidget(tags_label)
        self.tags_edit = QTextEdit()
        self.tags_edit.setPlaceholderText('Например: furry, anthro, raccoon, male, hoodie')
        self.tags_edit.setMinimumHeight(60)
        self.tags_edit.setMaximumHeight(80)
        content_layout.addWidget(self.tags_edit)

        template_box = QGroupBox('Шаблоны тегов')
        template_box.setMinimumHeight(155)
        template_layout = QVBoxLayout(template_box)
        self.tag_template_list = QListWidget()
        self.tag_template_list.setMinimumHeight(70)
        self.tag_template_list.setMaximumHeight(95)
        self.tag_template_list.itemDoubleClicked.connect(self.apply_selected_template_replace)
        template_layout.addWidget(self.tag_template_list)

        template_buttons_1 = QHBoxLayout()
        self.template_replace_button = QPushButton('Заменить тегами шаблона')
        self.template_replace_button.clicked.connect(self.apply_selected_template_replace)
        template_buttons_1.addWidget(self.template_replace_button)

        self.template_append_button = QPushButton('Добавить шаблон к тегам')
        self.template_append_button.clicked.connect(self.apply_selected_template_append)
        template_buttons_1.addWidget(self.template_append_button)
        template_layout.addLayout(template_buttons_1)

        template_buttons_2 = QHBoxLayout()
        self.template_save_button = QPushButton('Сохранить текущие теги как шаблон')
        self.template_save_button.clicked.connect(self.save_current_tags_as_template)
        template_buttons_2.addWidget(self.template_save_button)

        self.template_delete_button = QPushButton('Удалить шаблон')
        self.template_delete_button.clicked.connect(self.delete_selected_template)
        template_buttons_2.addWidget(self.template_delete_button)
        template_layout.addLayout(template_buttons_2)

        content_layout.addWidget(template_box)

        buttons_line = QHBoxLayout()
        self.gen_both_button = QPushButton('Сгенерировать подпись и теги')
        self.gen_both_button.clicked.connect(lambda: self.generate_content_clicked('both'))
        buttons_line.addWidget(self.gen_both_button)

        self.gen_caption_button = QPushButton('Только подпись')
        self.gen_caption_button.clicked.connect(lambda: self.generate_content_clicked('caption'))
        buttons_line.addWidget(self.gen_caption_button)

        self.gen_tags_button = QPushButton('Только теги')
        self.gen_tags_button.clicked.connect(lambda: self.generate_content_clicked('tags'))
        buttons_line.addWidget(self.gen_tags_button)

        content_layout.addLayout(buttons_line)
        right_layout.addWidget(content_box)

        platforms_box = QGroupBox('Площадки')
        platforms_box.setMinimumHeight(130)
        platforms_layout = QGridLayout(platforms_box)
        self.telegram_publish_cb = QCheckBox('Telegram')
        self.telegram_publish_cb.setChecked(True)
        self.x_publish_cb = QCheckBox('X')
        self.vk_publish_cb = QCheckBox('VK')
        self.e621_publish_cb = QCheckBox('e621')
        self.deviantart_publish_cb = QCheckBox('DeviantArt')

        platforms_layout.addWidget(self.telegram_publish_cb, 0, 0)
        platforms_layout.addWidget(self.x_publish_cb, 0, 1)
        platforms_layout.addWidget(self.vk_publish_cb, 1, 0)
        platforms_layout.addWidget(self.e621_publish_cb, 1, 1)
        platforms_layout.addWidget(self.deviantart_publish_cb, 2, 0)

        self.append_tags_checkbox = QCheckBox('Добавлять теги как хэштеги в соцсети')
        platforms_layout.addWidget(self.append_tags_checkbox, 3, 0, 1, 2)
        right_layout.addWidget(platforms_box)

        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        self.clear_button = QPushButton('Очистить')
        self.clear_button.clicked.connect(self.clear_current_image)
        self.clear_button.setMinimumHeight(38)
        actions_layout.addWidget(self.clear_button)

        self.publish_button = QPushButton('Опубликовать выбранное')
        self.publish_button.clicked.connect(self.publish_clicked)
        self.publish_button.setMinimumHeight(38)
        actions_layout.addWidget(self.publish_button)

        right_layout.addWidget(actions_widget)
        right_layout.addStretch(1)

        right_scroll.setWidget(right_panel)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([420, 760])
        return page

    def _build_files_tab(self) -> QWidget:
        page = QWidget()
        page.setMinimumSize(0, 0)
        page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        ready_box = QGroupBox('READY')
        ready_layout = QVBoxLayout(ready_box)
        self.ready_list_widget = QListWidget()
        self.ready_list_widget.itemDoubleClicked.connect(self.load_selected_ready_file)
        ready_layout.addWidget(self.ready_list_widget)
        ready_btns = QHBoxLayout()
        ready_refresh_btn = QPushButton('Обновить READY')
        ready_refresh_btn.clicked.connect(self.refresh_file_lists)
        ready_btns.addWidget(ready_refresh_btn)
        ready_load_btn = QPushButton('Загрузить выбранный')
        ready_load_btn.clicked.connect(self.load_selected_ready_file)
        ready_btns.addWidget(ready_load_btn)
        ready_open_folder_btn = QPushButton('Открыть папку')
        ready_open_folder_btn.clicked.connect(lambda: self.open_path(self.config.ready_path))
        ready_btns.addWidget(ready_open_folder_btn)
        ready_layout.addLayout(ready_btns)
        splitter.addWidget(ready_box)

        posted_box = QGroupBox('POSTED')
        posted_layout = QVBoxLayout(posted_box)
        self.posted_list_widget = QListWidget()
        self.posted_list_widget.itemDoubleClicked.connect(self.open_selected_posted_file)
        posted_layout.addWidget(self.posted_list_widget)
        posted_btns = QHBoxLayout()
        posted_refresh_btn = QPushButton('Обновить POSTED')
        posted_refresh_btn.clicked.connect(self.refresh_file_lists)
        posted_btns.addWidget(posted_refresh_btn)
        posted_open_btn = QPushButton('Открыть выбранный файл')
        posted_open_btn.clicked.connect(self.open_selected_posted_file)
        posted_btns.addWidget(posted_open_btn)
        posted_open_folder_btn = QPushButton('Открыть папку')
        posted_open_folder_btn.clicked.connect(lambda: self.open_path(self.config.posted_path))
        posted_btns.addWidget(posted_open_folder_btn)
        posted_layout.addLayout(posted_btns)
        splitter.addWidget(posted_box)

        splitter.setSizes([520, 520])
        return page

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        page.setMinimumSize(0, 0)
        page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        outer_layout = QVBoxLayout(page)
        # Do not let the settings form dictate the minimum height of the
        # application. When the window is small, the scroll area takes over.
        outer_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumSize(0, 0)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer_layout.addWidget(scroll, 1)

        inner = QWidget()
        inner.setMinimumSize(0, 0)
        inner.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        shared_box = QGroupBox('Общие настройки')
        shared_form = QFormLayout(shared_box)
        self.ready_dir_edit = QLineEdit()
        self.posted_dir_edit = QLineEdit()
        self.auto_move_checkbox = QCheckBox('Перемещать файл в POSTED после успешной публикации')

        ready_row = QHBoxLayout()
        ready_row.addWidget(self.ready_dir_edit)
        ready_btn = QPushButton('Выбрать')
        ready_btn.clicked.connect(lambda: self.choose_directory(self.ready_dir_edit))
        ready_row.addWidget(ready_btn)
        ready_widget = QWidget(); ready_widget.setLayout(ready_row)

        posted_row = QHBoxLayout()
        posted_row.addWidget(self.posted_dir_edit)
        posted_btn = QPushButton('Выбрать')
        posted_btn.clicked.connect(lambda: self.choose_directory(self.posted_dir_edit))
        posted_row.addWidget(posted_btn)
        posted_widget = QWidget(); posted_widget.setLayout(posted_row)

        shared_form.addRow('READY', ready_widget)
        shared_form.addRow('POSTED', posted_widget)
        shared_form.addRow('', self.auto_move_checkbox)
        layout.addWidget(shared_box)

        ai_box = QGroupBox('AI Assistance (опционально)')
        ai_form = QFormLayout(ai_box)
        self.ai_enabled_cb = QCheckBox('Включить помощь ИИ для подписей и тегов')
        self.ai_enabled_cb.toggled.connect(self._apply_ai_enabled_state)
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText('qwen3-vl:4b')
        self.lang_edit = QLineEdit()
        self.lang_edit.setPlaceholderText('ru')
        self.style_edit = QTextEdit()
        self.style_edit.setMaximumHeight(90)
        self.ai_install_hint = QLabel(
            'Без ИИ программа полностью работает: подписи и теги можно вводить вручную и через шаблоны. '
            'Для AI-функций нужен Ollama и зависимости из requirements-ai.txt.'
        )
        self.ai_install_hint.setWordWrap(True)
        ai_form.addRow('', self.ai_enabled_cb)
        ai_form.addRow('Ollama model', self.model_edit)
        ai_form.addRow('Язык подписи', self.lang_edit)
        ai_form.addRow('Стиль подписи', self.style_edit)
        ai_form.addRow('', self.ai_install_hint)
        layout.addWidget(ai_box)

        telegram_box = QGroupBox('Telegram')
        telegram_form = QFormLayout(telegram_box)
        self.telegram_enabled_cb = QCheckBox('Включено')
        self.telegram_token_edit = QLineEdit(); self.telegram_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_chat_id_edit = QLineEdit()
        telegram_form.addRow('', self.telegram_enabled_cb)
        telegram_form.addRow('Bot Token', self.telegram_token_edit)
        telegram_form.addRow('Chat ID / @channel', self.telegram_chat_id_edit)
        layout.addWidget(telegram_box)

        x_box = QGroupBox('X')
        x_form = QFormLayout(x_box)
        self.x_enabled_cb = QCheckBox('Включено')
        self.x_consumer_key_edit = QLineEdit()
        self.x_consumer_secret_edit = QLineEdit(); self.x_consumer_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.x_access_token_edit = QLineEdit()
        self.x_access_token_secret_edit = QLineEdit(); self.x_access_token_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.x_username_edit = QLineEdit()
        x_form.addRow('', self.x_enabled_cb)
        x_form.addRow('Consumer Key', self.x_consumer_key_edit)
        x_form.addRow('Consumer Secret', self.x_consumer_secret_edit)
        x_form.addRow('Access Token', self.x_access_token_edit)
        x_form.addRow('Access Token Secret', self.x_access_token_secret_edit)
        x_form.addRow('Username (optional)', self.x_username_edit)
        layout.addWidget(x_box)

        vk_box = QGroupBox('VK')
        vk_form = QFormLayout(vk_box)
        self.vk_enabled_cb = QCheckBox('Включено')
        self.vk_access_token_edit = QLineEdit(); self.vk_access_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.vk_owner_id_edit = QLineEdit()
        self.vk_group_id_edit = QLineEdit()
        self.vk_api_version_edit = QLineEdit()
        self.vk_from_group_cb = QCheckBox('Публиковать от имени сообщества')
        vk_form.addRow('', self.vk_enabled_cb)
        vk_form.addRow('Access Token', self.vk_access_token_edit)
        vk_form.addRow('Owner ID', self.vk_owner_id_edit)
        vk_form.addRow('Group ID (positive)', self.vk_group_id_edit)
        vk_form.addRow('API version', self.vk_api_version_edit)
        vk_form.addRow('', self.vk_from_group_cb)
        layout.addWidget(vk_box)

        e621_box = QGroupBox('e621 (настройки)')
        e621_form = QFormLayout(e621_box)
        self.e621_enabled_cb = QCheckBox('Включено')
        self.e621_username_edit = QLineEdit()
        self.e621_api_key_edit = QLineEdit(); self.e621_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.e621_rating_edit = QLineEdit()
        e621_form.addRow('', self.e621_enabled_cb)
        e621_form.addRow('Username', self.e621_username_edit)
        e621_form.addRow('API Key', self.e621_api_key_edit)
        e621_form.addRow('Default rating', self.e621_rating_edit)
        layout.addWidget(e621_box)

        da_box = QGroupBox('DeviantArt (настройки)')
        da_form = QFormLayout(da_box)
        self.da_enabled_cb = QCheckBox('Включено')
        self.da_client_id_edit = QLineEdit()
        self.da_client_secret_edit = QLineEdit(); self.da_client_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.da_access_token_edit = QLineEdit(); self.da_access_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.da_refresh_token_edit = QLineEdit(); self.da_refresh_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        da_form.addRow('', self.da_enabled_cb)
        da_form.addRow('Client ID', self.da_client_id_edit)
        da_form.addRow('Client Secret', self.da_client_secret_edit)
        da_form.addRow('Access Token', self.da_access_token_edit)
        da_form.addRow('Refresh Token', self.da_refresh_token_edit)
        layout.addWidget(da_box)

        buttons = QHBoxLayout()
        self.save_settings_button = QPushButton('Сохранить настройки')
        self.save_settings_button.clicked.connect(self.save_settings)
        buttons.addWidget(self.save_settings_button)
        self.reload_settings_button = QPushButton('Перечитать .env')
        self.reload_settings_button.clicked.connect(self.reload_settings)
        buttons.addWidget(self.reload_settings_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)
        return page

    def _build_history_tab(self) -> QWidget:
        page = QWidget()
        page.setMinimumSize(0, 0)
        page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.history_list = QListWidget()
        self.history_list.currentRowChanged.connect(self.on_history_selected)
        left_layout.addWidget(self.history_list, 1)

        hist_buttons = QHBoxLayout()
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.refresh_history_list)
        hist_buttons.addWidget(refresh_btn)

        open_history_btn = QPushButton('Открыть файл истории')
        open_history_btn.clicked.connect(lambda: self.open_path(HISTORY_PATH))
        hist_buttons.addWidget(open_history_btn)

        left_layout.addLayout(hist_buttons)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.history_preview = QLabel('Выбери запись')
        self.history_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_preview.setMinimumSize(QSize(140, 120))
        self.history_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.history_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.history_preview.setWordWrap(True)
        right_layout.addWidget(self.history_preview)

        self.history_meta_label = QLabel('—')
        self.history_meta_label.setWordWrap(True)
        right_layout.addWidget(self.history_meta_label)

        right_layout.addWidget(QLabel('Подпись'))
        self.history_caption_view = QTextEdit(); self.history_caption_view.setReadOnly(True); self.history_caption_view.setMinimumHeight(80)
        right_layout.addWidget(self.history_caption_view)

        right_layout.addWidget(QLabel('Теги'))
        self.history_tags_view = QTextEdit(); self.history_tags_view.setReadOnly(True); self.history_tags_view.setMaximumHeight(90)
        right_layout.addWidget(self.history_tags_view)

        link_buttons = QHBoxLayout()
        self.open_history_image_btn = QPushButton('Открыть файл')
        self.open_history_image_btn.clicked.connect(self.open_selected_history_image)
        link_buttons.addWidget(self.open_history_image_btn)

        self.open_history_url_btn = QPushButton('Открыть ссылку')
        self.open_history_url_btn.clicked.connect(self.open_selected_history_url)
        link_buttons.addWidget(self.open_history_url_btn)

        right_layout.addLayout(link_buttons)
        splitter.addWidget(right)
        splitter.setSizes([420, 820])
        return page

    def _load_settings_into_form(self) -> None:
        c = self.config
        self.ai_enabled_cb.setChecked(c.ai_enabled)
        self.model_edit.setText(c.ollama_model)
        self.lang_edit.setText(c.caption_language)
        self.style_edit.setPlainText(c.caption_style)
        self.ready_dir_edit.setText(c.ready_dir)
        self.posted_dir_edit.setText(c.posted_dir)
        self.auto_move_checkbox.setChecked(c.auto_move_after_publish)
        self.append_tags_checkbox.setChecked(c.append_tags_to_social_caption)
        self.telegram_enabled_cb.setChecked(c.telegram_enabled)
        self.telegram_token_edit.setText(c.telegram_bot_token)
        self.telegram_chat_id_edit.setText(c.telegram_chat_id)
        self.x_enabled_cb.setChecked(c.x_enabled)
        self.x_consumer_key_edit.setText(c.x_consumer_key)
        self.x_consumer_secret_edit.setText(c.x_consumer_secret)
        self.x_access_token_edit.setText(c.x_access_token)
        self.x_access_token_secret_edit.setText(c.x_access_token_secret)
        self.x_username_edit.setText(c.x_username)
        self.vk_enabled_cb.setChecked(c.vk_enabled)
        self.vk_access_token_edit.setText(c.vk_access_token)
        self.vk_owner_id_edit.setText(c.vk_owner_id)
        self.vk_group_id_edit.setText(c.vk_group_id)
        self.vk_api_version_edit.setText(c.vk_api_version)
        self.vk_from_group_cb.setChecked(c.vk_from_group)
        self.e621_enabled_cb.setChecked(c.e621_enabled)
        self.e621_username_edit.setText(c.e621_username)
        self.e621_api_key_edit.setText(c.e621_api_key)
        self.e621_rating_edit.setText(c.e621_default_rating)
        self.da_enabled_cb.setChecked(c.deviantart_enabled)
        self.da_client_id_edit.setText(c.deviantart_client_id)
        self.da_client_secret_edit.setText(c.deviantart_client_secret)
        self.da_access_token_edit.setText(c.deviantart_access_token)
        self.da_refresh_token_edit.setText(c.deviantart_refresh_token)
        self._apply_ai_enabled_state(c.ai_enabled)

    def _read_settings_from_form(self) -> AppConfig:
        return AppConfig(
            ai_enabled=self.ai_enabled_cb.isChecked(),
            ollama_model=self.model_edit.text().strip() or 'qwen3-vl:4b',
            caption_language=self.lang_edit.text().strip() or 'ru',
            caption_style=self.style_edit.toPlainText().strip() or 'коротко, живо, естественно, слегка игриво; без канцелярита',
            ready_dir=self.ready_dir_edit.text().strip() or 'READY',
            posted_dir=self.posted_dir_edit.text().strip() or 'POSTED',
            auto_move_after_publish=self.auto_move_checkbox.isChecked(),
            append_tags_to_social_caption=self.append_tags_checkbox.isChecked(),
            telegram_enabled=self.telegram_enabled_cb.isChecked(),
            telegram_bot_token=self.telegram_token_edit.text().strip(),
            telegram_chat_id=self.telegram_chat_id_edit.text().strip(),
            x_enabled=self.x_enabled_cb.isChecked(),
            x_consumer_key=self.x_consumer_key_edit.text().strip(),
            x_consumer_secret=self.x_consumer_secret_edit.text().strip(),
            x_access_token=self.x_access_token_edit.text().strip(),
            x_access_token_secret=self.x_access_token_secret_edit.text().strip(),
            x_username=self.x_username_edit.text().strip(),
            vk_enabled=self.vk_enabled_cb.isChecked(),
            vk_access_token=self.vk_access_token_edit.text().strip(),
            vk_owner_id=self.vk_owner_id_edit.text().strip(),
            vk_group_id=self.vk_group_id_edit.text().strip(),
            vk_api_version=self.vk_api_version_edit.text().strip() or '5.199',
            vk_from_group=self.vk_from_group_cb.isChecked(),
            e621_enabled=self.e621_enabled_cb.isChecked(),
            e621_username=self.e621_username_edit.text().strip(),
            e621_api_key=self.e621_api_key_edit.text().strip(),
            e621_default_rating=self.e621_rating_edit.text().strip() or 's',
            deviantart_enabled=self.da_enabled_cb.isChecked(),
            deviantart_client_id=self.da_client_id_edit.text().strip(),
            deviantart_client_secret=self.da_client_secret_edit.text().strip(),
            deviantart_access_token=self.da_access_token_edit.text().strip(),
            deviantart_refresh_token=self.da_refresh_token_edit.text().strip(),
        )

    def _refresh_status_labels(self) -> None:
        c = self.config
        tel_ok = c.telegram_enabled and bool(c.telegram_bot_token and c.telegram_chat_id)
        x_ok = c.x_enabled and bool(c.x_consumer_key and c.x_consumer_secret and c.x_access_token and c.x_access_token_secret)
        vk_ok = c.vk_enabled and bool(c.vk_access_token and c.vk_owner_id)
        self.telegram_status_label.setText(f"Telegram: {'✓' if tel_ok else '✗'}")
        self.x_status_label.setText(f"X: {'✓' if x_ok else '✗'}")
        self.vk_status_label.setText(f"VK: {'✓' if vk_ok else '✗'}")
        if not c.ai_enabled:
            self.ai_status_label.setText('AI: выключен')
        elif importlib.util.find_spec('ollama') is None:
            self.ai_status_label.setText('AI: модуль Ollama не установлен')
        else:
            self.ai_status_label.setText(f'AI: Ollama / {c.ollama_model}')

    def _apply_ai_enabled_state(self, enabled: bool) -> None:
        for widget in (self.model_edit, self.lang_edit, self.style_edit):
            widget.setEnabled(enabled)
        if hasattr(self, 'notes_box'):
            self.notes_box.setEnabled(enabled)
        if hasattr(self, 'gen_both_button'):
            self.gen_both_button.setEnabled(enabled)
            self.gen_caption_button.setEnabled(enabled)
            self.gen_tags_button.setEnabled(enabled)
        if hasattr(self, 'ai_install_hint'):
            if enabled:
                self.ai_install_hint.setText(
                    'AI включён. Для генерации нужен локальный Ollama, установленная vision-модель '
                    'и Python-зависимости из requirements-ai.txt.'
                )
            else:
                self.ai_install_hint.setText(
                    'AI выключен. Это нормальный основной режим: вводи подпись вручную, используй '
                    'шаблоны тегов и публикуй без Ollama.'
                )
        if hasattr(self, 'config'):
            self.config.ai_enabled = enabled
        if hasattr(self, 'ai_status_label'):
            self._refresh_status_labels()

    def refresh_tag_template_list(self) -> None:
        self.tag_templates.load()
        self.tag_template_list.clear()
        for template in self.tag_templates.templates:
            item = QListWidgetItem(f'{template.name} — {template.tags}')
            item.setData(Qt.ItemDataRole.UserRole, template.name)
            self.tag_template_list.addItem(item)

    def selected_template(self) -> Optional[TagTemplate]:
        item = self.tag_template_list.currentItem()
        if not item:
            return None
        name = item.data(Qt.ItemDataRole.UserRole)
        return self.tag_templates.get(name)

    def apply_selected_template_replace(self, *_args) -> None:
        template = self.selected_template()
        if not template:
            QMessageBox.information(self, 'Нет шаблона', 'Выбери шаблон тегов.')
            return
        self.tags_edit.setPlainText(template.tags)
        self.statusBar().showMessage(f'Применён шаблон: {template.name}')

    def apply_selected_template_append(self) -> None:
        template = self.selected_template()
        if not template:
            QMessageBox.information(self, 'Нет шаблона', 'Выбери шаблон тегов.')
            return
        current = self.tags_edit.toPlainText().strip()
        merged = current + ', ' + template.tags if current else template.tags
        self.tags_edit.setPlainText(self.normalize_tags_string(merged))
        self.statusBar().showMessage(f'Шаблон добавлен: {template.name}')

    def save_current_tags_as_template(self) -> None:
        tags = self.normalize_tags_string(self.tags_edit.toPlainText())
        if not tags:
            QMessageBox.information(self, 'Нет тегов', 'Сначала введи теги, которые надо сохранить как шаблон.')
            return
        name, ok = QInputDialog.getText(self, 'Новый шаблон', 'Название шаблона:')
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, 'Пустое имя', 'Название шаблона не может быть пустым.')
            return
        self.tag_templates.add_or_update(name, tags)
        self.refresh_tag_template_list()
        self.statusBar().showMessage(f'Шаблон сохранён: {name}')

    def delete_selected_template(self) -> None:
        template = self.selected_template()
        if not template:
            QMessageBox.information(self, 'Нет шаблона', 'Выбери шаблон для удаления.')
            return
        answer = QMessageBox.question(self, 'Удалить шаблон', f'Удалить шаблон "{template.name}"?')
        if answer == QMessageBox.StandardButton.Yes:
            self.tag_templates.delete(template.name)
            self.refresh_tag_template_list()
            self.statusBar().showMessage(f'Шаблон удалён: {template.name}')

    def normalize_tags_string(self, tags: str) -> str:
        parts = []
        seen = set()
        for raw in tags.replace('\n', ',').replace(';', ',').split(','):
            tag = raw.strip()
            if not tag:
                continue
            low = tag.lower()
            if low in seen:
                continue
            seen.add(low)
            parts.append(tag)
        return ', '.join(parts)

    def choose_directory(self, target_edit: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(self, 'Выбери папку', target_edit.text().strip() or str(APP_DIR))
        if directory:
            target_edit.setText(directory)

    def choose_image_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, 'Выбери рисунок', str(self.config.ready_path), 'Images (*.png *.jpg *.jpeg *.webp)')
        if file_path:
            self.load_image(file_path)

    def show_pixmap_in_label(self, label: QLabel, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            label.setText('Не удалось загрузить превью')
            label.setPixmap(QPixmap())
            return
        label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def load_image(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(self, 'Файл не найден', str(path))
            return
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            QMessageBox.warning(self, 'Неподдерживаемый формат', 'Нужен PNG/JPG/WEBP')
            return
        self.current_image_path = path
        self.file_name_label.setText(f'Файл: {path.name}')
        self.file_path_label.setText(f'Путь: {path}')
        self.show_pixmap_in_label(self.preview_label, path)
        self.statusBar().showMessage(f'Загружен файл: {path.name}')
        self.tabs.setCurrentIndex(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.current_image_path and self.current_image_path.exists():
            self.show_pixmap_in_label(self.preview_label, self.current_image_path)

    def clear_current_image(self) -> None:
        self.current_image_path = None
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText('Перетащи рисунок сюда\nили нажми «Открыть файл»')
        self.file_name_label.setText('Файл: —')
        self.file_path_label.setText('Путь: —')
        self.notes_edit.clear()
        self.caption_edit.clear()
        self.tags_edit.clear()
        self.statusBar().showMessage('Очищено')

    def load_next_from_ready(self) -> None:
        images = list_images(self.config.ready_path)
        if not images:
            QMessageBox.information(self, 'READY пуст', f'В папке нет изображений:\n{self.config.ready_path}')
            return
        self.load_image(str(images[0]))

    def save_settings(self) -> None:
        self.config = self._read_settings_from_form()
        self.config.save()
        self._refresh_status_labels()
        self.refresh_file_lists()
        self.statusBar().showMessage('Настройки сохранены')
        QMessageBox.information(self, 'Сохранено', f'Настройки сохранены в:\n{ENV_PATH}')

    def reload_settings(self) -> None:
        self.config = AppConfig.load()
        self._load_settings_into_form()
        self._refresh_status_labels()
        self.refresh_file_lists()
        self.statusBar().showMessage('Настройки перечитаны')

    def generate_content_clicked(self, mode: str) -> None:
        self.config = self._read_settings_from_form()
        if not self.config.ai_enabled:
            QMessageBox.information(
                self,
                'AI выключен',
                'Генерация отключена. Подпись и теги можно вводить вручную или использовать шаблоны тегов. '
                'Если нужна помощь ИИ — включи AI Assistance в настройках.'
            )
            return
        if not self.current_image_path:
            QMessageBox.warning(self, 'Нет изображения', 'Сначала загрузи рисунок.')
            return
        self._refresh_status_labels()
        self.gen_both_button.setEnabled(False)
        self.gen_caption_button.setEnabled(False)
        self.gen_tags_button.setEnabled(False)
        self.statusBar().showMessage('Генерирую через Ollama...')
        self._content_worker = ContentWorker(self.current_image_path, self.config, self.notes_edit.toPlainText(), mode)
        self._content_worker.finished_ok.connect(self._on_generation_success)
        self._content_worker.failed.connect(self._on_generation_failed)
        self._content_worker.start()

    def _on_generation_success(self, result: dict) -> None:
        self.gen_both_button.setEnabled(True)
        self.gen_caption_button.setEnabled(True)
        self.gen_tags_button.setEnabled(True)
        if 'caption' in result:
            self.caption_edit.setPlainText(result['caption'])
        if 'tags' in result:
            self.tags_edit.setPlainText(self.normalize_tags_string(result['tags']))
        self.statusBar().showMessage('Готово')

    def _on_generation_failed(self, message: str) -> None:
        self.gen_both_button.setEnabled(True)
        self.gen_caption_button.setEnabled(True)
        self.gen_tags_button.setEnabled(True)
        self.statusBar().showMessage('Ошибка генерации')
        QMessageBox.critical(self, 'Ошибка Ollama', f'Не удалось сгенерировать текст.\n\n{message}\n\nПроверь, что AI Assistance включён, установлен пакет из requirements-ai.txt, Ollama запущен и модель установлена.')

    def selected_platforms(self) -> list[str]:
        result = []
        if self.telegram_publish_cb.isChecked(): result.append('telegram')
        if self.x_publish_cb.isChecked(): result.append('x')
        if self.vk_publish_cb.isChecked(): result.append('vk')
        if self.e621_publish_cb.isChecked(): result.append('e621')
        if self.deviantart_publish_cb.isChecked(): result.append('deviantart')
        return result

    def publish_clicked(self) -> None:
        if not self.current_image_path:
            QMessageBox.warning(self, 'Нет изображения', 'Сначала загрузи рисунок.')
            return
        caption = self.caption_edit.toPlainText().strip()
        tags = self.normalize_tags_string(self.tags_edit.toPlainText())
        notes = self.notes_edit.toPlainText().strip()
        self.tags_edit.setPlainText(tags)
        if not caption:
            QMessageBox.warning(self, 'Нет подписи', 'Сгенерируй или введи подпись.')
            return
        platforms = self.selected_platforms()
        if not platforms:
            QMessageBox.warning(self, 'Нет площадок', 'Выбери хотя бы одну площадку.')
            return
        self.config = self._read_settings_from_form()
        self._refresh_status_labels()
        self.publish_button.setEnabled(False)
        self.statusBar().showMessage('Публикую...')
        self._publish_worker = PublishWorker(self.current_image_path, caption, tags, notes, self.config, platforms)
        self._publish_worker.finished_ok.connect(self._on_publish_success)
        self._publish_worker.failed.connect(self._on_publish_failed)
        self._publish_worker.start()

    def _on_publish_success(self, results: list) -> None:
        self.publish_button.setEnabled(True)
        original_path = self.current_image_path
        moved_to = ''
        if original_path is not None and self.config.auto_move_after_publish:
            moved_to = str(move_to_posted(original_path, self.config.posted_path))
        for item in results:
            self.history.add(HistoryEntry(
                timestamp=datetime.now().isoformat(timespec='seconds'),
                platform=item.get('platform', ''),
                status=item.get('status', ''),
                image_path=str(original_path) if original_path else '',
                display_name=original_path.name if original_path else '',
                caption=self.caption_edit.toPlainText().strip(),
                tags=self.tags_edit.toPlainText().strip(),
                notes=self.notes_edit.toPlainText().strip(),
                remote_id=item.get('remote_id', ''),
                url=item.get('url', ''),
                moved_to=moved_to,
                extra={'message': item.get('message', '')} if item.get('message') else {},
            ))
        self.refresh_history_list()
        self.refresh_file_lists()
        summary_lines = []
        for item in results:
            line = f"- {item.get('platform')}: {item.get('status')}"
            if item.get('url'):
                line += f"\n  {item.get('url')}"
            if item.get('message'):
                line += f"\n  {item.get('message')}"
            summary_lines.append(line)
        if moved_to:
            summary_lines.append(f'\nФайл перемещён в:\n{moved_to}')
        self.statusBar().showMessage('Публикация завершена')
        QMessageBox.information(self, 'Готово', '\n'.join(summary_lines))
        self.clear_current_image()
        self.tabs.setCurrentIndex(3)

    def _on_publish_failed(self, message: str) -> None:
        self.publish_button.setEnabled(True)
        self.statusBar().showMessage('Ошибка публикации')
        QMessageBox.critical(self, 'Ошибка', message)

    def refresh_history_list(self) -> None:
        self.history.load()
        self.history_list.clear()
        for entry in self.history.entries:
            ts = entry.timestamp.replace('T', ' ')[:19] if entry.timestamp else '—'
            text = f'[{entry.platform}] {ts} — {entry.display_name or Path(entry.image_path).name or "без имени"}'
            self.history_list.addItem(QListWidgetItem(text))

    def on_history_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.history.entries):
            return
        entry = self.history.entries[row]
        image_candidate = entry.moved_to or entry.image_path
        path = Path(image_candidate)
        if path.exists() and path.is_file():
            self.show_pixmap_in_label(self.history_preview, path)
        else:
            self.history_preview.setPixmap(QPixmap())
            self.history_preview.setText('Файл превью не найден')
        meta = [
            f'Платформа: {entry.platform}',
            f'Статус: {entry.status}',
            f'Время: {entry.timestamp}',
            f'Файл: {entry.display_name}',
        ]
        if entry.remote_id:
            meta.append(f'Remote ID: {entry.remote_id}')
        if entry.url:
            meta.append(f'URL: {entry.url}')
        if entry.extra and entry.extra.get('message'):
            meta.append(f"Примечание: {entry.extra.get('message')}")
        self.history_meta_label.setText('\n'.join(meta))
        self.history_caption_view.setPlainText(entry.caption or '')
        self.history_tags_view.setPlainText(entry.tags or '')

    def open_selected_history_image(self) -> None:
        row = self.history_list.currentRow()
        if row < 0 or row >= len(self.history.entries):
            return
        entry = self.history.entries[row]
        self.open_path(Path(entry.moved_to or entry.image_path))

    def open_selected_history_url(self) -> None:
        row = self.history_list.currentRow()
        if row < 0 or row >= len(self.history.entries):
            return
        entry = self.history.entries[row]
        if not entry.url:
            QMessageBox.information(self, 'Нет ссылки', 'Для этой записи ссылка не сохранена.')
            return
        QDesktopServices.openUrl(QUrl(entry.url))

    def refresh_file_lists(self) -> None:
        self.config = self._read_settings_from_form() if hasattr(self, 'ready_dir_edit') else self.config
        ready_files = list_images(self.config.ready_path)
        posted_files = list_images(self.config.posted_path)
        self.ready_list_widget.clear()
        self.posted_list_widget.clear()
        for p in ready_files:
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.ready_list_widget.addItem(item)
        for p in posted_files:
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.posted_list_widget.addItem(item)

    def load_selected_ready_file(self, *_args) -> None:
        item = self.ready_list_widget.currentItem()
        if not item:
            QMessageBox.information(self, 'Нет файла', 'Выбери файл из READY.')
            return
        self.load_image(item.data(Qt.ItemDataRole.UserRole))

    def open_selected_posted_file(self, *_args) -> None:
        item = self.posted_list_widget.currentItem()
        if not item:
            QMessageBox.information(self, 'Нет файла', 'Выбери файл из POSTED.')
            return
        self.open_path(Path(item.data(Qt.ItemDataRole.UserRole)))

    def open_path(self, path: Path) -> None:
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        except Exception as exc:
            QMessageBox.warning(self, 'Не удалось открыть', str(exc))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
