import re
import sys
from collections import deque


def isnamed(query_text: str, start_idx: int, stop_idx: int) -> tuple[bool, list]:
	"""
	Is this (sub-)query or SQL element named (adjacent to an AS)?

	Returns: (bool, [str(element_name),]) if prefix/suffix
				(bool, [(str(col_nam), str(alias_name),]) if object
	"""
	# Check prefix
	prefix = re.search(r'[ \t]*[\"\[]?([^\s()\"\\[\]\']+)[\"\]]?[ \t\r\n]+AS[ \t\r\n]+\(', query_text, flags=re.IGNORECASE | re.MULTILINE)
	suffix = re.search(r'\)[ \t\r\n]+AS[ \t\r\n]+[\"\[]?([^\s()\"\'\]\[]+)[\"\]]?[ \t\r\n]+', query_text, flags=re.IGNORECASE | re.MULTILINE)
	object = re.finditer(r'[ \t]*[\"\[]?([^\s()\"\'\[\]]+)[\"\]]?[ \t\r\n]+AS[ \t\r\n]+[\"\']?([^\s()\"\']+)[\"\']?[ \t]*,?[ \t\r\n]+', query_text, flags=re.IGNORECASE | re.MULTILINE)

	query_val = [bool(x) for x in [prefix, suffix]]
	assert(query_val.count(True) <= 1)
	query_name = [prefix, suffix][query_val.index(True)]
	ret_bool = True if any([prefix, suffix, object]) else False
	if ret_bool:
		if any(query_val):
			ret_val = [query_name.group(1)]
		else:
			ret_val = [(match.group(1), match.group(2)) for match in object]
	else:
		ret_val = []
	return ret_bool, ret_val


