import sys
from collections import deque
from sqlquery.sqlelement import SQLElement
from src import globals


class SQLJoin(SQLElement):
	"""
	One clause of SQL (sub-)query.
	"""
	
	def _parse_wheres(self, sql_text: str) -> None:
		print("\tTHIS WHERE: {}".format(sql_text))
		
		expanded = set()
		child_q = deque([sql_text])
		# TODO: 2026-04-12 modify _non_subquery_dfs for where clauses
		# Find table relations in non-subquery
		opens = deque([0])
		while child_q:
			self._non_subquery_dfs(child_q.popleft(), opens, expanded)
		print(self.relations)

		# if jointype.upper() == 'FROM':
		# 	basetable = globals.TSQL_JOIN_BASETABLE.search(clause_text).group('basetable')
		# 	self.relations[0].setdefault(basetable, [])
		# 	print('Basetable: {}'.format(basetable))  # TODO: add to relation data
		# # DFS to resolve table relations
		# self._resolve_tablevar_relations()  # <-- is this needed for WHERE?
	
	def _parse_joins(self, sql_text: str) -> None:
		"""
		Store table joins and relations.
		"""
		# Find keyword boundaries and parse each clause
		join_boundaries = []
		join_clauses = []
		consumed = set()
		for m in globals.TSQL_JOIN_JOINTYPES.finditer(sql_text):
			keyword_start = m.start('jointype')
			clause_stop = keyword_start + len(m.group()[0])
			match_interval = set(range(keyword_start, clause_stop))
			if not consumed.intersection(match_interval):
				jointype = m.group('jointype')
				join_boundaries.append((keyword_start, jointype),)
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
				self.relations[0].setdefault(basetable, [])
				self.jointables[basetable] = []
				print('Basetable: {}'.format(basetable))  # TODO: handle cases of multiple FROM tables
		print(self.relations)
		# DFS to resolve table relations
		# TODO: could leave it as self.relations and move this DFS to outer (tree) scope
		# 		so ambiguous fields can be resolved to a table first
		# TODO: alias resolution during table resolution?
		self._resolve_tablevar_relations()
		
	
	def _resolve_tablevar_relations(self) -> None:
		"""
		Using self.relations, determine tables and relations for this element into self.jointables
		"""
		self._resolve_subrelations(0)
		print('FROM/JOIN TABLES:')
		basetables = [k for k, v in self.jointables.items() if len(v) == 0]
		for b in basetables:
			print(b)
		for basetable, relations in self._temp_jointables[0].items():
			self.jointables[basetable] = relations
			print(basetable)
			for r in relations:
				print('\t{}'.format(r))  # TODO: order join so basetable comes first or last?

	def _resolve_subrelations(self, jointable_node: int):
		"""
		Resolve nested jointable nodes for _resolve_tablevar_relations
		"""
		retstring = None
		self._temp_jointables.setdefault(jointable_node, {})
		for basetable, tablevars in self.relations[jointable_node].items():
			self.table_dependencies.setdefault(basetable, set())
			for linerelation in tablevars:
				join_clauses = []
				for element in linerelation:
					for table, var in element:
						value = None
						if table:
							# TODO: alias resolution here if needed
							if basetable != table:
								self.table_dependencies[basetable].add(table)
							value = '.'.join([table, var])
						else:
							symb_match = globals.TSQL_SYMBOLIC.search(var)
							if var.strip().upper() in globals.ODBC_KEYWORDS:
								continue
							elif symb_match:
								symb = int(symb_match.group('symb'))
								value = self._resolve_subrelations(symb)
							else:
								value = '?.{}'.format(var)
						if not value:
							raise ValueError("Value in subrelation is None: {}".format(element))
						join_clauses.append(value)
				if join_clauses:
					retval = ' - '.join(join_clauses)
					self._temp_jointables[jointable_node].setdefault(basetable, []).append(retval)
			if basetable in self._temp_jointables[jointable_node]:
				retstring = ' | '.join(self._temp_jointables[jointable_node][basetable])
		return '({})'.format(retstring)
					
	def _non_subquery_dfs(self, substring: str, opens: deque, seen: set) -> None:
		"""
		Add characters to output queue DFS order.
		"""
		# Find current level relations here - keep symbolics
		# - use first symbolic only for nesteds, but use all for same-level
		this_node = opens[-1]
		self.relations.setdefault(this_node, {})
		self._extract_relations(self._with_outer_symbolics(substring), this_node)
		for m in globals.TSQL_SYMBOLIC.finditer(substring):
			symb = int(m.group('symb'))
			if symb in self.non_subqueries and symb not in seen:
				seen.add(symb)
				self._basetables.setdefault(symb, self._basetables[this_node])
				opens.append(symb)
				self._non_subquery_dfs(self.non_subqueries[symb], opens, seen)
		opens.pop()
	
	def _extract_relations(self, clause_text: str, current_node: int) -> None:
		"""
		Extract table/column relations, intended for from/join clauses.
		"""
		print('\tNode: {}\t{}'.format(current_node, clause_text))
		# Mask specific phrases
		phrase_masks = set()
		for (btwn_start, btwn_stop), (and_start, and_stop) in self._extract_between(clause_text):
			print(clause_text[btwn_start:and_stop])
			phrase_masks.update(set(range(btwn_start, btwn_stop)))
			phrase_masks.update(set(range(and_start, and_stop)))
		# Parse by major operator (AND|OR|NOT)
		self._basetables.setdefault(current_node, None)
		cond_clause_starts = [m.span('majop') for m in globals.TSQL_JOIN_MAJOROPS.finditer(clause_text)]
		phrase_mask_idxs = set()
		for i, (start, stop) in enumerate(cond_clause_starts):
			this_span = set(range(start, stop))
			if phrase_masks.intersection(this_span):
				phrase_mask_idxs.add(i)
		cond_clause_starts = [x for i, x in enumerate(cond_clause_starts) if i not in phrase_mask_idxs]
		if not cond_clause_starts:
			cond_clause_starts = [(None, None)]
		for i in range(len(cond_clause_starts)):
			start, stop = cond_clause_starts[i]
			if start is None:
				cond_clause_text = clause_text
				basetable = globals.TSQL_JOIN_BASETABLE.search(cond_clause_text)
				if basetable:
					self._basetables[current_node] = basetable.group('basetable')
					self.relations[current_node].setdefault(self._basetables[current_node], [])
				print('\t\tBasetable: {}'.format(self._basetables[current_node]))  # TODO: add to relation data
				self._extract_ops(cond_clause_text, current_node)
			else:  # Note that _extract_ops executes 1-2 times per loop for this fork
				if i == 0:
					cond_clause_text = clause_text[:start]
					basetable = globals.TSQL_JOIN_BASETABLE.search(cond_clause_text)
					if basetable:
						self._basetables[current_node] = basetable.group('basetable')
						self.relations[current_node].setdefault(self._basetables[current_node], [])
					print('\t\tBasetable: {}'.format(self._basetables[current_node]))  # TODO: add to relation data
					self._extract_ops(cond_clause_text, current_node)
				if (i+1) == len(cond_clause_starts):
					cond_clause_text = clause_text[stop:]
				else:
					next_start = cond_clause_starts[i+1][0]
					cond_clause_text = clause_text[stop:next_start]
				print('\t\tMAJOP Clause: {}'.format(cond_clause_text))
				self._extract_ops(cond_clause_text, current_node)
	
	def _extract_ops(self, op_clause: str, current_node: int) -> None:
		"""
		Extract tables and variables from clauses split by operator.
		"""
		# Parse further by comparison operator -> LHS - RHS
		op_match = globals.TSQL_JOIN_ALLOPS.finditer(op_clause)
		op_starts = [m.span('op') for m in op_match]
		print('\t\t\tOp: {}'.format([x.group('op') for x in globals.TSQL_JOIN_ALLOPS.finditer(op_clause)]))
		if not self._basetables[current_node]:
			sys.stderr.write('ERROR: No basetable found for node {} conditional clause: {}\n'.format(
				current_node, 
				op_clause
			))
			raise ValueError
		if not op_starts:
			relations = self._extract_tablevar(op_clause)
			print('\t\t\tRelations: {}'.format(relations))
			self.relations[current_node].setdefault(self._basetables[current_node], []).append(((relations[0],),))
		else:
			# Note: for comparisons on the same precendence level, we do not care about
			# evaluation order for the purposes of this parser: they will be displayed as
			# Field1 - Field2 - Field3, even though they might be evaluated in precendence order
			# (Field1 - Field2) - Field3.  Explicit parentheses will be retained, however, since 
			# they trigger a symbolic masking, 
			# e.g. Field1 - (Subquery1_Field2 - Subquery1_Field3) will display as
			# Field1 - (Field2 - Field3)
			relations = tuple()
			for j in range(len(op_starts)):
				op_start, op_end = op_starts[j]
				if j == 0:
					lhs = op_clause[:op_start]
					relations += self._extract_tablevar(lhs)
				if (j+1) == len(op_starts):
					rhs = op_clause[op_end:]
					relations += self._extract_tablevar(rhs)
				else:
					next_op_start = op_starts[j+1][0]
					rhs = op_clause[op_end:next_op_start]
					relations += self._extract_tablevar(rhs)
			# Determine if nested comparison or just parentheses for evaluation order
			op_match = globals.TSQL_JOIN_ALLOPS.finditer(op_clause)
			ops = [m.group('op') for m in op_match]
			new_relations = []
			pending = [relations[0]]
			for e, j in enumerate(ops):
				if j not in globals.LOGICAL_OPERATORS:
					pending.append(relations[e+1])
				else:
					new_relations.append(pending)
					pending = [relations[e+1]]
				if (e+1) == len(ops):
					new_relations.append(pending)
					break
			if new_relations:
				relations = tuple(tuple(x) for x in new_relations)
			# Collapse arithemetics not informative for the SQL graph (e.g. '%' + var + '%')
			relation_removes = set()
			op_removes = set()
			if len(relations[0]) != (len(ops) + 1):
				sys.stderr.write('Number of relations ({}) must be one greater than number of ops ({}).\n'.format(
					relations,
					ops
				))
				raise ValueError
			for e, j in enumerate(ops):
				clean_op = j.strip()
				if clean_op in globals.ARITHMETIC_OPERATORS:
					lhs_null = all(x is None for x in relations[0][e])
					rhs_null = all(x is None for x in relations[0][e+1])
					if lhs_null:
						if e not in relation_removes:
							op_removes.add(e)
						relation_removes.add(e)
					if rhs_null:
						if (e+1) not in relation_removes:
							op_removes.add(e)
						relation_removes.add(e+1)
			new_ops = tuple(j for e, j in enumerate(ops) if e not in op_removes)
			new_relations = tuple((j for e, j in enumerate(relations[0]) if e not in relation_removes))
			ops = new_ops
			relations = tuple()
			relations += new_relations,
			print('\t\t\tRelations: {}'.format(relations))
			print('\t\t\tOps: {}'.format(ops))
			self.relations[current_node].setdefault(self._basetables[current_node], []).append(tuple(relations))
			