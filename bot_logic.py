# bot_logic.py
import asyncio
import threading
import time
from bot_controller import BotController
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler, 
    ChatMemberHandler
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest
import logging
from collections import defaultdict
import queue

# Configura logging básico (para console/arquivo, se desejado)
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)
# Em vez de usar o logger padrão diretamente para a GUI, usaremos um callback

# --- Handler de Log Customizado para GUI ---
class GuiHandler(logging.Handler):
    """Um handler de log que envia registros para uma fila thread-safe."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """Envia o registro formatado para a fila."""
        log_entry = self.format(record)
        self.log_queue.put(log_entry)

# --- Variáveis Globais (Simulação) ---
pending_verification = {} # user_id: timestamp
user_message_counts = defaultdict(lambda: defaultdict(list)) # user_id: {chat_id: [timestamp1, timestamp2,...]}

class TelegramBot:
    """Classe para gerenciar a lógica do bot do Telegram."""

    def __init__(self, config, status_callback=None, error_callback=None, log_queue=None):
        """Inicializa o bot."""
        self.config = config
        self.application = None
        self.bot_thread = None
        self.stop_event = threading.Event()  # Não usado ativamente para parar asyncio, mas pode ser útil
        self.status_callback = status_callback  # Função para atualizar status na GUI
        self.error_callback = error_callback  # Função para reportar erros na GUI
        self.log_queue = log_queue  # Fila para enviar logs para a GUI
        self.running = False
        self.loop = None  # Event loop para asyncio

        # Configura o logger específico desta instância do bot
        self.logger = logging.getLogger(f"BotManager_{id(self)}")
        self.logger.setLevel(logging.INFO)
        # Evita propagar logs para o logger root, se houver um configurado globalmente
        self.logger.propagate = False

        # Remove handlers antigos para evitar duplicação se re-inicializar
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Adiciona o handler da GUI se a fila foi fornecida
        if self.log_queue:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
            gui_handler = GuiHandler(self.log_queue)
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)
        else:
            # Fallback para console se não houver fila (útil para debug)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Inicializa o controlador de parada
        self.controller = BotController(self)
        
        # Adiciona esta verificação para garantir que o loop não seja reutilizado
        self._loop_lock = threading.Lock()
        
        
    def _log(self, message, level=logging.INFO):
        """Registra uma mensagem usando o logger da instância."""
        self.logger.log(level, message)

    def _update_status(self, status):
        """Chama o callback de status se disponível e loga."""
        self._log(f"Atualizando status para: {status}", level=logging.DEBUG)
        if self.status_callback:
            self.status_callback(status)
        self.running = (status == "Running")
        # Atualiza config apenas se necessário (pode causar I/O excessivo)
        # self.config["bot_status"] = status

    def _report_error(self, message):
        """Chama o callback de erro se disponível e loga como erro."""
        self._log(message, level=logging.ERROR)
        if self.error_callback:
            self.error_callback(message)

    async def _restricted_until(self, user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Verifica se o usuário está restrito no grupo."""
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status == 'restricted' and member.until_date is not None
        except TelegramError as e:
            self._log(f"Erro ao verificar status do membro {user_id} no chat {chat_id}: {e}", level=logging.ERROR)
            return False # Assume não restrito se houver erro

    async def _restrict_user(self, user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE, can_send_messages=False):
        """Restringe um usuário no grupo (não pode enviar mensagens, mídia, etc.)."""
        permissions = ChatPermissions(
            can_send_messages=can_send_messages, # Permite msg se True (após seguir)
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions,
                until_date=0 # Restrição permanente até ser removida manualmente ou pelo bot
            )
            self._log(f"Usuário {user_id} restringido no chat {chat_id}.")
        except Forbidden:
             self._report_error(f"Erro: Permissão negada para restringir usuário {user_id} no chat {chat_id}. O bot tem direitos de administrador?")
        except BadRequest as e:
             self._report_error(f"Erro ao restringir usuário {user_id}: {e}")
        except Exception as e:
            self._report_error(f"Erro inesperado ao restringir usuário {user_id}: {e}")

    async def _unrestrict_user(self, user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Remove restrições de um usuário."""
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True, # Ou ajuste conforme necessário
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False, # Geralmente não permitido a usuários normais
            can_invite_users=True, # Permitir convidar outros
            can_pin_messages=False, # Geralmente restrito a admins
        )
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions,
                use_independent_chat_permissions=True # Necessário para remover restrições específicas
            )
            self._log(f"Restrições removidas para usuário {user_id} no chat {chat_id}.")
        except Forbidden:
             self._report_error(f"Erro: Permissão negada para remover restrições do usuário {user_id}. O bot tem direitos de administrador?")
        except BadRequest as e:
            # Pode acontecer se o usuário não estava restrito
            self._log(f"Info ao remover restrições do usuário {user_id}: {e}", level=logging.WARNING)
        except Exception as e:
            self._report_error(f"Erro inesperado ao remover restrições do usuário {user_id}: {e}")

    async def _ban_user(self, user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE, reason: str = "Violação das regras"):
        """Bane um usuário do grupo."""
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            self._log(f"Usuário {user_id} banido do chat {chat_id} por: {reason}")
            # Opcional: Enviar mensagem ao grupo informando o banimento (cuidado para não poluir)
            # await context.bot.send_message(chat_id=chat_id, text=f"Usuário banido por: {reason}")
        except Forbidden:
             self._report_error(f"Erro: Permissão negada para banir usuário {user_id}. O bot tem direitos de administrador?")
        except BadRequest as e:
            self._report_error(f"Erro ao banir usuário {user_id}: {e}")
        except Exception as e:
            self._report_error(f"Erro inesperado ao banir usuário {user_id}: {e}")

    async def _delete_message(self, chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Apaga uma mensagem."""
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            self._log(f"Mensagem {message_id} apagada no chat {chat_id}.", level=logging.DEBUG)
        except Forbidden:
            # Comum se a mensagem for antiga ou o bot não for admin
            self._log(f"Permissão negada para apagar mensagem {message_id} no chat {chat_id}.", level=logging.WARNING)
        except BadRequest as e:
            # Mensagem pode já ter sido apagada
            self._log(f"Não foi possível apagar mensagem {message_id}: {e}", level=logging.WARNING)
        except Exception as e:
            self._report_error(f"Erro inesperado ao apagar mensagem {message_id}: {e}")


    # --- Handlers ---

    async def _handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lida com novos membros entrando no grupo."""
        if not update.message or not update.message.new_chat_members:
            return

        chat_id = update.message.chat_id
        # Verifica se o chat é o grupo configurado
        if str(chat_id) != str(self.config.get("group_id")): # Comparar como strings
            self._log(f"Novo membro detectado em chat não configurado: {chat_id}", level=logging.WARNING)
            return

        bot: Bot = context.bot
        for member in update.message.new_chat_members:
            if member.is_bot:
                self._log(f"Bot {member.username} entrou no grupo. Ignorando.", level=logging.INFO)
                continue # Ignora outros bots

            user_id = member.id
            user_name = member.first_name

            self._log(f"Novo membro {user_name} ({user_id}) entrou no chat {chat_id}.")

            # 1. Restringe o usuário imediatamente
            await self._restrict_user(user_id, chat_id, context)

            # 2. Envia mensagem de boas-vindas com botão de verificação
            welcome_text = self.config.get("welcome_message", "").format(
                user=user_name,
                insta=self.config.get("instagram_url"),
                tiktok=self.config.get("tiktok_url")
            )
            keyboard = [[InlineKeyboardButton("✅ Já segui", callback_data=f"verify_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML # Ou MARKDOWN se preferir
                )
                pending_verification[user_id] = time.time() # Marca para verificação
                self._log(f"Mensagem de boas-vindas enviada para {user_name} ({user_id}). Aguardando verificação.")
            except TelegramError as e:
                self._report_error(f"Falha ao enviar mensagem de boas-vindas para {user_id}: {e}")

    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lida com cliques em botões inline."""
        query = update.callback_query
        await query.answer() # Responde ao Telegram que o clique foi recebido

        user_id = query.from_user.id
        user_name = query.from_user.first_name
        # O chat_id pode não estar presente em todas as queries, mas geralmente está na mensagem associada
        chat_id = query.message.chat_id if query.message else None
        data = query.data

        self._log(f"Callback query recebido de {user_name} ({user_id}): {data}", level=logging.DEBUG)

        if data.startswith("verify_"):
            target_user_id = int(data.split("_")[1])

            # Apenas o próprio usuário pode clicar no seu botão de verificação
            if user_id != target_user_id:
                await query.answer("Este botão não é para você.", show_alert=True)
                self._log(f"Usuário {user_name} ({user_id}) clicou no botão de verificação de outro usuário ({target_user_id}).", level=logging.WARNING)
                return

            if not chat_id:
                 self._log(f"Não foi possível obter chat_id para a query de verificação do usuário {user_id}.", level=logging.ERROR)
                 await query.answer("Erro interno ao processar a verificação.", show_alert=True)
                 return

            if user_id in pending_verification:
                self._log(f"Usuário {user_name} ({user_id}) clicou em 'Já segui'. Simulando verificação.")
                # --- SIMULAÇÃO DE VERIFICAÇÃO ---
                # Aqui você integraria com as APIs do Instagram/TikTok se disponíveis.
                # Por agora, vamos assumir que ele seguiu.
                followed = True # Simulação

                if followed:
                    await self._unrestrict_user(user_id, chat_id, context)
                    if user_id in pending_verification: # Verifica novamente antes de deletar
                        del pending_verification[user_id] # Remove da lista de pendentes
                    try:
                        await query.edit_message_text(text=f"Obrigado por seguir, {user_name}! Acesso liberado.")
                        self._log(f"Acesso liberado para {user_name} ({user_id}) no chat {chat_id}.")
                    except TelegramError as e:
                         self._log(f"Erro ao editar mensagem de confirmação para {user_id}: {e}", level=logging.WARNING)

                else:
                    # Se a verificação real falhar:
                    await query.answer("Parece que você ainda não seguiu os perfis. Tente novamente após seguir.", show_alert=True)
                    self._log(f"Verificação simulada falhou para {user_name} ({user_id}).", level=logging.INFO)
                    # Poderia adicionar um limite de tempo ou tentativas aqui
            else:
                # Usuário clicou mas não estava pendente (talvez já verificado ou erro)
                 await query.answer("Verificação não necessária ou já concluída.", show_alert=True)
                 self._log(f"Usuário {user_name} ({user_id}) clicou em 'Já segui', mas não estava pendente.", level=logging.WARNING)


    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa todas as mensagens recebidas."""
        if not update.message or not update.message.from_user:
             return # Ignora atualizações sem mensagem ou usuário

        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        user_id = user.id
        user_name = user.first_name
        text = message.text or message.caption or "" # Pega texto da msg ou legenda de midia
        message_id = message.message_id

        # Ignora mensagens do próprio bot ou de chats não configurados
        bot_info = await context.bot.get_me()
        if user.id == bot_info.id:
            return
        if str(chat_id) != str(self.config.get("group_id")):
            return

        # Log da mensagem recebida (cuidado com privacidade em produção)
        # self._log(f"Msg de {user_name}({user_id}) no chat {chat_id}: {text[:50]}...", level=logging.DEBUG)


        # --- Verificação de Restrição ---
        if user_id in pending_verification:
             self._log(f"Mensagem de usuário não verificado {user_name}({user_id}) detectada. Apagando.")
             await self._delete_message(chat_id, message_id, context)
             # Opcional: Reenviar instrução ou avisar no privado
             # await context.bot.send_message(user_id, "Você precisa clicar em 'Já segui' no grupo após seguir os perfis.")
             return # Interrompe processamento adicional para este usuário


        # --- Aplicação das Regras ---
        rules = self.config.get("rules", {})
        delete_msg = False
        ban_user = False
        ban_reason = ""

        # 1. Palavrões/Ofensas
        if rules.get("block_profanity"):
            profanity_list = rules.get("profanity_list", [])
            if any(word.lower() in text.lower() for word in profanity_list):
                self._log(f"Palavrão detectado de {user_name}({user_id}): {text}")
                delete_msg = True
                ban_user = True
                ban_reason = "Conteúdo ofensivo"

        # 2. Fora de Tópico (se não for banido por profanidade)
        if not ban_user and rules.get("block_off_topic") and text: # Verifica se há texto
            keywords = rules.get("allowed_topics_keywords", [])
            is_greeting = any(greet in text.lower() for greet in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "tudo bem"])
            # Considera fora de tópico se não for saudação E não contiver nenhuma keyword
            if not is_greeting and not any(keyword.lower() in text.lower() for keyword in keywords):
                self._log(f"Mensagem fora de tópico detectada de {user_name}({user_id}): {text}")
                delete_msg = True
                # ban_user = False # Normalmente não bane

        # 3. Links (se não for banido antes)
        if not ban_user and rules.get("block_links"):
             has_link = any(entity.type in ['url', 'text_link'] for entity in message.entities or [])
             has_explicit_link = 'http://' in text or 'https://' in text or 'www.' in text or '.com' in text or '.net' in text or '.org' in text
             if has_link or has_explicit_link:
                 self._log(f"Link detectado de {user_name}({user_id}): {text}")
                 delete_msg = True
                 # ban_user = False

        # 4. Tipo de Arquivo (apenas PDF)
        if not ban_user and rules.get("allow_only_pdf"):
            if message.document and message.document.mime_type != 'application/pdf':
                self._log(f"Tipo de arquivo não permitido ({message.document.mime_type}) de {user_name}({user_id})")
                delete_msg = True
                # ban_user = False
            elif message.photo or message.video or message.audio or message.voice or message.sticker:
                 self._log(f"Tipo de mídia não permitida (não PDF) de {user_name}({user_id})")
                 delete_msg = True
                 # ban_user = False


        # 5. Spam/Flood (verificação final)
        if not ban_user and rules.get("block_spam_flood"):
            now = time.time()
            limit = rules.get("spam_message_limit", 5)
            time_window = rules.get("spam_time_limit_sec", 10)

            user_msgs = user_message_counts[user_id][chat_id]
            # Limpa timestamps antigos
            user_msgs = [t for t in user_msgs if now - t < time_window]
            user_msgs.append(now)
            user_message_counts[user_id][chat_id] = user_msgs

            if len(user_msgs) > limit:
                self._log(f"Spam/Flood detectado de {user_name}({user_id}) (mensagens: {len(user_msgs)} em {time_window}s)")
                delete_msg = True # Apaga a mensagem atual que causou o spam
                ban_user = True
                ban_reason = "Spam/Flood"
                # Limpa o histórico de mensagens para evitar banimentos múltiplos rápidos
                user_message_counts[user_id][chat_id] = []


        # --- Ações ---
        if delete_msg:
            await self._delete_message(chat_id, message_id, context)
        if ban_user:
            await self._ban_user(user_id, chat_id, context, reason=ban_reason)
            # Limpa contagem de spam se banido
            if user_id in user_message_counts and chat_id in user_message_counts[user_id]:
                 del user_message_counts[user_id][chat_id]


    async def _post_init(self, application: Application):
        """Tarefas a serem executadas após a inicialização do bot."""
        try:
            bot_info = await application.bot.get_me()
            self._log(f"Bot {bot_info.username} (ID: {bot_info.id}) iniciado com sucesso.")
            self._update_status("Running")
            # TODO: Implementar lógica de processamento de mensagens offline
            self._log("Verificação de mensagens offline ainda não implementada.")
        except TelegramError as e:
            self._report_error(f"Falha ao iniciar o bot: {e}. Verifique o token e a conexão.")
            self._update_status("Error")
            # Tenta parar o loop asyncio se a inicialização falhar
            await self.stop_bot_async()

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Loga os erros causados por Updates."""
        error = context.error
        error_message = f"Exceção ao processar uma atualização: {error}"
        # Tenta obter mais detalhes do update, se disponível
        update_details = ""
        if isinstance(update, Update) and update.effective_message:
            update_details = f" (Update ID: {update.update_id}, Chat ID: {update.effective_chat.id if update.effective_chat else 'N/A'}, User ID: {update.effective_user.id if update.effective_user else 'N/A'})"

        self._log(error_message + update_details, level=logging.ERROR)

        # Reporta erros específicos para a GUI se necessário
        if isinstance(error, Forbidden):
             self._report_error("Erro de permissão: Verifique se o bot é administrador no grupo e tem as permissões necessárias.")
        elif isinstance(error, BadRequest):
             self._report_error(f"Erro na requisição ao Telegram: {error}")
        # Adicione mais tratamentos de erro específicos conforme necessário


    async def _run_bot_async(self):
        """Configura e executa o bot no loop asyncio."""
        token = self.config.get("bot_token")
        if not token or token == "SEU_TOKEN_AQUI":
            self._report_error("Configure o Token da API do Bot antes de iniciar.")
            self._update_status("Error")
            return

        # Cria o Application
        app_builder = Application.builder().token(token).post_init(self._post_init)
        app_builder.connect_timeout(30).read_timeout(30).write_timeout(30)
        self.application = app_builder.build()

        # Configura handlers
        self.application.add_handler(ChatMemberHandler(self._handle_new_member, ChatMemberHandler.CHAT_MEMBER))
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        # Filtro de mensagens
        msg_filter = (
            filters.ChatType.GROUPS & (
                filters.TEXT | filters.COMMAND |
                filters.PHOTO | filters.VIDEO |
                filters.AUDIO | filters.VOICE |
                filters.Document.ALL |
                filters.Sticker.ALL
            )
        )
        
        self.application.add_handler(MessageHandler(msg_filter, self._handle_message))
        self.application.add_error_handler(self._error_handler)

        # Inicia o bot
        self._log("Iniciando polling do bot...")
        self._update_status("Starting")
        
        try:
            await self.application.run_polling(
                stop_signals=None,
                allowed_updates=Update.ALL_TYPES
            )
        except Exception as e:
            self._report_error(f"Erro: {str(e)}")
            self._update_status("Error")
        finally:
            self._log("Polling finalizado")
            # O status final (Stopped/Error) deve ser definido por quem chamou stop ou pelo erro


async def stop_bot_async(self):
    """Para o bot de forma assíncrona com tratamento seguro de event loop."""
    try:
        # Verificação do estado
        status_text = self.status_callback.__self__.status_label.cget("text")
        if not self.application and (self.running or status_text.endswith(("Starting", "Running"))):
            self._log("Bot não estava em execução.")
            self._update_status("Stopped")
            return

        self._update_status("Stopping")
        
        # Processo de parada em etapas
        if hasattr(self.application, 'running') and self.application.running:
            try:
                await self.application.stop()
                await asyncio.sleep(0.2)  # Pausa curta para finalização
            except RuntimeError as e:
                if "Event loop is closed" not in str(e):
                    raise

        # Shutdown seguro
        if hasattr(self.application, 'is_shutting_down'):
            if not self.application.is_shutting_down:
                await self.application.shutdown()
        
        self._log("Bot parado com sucesso.")

    except Exception as e:
        self._report_error(f"Erro durante a parada: {str(e)}")
    finally:
        # Garante estado consistente
        self.running = False
        self._update_status("Stopped")
        try:
            if self.application:
                self.application = None
        except:
            pass
            
            
    def _run_wrapper(self):
        """Wrapper para executar o loop asyncio em uma thread separada."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_bot_async())
        except Exception as e:
            self._report_error(f"Erro fatal na thread do bot: {e}")
        finally:
            if self.loop and self.loop.is_running():
                self.loop.stop()
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            self.loop = None
            self._update_status("Stopped")


    def start_bot(self):
        """Inicia o bot em uma nova thread."""
        if self.running:
            self._log("Bot já está em execução.", level=logging.WARNING)
            return

        # Validações básicas da configuração
        if not self.config.get("bot_token") or self.config.get("bot_token") == "SEU_TOKEN_AQUI":
            self._report_error("Configure o Token da API do Bot antes de iniciar.")
            self._update_status("Error")
            return
        
        if not self.config.get("group_id") or self.config.get("group_id") == "SEU_GROUP_ID_AQUI":
            self._report_error("Configure o ID do Grupo antes de iniciar.")
            self._update_status("Error")
            return

        try:
            self.stop_event.clear()
            self.bot_thread = threading.Thread(target=self._run_wrapper, daemon=True)
            self.bot_thread.start()
            self._log("Thread do bot iniciada com sucesso.")
        except Exception as e:
            self._report_error(f"Falha ao iniciar thread: {str(e)}")
            self._update_status("Error")
            # Limpa eventos antigos e inicia a thread
            self.stop_event.clear()
            self.bot_thread = threading.Thread(target=self._run_wrapper, daemon=True)
            self.bot_thread.start()
            self._log("Thread do bot iniciada.")
            # O status será atualizado para Starting/Running/Error dentro da thread via _post_init ou erros


    def stop_bot(self):
        """Delega a parada para o controlador"""
        self.controller.stop_bot()
    def update_config(self, new_config):
        """Atualiza a configuração do bot."""
        self.config = new_config
        self._log("Configuração do bot atualizada pela GUI.")
        # Nota: Alterações críticas como token/group_id exigem reinício do bot.
        # A GUI deve informar isso ao usuário.
