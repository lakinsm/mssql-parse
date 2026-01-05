import re
import sys
from collections import deque


class DFS:
	"""
	Construct tree using Depth First Search from nested intervals.
	"""
	def __init__(self, starts: list, stops: list) -> None:
		self._level = 0  # Tree level
		self._parent = deque()  # DFS seen open nodes LIFO
		self._lhs = deque(starts)  # DFS unseen LHS FIFO
		self._rhs = deque(stops)  # DFS unseen RHS FIFO
		self.tree = {0: []}  # Map: parent_node_idx -> [children_idx,]
		self.levels = {}  # Map: tree_level -> [node_idx,]
		self.intervals = {}  # Map: node_idx -> [char_start_idx, char_stop_idx]
		self.traversal = ()  # Tuple: (node_idx, ) traversal order

		assert(len(starts) == len(stops))
		self._dfs(0)
	
	def _dfs(self, node):
		self.traversal += (node,)
		if node not in self.tree:
			self.levels.setdefault(self._level, []).append(node)
			self.tree[self._parent[-1]].append(node)
		self.tree.setdefault(node, [])
		if not self._lhs:
			self.intervals[node][1] = self._rhs.popleft()
			self._level -= 1
		elif self._rhs[0] < self._lhs[0]:
			self.intervals[node][1] = self._rhs.popleft()
			self._level -= 1
		elif self._lhs[0] < self._rhs[0]:
			self.intervals[len(self.tree)] = [self._lhs.popleft(), None]
			self._parent.append(node)
			self._level += 1
			self._dfs(len(self.tree))  # down to child
		else:
			sys.stderr.write('ERROR: DFS.dfs() should not reach\n')
			raise ValueError
		if not self._rhs:
			return
		self._dfs(self._parent.pop())  # up to parent


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
	def __init__(self, full_query_text: str, ignore_strings = True) -> None:
		self._ignore_idxs = set()
		self.variables = {}
		self.tree = {}
		opens = [match.start() for match in re.finditer(re.escape('('), full_query_text)]
		closes = [match.start() for match in re.finditer(re.escape(')'), full_query_text)]
		if ignore_strings:
			quote_idxs = [m.start() for m in re.finditer('[\'"]', full_query_text)]
			assert(len(quote_idxs) % 2 == 0)
			self._ignore_idxs = set([y for x in [list(range(quote_idxs[i], quote_idxs[i+1])) 
												for i in range(0, len(quote_idxs), 2)] 
									for y in x])
			opens = [x for x in opens if x not in self._ignore_idxs]
			closes = [x for x in closes if x not in self._ignore_idxs]
			print(self._ignore_idxs)
		self.dfs = DFS(opens, closes)



if __name__ == '__main__':
	example1_nested = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)'
	opens = [match.start() for match in re.finditer(re.escape('('), example1_nested)]
	closes = [match.start() for match in re.finditer(re.escape(')'), example1_nested)]
	dfs = DFS(opens, closes)
	print(example1_nested)
	print('Traversal: {}'.format(dfs.traversal))
	print('Tree: {}'.format(dfs.tree))
	print('Levels: {}'.format(dfs.levels))
	print('Intervals: {}\n'.format(dfs.intervals))

	example2_nested = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)")"\')\''
	sqltree = SQLTree(example2_nested)
	print(example2_nested)
	print('Traversal: {}'.format(sqltree.dfs.traversal))
	print('Tree: {}'.format(sqltree.dfs.tree))
	print('Levels: {}'.format(sqltree.dfs.levels))
	print('Intervals: {}\n'.format(sqltree.dfs.intervals))
	assert(dfs.traversal == sqltree.dfs.traversal)
	assert(dfs.tree == sqltree.dfs.tree)
	assert(dfs.levels == sqltree.dfs.levels)
	assert(dfs.intervals == sqltree.dfs.intervals)
	