import pytest
import re
from sqlparser.sqlquery.dfs import DFS


class TestDFS:
	def test_constructor(self):
		opens = [1]
		closes = [1, 2]
		with pytest.raises(ValueError) as e:
			dfs = DFS(opens, closes)
		assert("start and stop indices not equal" in str(e.value))

	def test_dfs(self):
		test1 = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)'
		opens = [match.start() for match in re.finditer(re.escape('('), test1)]
		closes = [match.start() for match in re.finditer(re.escape(')'), test1)]
		dfs = DFS(opens, closes)

		assert(dfs.tree[0] == [1, 9, 11, 12])
		assert(dfs.tree[1] == [2])
		assert(dfs.tree[2] == [3, 4, 5, 6])
		assert(dfs.tree[3] == [])
		assert(dfs.tree[4] == [])
		assert(dfs.tree[5] == [])
		assert(dfs.tree[6] == [7])
		assert(dfs.tree[7] == [8])
		assert(dfs.tree[8] == [])
		assert(dfs.tree[9] == [10])
		assert(dfs.tree[10] == [])
		assert(dfs.tree[11] == [])
		assert(dfs.tree[12] == [13])
		assert(dfs.tree[13] == [])

		assert(dfs.levels[1] == [1, 9, 11, 12])
		assert(dfs.levels[2] == [2, 10, 13])
		assert(dfs.levels[3] == [3, 4, 5, 6])
		assert(dfs.levels[4] == [7])
		assert(dfs.levels[5] == [8])

		assert(dfs.intervals[1] == [1, 42])
		assert(dfs.intervals[2] == [3, 39])
		assert(dfs.intervals[3] == [5, 7])
		assert(dfs.intervals[4] == [9, 12])
		assert(dfs.intervals[5] == [15, 18])
		assert(dfs.intervals[6] == [21, 36])
		assert(dfs.intervals[7] == [24, 33])
		assert(dfs.intervals[8] == [27, 30])
		assert(dfs.intervals[9] == [45, 54])
		assert(dfs.intervals[10] == [48, 51])
		assert(dfs.intervals[11] == [57, 60])
		assert(dfs.intervals[12] == [63, 72])
		assert(dfs.intervals[13] == [66, 69])

		assert(dfs.traversal == (0, 1, 2, 3, 2, 4, 2, 5, 2, 6, 7, 8, 7, 6, 2, 1, 0, 9, 10, 9, 0, 11, 0, 12, 13, 12))
		assert(dfs.node_order == (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13))
	
	def test_bfs(self):
		test1 = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)'
		opens = [match.start() for match in re.finditer(re.escape('('), test1)]
		closes = [match.start() for match in re.finditer(re.escape(')'), test1)]
		dfs = DFS(opens, closes)
		solution = [0, 1, 9, 11, 12, 2, 10, 13, 3, 4, 5, 6, 7, 8]
		observed = []
		for node in dfs.bfs():
			observed.append(node)
		assert(observed == solution)
