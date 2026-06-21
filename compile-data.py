import yaml
import os
import sys
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.absolute()

DATA_DIR = ROOT_DIR / '_data'
TEX_DIR = ROOT_DIR / '_resume'

DATA_FILE = DATA_DIR / 'publication-data.yml'
CONFERENCE_PAPER_FILE = DATA_DIR / 'publications.yml'
WORKING_PAPER_FILE = DATA_DIR / 'working-papers.yml'
UNPUBLISHED_PAPER_FILE = DATA_DIR / 'unpublished.yml'
JOURNAL_PAPER_FILE = DATA_DIR / 'journal.yml'
COMBINED_PAPER_FILE = DATA_DIR / 'papers.yml'

RESUME_PUBLICATIONS_FILE = TEX_DIR / 'publications.tex'
RESUME_WORKING_FILE = TEX_DIR / 'working.tex'
RESUME_JOURNAL_FILE = TEX_DIR / 'journal.tex'
RESUME_TEX_FILE = TEX_DIR / 'resume.tex'


with open(DATA_FILE, 'r') as f:
	all_data = yaml.safe_load(f)

coauthors = all_data['coauthors']
conference = all_data['conference']
working = all_data['working']
unpublished = all_data['unpublished']
journal = all_data['journal']

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
	return f'*{paper["conference"]} {paper["year"]}*'

def website_journal_citation(paper):
	return f'*{paper["journal"]}*'

def order_prefix(paper):
	if 'alphabetical' in paper:
		return '$(\\alpha)$ '
	elif 'random' in paper:
		return '$(r)$ '
	else:
		return ''


def resume_citation(paper):
	reference = []
	reference.append(f"In \\textit{{Proceedings of the {paper['citation']} (\\textbf{{{paper['conference']}}})}},")

	reference.append(f"{paper['year']}.")
	if 'special' in paper:
		if 'special-latex' in paper:
			special = paper['special-latex']
		else:
			special = paper['special']
		reference.append(f'\\\\$\\bigstar$ \\textbf{{{special}}}')
	return ' '.join(reference)


def journal_citation(paper):
	beginning_citation = f"In \\textit{{{paper['journal']}}}"
	if 'year' in paper:
		return f"{beginning_citation}, {paper['year']}."
	else:
		return f"{beginning_citation}. Forthcoming."



with open(CONFERENCE_PAPER_FILE, 'w') as f:
	for i, paper in enumerate(conference):
		f.write(f"- title: '{paper['title']}'\n"
			  	f"  citation: '{website_citation(paper)}'\n"
			  	f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
			  	f"  link: '{paper['link']}.pdf'\n"
			  	f"  paper_id: 'C{len(conference) - i}'\n")
		if 'special' in paper:
			f.write(f"  special: '**★ {paper['special']}**'\n")
		f.write("\n")


with open(UNPUBLISHED_PAPER_FILE, 'w') as f:
	for i, paper in enumerate(unpublished):
		f.write(f"- title: '{paper['title']}'\n"
	  			f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
	  			f"  link: '{paper['link']}.pdf'\n"
	  			f"  paper_id: 'U{len(unpublished) - i}'\n\n")

with open(WORKING_PAPER_FILE, 'w') as f:
	for i, paper in enumerate(working):
		if 'note' in paper:
			added_line = f"  citation: '{paper['note']}'\n\n"
		else:
			added_line = "\n"
		f.write(f"- title: '{paper['title']}'\n"
	  			f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
	  			f"  link: '{paper['link']}.pdf'\n"
	  			f"  paper_id: 'W{len(working) - i}'\n" + added_line)

with open(JOURNAL_PAPER_FILE, 'w') as f:
	for i, paper in enumerate(journal):
		f.write(f"- title: '{paper['title']}'\n"
				f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
				f"  citation: '{website_journal_citation(paper)}'\n"
				f"  link: '{paper['link']}.pdf'\n"
				f"  paper_id: 'J{len(journal) - i}'\n\n")

combined = []
for i, paper in enumerate(journal):
	entry = {
		'title': paper['title'],
		'authors': author_list(paper['authors'], convert_website_author),
		'citation': website_journal_citation(paper),
		'link': f"{paper['link']}.pdf",
		'year': paper.get('year', '') or 'Forthcoming',
		'paper_id': f"J{len(journal) - i}",
	}
	if 'special' in paper:
		entry['special'] = f"**★ {paper['special']}**"
	combined.append(entry)

for i, paper in enumerate(conference):
	entry = {
		'title': paper['title'],
		'authors': author_list(paper['authors'], convert_website_author),
		'citation': website_citation(paper),
		'link': f"{paper['link']}.pdf",
		'year': paper.get('year', '') or 'Forthcoming',
		'paper_id': f"C{len(conference) - i}",
	}
	if 'special' in paper:
		entry['special'] = f"**★ {paper['special']}**"
	combined.append(entry)

for i, paper in enumerate(unpublished):
	entry = {
		'title': paper['title'],
		'authors': author_list(paper['authors'], convert_website_author),
		'citation': 'Unpublished manuscript',
		'link': f"{paper['link']}.pdf",
		'year': paper.get('year', '') or '2021',
		'paper_id': f"U{len(unpublished) - i}",
	}
	if 'special' in paper:
		entry['special'] = f"**★ {paper['special']}**"
	combined.append(entry)

combined.sort(key=lambda x: (1, '') if x['year'] == 'Forthcoming' else (0, x['year']), reverse=True)

with open(COMBINED_PAPER_FILE, 'w') as f:
	for entry in combined:
		f.write(f"- title: '{entry['title']}'\n"
				f"  authors: '{entry['authors']}'\n"
				f"  citation: '{entry['citation']}'\n"
				f"  link: '{entry['link']}'\n"
				f"  year: '{entry['year']}'\n"
				f"  paper_id: '{entry['paper_id']}'\n")
		if 'special' in entry:
			f.write(f"  special: '{entry['special']}'\n")
		f.write("\n")




with open(RESUME_PUBLICATIONS_FILE, 'w') as f:
	for paper in conference:
		f.write(f"\\item \\websitelink{{{paper['link']}}}{{{paper['title']}}}.\\\\{order_prefix(paper)}{author_list(paper['authors'], convert_resume_author)}. \\\\{resume_citation(paper)}\n\n")


with open(RESUME_WORKING_FILE, 'w') as f:
	for paper in working:
		if 'note' in paper:
			note = f" \\textit{{{paper['note']}}}."
		else:
			note = ''
		f.write(f"\\item \\websitelink{{{paper['link']}}}{{{paper['title']}}}.\\\\{order_prefix(paper)}{author_list(paper['authors'], convert_resume_author)}. {note}\n\n")

with open(RESUME_JOURNAL_FILE, 'w') as f:
	for paper in journal:
		f.write(f"\\item \\websitelink{{{paper['link']}}}{{{paper['title']}}}.\\\\{order_prefix(paper)}{author_list(paper['authors'], convert_resume_author)}.\\\\{journal_citation(paper)}\n\n")





if len(sys.argv) == 1:
	os.chdir(TEX_DIR)
	os.system(f'pdflatex {RESUME_TEX_FILE}')
	os.system(f'pdflatex {RESUME_TEX_FILE}')
	os.system(f'pdflatex {RESUME_TEX_FILE}')
	# Copy compiled PDF to public files directory
	shutil.copy2(TEX_DIR / 'resume.pdf', ROOT_DIR / 'files' / 'resume.pdf')