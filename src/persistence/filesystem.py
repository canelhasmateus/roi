from typing import Generator

from src.processing.web.domain import TabSeparated


def read_articles_tsv( filepath ) -> Generator[ TabSeparated ]:
	with open( filepath, "r" ) as file:
		for content in file.readlines():
			yield content
