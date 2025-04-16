# config_manager.py
import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    # Configurações do Bot
    "bot_token": "SEU_TOKEN_AQUI", # Substitua pelo token do seu bot
    "group_id": "SEU_GROUP_ID_AQUI", # Substitua pelo ID do seu grupo (ex: -1001234567890)
    "instagram_url": "https://instagram.com/seu_perfil",
    "tiktok_url": "https://tiktok.com/@seu_perfil",
    "welcome_message": "Olá {user}! Bem-vindo(a) ao grupo! Por favor, siga nossos perfis:\nInstagram: {insta}\nTikTok: {tiktok}\n\nClique em 'Já segui' abaixo quando terminar.",

    # Configurações da Interface (Personalizar)
    "theme": "System", # System, Light, Dark
    "ui_primary_color": "#3B8ED0", # Azul padrão do CustomTkinter
    "ui_secondary_color": "#DCE4EE", # Cor de texto padrão (claro) - Pode ser menos eficaz dependendo do tema
    "ui_text_color": "#1F1F1F", # Cor de texto principal (para modo claro)
    "ui_button_text_color": "#FFFFFF", # Cor do texto nos botões principais
    "ui_corner_radius": 10, # Raio dos cantos para widgets principais (ex: botões, frames)

    # Regras do Bot
    "rules": {
        "block_profanity": True,
        "profanity_list": ["palavra1", "palavra2", "xingamento"], # Adicione palavras a bloquear
        "block_off_topic": True,
        "allowed_topics_keywords": ["papelaria", "personalizados", "arte digital", "caneta", "adesivo", "planner"], # Palavras-chave do tema
        "block_links": True,
        "allow_only_pdf": True,
        "block_spam_flood": True,
        "spam_message_limit": 5, # Máximo de mensagens
        "spam_time_limit_sec": 10 # Em segundos
    },

    # Estado Interno (não editável diretamente pela GUI usualmente)
    "bot_status": "Stopped" # Estado inicial do bot
}

def load_config():
    """Carrega as configurações do arquivo JSON."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Arquivo '{CONFIG_FILE}' não encontrado. Criando com valores padrão.")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy() # Retorna uma cópia para evitar modificação acidental do default

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Garante que todas as chaves e subchaves padrão existam
            updated = False
            for key, default_value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = default_value
                    updated = True
                elif isinstance(default_value, dict):
                    # Verifica sub-dicionários (como 'rules')
                    for sub_key, default_sub_value in default_value.items():
                        if sub_key not in config[key]:
                            config[key][sub_key] = default_sub_value
                            updated = True
                # Garante que as novas chaves de UI existam
                elif key.startswith("ui_") and key not in config:
                     config[key] = default_value
                     updated = True


            if updated:
                print("Configuração atualizada com novas chaves padrão.")
                save_config(config) # Salva se adicionou chaves faltantes
            return config
    except json.JSONDecodeError:
        print(f"Erro ao decodificar '{CONFIG_FILE}'. Usando valores padrão.")
        # Opcional: fazer backup do arquivo corrompido
        # os.rename(CONFIG_FILE, CONFIG_FILE + ".corrupted")
        save_config(DEFAULT_CONFIG) # Sobrescreve com padrão se corrompido
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"Erro inesperado ao carregar config: {e}. Usando valores padrão.")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config_data):
    """Salva as configurações no arquivo JSON."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar config: {e}")

# Exemplo de como usar:
# if __name__ == "__main__":
#     config = load_config()
#     print("Configuração carregada:", config)
#     config["bot_token"] = "novo_token_teste" # Modifica algo
#     save_config(config) # Salva a modificação
#     print(f"Configuração salva em '{CONFIG_FILE}'.")
