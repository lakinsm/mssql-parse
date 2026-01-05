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
		if not starts:
			return
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


class SQLElement:
	"""
	One clause of SQL (sub-)query.
	"""
	def __init__(self):
		self.text = ''
		self.fields = []
		self.tables = []


class SQLNode:
	"""
	One (sub-)query and its components.
	"""
	def __init__(self, query_text: str, row_ops: list = []) -> None:
		self.internal_degree = len(row_ops)
		self.row_ops = row_ops
		self.select = [SQLElement()] * self.internal_degree
		self.from_ = [SQLElement()] * self.internal_degree
		self.join = [SQLElement()] * self.internal_degree
		self.where = [SQLElement()] * self.internal_degree
		self.groupby = [SQLElement()] * self.internal_degree
		self.orderby = [SQLElement()] * self.internal_degree
		

class SQLTree:
	"""
	Stores query node types and relationships in tree structures.
	Assumptions:
		- Only a single query statement is contained within
		- BEGIN and END are optional
		- Variable definitions can optionally be terminated with semi-colons
		- Only one other semi-colon exists to denote the end of the actual query
		- All (sub-)queries contain a single SELECT statement, which represent single nodes
		- (Sub-)queries with row operations (UNION, INTERSECT, EXCEPT) represent a single node with degree > 0
		- Aliases will be replaced where applicable unless specified otherwise or:
			-- Aliases are a part of a mutated (sub-)query and not directly queried
			-- Aliases name a self join or table joined again in the same context with different join conditions
	"""
	def __init__(
			self, 
			full_query_text: str, 
			ignore_strings: bool = True, 
			ignore_comments: bool = True,
			flatten: bool = True,
			expand_aliases: bool = True,
			pprint: bool = True
	) -> None:
		self._ignore_idxs = set()
		self._pprint = pprint
		self._outer_statements = []
		self._typemap = {
			'NVARCHAR': 'TEXT',
			'VARCHAR': 'TEXT',
			'NCHAR': 'TEXT',
			'CHAR': 'TEXT',
			'BINARY': 'TEXT',
			'VARBINARY': 'TEXT',
			'TEXT': 'TEXT',
			'TINYTEXT': 'TEXT',
			'MEDIUMTEXT': 'TEXT',
			'LONGTEXT': 'TEXT',
			'TINYBLOB': 'BLOB',
			'MEDIUMBLOB': 'BLOB',
			'LONGBLOB': 'BLOB',
			'BIT': 'INTEGER',
			'TINYINT': 'INTEGER',
			'BOOL': 'INTEGER',
			'SMALLINT': 'INTEGER',
			'MEDIUMINT': 'INTEGER',
			'INT': 'INTEGER',
			'INTEGER': 'INTEGER',
			'BIGINT': 'INTEGER',
			'SMALLMONEY': 'REAL',
			'MONEY': 'REAL',
			'FLOAT': 'REAL',
			'DOUBLE': 'REAL',
			'DECIMAL': 'REAL',
			'DEC': 'REAL',
			'REAL': 'REAL',
			'DATE': 'TEXT',
			'DATETIME': 'TEXT',
			'DATETIME2': 'TEXT',
			'SMALLDATETIME': 'TEXT',
			'DATETIMEOFFSET': 'TEXT',
			'TIMESTAMP': 'TEXT',
			'TIME': 'TEXT',
			'YEAR': 'TEXT'
		}
		self.variables = {}
		self.tree = {}
		self.original_query = full_query_text
		self.flattened_query = None
		self.working_query = full_query_text
		if not full_query_text:
			sys.stderr.write('ERROR: query text passed to SQLTree must not be empty\n')
			raise ValueError
		if ignore_comments:
			self.working_query = self._remove_comments(self.working_query)
		
		if flatten:
			self.flattened_query = self._flatten(self.working_query)
			self.working_query = self.flattened_query
		
		opens = [match.start() for match in re.finditer(re.escape('('), self.working_query)]
		closes = [match.start() for match in re.finditer(re.escape(')'), self.working_query)]
		if ignore_strings:
			quote_idxs = [m.start() for m in re.finditer('[\'"]', self.working_query)]
			assert(len(quote_idxs) % 2 == 0)
			self._ignore_idxs = set([y for x in [list(range(quote_idxs[i], quote_idxs[i+1])) 
												for i in range(0, len(quote_idxs), 2)] 
									for y in x])
			opens = [x for x in opens if x not in self._ignore_idxs]
			closes = [x for x in closes if x not in self._ignore_idxs]

		# Create tree
		# Break query into statements
		self.working_query = re.sub(r'^\s*begin', '', self.working_query, flags=re.IGNORECASE)
		self.working_query = re.sub(r'\s*end\s*;?\s*$', '', self.working_query, flags=re.IGNORECASE)
		self.working_query = re.sub(r'^\s*', '', self.working_query)
		self.working_query = re.sub(r'\s*$', '', self.working_query)
		if 'SELECT' not in self.working_query.upper():
			sys.stderr.write('ERROR: query text passed to SQLTree must contain a SELECT statement')
		statements = self.working_query.split(';')
		selects = ['SELECT' in x.upper() for x in statements]
		if selects.count(True) > 1:
			sys.stderr.write('ERROR: query text passed to SQLTree must contain only one SELECT statement')
		print(selects)		
		
		# DFS -> tree by subquery
		self.dfs = DFS(opens, closes)



	def __repr__(self) -> str:
		"""
		Print representation 
		"""
		if self._pprint:
			return self._prettyprint()
		else:
			return self.working_query
	
	def _remove_comments(self, query_text: str) -> str:
		"""
		Remove block and inline comments from query text
		"""
		block_starts = [match.start() for match in re.finditer(re.escape('/*'), query_text)]
		block_stops = [match.end() for match in re.finditer(re.escape('*/'), query_text)]
		block = DFS(block_starts, block_stops)
		inline_matches = re.finditer(r'--.*$', query_text, re.MULTILINE)
		try:
			inline_starts, inline_stops = zip(*[(match.start(), match.end()) for match in inline_matches])
		except ValueError:
			inline_starts, inline_stops = [], []
		inline = DFS(inline_starts, inline_stops)
		comment_idxs = set([x for y in 
					  		[range(m, n) for m, n in list(block.intervals.values()) + list(inline.intervals.values())] 
							for x in y])
		return ''.join([x for i, x in enumerate(query_text) if i not in comment_idxs])
	
	def _flatten(self, query_text: str) -> str:
		"""
		Remove all white space except spaces for internal processing or compact representation
		"""
		flattened = re.sub(r'\s', ' ', query_text)
		flattened = re.sub(r'\s{2,}', ' ', flattened)
		flattened = flattened.strip()
		return flattened
	
	def _prettyprint(self) -> str:
		"""
		Format query to be more readable using internal structure information
		"""



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

	example2_nested = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)")"\')\' SELECT'
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

	example3_comments = """
		/* This is an example query with comments.
		Select the following examples from example
		for example and order by example.
		*/
		BEGIN

		-- Some variable definitions
		DECLARE mychar1 = NVARCHAR(80);
		SET mychar1 = 'example4';

		SELECT 
			mytable1.*,
			mytable2.foo1,
			mytable2.bar1,
			mytable3.foo1 AS "t3foo1",
			mytable4.bar2,  -- Example comment
			mytable5.*
		FROM mytable1
		JOIN mytable2
			ON mytable1.key1 = mytable2.key1
			AND mytable1.var1 = 'example'
		-- This table join is necessary
		FULL JOIN mytable3
			ON mytable2.key2 = mytable3.key1
		LEFT JOIN mytable4
			ON mytable3.key3 = mytable4.key1
			AND mytable2.key1 = mytable4.key2
			AND mytable1.key2 = mytable4.key3
		RIGHT JOIN mytable5
			ON mytable1.key1 = mytable5.key1
		
		UNION ALL  -- Introduce internal degree

		SELECT
			mytable3.*,
			mytable4.*
		FROM mytable3
		JOIN mytable4
			ON mytable3.key3 = mytable4.key1
		JOIN (  -- Subquery calculates group sum from most recent date
			SELECT groupid1, MAX(field1), SUM(field2) FROM mytable6 WHERE foobar = 'example2' 
			GROUP BY groupid1
		) AS "groupsum"
		WHERE mytable3.field5 = "bar4"
		ORDER BY mytable1.key1 DESC  -- Order by request of end users
		
		END;

		/*
		-- Trailing comment with indentation formatting because?
		" foo ' example ( bar)
		*/
	"""
	sqltree = SQLTree(example3_comments)
	print(sqltree.working_query)
