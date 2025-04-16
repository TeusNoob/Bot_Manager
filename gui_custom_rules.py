# gui_custom_rules.py
import customtkinter as ctk
from tkinter import messagebox

def create_custom_rules_tab(app):
    """Cria as abas 'Personalizar' e 'Regras'"""
    app.tab_view.add("Personalizar")
    app.tab_view.add("Regras")
    
    # --- Aba Personalizar ---
    tab_custom = app.tab_view.tab("Personalizar")
    tab_custom.grid_columnconfigure(1, weight=1)
    
    # Tema
    ctk.CTkLabel(tab_custom, text="Tema da Interface:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
    app.theme_menu = ctk.CTkOptionMenu(tab_custom, 
                                     values=["Light", "Dark", "System"], 
                                     command=app.change_theme)
    app.theme_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    app.theme_menu.set(app.config.get("theme", "System"))
    
    # Cores
    color_options = [
        ("Cor Principal (Botões):", "ui_primary_color", "#3B8ED0"),
        ("Cor do Texto (Geral):", "ui_text_color", "#1F1F1F"),
        ("Cor Texto dos Botões:", "ui_button_text_color", "#FFFFFF")
    ]
    
    for i, (label, config_key, default) in enumerate(color_options, start=1):
        ctk.CTkLabel(tab_custom, text=label).grid(row=i, column=0, padx=10, pady=10, sticky="w")
        btn = ctk.CTkButton(tab_custom, 
                           text="Escolher Cor", 
                           command=lambda k=config_key: app.choose_color(k))
        btn.grid(row=i, column=1, padx=10, pady=10, sticky="w")
        
        # Preview da cor
        preview = ctk.CTkFrame(tab_custom, width=50, height=30, border_width=1)
        preview.configure(fg_color=app.config.get(config_key, default))
        preview.grid(row=i, column=2, padx=10, pady=10, sticky="w")
        setattr(app, f"{config_key}_preview", preview)
    
    # Raio dos cantos
    ctk.CTkLabel(tab_custom, text="Raio dos Cantos (Widgets):").grid(row=4, column=0, padx=10, pady=10, sticky="w")
    app.corner_radius_slider = ctk.CTkSlider(tab_custom, from_=0, to=20, number_of_steps=20,
                                            command=lambda v: app.corner_radius_label.configure(text=f"{int(v)}px"))
    app.corner_radius_slider.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
    app.corner_radius_label = ctk.CTkLabel(tab_custom, text=f"{app.config.get('ui_corner_radius', 10)}px")
    app.corner_radius_label.grid(row=4, column=2, padx=10, pady=10, sticky="w")
    app.corner_radius_slider.set(app.config.get("ui_corner_radius", 10))
    
    # Botão aplicar
    ctk.CTkButton(tab_custom,
                 text="Aplicar e Salvar Estilos",
                 command=app.apply_and_save_styles).grid(row=5, column=0, columnspan=3, padx=10, pady=20)
    
    # --- Aba Regras ---
    tab_rules = app.tab_view.tab("Regras")
    tab_rules.grid_columnconfigure(1, weight=1)
    create_rules_tab(app, tab_rules)

def create_rules_tab(app, tab):
    """Preenche a aba de Regras"""
    rules = app.config.get("rules", {})
    app.rule_vars = {}
    app.rule_widgets = []
    
    rule_configs = [
        ("block_profanity", "Bloquear Palavrões/Ofensas e Banir", None),
        ("profanity_list", "Palavras Bloqueadas (separadas por vírgula):", ",".join(rules.get("profanity_list", []))),
        ("block_off_topic", "Apagar Mensagens Fora de Tópico", None),
        ("allowed_topics_keywords", "Palavras-chave do Tópico (separadas por vírgula):", ",".join(rules.get("allowed_topics_keywords", []))),
        ("block_links", "Apagar Mensagens com Links", None),
        ("allow_only_pdf", "Permitir Apenas Arquivos PDF", None),
        ("block_spam_flood", "Bloquear Spam/Flood e Banir", None),
        ("spam_message_limit", "Limite de Mensagens (Spam):", str(rules.get("spam_message_limit", 5))),
        ("spam_time_limit_sec", "Janela de Tempo (segundos, Spam):", str(rules.get("spam_time_limit_sec", 10)))
    ]
    
    for i, (key, label, default) in enumerate(rule_configs):
        if default is None:  # Checkbox
            var = ctk.StringVar(value="on" if rules.get(key) else "off")
            cb = ctk.CTkCheckBox(tab, text=label, variable=var, onvalue="on", offvalue="off")
            cb.grid(row=i, column=0, columnspan=2, padx=10, pady=5, sticky="w")
            app.rule_vars[key] = var
            app.rule_widgets.append(cb)
        else:  # Entry
            ctk.CTkLabel(tab, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(tab)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            entry.insert(0, default)
            app.rule_vars[key] = entry
            app.rule_widgets.append(entry)

    # Botão salvar regras
    ctk.CTkButton(tab,
                 text="Salvar Regras",
                 command=lambda: save_rules(app)).grid(row=len(rule_configs)+1, column=0, columnspan=2, padx=10, pady=20)

def save_rules(app):
    """Salva as configurações de regras"""
    try:
        rules = {}
        rules["block_profanity"] = app.rule_vars["block_profanity"].get() == "on"
        rules["profanity_list"] = [w.strip() for w in app.rule_vars["profanity_list"].get().split(',') if w.strip()]
        rules["block_off_topic"] = app.rule_vars["block_off_topic"].get() == "on"
        rules["allowed_topics_keywords"] = [w.strip() for w in app.rule_vars["allowed_topics_keywords"].get().split(',') if w.strip()]
        rules["block_links"] = app.rule_vars["block_links"].get() == "on"
        rules["allow_only_pdf"] = app.rule_vars["allow_only_pdf"].get() == "on"
        rules["block_spam_flood"] = app.rule_vars["block_spam_flood"].get() == "on"
        rules["spam_message_limit"] = int(app.rule_vars["spam_message_limit"].get())
        rules["spam_time_limit_sec"] = int(app.rule_vars["spam_time_limit_sec"].get())
        
        app.config["rules"] = rules
        save_config(app.config)
        messagebox.showinfo("Salvo", "Regras atualizadas com sucesso!")
        app.update_console("Regras salvas. Reinicie o bot se necessário.")
    except ValueError:
        messagebox.showerror("Erro", "Valores inválidos para limites de spam")
        app.update_console("ERRO: Valores inválidos para limites de spam")