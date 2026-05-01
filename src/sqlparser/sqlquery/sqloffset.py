import sys
from collections import deque
from sqlparser.sqlquery.sqlelement import SQLElement
import sqlparser.globals


class SQLOffset(SQLElement):
	"""
	Description
	"""
	def parse(self, sql_text: str) -> None:
		pass

	def resolve_tablevar_relations(self) -> None:
		pass

	def resolve_subrelations(self) -> None:
		pass

	def non_subquery_dfs(self, substring: str, opens: deque, seen: set) -> None:
		pass

	def extract_relations(self, clause_text: str, current_node: int) -> None:
		pass

	def extract_ops(self, op_clause: str, current_node: int) -> None:
		pass
