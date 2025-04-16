# gui_console.py (parte 4/4)
import customtkinter as ctk
from tkinter import messagebox

def create_console_tab(app):
    """Cria a aba 'Console'"""
    app.tab_view.add("Console")
    tab_console = app.tab_view.tab("Console")
    
    # Configura layout
    tab_console.grid_columnconfigure(0, weight=1)
    tab_console.grid_rowconfigure(0, weight=1)
    
    # Console de log
    app.console_textbox = ctk.CTkTextbox(tab_console, state="disabled", wrap="word")
    app.console_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    
    # Botão limpar console
    ctk.CTkButton(tab_console,
                 text="Limpar Console",
                 command=lambda: clear_console(app)).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

def clear_console(app):
    """Limpa o conteúdo do console"""
    app.console_textbox.configure(state="normal")
    app.console_textbox.delete("1.0", "end")
    app.console_textbox.configure(state="disabled")
    app.update_console("--- Console limpo ---")

# Funções auxiliares que precisam ser acessadas pela classe principal
def apply_custom_styles(app):
    """Aplica os estilos personalizados"""
    primary_color = app.config.get("ui_primary_color", "#3B8ED0")
    text_color = app.config.get("ui_text_color")
    button_text_color = app.config.get("ui_button_text_color")
    corner_radius = app.config.get("ui_corner_radius", 10)
    
    # Atualiza widgets principais
    for widget in [app.start_button, app.stop_button]:
        widget.configure(fg_color=primary_color, corner_radius=corner_radius)
        if button_text_color:
            widget.configure(text_color=button_text_color)
    
    # Atualiza previews de cor
    if hasattr(app, 'primary_color_preview'):
        app.primary_color_preview.configure(fg_color=primary_color)
    if hasattr(app, 'text_color_preview'):
        app.text_color_preview.configure(fg_color=text_color)
    if hasattr(app, 'button_text_color_preview'):
        app.button_text_color_preview.configure(fg_color=button_text_color)
    
    # Atualiza label do slider
    if hasattr(app, 'corner_radius_label'):
        app.corner_radius_label.configure(text=f"{corner_radius}px")

def change_theme(app, new_theme):
    """Muda o tema da aplicação"""
    ctk.set_appearance_mode(new_theme)
    app.config["theme"] = new_theme

def apply_and_save_styles(app):
    """Aplica e salva os estilos"""
    app.config["ui_corner_radius"] = int(app.corner_radius_slider.get())
    apply_custom_styles(app)
    messagebox.showinfo("Estilos Salvos", "Configurações aplicadas com sucesso!")