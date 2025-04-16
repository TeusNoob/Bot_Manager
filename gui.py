# gui.py
import customtkinter as ctk
from tkinter import messagebox, colorchooser
import threading
import queue
import logging
from config_manager import load_config, save_config

# Definição do GuiHandler
class GuiHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)

# Classe principal da interface gráfica
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.bot_instance = None
        self.log_queue = queue.Queue()
        
        self.title("Bot Manager")
        self.geometry("750x650")
        ctk.set_appearance_mode(self.config.get("theme", "System"))
        
        # Estrutura principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Frame de status
        self.status_frame = ctk.CTkFrame(self, corner_radius=self.config.get("ui_corner_radius", 10))
        self.status_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Status do Bot: Parado", font=ctk.CTkFont(weight="bold"))
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.status_indicator = ctk.CTkLabel(self.status_frame, text="●", text_color="red", font=ctk.CTkFont(size=20))
        self.status_indicator.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.start_button = ctk.CTkButton(self.status_frame, text="Iniciar Bot", command=self.start_bot_thread)
        self.start_button.grid(row=0, column=2, padx=10, pady=5)
        
        self.stop_button = ctk.CTkButton(self.status_frame, text="Parar Bot", command=self.stop_bot_thread, state="disabled")
        self.stop_button.grid(row=0, column=3, padx=10, pady=5)
        
        # Label para exibir erros
        self.error_label = ctk.CTkLabel(self, text="", text_color="red", wraplength=730)
        self.error_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Importa e cria as abas dos outros arquivos
        from gui_home_settings import create_home_settings_tabs
        from gui_custom_rules import create_custom_rules_tab
        from gui_console import create_console_tab
        
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Cria todas as abas
        create_home_settings_tabs(self)
        create_custom_rules_tab(self)
        create_console_tab(self)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.process_log_queue)

    # Métodos principais
    def process_log_queue(self):
        try:
            while True:
                log_entry = self.log_queue.get_nowait()
                self.update_console(log_entry)
        except queue.Empty:
            pass
        finally:
            self.after(200, self.process_log_queue)

    def update_console(self, message: str):
        if hasattr(self, 'console_textbox'):
            self.console_textbox.configure(state="normal")
            self.console_textbox.insert("end", message + "\n")
            self.console_textbox.see("end")
            self.console_textbox.configure(state="disabled")

    def update_bot_status(self, status: str):
        status_map = {
            "Stopped": "Parado",
            "Starting": "Iniciando...",
            "Running": "Em Execução",
            "Stopping": "Parando...",
            "Error": "Erro"
        }
        display_status = status_map.get(status, status)
        
        self.config["bot_status"] = status
        self.status_label.configure(text=f"Status do Bot: {display_status}")
        
        if status == "Running":
            self.status_indicator.configure(text_color="green")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        elif status in ["Starting", "Stopping"]:
            self.status_indicator.configure(text_color="orange")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
        elif status == "Error":
            self.status_indicator.configure(text_color="red")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
        else:
            self.status_indicator.configure(text_color="red")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def save_settings(self):
        """Método que delega para a função em gui_home_settings.py"""
        from gui_home_settings import save_settings
        save_settings(self)

    def change_theme(self, new_theme: str):
        """Muda o tema da aplicação"""
        ctk.set_appearance_mode(new_theme)
        self.config["theme"] = new_theme

    def choose_color(self, config_key: str):
        """Abre o seletor de cores"""
        initial_color = self.config.get(config_key)
        color_code = colorchooser.askcolor(initialcolor=initial_color)
        if color_code and color_code[1]:
            self.config[config_key] = color_code[1]
            getattr(self, f"{config_key}_preview").configure(fg_color=color_code[1])

    def apply_custom_styles(self):
        """Aplica os estilos personalizados"""
        primary_color = self.config.get("ui_primary_color", "#3B8ED0")
        text_color = self.config.get("ui_text_color")
        button_text_color = self.config.get("ui_button_text_color")
        corner_radius = self.config.get("ui_corner_radius", 10)
        
        # Atualiza widgets principais
        for widget in [self.start_button, self.stop_button]:
            widget.configure(fg_color=primary_color, corner_radius=corner_radius)
            if button_text_color:
                widget.configure(text_color=button_text_color)
        
        # Atualiza outros widgets conforme necessário
        widgets_to_style = [
            self.status_frame, self.tab_view,
            getattr(self, 'info_frame', None),
            getattr(self, 'welcome_textbox', None),
            getattr(self, 'console_textbox', None)
        ]
        
        for widget in widgets_to_style:
            if widget and hasattr(widget, 'configure'):
                widget.configure(corner_radius=corner_radius)

    def apply_and_save_styles(self):
        """Aplica e salva os estilos"""
        self.config["ui_corner_radius"] = int(getattr(self, 'corner_radius_slider').get())
        self.apply_custom_styles()
        save_config(self.config)
        messagebox.showinfo("Estilos Salvos", "Configurações aplicadas com sucesso!")
        self.update_console("Estilos da interface atualizados.")

    def start_bot_thread(self):
        self.error_label.configure(text="")
        self.update_console("--- Iniciando Bot ---")
        
        # Adiar a importação para evitar importação circular
        from telegram_bot import TelegramBot
        
        self.bot_instance = TelegramBot(
            self.config.copy(),
            status_callback=self.update_bot_status,
            error_callback=self.report_error_gui,
            log_queue=self.log_queue
        )
        thread = threading.Thread(target=self.bot_instance.start_bot, daemon=True)
        thread.start()

    def stop_bot_thread(self):
        self.error_label.configure(text="")
        self.update_console("--- Solicitando Parada do Bot ---")
        if self.bot_instance:
            thread = threading.Thread(target=self.bot_instance.stop_bot, daemon=True)
            thread.start()
        else:
            self.update_bot_status("Stopped")
            self.update_console("--- Bot já estava parado ---")

    def on_closing(self):
        if self.bot_instance and self.bot_instance.running:
            if messagebox.askyesno("Sair", "O bot está em execução. Deseja pará-lo antes de sair?"):
                self.stop_bot_thread()
                self.after(2000, self.destroy)
        else:
            self.destroy()

    def report_error_gui(self, message: str):
        def _update():
            self.error_label.configure(text=f"Erro Crítico: {message}")
        self.after(0, _update)