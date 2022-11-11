import yaml
import os
import sys

DATA_FILE = 'publication-data.yml'
WEBSITE_FILE = 'publications.yml'
RESUME_DIRECTORY = '../files/Academic-Resume/'
RESUME_PUBLICATIONS_FILE = 'publications.tex'
RESUME_TEX_FILE = 'resume.tex'

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
		beginning_citation = f"\\textit{{In Proceedings of the {paper['citation']} (\\textbf{{{paper['conference']}}})}}."
		if 'starting-page' in paper:
			return f"{beginning_citation} {paper['starting-page']}--{paper['ending-page']}."
		else:
			return f'{beginning_citation} Forthcoming.'


with open(WEBSITE_FILE, 'w') as f:
	for paper in papers:
		f.write(f"-\n"
			  	f"  title: '{paper['title']}'\n"
			  	f"  citation: '{website_citation(paper)}'\n"
			  	f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
			  	f"  link: '{paper['link']}.pdf'\n")
os.chdir(RESUME_DIRECTORY)

with open(RESUME_PUBLICATIONS_FILE, 'w') as f:
	for paper in papers:
		f.write(f"\\item {author_list(paper['authors'], convert_resume_author)}. \\websitelink{{{paper['link']}}}{{{paper['title']}}}. {resume_citation(paper)}\n\n")

if len(sys.argv) > 1:
	os.system(f'pdflatex {RESUME_TEX_FILE}')