import re
import sqlparser.globals
from collections.abc import Iterator


class SQLRegex(object):
	def __init__(self, pattern: re.Pattern):
		self.pattern = pattern
		self.text = None
		self.match = None

	def _mask_sql_keywords(self) -> None:
		if self.match:
			filtered = []
			for m in self.match:
				no_matches = True
				for v in m.groupdict().values():
					no_matches &= v not in sqlparser.globals.ODBC_KEYWORDS
				if no_matches:
					filtered.append(m)
			self.match = iter(filtered)

	def finditer(self, text: str) -> Iterator[re.Match]:
		self.text = text
		self.match = self.pattern.finditer(text)
		self._mask_sql_keywords()
		return self.match

	def findall(self, text: str) -> list[str]:
		self.text = text
		self.match = self.pattern.findall(text)
		self._mask_sql_keywords()
		return [m.group() for m in self.match]
	
	def search(self, text: str) -> re.Match:
		self.text = text
		self.match = self.pattern.search(text)
		self._mask_sql_keywords()
		if self.match:
			self.match = self.match[0]
		return self.match

	def match(self, text: str) -> re.Match:
		self.text = text
		self.match = self.pattern.match(text)
		self._mask_sql_keywords()
		if self.match:
			self.match = self.match[0]
		return self.match
