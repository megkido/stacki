# @copyright@
# Copyright (c) 2006 - 2019 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@

from ariadne import ObjectType, QueryType, SubscriptionType, gql, make_executable_schema, load_schema_from_path
from ariadne.asgi import GraphQL
from stack.db import db
import asyncio

type_defs = load_schema_from_path("/opt/stack/lib/python3.7/site-packages/stack/graph_ql/schema/")

query = QueryType()

@query.field("allHosts")
def resolve_all_hosts(*_):
	db.execute(
		"""
		select n.id as id, n.name as name, n.rack as rack, n.rank as rank,
		n.comment as comment, n.metadata as metadata,	a.name as appliance,
		o.name as os, b.name as box, e.name as environment,
		bno.name as osaction, bni.name as installaction
		from nodes n
		left join appliances a   on n.appliance     = a.id
		left join boxes b        on n.box           = b.id
		left join environments e on n.environment   = e.id
		left join bootnames bno  on n.osaction      = bno.id
		left join bootnames bni  on n.installaction = bni.id
		left join oses o	 on b.os            = o.id
		"""
	)

	return db.fetchall()

host = ObjectType("Host")

@host.field("interfaces")
def resolve_host_interfaces(host, *_):
	db.execute(
	f"""
	select i.id as id, n.name as host, mac, ip, netmask, i.gateway,
	i.name as name, device, s.name as subnet, module, vlanid, options, channel, main
	from networks i, nodes n, subnets s
	where i.node = {host['id']} and i.subnet = s.id
	"""
	)

	return db.fetchall()

subscription = SubscriptionType()

@subscription.source("allHosts")
async def host_generator(obj, info):
	while True:
		await asyncio.sleep(1)
		db.execute(
		"""
		select n.id as id, n.name as name, n.rack as rack, n.rank as rank,
		n.comment as comment, n.metadata as metadata,	a.name as appliance,
		o.name as os, b.name as box, e.name as environment,
		bno.name as osaction, bni.name as installaction
		from nodes n
		left join appliances a   on n.appliance     = a.id
		left join boxes b        on n.box           = b.id
		left join environments e on n.environment   = e.id
		left join bootnames bno  on n.osaction      = bno.id
		left join bootnames bni  on n.installaction = bni.id
		left join oses o	 on b.os            = o.id
		"""
		)

		yield db.fetchall()

@subscription.field("allHosts")
def host_resolver(obj, info):
	return obj

# TODO: Move out of init
# Dynamic queries
def camel_case_it(string, delimeter = "_"):
		"""Return string in camelCase form"""
		string = "".join([word.capitalize() for word in string.split(delimeter)])
		return string[0].lower() + string[1:]

def find_field_name(field_name):
		"""Find the non camelCase version of a table name"""
		for table in get_table_names():
			if field_name == camel_case_it(table):
				return table

def get_table_names():
		"""Returns a list of the table names in the database"""
		db.execute("SHOW tables")

		table_names = []
		for table in db.fetchall():
			table_names.append(list(table.values())[0])

		return table_names

def select_query(obj, info):
	table_name = info.field_name
	try:
		db.execute(f'DESCRIBE {table_name}')
		table_info = db.fetchall()
	except:
		table_name = find_field_name(info.field_name)
		db.execute(f'DESCRIBE {table_name}')
		table_info = db.fetchall()

	query_string = ", ".join([field["Field"].lower() for field in table_info])
	db.execute(f'select {query_string} from {table_name}')

	return db.fetchall()

[query.field(camel_case_it(field))(lambda obj, info: select_query(obj, info)) for field in get_table_names()]
# End dynamic queries

schema = make_executable_schema(type_defs, [query, host, subscription])

# Create an ASGI app using the schema, running in debug mode
app = GraphQL(schema)