def issubquery(query_text: str, require_name: bool = False) -> bool:
	"""
	Determine if text is a TSQL subquery.

	Assumptions:
		- This query does not contain nested queries (remove or mask them ahead of time)
		- Subqueries in TSQL must:
			1. Be a subquery (contain a SELECT)
			2. Begin and end with parentheses
		- Subqueries can:
			3. Be named
	"""
	select = False
	parentheses = False
	name = False
	try:
		opening = query_text.index('(')
	except ValueError:
		return parentheses
	try:
		closing = query_text.index(')')
	except ValueError:
		return parentheses
	parentheses = opening < closing
	try:
		select_idx = re.search(r'select', query_text[(opening+1):closing], flags=re.IGNORECASE).start()
	except AttributeError:
		return select
	select = opening < select_idx < closing
	name = isnamed(query_text)[0] if require_name else True
	return select and parentheses and name


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
	
	def _dfs(self, node: int) -> None:
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
		self.issql = self.issql(query_text)
		self.internal_degree = len(row_ops)
		self.row_ops = row_ops
		self.select = [SQLElement()] * self.internal_degree
		self.from_ = [SQLElement()] * self.internal_degree
		self.join = [SQLElement()] * self.internal_degree
		self.where = [SQLElement()] * self.internal_degree
		self.groupby = [SQLElement()] * self.internal_degree
		self.orderby = [SQLElement()] * self.internal_degree
	
	@staticmethod
	def issql(query_text: str) -> bool:
		"""
		Does this "node" contain an outer-scope SELECT statement?
		"""
		quote_idxs = [m.start() for m in re.finditer('[\'"]', query_text)]
		assert(len(quote_idxs) % 2 == 0)
		ignore_idxs = set([y for x in [list(range(quote_idxs[i], quote_idxs[i+1])) 
											for i in range(0, len(quote_idxs), 2)] 
								for y in x])
		query_nostring = ''.join(x for i, x in enumerate(query_text) if i not in ignore_idxs)
		return bool(re.search(r'select', query_nostring, flags=re.IGNORECASE))
		

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
		self._sqlkeywords = set((
			'SELECT', 'FROM', 'WHERE',
			'INSERT', 'INTO', 'UPDATE', 'DELETE',
			'CREATE', 'ALTER', 'DROP', 'JOIN', 
			'GROUP BY', 'ORDER BY', 'HAVING', 'DISTINCT',
			'WITH', 'DECLARE', 'SET', ';',
			'BEGIN', 'END', ',', ')', '(',
			'UNION', 'INTERSECT', 'EXCEPT', 'OUTER',
			'INNER', 'FULL', 'OVER', 'LEFT',
			'RIGHT'
		))
		self.variables = {}
		self.tree = {}
		self.root = SQLNode
		self.original_query = full_query_text
		self.flattened_query = None
		self.symbolic_query = ''
		self.symbolic_intervals = {}
		self.working_query = full_query_text
		if not full_query_text:
			sys.stderr.write('ERROR: query text passed to SQLTree must not be empty\n')
			raise ValueError
		if ignore_comments:
			self.working_query = self._remove_comments(self.working_query)
		
		if flatten:
			self.flattened_query = self._flatten(self.working_query)
			self.working_query = self.flattened_query

		# Create tree
		# Break query into statements
		self.working_query = re.sub(r'^\s*begin', '', self.working_query, flags=re.IGNORECASE)
		self.working_query = re.sub(r'\s*end\s*;?\s*$', '', self.working_query, flags=re.IGNORECASE)
		self.working_query = self._remove_whitespace(self.working_query)
		
		if 'SELECT' not in self.working_query.upper():
			sys.stderr.write('ERROR: query text passed to SQLTree must contain a SELECT statement')
		statements = [self._remove_whitespace(x) for x in self.working_query.split(';')]
		selects = ['SELECT' in x.upper() for x in statements]
		if selects.count(True) > 1:
			sys.stderr.write('ERROR: query text passed to SQLTree must contain only one SELECT statement')
		
		for s in statements:
			self._extract_variables(s)
		self.working_query = statements[selects.index(True)]  # Keep only main query for tree
		
		# DFS -> tree by subquery
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
		self.dfs = DFS(opens, closes)

		# Initiatlize symbolic query by replacing parentheticals temporarily
		self._init_symbolic_query()
		print(self.symbolic_query)
		# sys.exit()

		# Check for CTE with leaf -> root traversal
		for node in self.dfs.bfs(descending=False):
			if node != 0:
				start, stop = self.dfs.intervals[node]
				subquery_context = self._get_query_context(self.working_query, start, stop, include_body=False)
				ctes = {node: self._iscte(subquery_context, node)}
				print(node, start, stop, ctes[node])

	def __repr__(self) -> str:
		"""
		Print representation 
		"""
		if self._pprint:
			return self._prettyprint()
		else:
			return self.working_query
	
	def _extract_variables(self, query_text:str) -> None:
		"""
		Capture variable name, type, and value from DECLARE and SET statements 
		"""
		match = re.search(r'declare (\S+) = ([A-Za-z2]+)[\(;]?', query_text, flags=re.IGNORECASE)
		if match:
			varname = match.group(1)
			vartype = match.group(2)
			try:
				simpletype = self._typemap[vartype]
			except KeyError:
				simpletype = 'TEXT'
			self.variables[varname] = [simpletype, None]
		match = re.search(r'set (\S+) = [\"\']?([^\s()\"\']+)[\"\']?[;]?', query_text, flags=re.IGNORECASE)
		if match:
			varname = match.group(1)
			varvalue = match.group(2)
			self.variables[varname][1] = varvalue
	
	def _flatten(self, query_text: str) -> str:
		"""
		Remove all white space except spaces for internal processing or compact representation
		"""
		flattened = re.sub(r'\s', ' ', query_text)
		flattened = re.sub(r'\s{2,}', ' ', flattened)
		flattened = flattened.strip()
		return flattened
	
	def _get_query_context(self, query_text: str, start: int, stop: int, include_body: bool = True) -> str:
		pretext = []
		posttext = []
		for word in query_text[:start].split()[::-1]:
			if word in self._sqlkeywords or word[0] in self._sqlkeywords or word[-1] in self._sqlkeywords:
				break
			pretext.append(word)
		for word in query_text[(stop+1):].split():
			
			if word in self._sqlkeywords or word[0] in self._sqlkeywords or word[-1] in self._sqlkeywords:
				break
			posttext.append(word)
		if include_body:
			retval = ' '.join(pretext[::-1]) + ' ' + query_text[start:(stop+1)] + ' ' + ' '.join(posttext)
		else:
			retval = ' '.join(pretext[::-1]) + ' ' + query_text[(start+1):stop] + ' ' + ' '.join(posttext)
		return retval
	
	def _init_symbolic_query(self) -> None:
		rev_idx_intervals = {}
		ignore_idxs = set()
		for node, (start, stop) in self.dfs.intervals.items():
			rev_idx_intervals[start] = '[@{}]'.format(node)
			ignore_idxs.update(list(range(start, stop)))
		for i, c in enumerate(self.working_query):
			if i in rev_idx_intervals:
				self.symbolic_query += rev_idx_intervals[i]
			elif i not in ignore_idxs:
				self.symbolic_query += c
		# TODO: map dfs.intervals to self.symbolic_intervals for _iscte testing

	def _iscte(self, query_text: str, node: int) -> bool:
		"""
		Common Table Expressions in TSQL must:
			1. Be named
			2. Be a subquery (contain a SELECT)
			3. Begin and end with parentheses
			4. Be declared between the WITH and outer SELECT statements
		
		Items 1-3 are checked by issubquery(), and 4 is checked here against the working_query outer scope
		"""
		subquery = issubquery(query_text, require_name=True)
		try:
			with_end = re.search(r'\s?with\s', self.working_query, flags=re.IGNORECASE | re.MULTILINE).end()
		except AttributeError:
			return False
		select_idxs = [match.start() for match in 
				 		re.finditer(r'\s?select\s', self.symbolic_query, flags=re.IGNORECASE | re.MULTILINE)]
		print(with_end, self.dfs.intervals[node][0], self.dfs.intervals[node][1], select_idxs[0])
		cte_scope = with_end < self.dfs.intervals[node][0] < self.dfs.intervals[node][1] < select_idxs[0]
		return subquery and cte_scope

	
	def _prettyprint(self) -> str:
		"""
		Format query to be more readable using internal structure information
		"""
	
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

	def _remove_whitespace(self, query_text: str) -> str:
		return re.sub(r'^\s*', '', re.sub(r'\s*$', '', query_text))
	

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

		WITH
		cte1 AS
		(
			SELECT *
			FROM othertable1
			JOIN othertable2
				ON othertable1.field1 = othertable2.field2
			WHERE othertable1.field3 = 'filter1'
		),
		cte2 AS
		(
			SELECT
				othertable3.field1 AS "myvar1",
				cte1.field1 AS 'myvar2'
			FROM othertable3
			JOIN cte1
				ON othertable3.field2 = cte1.field1
		),
		cte3 AS
		(
			SELECT
				othertable4.key1,
				SUM(othertable4.count) AS sumcount
			FROM othertable4
			WHERE othertable4.field1 = 'value1'
			GROUP BY
				othertable4.count
		)
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
		JOIN cte3
			ON mytable3.key1 = cte3.key1
		JOIN cte2
			ON mytable4.key1 = cte2.myvar1
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
