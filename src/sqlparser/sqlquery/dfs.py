from collections import deque
import sys


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
		self.node_order = ()  # Tuple: (node_idx, ) unique DFS node order

		if len(starts) != len(stops):
			raise ValueError(
				"Error: DFS|constructor() - start and stop indices not equal in length."
			)
		if not starts:
			return
		self._dfs(0)
	
	def _dfs(self, node: int) -> None:
		self.traversal += (node,)
		if node not in self.node_order:
			self.node_order += (node,)
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
	
	def bfs(self, descending = True):
		if descending:
			stack = deque([0])
			while stack:
				current = stack.popleft()
				for child in self.tree[current]:
					stack.append(child)
				yield current
		else:
			revtree = {x: k for k, v in self.tree.items() for x in v}
			seen = set()
			stack = deque([k for k, v in self.tree.items() if not v])
			while stack:
				current = stack.popleft()
				if current != 0:
					parent = revtree[current]
					if parent not in seen:
						seen.add(parent)
						stack.append(parent)
				yield current

