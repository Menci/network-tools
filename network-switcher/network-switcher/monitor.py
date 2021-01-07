import asyncio
import subprocess
import time
from collections import deque

import utils

class NetworkMonitor:
    def __init__(self, name, command, interval, log_count, callback):
        self.name = name
        self.command = command
        self.interval = interval
        self.log_count = log_count
        self.callback = callback

        self.logs = deque()
        self.process = None
        self.stopped = False

    def start(self):
        asyncio.create_task(self.runner())

    async def stop(self):
        self.stopped = True
        if self.process is None:
            return
        self.kill_process()
        await self.process.wait()

    def kill_process(self):
        try:
            self.process.kill()
        except ProcessLookupError:
            pass

    async def runner(self):
        while not self.stopped:
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            utils.log([self.name], "self.process.pid = %d" % self.process.pid)

            start_time = time.time()

            success = False
            try:
                await asyncio.wait_for(self.process.wait(), timeout=self.interval)
                success = self.process.returncode == 0
            except asyncio.TimeoutError:
                utils.log([self.name], "timeout")
                self.kill_process()
                await self.process.wait()

            # Calculate the remaining time to ensure a full interval
            elapsed_time = time.time() - start_time
            remaining_time = self.interval - elapsed_time

            utils.log([self.name], "command returned after %s seconds" % elapsed_time)

            if remaining_time > 0:
                await asyncio.sleep(remaining_time)

            # Append to logs
            if len(self.logs) == self.log_count:
                self.logs.popleft()
            
            self.logs.append(success)
            self.callback(self.name, self.logs)
