# telegram_bot.py
import asyncio
import threading
import logging
from collections import defaultdict
from telegram.ext import Application, CallbackQueryHandler, ChatMemberHandler, MessageHandler, filters

class TelegramBot:
    """Classe completa para gerenciar o bot do Telegram."""

    def __init__(self, config, status_callback=None, error_callback=None, log_queue=None):
        """Inicializa o bot com configurações."""
        self.config = config
        self.application = None
        self.bot_thread = None
        self.stop_event = threading.Event()
        self.status_callback = status_callback
        self.error_callback = error_callback
        self.log_queue = log_queue
        self.running = False
        self.loop = None

        # Configuração do logger
        self._setup_logger()

    def _setup_logger(self):
        """Configura o sistema de logging."""
        self.logger = logging.getLogger(f"BotManager_{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        if self.log_queue:
            from gui import GuiHandler
            
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
            gui_handler = GuiHandler(self.log_queue)
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)
        else:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def start_bot(self):
        """Inicia o bot em uma nova thread."""
        if self.running:
            self._log("Bot já está em execução.")
            return

        if not self._validate_config():
            return

        try:
            self.stop_event.clear()
            self.bot_thread = threading.Thread(target=self._run_wrapper, daemon=True)
            self.bot_thread.start()
            self._log("Bot iniciado em thread separada")
        except Exception as e:
            self._report_error(f"Falha ao iniciar thread: {str(e)}")
            self._update_status("Error")

    def _validate_config(self):
        """Valida as configurações necessárias."""
        if not self.config.get("bot_token") or self.config.get("bot_token") == "SEU_TOKEN_AQUI":
            self._report_error("Token do Bot não configurado")
            self._update_status("Error")
            return False
        return True

    def _run_wrapper(self):
        """Wrapper para executar o loop asyncio."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_bot_async())
        except Exception as e:
            self._report_error(f"Erro na thread do bot: {str(e)}")
        finally:
            self._cleanup_resources()

    async def _run_bot_async(self):
        """Configura e executa o bot no loop asyncio."""
        try:
            self._update_status("Starting")
            builder = Application.builder().token(self.config["bot_token"])
            self.application = builder.build()
            
            self._setup_handlers()
            
            await self.application.initialize()  # Inicializa o bot

            # Envia mensagem de confirmação ao grupo
            group_id = self.config.get("group_id")
            if group_id:
                try:
                    await self.application.bot.send_message(
                        chat_id=group_id,
                        text="🤖 Bot iniciado com sucesso! Estou online e pronto para ajudar."
                    )
                    self._log(f"Mensagem de início enviada ao grupo com ID {group_id}")
                except Exception as e:
                    self._report_error(f"Falha ao enviar mensagem de início ao grupo: {str(e)}")
            
            self.running = True
            self._update_status("Running")
            
            # Executa o polling enquanto o stop_event não for definido
            while not self.stop_event.is_set():
                await asyncio.sleep(0.1)  # Mantém o loop ativo
        except Exception as e:
            self._report_error(f"Falha ao iniciar bot: {str(e)}")
            self._update_status("Error")
        finally:
            await self.application.shutdown()  # Encerra o bot de forma controlada

    def _setup_handlers(self):
        """Configura todos os handlers do bot."""
        self.application.add_handler(ChatMemberHandler(self._handle_new_member))
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        msg_filter = (filters.ChatType.GROUPS & 
                     (filters.TEXT | filters.COMMAND |
                      filters.PHOTO | filters.VIDEO |
                      filters.Document.ALL))
        
        self.application.add_handler(MessageHandler(msg_filter, self._handle_message))
        self.application.add_error_handler(self._error_handler)

    def _cleanup_resources(self):
        """Limpa todos os recursos do bot."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
        if self.loop and not self.loop.is_closed():
            self.loop.close()
        self._update_status("Stopped")

    def stop_bot(self):
        """Para o bot de forma segura."""
        if self.running:
            self.stop_event.set()  # Notifica o bot para parar
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
            self._cleanup_resources()

    def _log(self, message, level=logging.INFO):
        """Método auxiliar para logging."""
        self.logger.log(level, message)
        if self.log_queue:
            self.log_queue.put(f"{level}: {message}")

    def _update_status(self, status):
        """Atualiza o status na GUI."""
        if self.status_callback:
            self.status_callback(status)

    def _report_error(self, message):
        """Reporta erros para a GUI."""
        self._log(message, level=logging.ERROR)
        if self.error_callback:
            self.error_callback(message)

    # Métodos para lidar com eventos
    async def _handle_new_member(self, update, context):
        """Lida com eventos de novos membros em grupos."""
        chat_id = update.chat.id
        new_members = update.chat_member.new_chat_members
        
        if new_members:
            for member in new_members:
                user_name = member.user.full_name or member.user.username or member.user.id
                self._log(f"Novo membro detectado no chat {chat_id}: {user_name}")

    async def _handle_callback_query(self, update, context):
        """Lida com callback queries."""
        query = update.callback_query
        await query.answer()
        self._log(f"Callback Query recebido: {query.data}")

    async def _handle_message(self, update, context):
        """Lida com mensagens recebidas."""
        message = update.message.text
        self._log(f"Mensagem recebida: {message}")

    async def _error_handler(self, update, context):
        """Lida com erros durante a execução do bot."""
        error = context.error
        self._report_error(f"Erro no bot: {str(error)}")