import utils

class DefinedRoutes:
    class SystemRouteTable:
        def __init__(self, route, table_id, fwmark):
            self.table_id = table_id
            self.fwmark = fwmark
            self.route = route
        
        def add(self):
            utils.system("ip route add default %s table %d" % (self.route, self.table_id))
            utils.system("ip rule add fwmark %d lookup %d" % (self.fwmark, self.table_id))

        def remove(self):
            utils.system("ip route del default %s table %d" % (self.route, self.table_id))
            utils.system("ip rule del fwmark %d lookup %d" % (self.fwmark, self.table_id))

    def __init__(self, routes, table_id_start, fwmark_start):
        self.routes = routes
        self.current_table_id = table_id_start
        self.current_fwmark = fwmark_start + 1

        # fwmark_start is the fwmark for a matched but neither routed nor set fallthrough packet
        # These packets are DROPped
        self.fwmark_drop = fwmark_start

        self.tables = []
        self.map_name_fwmark = {}
        self.map_name_route = {}

    def add_iproute2_rules(self):
        for route in self.routes:
            table = DefinedRoutes.SystemRouteTable(route["route"], self.current_table_id, self.current_fwmark)
            table.add()
            self.tables.append(table)

            self.map_name_fwmark[route["name"]] = self.current_fwmark
            self.map_name_route[route["name"]] = route["route"]

            self.current_table_id += 1
            self.current_fwmark += 1

    def get_fwmark(self, name):
        return self.map_name_fwmark[name]

    def get_route(self, name):
        return self.map_name_route[name]

    def get_fwmark_drop(self):
        return self.fwmark_drop

    def remove_iproute2_rules(self):
        for table in self.tables:
            table.remove()
