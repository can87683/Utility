#!/usr/bin/env python3
# huggingface_downloader.py
# Copyright Su Nie | BSD-3C License | https://github.com/can87683

import os
import sys
import setproctitle
setproctitle.setproctitle(os.path.basename(sys.argv[0]))

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import requests
import threading
import configparser
from datetime import datetime
import webbrowser
import time
import hashlib


class Config:
    SCRIPT_NAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    CONFIG_FILE = f"{SCRIPT_NAME}.ini"

    WINDOW_TITLE = "HF Model Browser - Download Manager"
    WINDOW_WIDTH = 640
    WINDOW_HEIGHT = 1050
    WINDOW_RESIZABLE = False

    FONT_FAMILY = "Arial"
    FONT_SIZE_BODY = 10
    FONT_SIZE_HEADER = 14
    FONT_WEIGHT_HEADER = "bold"

    BG_MAIN = "#2b2b2b"
    BG_FRAME = "#2b2b2b"
    BG_LOG = "#1e1e1e"
    BG_STATUS = "#1f1f1f"

    FG_BODY = "#ffffff"
    FG_HEADER = "yellow"
    FG_LOG_NORMAL = "#ffffff"
    FG_LOG_ERROR = "#ffff00"
    FG_PROGRESS = "#4da6ff"
    FG_STATUS = "#ffffff"

    BTN_BG = "#1f6aa5"
    BTN_FG = "#ffffff"
    BTN_BORDER = "#ffffff"
    BTN_BORDER_WIDTH = 1

    DROPDOWN_BG = "#2b2b2b"
    DROPDOWN_FG = "#ffffff"
    DROPDOWN_MENU_BG = "#2b2b2b"
    DROPDOWN_MENU_FG = "#ffffff"

    TV_BG = "#2b2b2b"
    TV_FG = "#ffffff"
    TV_SELECT_BG = "#1f6aa5"
    TV_SELECT_FG = "#ffffff"
    TV_HEADING_BG = "#1f1f1f"

    PADDING = 2
    TREEVIEW_HEIGHT = 10
    LOG_HEIGHT_LINES = 16

    FORMAT_OPTIONS = ["all", "gguf", "onnx", "pytorch", "tensorflow", "safetensors"]
    SORT_OPTIONS = ["downloads", "likes", "trending", "recent"]
    PAGE_SIZE_OPTIONS = ["10", "20", "50", "100"]
    DEFAULT_FORMAT = "all"
    DEFAULT_SORT = "downloads"
    DEFAULT_PAGE_SIZE = "20"

    MAX_RETRIES = 5
    BLOCK_SIZE = 8192
    PROGRESS_UPDATE_INTERVAL = 0.5
    DOWNLOAD_TIMEOUT = 30
    VERIFY_CHECKSUM = False

    API_TIMEOUT = 15
    API_LIMIT = 100
    # persistent in user agent name
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"

    MODEL_EXTENSIONS = ['.onnx', '.safetensors', '.bin', '.pt', '.pth', '.gguf', '.pb']
    METADATA_EXTENSIONS = ['.json', '.txt', '.md', '.gitattributes', '.cfg', '.yaml', '.yml']
    SKIP_EXTENSIONS = ['.gitattributes', '.xet']

    BTN_DOWNLOAD = "⬇ Download All Files"
    BTN_CANCEL = "⏹ Cancel"
    BTN_OPEN = "🌐 Open HF"
    BTN_VIEW_FILES = "📂 View Files"
    BTN_COPY_URL = "📋 Copy URL"
    BTN_REFRESH = "🔄 Refresh"
    BTN_SEARCH = "🔍 Search"
    BTN_CLEAR = "✕ Clear"
    MSG_READY = "Ready"

    @classmethod
    def get_font(cls, size=None, weight=None):
        return (cls.FONT_FAMILY, size or cls.FONT_SIZE_BODY, weight or "normal")


