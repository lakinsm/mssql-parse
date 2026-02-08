import re
import sys
import globals
from collections import deque


def isnamed(query_text: str) -> tuple[bool, list]:
	"""
	Is this (sub-)query or SQL element named (adjacent to an AS)?

	Returns: (bool, [str(element_name),]) if prefix/suffix
				(bool, [(str(col_nam), str(alias_name),]) if object
	"""
	# Check prefix/suffix for subqueries/CTEs
	prefix = globals.TSQL_SUBQUERY_ALIAS_PREFIX.search(query_text)
	suffix = globals.TSQL_SUBQUERY_ALIAS_SUFFIX.search(query_text)

	# Check for tables/vars with aliases
	object_matches = []
	consumed = set()
	# 1. table.var AS? alias
	for m in globals.TSQL_VARTABLE_NAMED.finditer(query_text):
		start = m.start()
		stop = start + len(m.groups()[0])
		match_interval = set(range(start, stop))
		if not consumed.intersection(match_interval):
			table, varname, alias = m.group('table', 'varname', 'alias')
			if alias not in globals.ODBC_KEYWORDS:
				object_matches.append(('{}.{}'.format(table, varname), alias),)
		consumed.update(match_interval)

	# 2. var AS? alias
	for m in globals.TSQL_VAR_NAMED.finditer(query_text):
		start = m.start()
		stop = start + len(m.groups()[0])
		match_interval = set(range(start, stop))
		if not consumed.intersection(match_interval):
			varname, alias = m.group('varname', 'alias')
			if alias not in globals.ODBC_KEYWORDS:
				object_matches.append((varname, alias),)
		consumed.update(match_interval)

	query_val = [bool(x) for x in [prefix, suffix]]
	true_count = query_val.count(True)
	assert(true_count <= 1)
	if true_count:
		query_name = [prefix, suffix][query_val.index(True)]
	ret_bool = True if any([prefix, suffix, object_matches]) else False
	if ret_bool:
		if any(query_val):
			ret_val = [query_name.group(1)]
		else:
			ret_val = object_matches
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
	query_flag = globals.IS_SQL_QUERY.search(query_text) is not None
	name = isnamed(query_text)[0] if require_name else True
	return query_flag and name


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

		assert(len(starts) == len(stops))
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


