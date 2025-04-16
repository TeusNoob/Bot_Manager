# main.py
import customtkinter as ctk
from gui import App # Importa a classe da GUI
import sys # Para verificar se está rodando como script ou congelado (PyInstaller)
import os

# Define o diretório base (útil para PyInstaller)
if getattr(sys, 'frozen', False):
    # Se rodando em um bundle PyInstaller
    base_dir = sys._MEIPASS # type: ignore
else:
    # Se rodando como script normal
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Opcional: Adicionar o diretório base ao path se necessário para encontrar módulos
# sys.path.insert(0, base_dir)

# Opcional: Configurar logging para um arquivo (além do console)
# import logging
# log_file = os.path.join(base_dir, "bot_manager.log")
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     handlers=[logging.FileHandler(log_file), logging.StreamHandler()])


if __name__ == "__main__":
    # Linha removida: ctk.set_ctk_parent_class(ctk.CTk)
    # A inicialização padrão do CustomTkinter geralmente funciona bem.

    # Cria e executa a aplicação GUI
    app = App()
    app.mainloop()