class HFBrowse:
    def __init__(self):
        self.config = Config()
        self.all_models = []
        self.filtered_models = []
        self.current_page = 0
        self.search_query = ""
        self.sort_by = Config.DEFAULT_SORT
        self.total_models = 0
        self.is_closing = False
        self.access_token = None
        self.session = requests.Session()
        self.download_dir = os.getcwd()
        self.load_config()

    @staticmethod
    def get_centered_position(width, height):
        temp = tk.Tk()
        temp.withdraw()
        x = (temp.winfo_screenwidth() - width) // 2
        y = (temp.winfo_screenheight() - height) // 2
        temp.destroy()
        return x, y

    def load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config.CONFIG_FILE)

        if not config.has_section('Window'):
            config.add_section('Window')
        if not config.has_option('Window', 'x') or not config.has_option('Window', 'y'):
            def_x, def_y = self.get_centered_position(self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT)
            config.set('Window', 'x', str(def_x))
            config.set('Window', 'y', str(def_y))

        if not config.has_section('Settings'):
            config.add_section('Settings')
        if not config.has_option('Settings', 'sort_by'):
            config.set('Settings', 'sort_by', self.config.DEFAULT_SORT)
        if not config.has_option('Settings', 'last_search'):
            config.set('Settings', 'last_search', "")

        if not config.has_section('Repo'):
            config.add_section('Repo')
        if not config.has_option('Repo', 'path'):
            config.set('Repo', 'path', os.getcwd())

        with open(self.config.CONFIG_FILE, 'w') as f:
            config.write(f)

        self.window_x = config.getint('Window', 'x')
        self.window_y = config.getint('Window', 'y')
        self.sort_by = config.get('Settings', 'sort_by')
        self.search_query = config.get('Settings', 'last_search')
        self.download_dir = config.get('Repo', 'path')

    def save_config(self, window_x, window_y):
        config = configparser.ConfigParser()
        config.read(self.config.CONFIG_FILE)
        config['Window'] = {'x': str(window_x), 'y': str(window_y)}
        config['Settings'] = {'sort_by': self.sort_by, 'last_search': self.search_query}
        config['Repo'] = {'path': self.download_dir}
        with open(self.config.CONFIG_FILE, 'w') as f:
            config.write(f)

    def fetch_models_from_hf(self, search_term="", format_filter="all"):
        all_models = []
        search_strategies = [search_term] if search_term else [""]
        for strategy in search_strategies[:4]:
            url = "https://huggingface.co/api/models"
            params = {"limit": self.config.API_LIMIT, "sort": "downloads"}
            if strategy: params["search"] = strategy
            headers = {"User-Agent": self.config.USER_AGENT, "Accept": "application/json"}
            if self.access_token: headers["Authorization"] = f"Bearer {self.access_token}"

            response = requests.get(url, params=params, headers=headers, timeout=self.config.API_TIMEOUT)
            response.raise_for_status()
            models = response.json()
            if models:
                processed = []
                for model in models[:20]:
                    model_id = model.get("modelId", model.get("id", ""))
                    if model_id:
                        is_gated = isinstance(model.get("gated", False), dict) or model.get("gated", False)
                        files = self.fetch_model_files(model_id)
                        model_data = self.process_model_with_files(model, files, format_filter)
                        if model_data:
                            model_data['gated'] = is_gated
                            processed.append(model_data)
                if processed:
                    all_models.extend(processed)
                    if strategy and len(processed) >= 5: break

        seen = set()
        unique_models = []
        for model in all_models:
            model_id = model.get("id")
            if model_id and model_id not in seen:
                model = self.ensure_model_fields(model)
                seen.add(model_id)
                unique_models.append(model)
        return unique_models

    def fetch_model_files(self, model_id):
        url = f"https://huggingface.co/api/models/{model_id}"
        headers = {"User-Agent": self.config.USER_AGENT, "Accept": "application/json"}
        if self.access_token: headers["Authorization"] = f"Bearer {self.access_token}"
        response = requests.get(url, timeout=self.config.API_TIMEOUT, headers=headers)
        response.raise_for_status()
        data = response.json()
        siblings = data.get("siblings", [])
        files = []
        for sibling in siblings:
            filename = sibling.get("rfilename", "")
            if not filename or any(filename.endswith(ext) for ext in self.config.SKIP_EXTENSIONS):
                continue
            file_size = sibling.get("size", 0)
            lfs_info = sibling.get("lfs", {})
            sha256 = lfs_info.get("sha256") if isinstance(lfs_info, dict) else None
            is_model = any(filename.endswith(ext) for ext in self.config.MODEL_EXTENSIONS)
            is_metadata = any(filename.endswith(ext) for ext in self.config.METADATA_EXTENSIONS)
            files.append({
                "filename": filename,
                "size": file_size,
                "sha256": sha256,
                "format": self.detect_file_format(filename),
                "is_model": is_model,
                "is_metadata": is_metadata
            })
        files.sort(key=lambda x: (0 if x.get('is_model', False) else 1, -x.get('size', 0)))
        return files

    def process_model_with_files(self, model, files, format_filter):
        model_id = model.get("modelId", model.get("id", ""))
        if not model_id: return None
        format_type = self.detect_format_from_files(files) if files else self.detect_format_from_model(model)
        if format_filter != "all" and format_filter not in format_type.lower(): return None
        return {
            "id": model_id,
            "downloads": model.get("downloads", 0),
            "likes": model.get("likes", 0),
            "format": format_type,
            "size": self.estimate_model_size(model),
            "tags": self.generate_tags(model),
            "description": self.generate_description(model),
            "pipeline_tag": model.get("pipeline_tag", "Unknown"),
            "files": files,
            "download_url": f"https://huggingface.co/{model_id}/resolve/main/",
            "gated": isinstance(model.get("gated", False), dict) or model.get("gated", False)
        }

    def detect_file_format(self, filename):
        fl = filename.lower()
        if fl.endswith(".gguf"): return "gguf"
        if fl.endswith(".onnx"): return "onnx"
        if ".pth" in fl or ".pt" in fl: return "pytorch"
        if ".pb" in fl: return "tensorflow"
        if fl.endswith(".safetensors"): return "safetensors"
        if fl.endswith(".bin"): return "bin"
        return "unknown"

    def detect_format_from_files(self, files):
        formats = {f.get("format", "unknown") for f in files if f.get("format", "unknown") != "unknown"}
        return ", ".join(sorted(formats)) if formats else "unknown"

    def detect_format_from_model(self, model):
        model_id = model.get("id", "").lower()
        tags = [t.lower() for t in model.get("tags", [])]
        formats = []

        for fmt, keywords in {
            "gguf": ["gguf"],
            "onnx": ["onnx"],
            "pytorch": ["pytorch"],
            "tensorflow": ["tensorflow"],
            "safetensors": ["safetensors"]
        }.items():
            if any(kw in tag for kw in keywords for tag in tags) or any(kw in model_id for kw in keywords):
                formats.append(fmt)

        if not formats:
            if any(x in model_id for x in ["llama", "mistral", "phi", "gemma", "deepseek"]):
                formats = ["pytorch", "gguf"]
            else:
                formats = ["unknown"]

        return ", ".join(sorted(set(formats)))

    def ensure_model_fields(self, model):
        if not model.get("format") or model.get("format") == "unknown": model["format"] = self.detect_format_from_model(model)
        if not model.get("size") or model.get("size") == "Unknown": model["size"] = self.estimate_model_size(model)
        if not model.get("tags") or model["tags"] == ["Unknown"]: model["tags"] = self.generate_tags(model)
        if not model.get("description") or model["description"] == "No description available": model["description"] = self.generate_description(model)
        return model

    def estimate_model_size(self, model):
        model_id = model.get("id", "").lower()
        pipeline = model.get("pipeline_tag", "").lower()
        size_indicators = {"7b": "13.5GB", "13b": "26.0GB", "70b": "140.0GB", "2b": "1.5GB", "3b": "6.0GB", "6.7b": "12.8GB", "1.5b": "1.2GB", "0.5b": "400MB"}
        for ind, size in size_indicators.items():
            if ind in model_id: return size
        if pipeline in ["text-generation", "llm"]: return "~5-15GB"
        if pipeline in ["image-generation", "diffusion"]: return "~2-7GB"
        if pipeline in ["speech-recognition", "asr"]: return "~1-3GB"
        if pipeline in ["image-classification", "vision"]: return "~300-600MB"
        return "Unknown"

    def generate_tags(self, model):
        tags = []
        model_id = model.get("id", "").lower()
        pipeline = model.get("pipeline_tag", "")
        if pipeline: tags.append(pipeline.replace("-", " ").title())
        if "gguf" in model.get("format", "").lower(): tags.append("GGUF")
        if "onnx" in model.get("format", "").lower(): tags.append("ONNX")
        for key, value in {"llama": "LLaMA", "mistral": "Mistral", "phi": "Phi", "gemma": "Gemma", "deepseek": "DeepSeek", "bert": "BERT", "vit": "ViT", "resnet": "ResNet", "whisper": "Whisper"}.items():
            if key in model_id:
                tags.append(value)
                break
        return tags[:3] if tags else ["Model"]

    def generate_description(self, model):
        parts = []
        pipeline = model.get("pipeline_tag", "")
        format_info = model.get("format", "")
        model_id = model.get("id", "")
        if pipeline: parts.append(f"{pipeline.replace('-', ' ').title()} model")
        else: parts.append("Machine learning model")
        if "gguf" in format_info.lower(): parts.append("with GGUF quantization support")
        if "onnx" in format_info.lower(): parts.append("with ONNX compatibility")
        if "llama" in model_id.lower(): parts.append("from the LLaMA family")
        elif "mistral" in model_id.lower(): parts.append("from the Mistral family")
        return " ".join(parts) if parts else "Available on Hugging Face Hub"

    def format_file_size(self, size_bytes):
        if size_bytes <= 0: return "Unknown size", "unknown"
        if size_bytes >= 1024**4: return f"{size_bytes / (1024**4):.2f} TB", "large"
        if size_bytes >= 1024**3: return f"{size_bytes / (1024**3):.2f} GB", "large"
        if size_bytes >= 1024**2: return f"{size_bytes / (1024**2):.1f} MB", "medium"
        if size_bytes >= 1024: return f"{size_bytes / 1024:.0f} KB", "small"
        return f"{size_bytes} B", "small"

    def sort_models(self, models, sort_by):
        if sort_by == "downloads": return sorted(models, key=lambda x: x.get("downloads", 0), reverse=True)
        if sort_by == "likes": return sorted(models, key=lambda x: x.get("likes", 0), reverse=True)
        if sort_by == "trending": return sorted(models, key=lambda x: (x.get("downloads", 0) / (x.get("likes", 1) + 1)), reverse=True)
        return sorted(models, key=lambda x: x.get("downloads", 0), reverse=True)

    def filter_models(self, models, format_filter, search_query):
        filtered = models.copy()
        if format_filter != "all":
            filtered = [m for m in filtered if format_filter in m.get("format", "").lower()]
        if search_query:
            search_lower = search_query.lower()
            filtered = [m for m in filtered if search_lower in m.get("id", "").lower() or any(search_lower in tag.lower() for tag in m.get("tags", [])) or search_lower in m.get("description", "").lower()]
        return filtered

    def fetch_gated_model_questions(self, model_id):
        url = f"https://huggingface.co/api/models/{model_id}"
        headers = {"Accept": "application/json"}
        if self.access_token: headers["Authorization"] = f"Bearer {self.access_token}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        gated_info = data.get('gated', {})
        if isinstance(gated_info, dict):
            questions = gated_info.get('questions', [])
            if not questions and 'required_agreements' in gated_info:
                for agreement in gated_info.get('required_agreements', []):
                    questions.append(agreement.get('question', 'Do you agree to the terms?') if isinstance(agreement, dict) else f"Do you agree to {agreement}?")
            if not questions: questions = ["Do you accept the model's license terms?", "Do you agree to use this model responsibly?"]
            return {'questions': questions, 'terms': gated_info.get('terms', gated_info.get('description', 'Please read and accept the model license terms.')), 'instructions': gated_info.get('instructions', 'Please review the terms below.'), 'license_url': gated_info.get('license_url', '')}
        return {'questions': ["Do you accept the model's license terms?"], 'terms': 'Please read and accept the model license terms.', 'instructions': 'Review the terms below.', 'license_url': ''}


