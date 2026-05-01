import re
import test_cases
from sqlparser.sqlquery.dfs import DFS
from sqlparser.sqlquery.sqltree import SQLTree
from sqlparser.sqlquery.sqlnode import SQLNode


def main():
	opens = [match.start() for match in re.finditer(re.escape('('), test_cases.example1_nested)]
	closes = [match.start() for match in re.finditer(re.escape(')'), test_cases.example1_nested)]
	dfs = DFS(opens, closes)
	# print(example1_nested)
	# print('Traversal: {}'.format(dfs.traversal))
	# print('Tree: {}'.format(dfs.tree))
	# print('Levels: {}'.format(dfs.levels))
	# print('Intervals: {}\n'.format(dfs.intervals))

	
	sqltree = SQLTree(test_cases.example2_nested)
	# print(example2_nested)
	# print('Traversal: {}'.format(sqltree.dfs.traversal))
	# print('Tree: {}'.format(sqltree.dfs.tree))
	# print('Levels: {}'.format(sqltree.dfs.levels))
	# print('Intervals: {}\n'.format(sqltree.dfs.intervals))
	assert(dfs.traversal == sqltree.dfs.traversal)
	assert(dfs.tree == sqltree.dfs.tree)
	assert(dfs.levels == sqltree.dfs.levels)
	assert(dfs.intervals == sqltree.dfs.intervals)

	
	sqltree = SQLTree(test_cases.example3_comments)
	# print(sqltree.variables)
	# print('\n')
	# print(sqltree.symbolic_query)
	# print('\n')
	# print(sqltree.working_query)

	print(sqltree.symbolic_query)
	SQLNode(sqltree.symbolic_query, sqltree.non_subqueries)
	

if __name__ == '__main__':
	main()
	