import re
import sys
from collections import deque


class DFS:
	"""
	Construct tree using Depth First Search from nested intervals.
	"""
	def __init__(self, root_start, child_starts, stops):
		self._parent_this = deque([root_start])  # DFS Seen LHS
		self._child_starts = deque(child_starts)  # DFS Unseen LHS
		self._stops = deque(stops)  # DFS Unseen RHS
		self.tree = {0: []}  # Map: parent_node_idx -> [children_idx,]
		self.levels = {0: [0]}  # Map: tree_level -> [node_idx,]
		self.intervals = {0: [root_start, None]}  # Map: node_idx -> [char_start_idx, char_stop_idx]


class SQLNode:
	"""
	One (sub-)query and its components.
	"""
	def __init__(self, query_text: str) -> None:
		self.select = ''
		self.from_ = ''
		self.join = ''
		self.where = ''
		self.groupby = ''
		self.orderby = ''
		self.row_ops = ''


class SQLTree:
	"""
	Stores query node types and relationships in tree structures.
	"""
	def __init__(self, full_query_text: str) -> None:
		self.variables = {}
		self.tree = {'root': SQLNode}


if __name__ == '__main__':
	example1_nested = """
		( ( ( ) ( ) ( ) ( ( ( ) ) ) ) ) ( ( ) ) ( ) ( ( ) )
	"""
	opens = [match.start() for match in re.finditer(re.escape('('), example1_nested)]
	closes = [match.start() for match in re.finditer(re.escape(')'), example1_nested)]
	dfs = DFS(opens[0], opens[1:], closes)

	print(dfs._parent_this, dfs._child_starts, dfs._stops)
	