class HFDownload:
    def __init__(self, config, session, access_token=None):
        self.config = config
        self.session = session
        self.access_token = access_token
        self.downloading = False
        self.download_cancelled = False
        self.download_state = {}

    def is_file_identical(self, local_path, remote_size, remote_sha256=None):
        if not os.path.exists(local_path):
            return False
        local_size = os.path.getsize(local_path)
        if local_size != remote_size:
            return False
        if self.config.VERIFY_CHECKSUM and remote_sha256:
            sha256_hash = hashlib.sha256()
            with open(local_path, "rb") as f:
                for chunk in iter(lambda: f.read(self.config.BLOCK_SIZE), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest() == remote_sha256
        return True

    def start_download(self, model_id, model_info, download_dir, selected_files, progress_callback, log_callback, cancel_check, completion_callback):
        if self.downloading:
            return

        model_folder = model_id.replace('/', '_')
        download_path = os.path.join(download_dir, model_folder)
        self.downloading = True
        self.download_cancelled = False
        self.download_state = {'model_id': model_id, 'download_path': download_path, 'current_file': None, 'bytes_downloaded': 0}

        def download_thread():
            os.makedirs(download_path, exist_ok=True)
            log_callback(f"Downloading to: {download_path}")

            all_files = model_info.get("files", [])
            files_to_download = [f for f in all_files if f.get('filename') in selected_files]

            if not files_to_download:
                progress_callback(0, "No files selected for download")
                log_callback("No files selected for download")
                self.downloading = False
                completion_callback(success=False, message="No files selected")
                return

            total_files = len(files_to_download)
            downloaded_files = 0
            total_downloaded_bytes = 0
            total_file_sizes = sum(f.get('size', 0) for f in files_to_download)

            headers = {"User-Agent": self.config.USER_AGENT, "Accept": "*/*", "Accept-Encoding": "gzip, deflate, br", "Connection": "keep-alive"}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
                log_callback("Using Bearer token for authentication")

            for file_info in files_to_download:
                if self.download_cancelled or cancel_check():
                    completion_callback(success=False, message="Download cancelled")
                    self.downloading = False
                    return

                filename = file_info.get('filename')
                file_url = f"https://huggingface.co/{model_id}/resolve/main/{filename}"
                file_path = os.path.join(download_path, filename)
                self.download_state['current_file'] = filename

                file_size = file_info.get('size', 0)
                remote_sha256 = file_info.get('sha256')
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                if self.is_file_identical(file_path, file_size, remote_sha256):
                    log_callback(f"Skipping (identical): {filename}")
                    downloaded_files += 1
                    total_downloaded_bytes += file_size
                    final_progress = int((total_downloaded_bytes / total_file_sizes) * 100) if total_file_sizes > 0 else 100
                    progress_callback(final_progress, f"✓ {filename} skipped (identical)")
                    continue

                file_size_str, _ = self._format_file_size(file_size)
                log_callback(f"Downloading: {filename} ({file_size_str})")

                max_retries = self.config.MAX_RETRIES
                retry_count = 0
                downloaded_bytes = 0
                resume_pos = 0

                if os.path.exists(file_path):
                    resume_pos = os.path.getsize(file_path)
                    if resume_pos < file_size:
                        downloaded_bytes = resume_pos
                        log_callback(f"Resuming {filename} at {resume_pos} bytes")
                    else:
                        os.remove(file_path)
                        resume_pos = 0

                while retry_count < max_retries:
                    request_headers = headers.copy()
                    if resume_pos > 0 and resume_pos < file_size:
                        request_headers["Range"] = f"bytes={resume_pos}-"

                    response = self.session.get(file_url, stream=True, timeout=self.config.DOWNLOAD_TIMEOUT, headers=request_headers)
                    response.raise_for_status()

                    if resume_pos > 0 and response.status_code == 206:
                        log_callback(f"Resume successful: {response.headers.get('Content-Range', '')}")
                    elif resume_pos > 0 and response.status_code != 206:
                        resume_pos = 0
                        downloaded_bytes = 0
                        if os.path.exists(file_path): os.remove(file_path)

                    total_size = int(response.headers.get('content-length', 0))
                    if total_size == 0 and file_size > 0: total_size = file_size - resume_pos

                    mode = 'ab' if resume_pos > 0 else 'wb'
                    with open(file_path, mode) as f:
                        last_update_time = time.time()
                        last_downloaded_bytes = downloaded_bytes
                        for chunk in response.iter_content(chunk_size=self.config.BLOCK_SIZE):
                            if self.download_cancelled or cancel_check():
                                if os.path.exists(file_path): os.remove(file_path)
                                completion_callback(success=False, message="Download cancelled")
                                self.downloading = False
                                return

                            if chunk:
                                f.write(chunk)
                                downloaded_bytes += len(chunk)
                                total_downloaded_bytes += len(chunk)

                                current_time = time.time()
                                if current_time - last_update_time >= self.config.PROGRESS_UPDATE_INTERVAL:
                                    time_diff = current_time - last_update_time
                                    bytes_diff = downloaded_bytes - last_downloaded_bytes
                                    speed_mbps = (bytes_diff / time_diff) / (1024 * 1024) if time_diff > 0 else 0

                                    overall_progress = int((total_downloaded_bytes / total_file_sizes) * 100) if total_file_sizes > 0 else 0
                                    if overall_progress > 99: overall_progress = 99

                                    file_progress = int((downloaded_bytes / (file_size - resume_pos if file_size > resume_pos else 1)) * 100) if file_size > 0 else 0
                                    progress_msg = f"Downloading {filename}... {file_progress}% ({overall_progress}% total) | Speed: {speed_mbps:.2f} MB/s"
                                    progress_callback(overall_progress, progress_msg)

                                    last_update_time = current_time
                                    last_downloaded_bytes = downloaded_bytes

                    downloaded_files += 1
                    log_callback(f"Downloaded: {filename} ({downloaded_bytes} bytes)")
                    final_progress = int((downloaded_files / total_files) * 100)
                    progress_callback(final_progress, f"✓ {filename} downloaded")
                    break

            if not self.download_cancelled and not cancel_check():
                success_message = f"✅ Successfully downloaded {downloaded_files} files to:\n{download_path}\n\nModel: {model_id}"
                progress_callback(100, "Download complete!")
                log_callback(f"Download complete: {downloaded_files} files")
                log_callback(success_message)
                completion_callback(success=True, message=success_message)

            self.downloading = False

        threading.Thread(target=download_thread, daemon=True).start()

    def _format_file_size(self, size_bytes):
        if size_bytes <= 0: return "Unknown size", "unknown"
        if size_bytes >= 1024**4: return f"{size_bytes / (1024**4):.2f} TB", "large"
        if size_bytes >= 1024**3: return f"{size_bytes / (1024**3):.2f} GB", "large"
        if size_bytes >= 1024**2: return f"{size_bytes / (1024**2):.1f} MB", "medium"
        if size_bytes >= 1024: return f"{size_bytes / 1024:.0f} KB", "small"
        return f"{size_bytes} B", "small"


class HFBrowseGUI:
    def __init__(self, root):
        self.root = root
        self.core = HFBrowse()
        self.downloader = HFDownload(self.core.config, self.core.session, self.core.access_token)

        self.root.title(self.core.config.WINDOW_TITLE)
        if hasattr(self.core, 'window_x') and hasattr(self.core, 'window_y'):
            self.root.geometry(f"{self.core.config.WINDOW_WIDTH}x{self.core.config.WINDOW_HEIGHT}+{self.core.window_x}+{self.core.window_y}")
        else:
            self.root.geometry(f"{self.core.config.WINDOW_WIDTH}x{self.core.config.WINDOW_HEIGHT}")
        self.root.resizable(self.core.config.WINDOW_RESIZABLE, self.core.config.WINDOW_RESIZABLE)
        self.root.configure(bg=self.core.config.BG_MAIN)

        self.setup_styles()
        self.root.report_callback_exception = lambda *args: print(f"Tkinter Error: {args}")

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.load_models()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=self.core.config.TV_BG,
            foreground=self.core.config.TV_FG,
            fieldbackground=self.core.config.TV_BG,
            font=Config.get_font(size=10)
        )

        style.configure(
            "Treeview.Heading",
            background=self.core.config.TV_HEADING_BG,
            foreground=self.core.config.FG_HEADER,
            font=Config.get_font(size=10, weight="bold")
        )

        style.map(
            "Treeview",
            background=[("selected", self.core.config.TV_SELECT_BG)],
            foreground=[("selected", self.core.config.TV_SELECT_FG)]
        )

    def setup_ui(self):
        self.status_var = ctk.StringVar(value=self.core.config.MSG_READY)
        ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            font=Config.get_font(),
            text_color=self.core.config.FG_STATUS,
            fg_color=self.core.config.BG_STATUS,
            anchor="w"
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        main_frame = ctk.CTkFrame(self.root, fg_color=self.core.config.BG_MAIN)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        header_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        header_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
        ctk.CTkLabel(
            header_frame,
            text="Copyright Su Nie | BSD-3C License | https://github.com/can87683",
            font=Config.get_font(size=14, weight="bold"),
            text_color=self.core.config.FG_HEADER,
            anchor="center"
        ).pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        repo_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        repo_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        ctk.CTkButton(
            repo_frame,
            text="Local Repo Path",
            command=self.select_repo_path,
            width=120,
            fg_color=self.core.config.BTN_BG,
            text_color=self.core.config.BTN_FG,
            border_width=self.core.config.BTN_BORDER_WIDTH,
            border_color=self.core.config.BTN_BORDER,
            font=Config.get_font()
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.repo_path_var = ctk.StringVar(value=self.core.download_dir)
        ctk.CTkLabel(
            repo_frame,
            textvariable=self.repo_path_var,
            font=Config.get_font(),
            text_color=self.core.config.FG_BODY,
            anchor="w"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        search_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        search_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.search_var = ctk.StringVar(value=self.core.search_query)
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            font=Config.get_font(),
            fg_color=self.core.config.DROPDOWN_BG,
            text_color=self.core.config.DROPDOWN_FG
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
        search_entry.bind("<Return>", lambda e: self.search_models())

        ctk.CTkButton(
            search_frame,
            text=self.core.config.BTN_SEARCH,
            command=self.search_models,
            width=80,
            fg_color=self.core.config.BTN_BG,
            text_color=self.core.config.BTN_FG,
            border_width=self.core.config.BTN_BORDER_WIDTH,
            border_color=self.core.config.BTN_BORDER,
            font=Config.get_font()
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.clear_search_btn = ctk.CTkButton(
            search_frame,
            text=self.core.config.BTN_CLEAR,
            command=self.clear_search,
            state="disabled",
            width=60,
            fg_color=self.core.config.BTN_BG,
            text_color=self.core.config.BTN_FG,
            border_width=self.core.config.BTN_BORDER_WIDTH,
            border_color=self.core.config.BTN_BORDER,
            font=Config.get_font()
        )
        self.clear_search_btn.pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        filter_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        filter_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        ctk.CTkLabel(
            filter_frame,
            text="Format:",
            font=Config.get_font(),
            text_color=self.core.config.FG_BODY
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.format_var = ctk.StringVar(value=self.core.config.DEFAULT_FORMAT)
        ctk.CTkComboBox(
            filter_frame,
            variable=self.format_var,
            values=self.core.config.FORMAT_OPTIONS,
            state="readonly",
            width=100,
            fg_color=self.core.config.DROPDOWN_BG,
            text_color=self.core.config.DROPDOWN_FG,
            dropdown_fg_color=self.core.config.DROPDOWN_MENU_BG,
            dropdown_text_color=self.core.config.DROPDOWN_MENU_FG,
            font=Config.get_font(),
            command=lambda e: self.apply_filters_and_sort()
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        ctk.CTkLabel(
            filter_frame,
            text="Sort:",
            font=Config.get_font(),
            text_color=self.core.config.FG_BODY
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.sort_var = ctk.StringVar(value=self.core.sort_by)
        ctk.CTkComboBox(
            filter_frame,
            variable=self.sort_var,
            values=self.core.config.SORT_OPTIONS,
            state="readonly",
            width=100,
            fg_color=self.core.config.DROPDOWN_BG,
            text_color=self.core.config.DROPDOWN_FG,
            dropdown_fg_color=self.core.config.DROPDOWN_MENU_BG,
            dropdown_text_color=self.core.config.DROPDOWN_MENU_FG,
            font=Config.get_font(),
            command=lambda e: self.apply_filters_and_sort()
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        ctk.CTkLabel(
            filter_frame,
            text="Per page:",
            font=Config.get_font(),
            text_color=self.core.config.FG_BODY
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.page_size_var = ctk.StringVar(value=self.core.config.DEFAULT_PAGE_SIZE)
        ctk.CTkComboBox(
            filter_frame,
            variable=self.page_size_var,
            values=self.core.config.PAGE_SIZE_OPTIONS,
            state="readonly",
            width=60,
            fg_color=self.core.config.DROPDOWN_BG,
            text_color=self.core.config.DROPDOWN_FG,
            dropdown_fg_color=self.core.config.DROPDOWN_MENU_BG,
            dropdown_text_color=self.core.config.DROPDOWN_MENU_FG,
            font=Config.get_font(),
            command=lambda e: self.apply_filters_and_sort()
        ).pack(side=tk.LEFT, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        button_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        button_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        btn_kwargs = {
            "width": 10,
            "fg_color": self.core.config.BTN_BG,
            "text_color": self.core.config.BTN_FG,
            "border_width": self.core.config.BTN_BORDER_WIDTH,
            "border_color": self.core.config.BTN_BORDER,
            "font": Config.get_font()
        }

        self.download_btn = ctk.CTkButton(
            button_frame,
            text=self.core.config.BTN_DOWNLOAD,
            command=self.download_selected,
            state="disabled",
            **btn_kwargs
        )

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text=self.core.config.BTN_CANCEL,
            command=self.cancel_download,
            state="disabled",
            **btn_kwargs
        )

        self.open_btn = ctk.CTkButton(
            button_frame,
            text=self.core.config.BTN_OPEN,
            command=self.open_on_hf,
            state="disabled",
            **btn_kwargs
        )

        self.view_files_btn = ctk.CTkButton(
            button_frame,
            text=self.core.config.BTN_VIEW_FILES,
            command=self.view_model_files,
            state="disabled",
            **btn_kwargs
        )

        self.copy_url_btn = ctk.CTkButton(
            button_frame,
            text=self.core.config.BTN_COPY_URL,
            command=self.copy_model_url,
            state="disabled",
            **btn_kwargs
        )

        self.refresh_btn = ctk.CTkButton(
            button_frame,
            text=self.core.config.BTN_REFRESH,
            command=self.load_models,
            **btn_kwargs
        )

        action_buttons = [
            self.download_btn,
            self.cancel_btn,
            self.open_btn,
            self.view_files_btn,
            self.copy_url_btn,
            self.refresh_btn
        ]

        for col, btn in enumerate(action_buttons):
            button_frame.grid_columnconfigure(col, weight=1, uniform="action_buttons")
            btn.grid(
                row=0,
                column=col,
                sticky="nsew",
                padx=self.core.config.PADDING,
                pady=self.core.config.PADDING
            )

        button_frame.grid_rowconfigure(0, weight=1)

        list_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        columns = ("Name", "Format", "Downloads", "Likes", "Size", "Tags")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=self.core.config.TREEVIEW_HEIGHT,
            style="Treeview"
        )

        column_widths = {
            "Name": 200,
            "Format": 120,
            "Downloads": 80,
            "Likes": 60,
            "Size": 80,
            "Tags": 60
        }

        for col, width in column_widths.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, minwidth=int(width * 0.75))

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=self.core.config.PADDING,
            pady=self.core.config.PADDING
        )

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<MouseWheel>", self.on_mousewheel)
        self.tree.bind("<Button-4>", self.on_mousewheel)
        self.tree.bind("<Button-5>", self.on_mousewheel)
        self.tree.bind("<<TreeviewSelect>>", self.on_model_select)

        list_frame.bind("<MouseWheel>", self.on_mousewheel)
        list_frame.bind("<Button-4>", self.on_mousewheel)
        list_frame.bind("<Button-5>", self.on_mousewheel)

        progress_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.core.config.BG_FRAME,
            border_width=1,
            border_color=self.core.config.BTN_BORDER
        )
        progress_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        ctk.CTkLabel(
            progress_frame,
            text="Download Progress",
            font=Config.get_font(size=10, weight="bold"),
            text_color=self.core.config.FG_HEADER
        ).pack(anchor=tk.W, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.progress_var = ctk.StringVar(value="Ready to download")
        ctk.CTkLabel(
            progress_frame,
            textvariable=self.progress_var,
            font=Config.get_font(),
            text_color=self.core.config.FG_PROGRESS,
            anchor="w"
        ).pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            mode="determinate",
            progress_color=self.core.config.BTN_BG,
            fg_color=self.core.config.BG_LOG
        )
        self.progress_bar.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
        self.progress_bar.set(0)

        log_frame = ctk.CTkFrame(main_frame, fg_color=self.core.config.BG_FRAME)
        log_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.log_text = tk.Text(
            log_frame,
            height=self.core.config.LOG_HEIGHT_LINES,
            wrap=tk.WORD,
            bg=self.core.config.BG_LOG,
            fg=self.core.config.FG_LOG_NORMAL,
            font=Config.get_font(),
            insertbackground=self.core.config.FG_LOG_NORMAL,
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            padx=self.core.config.PADDING,
            pady=self.core.config.PADDING
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=self.core.config.PADDING, pady=self.core.config.PADDING)

        self.log_text.tag_configure("normal", foreground=self.core.config.FG_LOG_NORMAL)
        self.log_text.tag_configure("error", foreground=self.core.config.FG_LOG_ERROR)
        self.log_text.config(state=tk.DISABLED)

        self.log_text.bind("<MouseWheel>", self.on_log_mousewheel)
        self.log_text.bind("<Button-4>", self.on_log_mousewheel)
        self.log_text.bind("<Button-5>", self.on_log_mousewheel)

        log_frame.bind("<MouseWheel>", self.on_log_mousewheel)
        log_frame.bind("<Button-4>", self.on_log_mousewheel)
        log_frame.bind("<Button-5>", self.on_log_mousewheel)

    def on_mousewheel(self, event):
        if event.num == 4:
            self.tree.yview_scroll(-1, "units")
        elif event.num == 5:
            self.tree.yview_scroll(1, "units")
        else:
            self.tree.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def on_log_mousewheel(self, event):
        if event.num == 4:
            self.log_text.yview_scroll(-1, "units")
        elif event.num == 5:
            self.log_text.yview_scroll(1, "units")
        else:
            self.log_text.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def log_message(self, message, is_error=False):
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        tag = "error" if is_error else "normal"
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def on_mousewheel(self, event):
        if event.num == 4: self.tree.yview_scroll(-1, "units")
        elif event.num == 5: self.tree.yview_scroll(1, "units")
        else: self.tree.yview_scroll(-1 if event.delta < 0 else 1, "units")

    def load_models(self):
        self.status_var.set("Loading models from Hugging Face...")
        self.log_message("Loading models from Hugging Face...")
        self.root.update()

        def fetch_models_thread():
            format_filter = self.format_var.get()
            models = self.core.fetch_models_from_hf(self.core.search_query, format_filter)
            self.core.all_models = models
            self.core.filtered_models = models.copy()
            self.core.total_models = len(self.core.filtered_models)
            self.core.filtered_models = self.core.sort_models(self.core.filtered_models, self.sort_var.get())
            self.root.after(0, self.update_display)
            if self.core.total_models > 0:
                self.root.after(0, lambda: self.status_var.set(f"Loaded {self.core.total_models} models"))
                self.root.after(0, lambda: self.log_message(f"Loaded {self.core.total_models} models"))
            else:
                self.root.after(0, lambda: self.status_var.set("No models found"))
                self.root.after(0, lambda: self.log_message("No models found"))

        threading.Thread(target=fetch_models_thread, daemon=True).start()

    def apply_filters_and_sort(self):
        self.core.current_page = 0
        self.core.filtered_models = self.core.filter_models(self.core.all_models, self.format_var.get(), self.core.search_query)
        self.core.total_models = len(self.core.filtered_models)
        self.core.filtered_models = self.core.sort_models(self.core.filtered_models, self.sort_var.get())
        self.update_display()

    def update_display(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        if not self.core.filtered_models: return

        page_size = int(self.page_size_var.get())
        start = self.core.current_page * page_size
        end = min(start + page_size, len(self.core.filtered_models))
        page_models = self.core.filtered_models[start:end]

        for model in page_models:
            format_str = model.get("format", "unknown")
            format_parts = []
            if "gguf" in format_str.lower(): format_parts.append("🟢GGUF")
            if "onnx" in format_str.lower(): format_parts.append("🔵ONNX")
            if "pytorch" in format_str.lower() or "torch" in format_str.lower(): format_parts.append("🟣PyTorch")
            if "tensorflow" in format_str.lower(): format_parts.append("🟠TF")
            if "safetensors" in format_str.lower(): format_parts.append("🟡Safe")
            if not format_parts: format_parts = ["⚪Unknown"]
            format_display = " ".join(format_parts)
            if model.get('gated', False): format_display = "🔒 " + format_display

            tags = model.get("tags", ["Model"])
            if not tags or tags == ["Unknown"]: tags = ["Model"]
            tags_str = ", ".join(tags[:3])

            files = model.get('files', [])
            total_bytes = sum(f.get('size', 0) for f in files)
            size_str, _ = self.core.format_file_size(total_bytes) if total_bytes > 0 else (model.get("size", "Unknown"), "unknown")

            self.tree.insert("", "end", values=(model.get("id", "Unknown"), format_display, f"{model.get('downloads', 0):,}", f"❤️ {model.get('likes', 0)}", size_str, tags_str))

        self.core.models_cache = {m.get("id"): m for m in page_models}
        self.clear_search_btn.configure(state="normal" if self.core.search_query else "disabled")

    def search_models(self):
        self.core.search_query = self.search_var.get().strip()
        self.core.current_page = 0
        if self.core.search_query:
            self.status_var.set(f"Searching for '{self.core.search_query}'...")
            self.log_message(f"Searching for: {self.core.search_query}")
            self.load_models()
        else:
            self.clear_search()

    def clear_search(self):
        self.search_var.set("")
        self.core.search_query = ""
        self.core.current_page = 0
        self.clear_search_btn.configure(state="disabled")
        self.status_var.set("Cleared search - showing all models")
        self.log_message("Cleared search")
        self.load_models()

    def on_model_select(self, event):
        selection = self.tree.selection()
        if selection:
            self.download_btn.configure(state="normal")
            self.open_btn.configure(state="normal")
            self.view_files_btn.configure(state="normal")
            self.copy_url_btn.configure(state="normal")
            item = self.tree.item(selection[0])
            model_id = item["values"][0]
            model = self.core.models_cache.get(model_id, {})
            self.log_message(f"Selected: {model_id}")
            if model:
                files = model.get("files", [])
                total_size = sum(f.get('size', 0) for f in files)
                size_str, _ = self.core.format_file_size(total_size)
                self.log_message(f"  📊 Downloads: {model.get('downloads', 0):,} | ❤️ Likes: {model.get('likes', 0)}")
                self.log_message(f"  💾 Size: {size_str} | 📁 Files: {len(files)} | 🔒 Gated: {'Yes' if model.get('gated', False) else 'No'}")
                if files: self.log_message(f"  🔗 https://huggingface.co/{model_id}")
        else:
            self.download_btn.configure(state="disabled")
            self.open_btn.configure(state="disabled")
            self.view_files_btn.configure(state="disabled")
            self.copy_url_btn.configure(state="disabled")

    def open_on_hf(self):
        selection = self.tree.selection()
        if selection:
            model_id = self.tree.item(selection[0])["values"][0]
            url = f"https://huggingface.co/{model_id}"
            webbrowser.open(url)
            self.status_var.set(f"Opened {url}")
            self.log_message(f"Opened: {url}")

    def view_model_files(self):
        selection = self.tree.selection()
        if not selection: return
        model_id = self.tree.item(selection[0])["values"][0]
        model_info = self.core.models_cache.get(model_id, {})
        files = model_info.get("files", [])
        if not files:
            self.log_message(f"No files found for {model_id}")
            return
        self.log_message(f"📁 Files for {model_id}:")
        for file_info in files[:10]:
            filename = file_info.get('filename', 'unknown')
            size_str, _ = self.core.format_file_size(file_info.get('size', 0))
            format_type = file_info.get('format', 'unknown')
            is_model = file_info.get('is_model', False)
            line = f"  {'⭐ ' if is_model else '  '}{filename}"
            if format_type != 'unknown': line += f" [{format_type}]"
            line += f" - {size_str}"
            self.log_message(line)
        if len(files) > 10: self.log_message(f"  ... and {len(files)-10} more files")

    def copy_model_url(self):
        selection = self.tree.selection()
        if not selection: return
        model_id = self.tree.item(selection[0])["values"][0]
        url = f"https://huggingface.co/{model_id}"
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.root.update()
        self.status_var.set(f"URL copied: {url}")
        self.log_message(f"Copied URL: {url}")

    def select_repo_path(self):
        path = filedialog.askdirectory(title="Select Local Repo Path", parent=self.root)
        if path:
            self.core.download_dir = path
            self.repo_path_var.set(path)

    def download_selected(self):
        selection = self.tree.selection()
        if not selection or self.downloader.downloading: return

        item = self.tree.item(selection[0])
        model_id = item["values"][0]
        model_info = self.core.models_cache.get(model_id, {})

        if not model_info:
            self.log_message(f"Model info not found for {model_id}")
            self.status_var.set("Model information not found")
            return

        self.log_message(f"Starting download for: {model_id}")
        self.log_message(f"  Format: {model_info.get('format', 'Unknown')} | Gated: {'Yes' if model_info.get('gated', False) else 'No'}")

        if model_info.get('gated', False):
            if not self.core.logged_in:
                self.log_message(f"Gated model {model_id} requires login")
                self.status_var.set("Please login to access gated model")
                return
            self.show_gated_model_dialog(model_id, model_info)
            return

        self.status_var.set(f"Fetching file list for {model_id}...")
        self.log_message(f"Fetching file list for {model_id}...")
        self.root.update()

        def fetch_files_and_download():
            files = self.core.fetch_model_files(model_id)
            if files:
                model_info["files"] = files
                self.core.models_cache[model_id] = model_info
                all_filenames = [f.get('filename') for f in files if f.get('filename')]
                if all_filenames:
                    self.root.after(0, lambda: self.show_download_dialog(model_id, model_info, all_filenames))
                else:
                    self.root.after(0, lambda: self.show_no_files_dialog(model_id))
            else:
                self.root.after(0, lambda: self.show_no_files_dialog(model_id))

        threading.Thread(target=fetch_files_and_download, daemon=True).start()

    def show_download_dialog(self, model_id, model_info, all_filenames):
        files = model_info.get("files", [])
        if not files or not all_filenames:
            self.show_no_files_dialog(model_id)
            return

        download_dir = filedialog.askdirectory(title=f"Select download folder for {model_id} (all files)", initialdir=self.core.download_dir, parent=self.root)
        if not download_dir:
            self.log_message("Download cancelled - no folder selected")
            return

        self.core.download_dir = download_dir
        self.repo_path_var.set(download_dir)

        total_size = sum(f.get('size', 0) for f in files if f.get('filename') in all_filenames)
        total_str, _ = self.core.format_file_size(total_size)
        self.log_message(f"📦 Downloading {len(all_filenames)} files | 💾 Total size: {total_str} | 📁 Destination: {download_dir}")
        self.perform_download(model_id, model_info, download_dir, all_filenames)

    def show_no_files_dialog(self, model_id):
        self.log_message(f"No downloadable files found for {model_id}")
        self.status_var.set(f"No files found for {model_id}")

    def perform_download(self, model_id, model_info, download_dir, selected_files):
        if self.downloader.downloading: return

        def progress_callback(value, message):
            self.root.after(0, lambda v=value, m=message: self._update_progress(v, m))

        def log_callback(message, is_error=False):
            self.root.after(0, lambda m=message, err=is_error: self.log_message(m, is_error=err))

        def cancel_check():
            return self.downloader.download_cancelled

        def completion_callback(success, message):
            self.root.after(0, lambda s=success, m=message: self.download_complete(s, m))

        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.status_var.set(f"Downloading ALL files for {model_id}...")
        self.log_message(f"Starting download of {len(selected_files)} files...")
        self.progress_var.set(f"Downloading {model_id}...")
        self.progress_bar.set(0)

        self.downloader.start_download(
            model_id=model_id,
            model_info=model_info,
            download_dir=download_dir,
            selected_files=selected_files,
            progress_callback=progress_callback,
            log_callback=log_callback,
            cancel_check=cancel_check,
            completion_callback=completion_callback
        )

    def _update_progress(self, value, message):
        self.progress_bar.set(value / 100.0)
        self.progress_var.set(message)
        self.status_var.set(message[:100])
        self.root.update_idletasks()

    def cancel_download(self):
        if self.downloader.downloading:
            self.downloader.download_cancelled = True
            self.cancel_btn.configure(state="disabled")
            self.status_var.set("Cancelling download...")
            self.log_message("Cancelling download...")

    def download_complete(self, success, message):
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        if not success:
            self.progress_bar.set(0)
            self.log_message(f"Download failed: {message}", is_error=True)
            self.status_var.set("Download failed")
        else:
            self.progress_bar.set(1.0)
            self.log_message("Download complete!")
            self.status_var.set("Download complete!")
            self.log_message(message)

    def show_gated_model_dialog(self, model_id, model_info):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Access Required: {model_id}")
        dialog.geometry("700x650")
        dialog.transient(self.root)
        dialog.grab_set()

        gated_data = self.core.fetch_gated_model_questions(model_id)
        questions = gated_data.get('questions', [])
        terms = gated_data.get('terms', '')
        instructions = gated_data.get('instructions', '')
        license_url = gated_data.get('license_url', '')

        ctk.CTkFrame(dialog).pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
        ctk.CTkLabel(dialog, text="🔒 Gated Model Access Required", font=Config.get_font(size=14, weight="bold"), text_color=self.core.config.FG_HEADER).pack()
        ctk.CTkLabel(dialog, text=f"Model: {model_id}", font=Config.get_font(), text_color=self.core.config.FG_BODY).pack()

        if instructions:
            ctk.CTkLabel(dialog, text=instructions, font=Config.get_font(), text_color=self.core.config.FG_BODY, wraplength=650, justify=tk.LEFT).pack(pady=self.core.config.PADDING)

        if terms:
            terms_frame = ctk.CTkFrame(dialog, border_width=1, border_color=self.core.config.BTN_BORDER)
            terms_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
            ctk.CTkLabel(terms_frame, text="📋 Terms & Conditions", font=Config.get_font(size=14, weight="bold"), text_color=self.core.config.FG_HEADER).pack(anchor=tk.W, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
            terms_text = scrolledtext.ScrolledText(terms_frame, height=6, wrap=tk.WORD, font=Config.get_font(), bg=self.core.config.BG_LOG, fg=self.core.config.FG_LOG_NORMAL)
            terms_text.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
            terms_text.insert(tk.END, terms)
            terms_text.config(state=tk.DISABLED)

        if license_url:
            ctk.CTkLabel(dialog, text=f"📄 License: {license_url}", font=Config.get_font(), text_color="#4da6ff").pack(pady=self.core.config.PADDING)

        question_frame = ctk.CTkFrame(dialog, border_width=1, border_color=self.core.config.BTN_BORDER)
        question_frame.pack(fill=tk.X, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
        ctk.CTkLabel(question_frame, text="✅ Required Agreements", font=Config.get_font(size=14, weight="bold"), text_color=self.core.config.FG_HEADER).pack(anchor=tk.W, padx=self.core.config.PADDING, pady=self.core.config.PADDING)
        question_vars = {}
        for question in questions:
            var = tk.BooleanVar(value=False)
            question_vars[question] = var
            q_frame = ctk.CTkFrame(question_frame, fg_color="transparent")
            q_frame.pack(anchor=tk.W, pady=self.core.config.PADDING, padx=self.core.config.PADDING)
            tk.Checkbutton(q_frame, text=question, variable=var, font=Config.get_font(), bg=self.core.config.BG_MAIN, fg=self.core.config.FG_BODY, wraplength=600, justify=tk.LEFT).pack(anchor=tk.W)

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=self.core.config.PADDING)

        def agree_and_proceed():
            unanswered = [q for q, var in question_vars.items() if not var.get()]
            if unanswered:
                self.log_message(f"Unanswered questions for {model_id}")
                self.status_var.set("Please answer all questions")
                return
            dialog.destroy()
            self.proceed_with_download(model_id, model_info)

        btn_kwargs = {"fg_color": self.core.config.BTN_BG, "text_color": self.core.config.BTN_FG,
                      "border_width": self.core.config.BTN_BORDER_WIDTH, "border_color": self.core.config.BTN_BORDER,
                      "font": Config.get_font()}
        ctk.CTkButton(button_frame, text="✓ Agree and Proceed", command=agree_and_proceed, width=140, **btn_kwargs).pack(side=tk.LEFT, padx=self.core.config.PADDING)
        ctk.CTkButton(button_frame, text="🌐 Open Model Page", command=lambda: webbrowser.open(f"https://huggingface.co/{model_id}"), width=120, **btn_kwargs).pack(side=tk.LEFT, padx=self.core.config.PADDING)
        ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy, width=80, **btn_kwargs).pack(side=tk.LEFT, padx=self.core.config.PADDING)

    def proceed_with_download(self, model_id, model_info):
        self.status_var.set(f"Fetching file list for {model_id}...")
        self.log_message(f"Fetching file list for {model_id}...")
        self.root.update()

        def fetch_files_and_download():
            files = self.core.fetch_model_files(model_id)
            if files:
                model_info["files"] = files
                self.core.models_cache[model_id] = model_info
                all_filenames = [f.get('filename') for f in files if f.get('filename')]
                if all_filenames:
                    self.root.after(0, lambda: self.show_download_dialog(model_id, model_info, all_filenames))
                else:
                    self.root.after(0, lambda: self.show_no_files_dialog(model_id))
            else:
                self.root.after(0, lambda: self.show_no_files_dialog(model_id))

        threading.Thread(target=fetch_files_and_download, daemon=True).start()

    def on_closing(self):
        if self.downloader.downloading:
            if not messagebox.askokcancel("Download in Progress", "A download is currently in progress.\n\nAre you sure you want to quit?\nThe download will be interrupted.", icon='warning', parent=self.root):
                return
        if messagebox.askokcancel("Exit Application", "Are you sure you want to exit?\n\nYour position and settings will be saved.", icon='question', parent=self.root):
            self.core.is_closing = True
            geo_x, geo_y = self.root.geometry().split('+')[1:]
            self.core.save_config(int(geo_x), int(geo_y))
            self.root.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = HFBrowseGUI(root)
    root.mainloop()