import yaml
import os
import sys

WEBSITE_DIR_PATH = '/Users/daniel/Documents/Website'

DATA_DIR = os.path.join(WEBSITE_DIR_PATH, '_data')
TEX_DIR = os.path.join(WEBSITE_DIR_PATH, 'files', 'Academic-Resume')
print(DATA_DIR)

DATA_FILE = os.path.join(DATA_DIR, 'publication-data.yml')
print(DATA_FILE)
WEBSITE_FILE = os.path.join(DATA_DIR, 'publications.yml')
RESUME_PUBLICATIONS_FILE = os.path.join(TEX_DIR, 'publications.tex')
RESUME_TEX_FILE = os.path.join(TEX_DIR, 'resume.tex')

with open(DATA_FILE, 'r') as f:
	all_data = yaml.safe_load(f)

coauthors = all_data['coauthors']
papers = all_data['papers']

def convert_website_author(author_string):
	if author_string == 'me':
		return 'Daniel Halpern'
	else:
		author = coauthors[author_string]
		return f'[{author["long"]}]({author["website"]})'

def convert_resume_author(author_string):
	if author_string == 'me':
		return '\\link{https://daniel-halpern.com}{D. Halpern}'
	else:
		author = coauthors[author_string]
		return f'\\link{{{author["website"]}}}{{{author["short"]}}}'

def author_list(author_list, convert_func):
	website_authors = [convert_func(author) for author in author_list]
	if len(website_authors) == 2:
		return f'{website_authors[0]} and {website_authors[1]}'
	else:
		return ', '.join(website_authors[:-1]) + ', and ' + website_authors[-1]

def website_citation(paper):
	if 'conference' not in paper:
		return 'Working Paper'
	else:
		return f'*{paper["conference"]} {paper["year"]}*'

def resume_citation(paper):
	if 'conference' not in paper:
		return 'Working Paper.'
	else:
		beginning_citation = f"In \\textit{{Proceedings of the {paper['citation']} (\\textbf{{{paper['conference']}}})}},"
		if 'starting-page' in paper:
			return f"{beginning_citation} pp. {paper['starting-page']}--{paper['ending-page']}, {paper['year']}."
		else:
			return f"{beginning_citation} {paper['year']}. Forthcoming."


with open(WEBSITE_FILE, 'w') as f:
	for paper in papers:
		f.write(f"-\n"
			  	f"  title: '{paper['title']}'\n"
			  	f"  citation: '{website_citation(paper)}'\n"
			  	f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
			  	f"  link: '{paper['link']}.pdf'\n")

with open(RESUME_PUBLICATIONS_FILE, 'w') as f:
	for paper in papers:
		f.write(f"\\item {author_list(paper['authors'], convert_resume_author)}. \\websitelink{{{paper['link']}}}{{{paper['title']}}}. {resume_citation(paper)}\n\n")

if len(sys.argv) == 1:
	os.chdir(TEX_DIR)
	os.system(f'pdflatex {RESUME_TEX_FILE}')