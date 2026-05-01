from collections import deque
import re
import sys
from src import globals
from sqlnode import SQLNode
from dfs import DFS


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
		# for k, v in self.symbolic_clauses.items():
		# 	print(k, v)
		# print("\nSubqueries: ")
		# for k, v in self.subqueries.items():
		# 	print(k, v)

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
				subquery_flag = globals.issubquery(self.symbolic_clauses[node], require_name=False)

				if cte_flag:
					self.ctes[node] = globals.isnamed(with_context)[1][0]
				if subquery_flag:
					subquery_name = globals.isnamed(with_context)
					if subquery_name[0]:
						self.subqueries[node] = subquery_name[1][0]
					else:
						self.subqueries[node] = None  # subqueries can be inline and not named
				else:
					self.non_subqueries[node] = self.symbolic_clauses[node]
				if cte_flag:
					cte_val = self.ctes[node] + ' - CTE'
				elif subquery_flag:
					# print(start, stop, node, with_context)
					sq_name = self.subqueries[node]
					if not sq_name:
						sq_name = "UNNAMED"
					cte_val = sq_name + ' - SQ'
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
		subquery = globals.issubquery(query_text, require_name=True)
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