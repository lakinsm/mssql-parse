import re
import sys
from collections import deque


class DFS:
	"""
	Construct tree using Depth First Search from nested intervals.
	"""
	def __init__(self, starts: list, stops: list) -> None:
		self._seen = deque()  # DFS seen nodes
		self._lhs = deque(starts)  # DFS unseen LHS
		self._rhs = deque(stops)  # DFS unseen RHS
		self.tree = {}  # Map: parent_node_idx -> [children_idx,]
		self.levels = {}  # Map: tree_level -> [node_idx,]
		self.intervals = {}  # Map: node_idx -> [char_start_idx, char_stop_idx]
		self.traversal = ()  # Tuple: (node_idx, ) traversal order
		self._dfs(0)
	
	def _dfs(self, node):
		if not self._rhs:
			return
		elif not self._lhs:
			self._close_node(self._rhs.popleft())
			self._dfs(self._seen.pop())  # up to parent
		elif self._rhs[0] < self._lhs[0]:
			self._close_node(self._rhs.popleft())
			self._dfs(self._seen.pop())  # up to parent
		elif self._lhs[0] < self._rhs[0]:
			self._open_node(node, self._lhs.popleft(), self._rhs.popleft())
			self._dfs(len(self.tree))  # down to child
		else:
			sys.stderr.write('ERROR: DFS.dfs() should not reach\n')
			raise ValueError
		
	
	def _open_node(self, node: int, start: int, stop: int) -> None:
		x = 1

	def _close_node(self, stop: int) -> None:
		x = 1




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
	dfs = DFS(opens, closes)
	