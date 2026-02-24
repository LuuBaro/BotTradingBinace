"""
Telegram Bot Worker - Phase 3 main entry point
Runs the Telegram bot for remote operations
"""
import asyncio
import signal
from typing import Set

from packages.shared.logger import logger
from apps.telegram.bot import TelegramBot


class TelegramBotWorker:
    """Main worker that runs the Telegram bot"""

    def __init__(self):
        self.bot = TelegramBot()
        self._shutdown = False
        self._shutdown_event = asyncio.Event()
        self._tasks: Set[asyncio.Task] = set()

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info("telegram_worker_signal", signal=signum)
        self._shutdown = True
        self._shutdown_event.set()

    async def run(self):
        """Run the telegram bot worker"""
        logger.info("telegram_worker_starting")
        
        # Register signal handlers
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, self._signal_handler, signal.SIGTERM, None)
        loop.add_signal_handler(signal.SIGINT, self._signal_handler, signal.SIGINT, None)
        
        try:
            # Initialize and start bot
            await self.bot.initialize()
            bot_task = asyncio.create_task(self.bot.run())
            self._tasks.add(bot_task)
            
            logger.info("telegram_worker_running")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            logger.info("telegram_worker_shutdown_signal_received")
            
            # Cancel bot task
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
            
            # Shutdown gracefully
            await self.bot.shutdown()
            logger.info("telegram_worker_stopped")
        
        except Exception as e:
            logger.error("telegram_worker_error", error=str(e), exc_info=True)
            raise
        
        finally:
            # Cancel all pending tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)


async def main():
    """Main entry point"""
    worker = TelegramBotWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
