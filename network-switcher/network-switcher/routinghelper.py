import time
import definedroutes
import rulematchers
import utils
from iptables import IPTables

class RoutingHelper:
    def __init__(self, definedroutes, chain_name, routing_rules, update_interval):
        self.definedroutes = definedroutes
        self.chain_name = chain_name
        self.update_interval = update_interval

        self.routing_rules = routing_rules
        self.current_routes = []

        self.default_rule = None
        self.current_default_route = None

        self.iptables = IPTables()

        self.last_update_time = None

    def initialize_iptables(self):
        fwmark_drop = self.definedroutes.get_fwmark_drop()

        main_chain = self.chain_name["main"]
        self.iptables.add_chain("mangle", main_chain)
        self.iptables.add_rule("mangle", main_chain, "-j MARK --set-mark 0")

        i = 0
        for routing_rule in self.routing_rules:
            self.current_routes.append(None)

            check_chain = self.chain_name["check"] % i
            rule_chain = self.chain_name["rule"] % i
            self.iptables.add_chain("mangle", check_chain)
            self.iptables.add_chain("mangle", rule_chain)

            # If the packet match this rule in check chain, jump to the rule chain
            def add_rule_callback(filter_phrase):
                self.iptables.add_rule("mangle", check_chain, "%s -j %s" % (filter_phrase, rule_chain))
            
            if "match" in routing_rule:
                rulematchers.add_match_rule(add_rule_callback, routing_rule["match"], routing_rule["match_value"])
            else:
                # This is the default rule, should be added to the main table
                self.default_rule = routing_rule["route"]

            # If a packet returned to check chain from rule chain, it doesn't routed in rule chain
            # Because no available routing rule
            # Fallthrough?
            if "fallthrough" in routing_rule and routing_rule["fallthrough"]:
                # Clear the 'drop' mark to match the next rule
                self.iptables.add_rule("mangle", check_chain, "-j MARK --set-mark 0")

            # Append the rule's check chain to main chain
            self.iptables.add_rule("mangle", main_chain, "-m mark --mark 0 -j %s" % check_chain)

            i += 1

        self.iptables.add_rule("mangle", "OUTPUT", "-j %s" % main_chain)
        self.iptables.add_rule("mangle", "PREROUTING", "-j %s" % main_chain)

    def update_states(self, states):
        def compute_route(route, states):
            for case in route:
                if eval(case["condition"]):
                    return case["to"]
            return None

        current_time = time.time()
        if self.last_update_time and current_time - self.last_update_time < self.update_interval:
            # Update only once in an interval
            return

        self.last_update_time = current_time

        i = 0
        for routing_rule in self.routing_rules:
            # Compute the new route based on the new state
            self.update_rule_route(i, compute_route(routing_rule["route"], states))

            i += 1
        
        # Update 'default' rule route
        self.update_default_route(compute_route(self.default_rule, states))

    def update_default_route(self, new_route):
        if self.current_default_route == new_route:
            utils.log("Not updating default routing rule since route unchanged")
            return
        if self.current_default_route != None:
            utils.system("ip route del default %s metric 1" % self.definedroutes.get_route(self.current_default_route))
        if new_route != None:
            utils.system("ip route add default %s metric 1" % self.definedroutes.get_route(new_route))
        self.current_default_route = new_route

    def update_rule_route(self, index, new_route):
        utils.log("Routing rule %s => %s" % (self.routing_rules[index]["name"], new_route))
        if self.current_routes[index] == new_route:
            utils.log("Not updating routing rule %d since route unchanged" % index)
            return
        
        rule_chain = self.chain_name["rule"] % index
        self.iptables.flush_chain("mangle", rule_chain)

        if new_route != None:
            fwmark = self.definedroutes.get_fwmark(new_route)
            self.iptables.add_rule("mangle", rule_chain, "-j MARK --set-mark %d" % fwmark)
            self.iptables.add_rule("mangle", rule_chain, "-j ACCEPT")

        self.current_routes[index] = new_route

    def finalize(self):
        self.iptables.del_all()
