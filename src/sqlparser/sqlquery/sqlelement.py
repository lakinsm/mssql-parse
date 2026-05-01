from abc import ABC, abstractmethod
from collections import deque
import sqlparser.globals


class SQLElement(ABC):
	"""
	Abstract class representing one clause of SQL (sub-)query.
	"""
	def __init__(self, keyword: str, start: int, stop: int, text: str, non_subqueries: dict):
		self._unclaimedvars = set()
		self._basetables = {}
		self._temp_jointables = {}
		self._temp_symbtables = {}
		self.keyword = keyword
		self.text = text
		self.start = start
		self.stop = stop
		self.selecttables = {}
		self.jointables = {}
		self.aliases = {}
		self.relations = {}
		self.table_dependencies = {}
		self.non_subqueries = non_subqueries
		self.parse(self.text)

	@abstractmethod
	def parse(self, sql_text: str) -> None:
		pass

	@abstractmethod
	def resolve_tablevar_relations(self) -> None:
		pass

	@abstractmethod
	def resolve_subrelations(self) -> None:
		pass

	@abstractmethod
	def non_subquery_dfs(self, substring: str, opens: deque, seen: set) -> None:
		pass

	@abstractmethod
	def extract_relations(self, clause_text: str, current_node: int) -> None:
		pass

	@abstractmethod
	def extract_ops(self, op_clause: str, current_node: int) -> None:
		pass

	def parse_ctes(self, sql_text: str) -> None:
		"""
		Store CTE alias and subquery relations.
		"""
		for m in sqlparser.globals.TSQL_CTES.finditer(sql_text):
			table, alias = m.group('table', 'alias')  # table will be a symbolic here
			self.selecttables.setdefault(table, set())
			self.aliases[alias] = (None, table)  # table alias, no var
	
	def parse_tables_vars(self, sql_text:str) -> None:
		"""
		Store table, var, and alias info into self.selecttables and self.aliases 
		with None if element missing.
		"""
		consumed = set()
		# 1. table.var AS alias
		for m in sqlparser.globals.TSQL_VARTABLE_NAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				table, varname, alias = m.group('table', 'varname', 'alias')
				self.selecttables.setdefault(table, set()).add(varname)
				if alias not in globals.ODBC_KEYWORDS:
					self.aliases[alias] = (varname, table)
			consumed.update(match_interval)

		# 2. table.var
		for m in sqlparser.globals.TSQL_VARTABLE_UNNAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				table, varname = m.group('table', 'varname')
				self.selecttables.setdefault(table, set()).add(varname)
			consumed.update(match_interval)

		# 3. var AS alias
		for m in sqlparser.globals.TSQL_VAR_NAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				varname, alias = m.group('varname', 'alias')
				self._unclaimedvars.add(varname)
				if alias not in globals.ODBC_KEYWORDS:
					self.aliases[alias] = (varname, None)  # table will be resolved in SQLNode
			consumed.update(match_interval)

		# 4. var
		for m in sqlparser.globals.TSQL_VAR_UNNAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				varname, alias = m.group('varname')
				self._unclaimedvars.add(varname)
			consumed.update(match_interval)
