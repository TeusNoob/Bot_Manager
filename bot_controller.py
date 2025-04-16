# bot_controller.py
import asyncio
import logging
from typing import Optional
from telegram_bot import TelegramBot

class BotController:
    def __init__(self, bot_instance):
        self.bot = bot_instance  # Recebe a instância do TelegramBot
        self._stop_event = asyncio.Event()

    async def stop_bot_async(self):
        """Versão assíncrona para parada segura do bot"""
        try:
            if not self.bot.application or not self.bot.running:
                self.bot._log("Bot já está parado (async).")
                return

            self.bot._update_status("Stopping")
            self.bot._log("Iniciando processo de parada assíncrona...")

            # Sinaliza para o polling parar
            if self.bot.application.running:
                await self.bot.application.stop()
                await asyncio.sleep(0.5)  # Pausa para finalização

            # Shutdown limpo
            if not self.bot.application.is_running:
                await self.bot.application.shutdown()

        except RuntimeError as e:
            if "Event loop is closed" not in str(e):
                self.bot._report_error(f"Erro de runtime: {str(e)}")
        except Exception as e:
            self.bot._report_error(f"Erro na parada assíncrona: {str(e)}")
        finally:
            self._cleanup_resources()

    def stop_bot(self):
        """Interface síncrona para parada do bot"""
        try:
            if not self._is_bot_running():
                self.bot._update_status("Stopped")
                return

            if not self.bot.loop or not self.bot.loop.is_running():
                self.bot._report_error("Loop de eventos não disponível")
                return

            # Executa a parada assíncrona
            future = asyncio.run_coroutine_threadsafe(
                self.stop_bot_async(),
                self.bot.loop
            )
            future.result(timeout=15)  # Timeout aumentado para 15s

        except asyncio.TimeoutError:
            self.bot._report_error("Timeout ao parar o bot")
        except Exception as e:
            self.bot._report_error(f"Erro na parada: {str(e)}")
        finally:
            self._final_cleanup()

    def _is_bot_running(self) -> bool:
        """Verifica se o bot está em execução de forma segura"""
        return hasattr(self.bot, 'running') and self.bot.running

    def _cleanup_resources(self):
        """Limpeza de recursos assíncronos"""
        try:
            self.bot.running = False
            if hasattr(self.bot, 'application'):
                self.bot.application = None
        except Exception as e:
            logging.error(f"Erro na limpeza assíncrona: {str(e)}")

    def _final_cleanup(self):
        """Limpeza final síncrona"""
        try:
            if hasattr(self.bot, 'bot_thread'):
                self.bot.bot_thread = None
            if hasattr(self.bot, 'loop'):
                self.bot.loop = None
            self.bot._update_status("Stopped")
        except Exception as e:
            logging.error(f"Erro na limpeza final: {str(e)}")