class SQLElement:
	"""
	One clause of SQL (sub-)query.
	"""
	def __init__(self, keyword: str, start: int, stop: int, text: str, non_subqueries: dict):
		self._unclaimedvars = set()
		self._basetables = {}
		self.text = text
		self.start = start
		self.stop = stop
		self.tablesvars = {}
		self.aliases = {}
		self.relations = {}
		self.non_subqueries = non_subqueries

		print('\n{}'.format(text))
		# TODO: WITH, FROM, WHERE, OFFSET, FETCH
		if keyword in ('PRETEXT', 'SELECT', 'GROUP BY', 'ORDER BY'):
			self._parse_tables_vars(text)
		elif keyword == 'WITH':
			self._parse_ctes(text)
		elif keyword == 'FROM':
			self._parse_joins(text)
		elif keyword == 'WHERE':
			x = 1
		elif keyword == 'OFFSET':
			x = 1
		elif keyword == 'FETCH':
			x = 1
		else:
			sys.stderr.write('ERROR: keyword not in expected keywords, provided: {}\n'.format(
				keyword
			))
			raise(ValueError)
		
		print('TABLESVARS: ', self.tablesvars)
		print('ALIASES: ', self.aliases)
		print('UNCLAIMEDVARS: ', self._unclaimedvars)
	
	def _parse_joins(self, sql_text: str) -> None:
		"""
		Store table joins and relations.
		"""
		# Find keyword boundaries and parse each clause
		join_boundaries = []
		join_clauses = []
		consumed = set()
		for m in globals.TSQL_JOIN_JOINTYPES.finditer(sql_text):
			start = m.start()
			stop = start + len(m.group()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				jointype = m.group('jointype')
				join_boundaries.append((start, jointype),)
			consumed.update(match_interval)

		for i in range(len(join_boundaries)):
			start, jointype = join_boundaries[i]
			if i == 0:
				pretext = sql_text[:start]
				if pretext.strip():
					join_clauses.append((0, start, 'FROM'))
			if (i+1) == len(join_boundaries):
				join_clauses.append((start, len(sql_text), jointype),)
			else:
				next_start = join_boundaries[i+1][0]
				join_clauses.append((start, next_start, jointype),)

		for start, stop, jointype in join_clauses:
			clause_text = sql_text[start:stop]
			print(start, stop, jointype, '\t{}'.format(clause_text))
			expanded = set()
			child_q = deque([clause_text])
			# Find table relations in non-subquery
			opens = deque([0])
			while child_q:
				self._non_subquery_dfs(child_q.popleft(), opens, expanded)
			if jointype.upper() == 'FROM':
				basetable = globals.TSQL_JOIN_BASETABLE.search(clause_text).group('basetable')
				self.relations.setdefault(basetable, [])
				print('Basetable: {}'.format(basetable))  # TODO: add to relation data
		print(self.relations)
		sys.exit()

	def _non_subquery_dfs(self, substring: str, opens: deque, seen: set) -> None:
		"""
		Add characters to output queue DFS order.
		"""
		# Find current level relations here - keep symbolics
		# - use first symbolic only for nesteds, but use all for same-level
		self._extract_relations(self._with_outer_symbolics(substring), opens[-1])
		for m in globals.TSQL_SYMBOLIC.finditer(substring):
			symb = int(m.group('symb'))
			if symb in self.non_subqueries and symb not in seen:
				seen.add(symb)
				self._basetables.setdefault(symb, self._basetables[opens[-1]])
				opens.append(symb)
				self._non_subquery_dfs(self.non_subqueries[symb], opens, seen)
		opens.pop()
	
	@staticmethod
	def _with_outer_symbolics(clause_text: str) -> str:
		"""
		Return the clause_text with only top-level symbolics; remove nested symbolics.
		"""
		matches = globals.TSQL_SYMBOLIC_OUTER.finditer(clause_text)
		exclude_idxs = set(x for y in (range(m.end('outer_symb'), m.end()) for m in matches) for x in y)
		return ''.join(x for i, x in enumerate(clause_text) if i not in exclude_idxs)
	
	def _extract_relations(self, clause_text: str, current_node: int) -> None:
		"""
		Extract table/column relations, intended for from/join clauses.
		"""
		print('\tNode: {}\t{}'.format(current_node, clause_text))
		# Parse by major operator (AND|OR|NOT)
		self._basetables.setdefault(current_node, None)
		cond_clause_starts = [m.span('majop') for m in globals.TSQL_JOIN_MAJOROPS.finditer(clause_text)]
		for i in range(len(cond_clause_starts)):
			start, stop = cond_clause_starts[i]
			if i == 0:
				cond_clause_text = clause_text[:start]
				basetable = globals.TSQL_JOIN_BASETABLE.search(cond_clause_text)
				if basetable:
					self._basetables[current_node] = basetable.group('basetable')
					self.relations.setdefault(self._basetables[current_node], [])
				print('\t\tBasetable: {}'.format(self._basetables[current_node]))  # TODO: add to relation data
			if (i+1) == len(cond_clause_starts):
				cond_clause_text = clause_text[stop:]
			else:
				next_start = cond_clause_starts[i+1][0]
				cond_clause_text = clause_text[stop:next_start]
			print('\t\tMAJOP Clause: {}'.format(cond_clause_text))
			# Parse further by comparison operator -> LHS - RHS
			op_match = globals.TSQL_JOIN_ALLOPS.finditer(cond_clause_text)
			op_starts = [x.span('op') for x in op_match]
			print('\t\t\tOp: {}'.format([x.group('op') for x in globals.TSQL_JOIN_ALLOPS.finditer(cond_clause_text)]))
			if not self._basetables[current_node]:
				sys.stderr.write('ERROR: No basetable found for node {} conditional clause: {}\n'.format(
					current_node, 
					cond_clause_text
				))
				raise ValueError
			if not op_starts:
				relations = self._extract_tablevar(cond_clause_text)
				self.relations.setdefault(self._basetables[current_node], []).append(relations[0])
			else:
				for j in range(len(op_starts)):
					x = 1  # TODO: extract_tablevar for rhs/lhs w/ ops, may need to verify field exists in DFS later
					# TODO: self.relations probably needs to be split out by current_node to handl nested symbolics

	@staticmethod
	def _extract_tablevar(rhslhs_text: str) -> tuple[str, str]:
		"""
		Return table - var relation if present (no alias searching here),
		otherwise return (None, var).  Symbolics are included as vars.
		"""
		seen = set()
		seen_idxs = set()
		table_vars = []
		for m in globals.TSQL_RHSLHS_VARTABLE_NAMED.finditer(rhslhs_text):
			table, var = m.groups('table', 'varname')
			spans = [m.start('table'), m.end('table'), m.start('varname'), m.end('varname')]
			spans = (min(x for x in spans if x), max(x for x in spans if x))
			match_idxs = set(x for x in range(spans[0], spans[1]))
			unique = '-'.join([x if x else '' for x in (table, var)])
			if (unique not in seen) and not (seen_idxs.intersection(match_idxs)):
				table_vars.append((table, var),)
				seen.add(unique)
				seen_idxs.update(match_idxs)
		for m in globals.TSQL_RHSLHS_VARTABLE_UNNAMED.finditer(rhslhs_text):
			var = m.group('varname')
			match_idxs = set(x for x in range(m.start('varname'), m.end('varname')))
			unique = '-'.join([x if x else '' for x in (None, var)])
			if (unique not in seen) and not (seen_idxs.intersection(match_idxs)):
				table_vars.append((None, var),)
				seen.add(unique)
				seen_idxs.update(match_idxs)
		return table_vars
	
	def _parse_ctes(self, sql_text: str) -> None:
		"""
		Store CTE alias and subquery relations.
		"""
		for m in globals.TSQL_CTES.finditer(sql_text):
			table, alias = m.group('table', 'alias')  # table will be a symbolic here
			self.tablesvars.setdefault(table, set())
			self.aliases[alias] = (None, table)  # table alias, no var

	def _parse_tables_vars(self, sql_text:str) -> None:
		"""
		Store table, var, and alias info into self.tablesvars and self.aliases 
		with None if element missing.
		"""
		consumed = set()
		# 1. table.var AS alias
		for m in globals.TSQL_VARTABLE_NAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				table, varname, alias = m.group('table', 'varname', 'alias')
				self.tablesvars.setdefault(table, set()).add(varname)
				if alias not in globals.ODBC_KEYWORDS:
					self.aliases[alias] = (varname, table)
			consumed.update(match_interval)

		# 2. table.var
		for m in globals.TSQL_VARTABLE_UNNAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				table, varname = m.group('table', 'varname')
				self.tablesvars.setdefault(table, set()).add(varname)
			consumed.update(match_interval)

		# 3. var AS alias
		for m in globals.TSQL_VAR_NAMED.finditer(sql_text):
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
		for m in globals.TSQL_VAR_UNNAMED.finditer(sql_text):
			start = m.start()
			stop = start + len(m.groups()[0])
			match_interval = set(range(start, stop))
			if not consumed.intersection(match_interval):
				varname, alias = m.group('varname')
				self._unclaimedvars.add(varname)
			consumed.update(match_interval)


class SQLNode:
	"""
	One (sub-)query and its components.

	- Main
		- SELECT
			- DISTINCT, TOP
			- AS, =
			- variables plain, "", [] AS plain, "", ''
				- subquery +/- named
				- Other keywords +/- ()
		- FROM
			- tables plain, "", [] AS plain, '', ""
			- JOIN table plain, "", [] AS plain, '', ""; subquery AS plain, "", []
				- OUTER, INNER, LEFT, RIGHT, FULL OUTER
				- ON table.var plain, "", [] = table.var plain, "", []
				- ON subquery AS plain, "", []
		- WHERE
			- table.var plain, "", []
				- Operator =, <>, >, >=, <=, !=, IS NULL, IS NOT NULL, &, |, ^
				- AND, OR, NOT, BETWEEN, IN, LIKE, EXISTS +/- NOT
		- GROUP BY
			- HAVING
		- ORDER BY
			- Variable +/- <order>, ...
			- Order: ASC, DESC
		- OFFSET
			- ROWS
		- FETCH
			- NEXT <int> ROWS ONLY
	- Row operations
		- UNION +/- ALL
		- INTERSECT
		- EXCEPT
	- Table modifications
		- INSERT INTO
		- INTO
		- ___ TABLE
			- CREATE, ALTER, DROP
			- Suffix: IF/IF NOT EXISTS
	"""
	def __init__(self, query_text: str, non_subqueries: dict) -> None:
		self.issql = self.issql(query_text)
		self.row_ops = [(m.group(1), m.start(), m.end()) for m in globals.TSQL_ROWOPS.finditer(query_text)]
		self.internal_degree = len(self.row_ops) + 1
		self.query_text = []
		self.non_subqueries = non_subqueries
		if self.row_ops:
			self.query_text.append(query_text[:self.row_ops[0][1]])
			for i in range(len(self.row_ops)):
				try:
					self.query_text.append(query_text[self.row_ops[i][2]:self.row_ops[i+1][1]])
				except IndexError:
					self.query_text.append(query_text[self.row_ops[i][2]:])
		else:
			self.query_text.append(query_text)
		
		statement_boundaries = []
		for r in range(self.internal_degree):
			statement_boundaries.append({})
			keyword_breaks = [(m.start(), m.group(1).upper()) 
								for m in globals.TSQL_STATEMENTS.finditer(self.query_text[r])]
			for i in range(len(keyword_breaks)):
				start, keyword = keyword_breaks[i]
				if i == 0:
					pretext = self.query_text[r][:start]
					if pretext.strip():
						statement_boundaries[r].setdefault('PRETEXT', []).append((0, start),)
				if (i+1) == len(keyword_breaks):
					statement_boundaries[r].setdefault(keyword, []).append((start, len(self.query_text[r])),)
				else:
					next_start = keyword_breaks[i+1][0]
					statement_boundaries[r].setdefault(keyword, []).append((start, next_start),)
		
		self.clause = [{
			'PRETEXT': None,
			'WITH': None,
			'SELECT': None,
			'FROM': None,
			'WHERE': None,
			'GROUP BY': None,
			'ORDER BY': None,
			'OFFSET': None,
			'FETCH': None
		} for _ in  range(self.internal_degree)]
		for r in range(self.internal_degree):
			for keyword, breaks in statement_boundaries[r].items():
				for start, stop in breaks:
					self.clause[r][keyword] = SQLElement(
						keyword,
						start,
						stop,
						self.query_text[r][start:stop],
						self.non_subqueries
					)
		print(self.clause)
		# TODO: resolve unclaimed vars within elements
		# TODO: validate selects & by clauses with tables in from/joins
	
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
		self._typemap = globals.TYPEMAP
		self._sqlkeywords = globals.ODBC_KEYWORDS
		self.variables = {}
		self.tree = {}
		self.root = SQLNode
		self.original_query = full_query_text
		self.flattened_query = None
		self.symbolic_query = ''
		self.symbolic_intervals = {}
		self.symbolic_clauses = {}
		self.working_query = full_query_text
		self.ctes = {}
		self.subqueries = {}
		self.non_subqueries = {}  # parenthetical clauses that are not queries
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

		# Initiatlize symbolic query and SQLNode objects
		self._init_symbolic_query()

		# Identify subqueries and CTEs
		for node in self.dfs.node_order:
			if node != 0:
				start, stop = self.dfs.intervals[node]
				pretext, posttext = self._get_query_context(self.working_query, start, stop)
				with_context = '{} {} {}'.format(pretext, self.symbolic_clauses[node], posttext)
				cte_flag = self._iscte(
					 # symbolic_clause to avoid detecting nested selects
					with_context, 
					node
				)
				subquery_flag = issubquery(self.symbolic_clauses[node], require_name=False)

				if cte_flag:
					self.ctes[node] = isnamed(with_context)[1][0]
				if subquery_flag:
					subquery_name = isnamed(with_context)
					if subquery_name[0]:
						self.subqueries[node] = subquery_name[1][0]
					else:
						self.subqueries[node] = None  # subqueries can be inline and not named
				else:
					self.non_subqueries[node] = self.symbolic_clauses[node]
				if cte_flag:
					cte_val = self.ctes[node] + ' - CTE'
				elif subquery_flag:
					cte_val = self.subqueries[node] + ' - SQ'
				else:
					cte_val = ''
				# print('{}\t{}'.format('({}){}'.format(cte_val, node), '{} {} {}'.format( pretext, self.symbolic_clauses[node], posttext)))
				# print('\n')

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
	
	def _get_query_context(self, query_text: str, start: int, stop: int) -> tuple[str, str]:
		pretext = []
		posttext = []
		for word in query_text[:start].split()[::-1]:
			if word in self._sqlkeywords or word[0] in self._sqlkeywords or word[-1] in self._sqlkeywords:
				if word != 'AS':
					break
			pretext.append(word)
		for word in query_text[(stop+1):].split():
			if word in self._sqlkeywords or word[0] in self._sqlkeywords or word[-1] in self._sqlkeywords:
				if word != 'AS':
					break
			posttext.append(word)
		return ' '.join(pretext[::-1]), ' '.join(posttext)
	
	def _init_symbolic_query(self) -> None:
		rev_idx_starts = {}
		rev_idx_stops = set()
		ignore_idxs = set()

		# For subquery tokenization, mask BFS and create symbolic nodes
		# to prevent inclusion of subquery context in node characterization
		stack = deque()
		level_op = 0
		for node in self.dfs.bfs(descending=False):
			# TODO: SQLNode creation
			if node != 0:
				start, stop = self.dfs.intervals[node]
			else:
				start, stop = 0, len(self.working_query)
			node_contents = ''
			for i in range(start, stop):
				if i in rev_idx_starts:
					child = rev_idx_starts[i]
					if level_op < 0:
						node_contents += '.'
					elif level_op == 1 and stack:
						node_contents += '-'
					elif level_op > 1 and stack:
						node_contents += '^' * level_op
					node_contents += '<@{}>'.format(rev_idx_starts[i])
					stack.append(child)
					level_op = -1
				elif i in rev_idx_stops:
					level_op = max(1, level_op+1)
					if stack:
						stack.pop()  # can manipulate child nodes here if needed for SQLNode
				elif i not in ignore_idxs:
					node_contents += self.working_query[i]
					level_op = 0
			if node != 0:
				node_contents += self.working_query[stop]
				rev_idx_starts[start] = node
				rev_idx_stops.add(stop)
				ignore_idxs.update(list(range(start, stop)))
			self.symbolic_clauses[node] = node_contents

		# For query as a whole, mask DFS
		stack = deque()
		level_op = 0
		for i, c in enumerate(self.working_query):
			if i in rev_idx_starts:
				node = rev_idx_starts[i]
				self.symbolic_intervals[node] = [len(self.symbolic_query), None]
				if level_op < 0:
					self.symbolic_query += '.'
				elif level_op == 1 and stack:
					self.symbolic_query += '-'
				elif level_op > 1 and stack:
					self.symbolic_query += '^' * level_op
				self.symbolic_query += '<@{}>'.format(rev_idx_starts[i])
				stack.append(node)
				level_op = -1
			elif i in rev_idx_stops:
				level_op = max(1, level_op+1)
				if stack:
					self.symbolic_intervals[stack.pop()][1] = len(self.symbolic_query)
			elif i not in ignore_idxs:
				self.symbolic_query += c
				level_op = 0

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
		cte_scope = with_end <= self.symbolic_intervals[node][0] <= self.symbolic_intervals[node][1] <= select_idxs[0]
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
	# print(example1_nested)
	# print('Traversal: {}'.format(dfs.traversal))
	# print('Tree: {}'.format(dfs.tree))
	# print('Levels: {}'.format(dfs.levels))
	# print('Intervals: {}\n'.format(dfs.intervals))

	example2_nested = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)")"\')\' SELECT'
	sqltree = SQLTree(example2_nested)
	# print(example2_nested)
	# print('Traversal: {}'.format(sqltree.dfs.traversal))
	# print('Tree: {}'.format(sqltree.dfs.tree))
	# print('Levels: {}'.format(sqltree.dfs.levels))
	# print('Intervals: {}\n'.format(sqltree.dfs.intervals))
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
		DECLARE mydate1 = DATE;
		SET mychar1 = 'example4';
		SET mydate1 = '2100-10-15';

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
		),
		cte4 AS
		(
			SELECT *,
			(SELECT TOP 1 keyvar FROM subtable1 WHERE keyvar = 'keyvalue') "aliassqval"
			FROM blankettable globalias
		),
		cte6 AS
		(
			SELECT
				othertable4.key1,
				othertable4.key2
			FROM othertable4
			WHERE 
				key3 <> 'implied column value'
				AND othertable4.key4 >= 1
		),
		cte5 AS
		(
			SELECT
				unnamedvar1 AS key1,
				unnamedvar2 as key2
			FROM relativetable reltable
			JOIN cte6
				USING (key1, [key2])
			WHERE unnamedvar1 = 'othervalue1'
		)
		SELECT 
			mytable1.*,
			mytable2.foo1,
			mytable2.bar1 b1,
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
			AND 
			( 
				mytable2.key1 = mytable4.key2
				OR mytable1.key2 = mytable4.key3
				AND
				(
					mytable1.key2 <> mytable4.key2
				)
			)
			AND mytable1.key1 NOT IN mytable4.key2
		RIGHT JOIN mytable5
			ON mytable1.key1 = mytable5.key1
		
		UNION ALL  -- Introduce internal degree

		SELECT
			mytable3.*,
			mt4.*
		FROM mytable3
		JOIN mytable4 mt4
			ON mytable3.key3 = mt4.key1
		JOIN (  -- Subquery calculates group sum from most recent date
			SELECT groupid1, MAX(field1), SUM(field2) FROM mytable6 WHERE foobar = 'example2' 
			GROUP BY groupid1
		) "groupsum"
			ON mt4.key1 = groupsum.groupid1
		JOIN cte3
			ON mytable3.key1 = cte3.key1
		JOIN cte2
			ON LEFT(mytable4.key1, 3) LIKE '%' + cte2.myvar1 + '%'
		FULL JOIN cte4
			ON ('/mystring/' || mytable4.key1) = cte4.key1
			AND (mytable3.string1 || mytable.key1) = cte4.key1
		LEFT JOIN cte5
			ON mytable4.key2 = cte5.key2
			AND cte5.unnamedvar1 = "filtervalue"
			AND cte5.datevar1 BETWEEN mytable4.date1 AND mytable4.date2
			AND cte5.datevar2 = @mydate1
		WHERE 
			mytable3.field5 = "bar4"
			AND mytable4.date1 BETWEEN mytable4.date1 AND '2100-01-01'
		ORDER BY mytable1.key1 DESC;  -- Order by request of end users
		
		END

		/*
		-- Trailing comment with indentation formatting because?
		" foo ' example ( bar)
		*/
	"""
	sqltree = SQLTree(example3_comments)
	# print(sqltree.variables)
	# print('\n')
	# print(sqltree.symbolic_query)
	# print('\n')
	# print(sqltree.working_query)

	print(sqltree.symbolic_query)
	SQLNode(sqltree.symbolic_query, sqltree.non_subqueries)
