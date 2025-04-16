# gui_home_settings.py
import customtkinter as ctk
from tkinter import messagebox
import webbrowser

def create_home_settings_tabs(app):
    """Cria as abas 'Início' e 'Configurações'"""
    app.tab_view.add("Início")
    app.tab_view.add("Configurações")
    
    # --- Aba Início ---
    tab_home = app.tab_view.tab("Início")
    tab_home.grid_columnconfigure(0, weight=1)
    
    app.info_frame = ctk.CTkFrame(tab_home, corner_radius=app.config.get("ui_corner_radius", 10))
    app.info_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    app.info_frame.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(app.info_frame, text="Token API:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    app.home_token_label = ctk.CTkLabel(app.info_frame, text=app.config.get("bot_token", "N/A"), wraplength=500)
    app.home_token_label.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    
    ctk.CTkLabel(app.info_frame, text="ID do Grupo:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    app.home_group_label = ctk.CTkLabel(app.info_frame, text=app.config.get("group_id", "N/A"))
    app.home_group_label.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
    
    ctk.CTkLabel(app.info_frame, text="Instagram:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
    app.home_insta_label = ctk.CTkLabel(app.info_frame, 
                                      text=app.config.get("instagram_url", "N/A"),
                                      text_color="lightblue",
                                      cursor="hand2")
    app.home_insta_label.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
    app.home_insta_label.bind("<Button-1>", lambda e: webbrowser.open_new(app.config.get("instagram_url")))
    
    ctk.CTkLabel(app.info_frame, text="TikTok:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
    app.home_tiktok_label = ctk.CTkLabel(app.info_frame, 
                                       text=app.config.get("tiktok_url", "N/A"),
                                       text_color="lightblue",
                                       cursor="hand2")
    app.home_tiktok_label.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
    app.home_tiktok_label.bind("<Button-1>", lambda e: webbrowser.open_new(app.config.get("tiktok_url")))
    
    # --- Aba Configurações ---
    tab_settings = app.tab_view.tab("Configurações")
    tab_settings.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(tab_settings, text="Token API Bot:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    app.token_entry = ctk.CTkEntry(tab_settings, width=450)
    app.token_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    app.token_entry.insert(0, app.config.get("bot_token", ""))
    
    ctk.CTkLabel(tab_settings, text="ID do Grupo:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    app.group_id_entry = ctk.CTkEntry(tab_settings, width=450)
    app.group_id_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
    app.group_id_entry.insert(0, app.config.get("group_id", ""))
    
    ctk.CTkLabel(tab_settings, text="URL Instagram:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
    app.insta_entry = ctk.CTkEntry(tab_settings, width=450)
    app.insta_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
    app.insta_entry.insert(0, app.config.get("instagram_url", ""))
    
    ctk.CTkLabel(tab_settings, text="URL TikTok:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
    app.tiktok_entry = ctk.CTkEntry(tab_settings, width=450)
    app.tiktok_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
    app.tiktok_entry.insert(0, app.config.get("tiktok_url", ""))
    
    ctk.CTkLabel(tab_settings, text="Mensagem Boas-Vindas:").grid(row=4, column=0, padx=10, pady=5, sticky="nw")
    app.welcome_textbox = ctk.CTkTextbox(tab_settings, height=120, wrap="word")
    app.welcome_textbox.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
    app.welcome_textbox.insert("1.0", app.config.get("welcome_message", ""))
    
    # Botão de salvar
    save_button = ctk.CTkButton(tab_settings, 
                              text="Salvar Configurações", 
                              command=app.save_settings)
    save_button.grid(row=6, column=0, columnspan=2, padx=10, pady=20)

def save_settings(app):
    """Salva as configurações na classe App"""
    app.config["bot_token"] = app.token_entry.get()
    app.config["group_id"] = app.group_id_entry.get()
    app.config["instagram_url"] = app.insta_entry.get()
    app.config["tiktok_url"] = app.tiktok_entry.get()
    app.config["welcome_message"] = app.welcome_textbox.get("1.0", "end-1c")
    
    # Atualiza a interface
    app.home_token_label.configure(text=app.config["bot_token"])
    app.home_group_label.configure(text=app.config["group_id"])
    app.home_insta_label.configure(text=app.config["instagram_url"])
    app.home_tiktok_label.configure(text=app.config["tiktok_url"])
    
    # Atualiza links
    app.home_insta_label.bind("<Button-1>", lambda e: webbrowser.open_new(app.config["instagram_url"]))
    app.home_tiktok_label.bind("<Button-1>", lambda e: webbrowser.open_new(app.config["tiktok_url"]))
    
    messagebox.showinfo("Salvo", "Configurações salvas com sucesso!")
    app.update_console("Configurações salvas. Reinicie o bot se necessário.")