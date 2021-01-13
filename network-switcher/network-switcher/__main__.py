import asyncio
import signal
import os
import argparse
import traceback

import utils
import config
import statusreporter
from monitor import NetworkMonitor
from definedroutes import DefinedRoutes
from routinghelper import RoutingHelper

class Main:
    def __init__(self, arguments):
        self.monitors = []
        self.logs = {}
        self.states = {}
        self.definedroutes = None
        self.routinghelper = None
        self.config = config.load(arguments.config)

        self.stopped = False

    async def start(self):
        # Load defined routes
        self.definedroutes = DefinedRoutes(
            self.config["defined_routes"],
            self.config["consts"]["table_id_start"],
            self.config["consts"]["fwmark_start"]
        )
        self.definedroutes.add_iproute2_rules()

        # Load routing helper
        self.routinghelper = RoutingHelper(
            self.definedroutes,
            self.config["consts"]["chain_name"],
            self.config["routing_rules"],
            self.config["monitor"]["interval"]
        )
        self.routinghelper.initialize_iptables()

        # Start monitors
        monitor_config = self.config["monitor"]
        for watch in monitor_config["watches"]:
            self.states[watch["name"]] = None
            self.logs[watch["name"]] = {}
            network_monitor = NetworkMonitor(
                watch["name"],
                watch["command"],
                monitor_config["interval"],
                monitor_config["log_count"],
                self.monitor_callback
            )
            network_monitor.start()
            self.monitors.append(network_monitor)
        
        # Start status reporter http server
        await statusreporter.start_server(
            self.config["status_reporter"]["host"],
            self.config["status_reporter"]["port"]
        )

    def monitor_callback(self, name, logs):
        if self.stopped:
            return

        self.logs[name] = list(logs)
        statusreporter.update_logs(self.logs)

        logs_state = None
        for state, condition in self.config["monitor"]["states"].items():
            success_count = sum(1 for log in logs if log == True)
            success_rate = 0 if len(logs) == 0 else success_count / len(logs)
            if eval(condition):
                logs_state = state
                break
        
        if not logs_state:
            utils.log("Ambiguous state")
        
        self.update_watch_state(name, logs_state)

    def update_watch_state(self, name, new_state):
        if self.states[name] != new_state:
            self.states[name] = new_state
        for state_item in self.states.items():
            utils.log((name, new_state))
        statusreporter.update_states(self.states)
        self.routinghelper.update_states(self.states)

    async def stop(self):
        self.stopped = True
        await statusreporter.stop_server()
        for monitor in self.monitors:
            await monitor.stop()
        self.routinghelper.finalize()
        self.definedroutes.remove_iproute2_rules()

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help="configure file", required=True)
arguments = parser.parse_args()

main = Main(arguments)

signaled = False
def on_signal():
    global signaled
    if signaled:
        utils.log("Duplicate signals, ignoring")
    
    signaled = True
    utils.log("Signaled, stopping")

    try:
        asyncio.create_task(main.stop())
    except Exception as e:
        traceback.print_exc()
        exit(-1)

loop = asyncio.get_event_loop()

loop.add_signal_handler(signal.SIGINT, on_signal)
loop.add_signal_handler(signal.SIGTERM, on_signal)

loop.run_until_complete(main.start())
loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
