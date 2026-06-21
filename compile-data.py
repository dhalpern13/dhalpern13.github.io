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



def write_yaml(filepath, data):
	with open(filepath, 'w') as f:
		yaml.dump(data, f, sort_keys=False, allow_unicode=True)

conference_out = []
for i, paper in enumerate(conference):
	entry = {
		'title': paper['title'],
		'citation': website_citation(paper),
		'authors': author_list(paper['authors'], convert_website_author),
		'link': f"{paper['link']}.pdf",
		'paper_id': f"C{len(conference) - i}",
	}
	if 'special' in paper:
		entry['special'] = f"**★ {paper['special']}**"
	conference_out.append(entry)
write_yaml(CONFERENCE_PAPER_FILE, conference_out)


unpublished_out = []
for i, paper in enumerate(unpublished):
	unpublished_out.append({
		'title': paper['title'],
		'authors': author_list(paper['authors'], convert_website_author),
		'link': f"{paper['link']}.pdf",
		'paper_id': f"U{len(unpublished) - i}",
	})
write_yaml(UNPUBLISHED_PAPER_FILE, unpublished_out)

working_out = []
for i, paper in enumerate(working):
	entry = {
		'title': paper['title'],
		'authors': author_list(paper['authors'], convert_website_author),
		'link': f"{paper['link']}.pdf",
		'paper_id': f"W{len(working) - i}",
	}
	if 'note' in paper:
		entry['citation'] = paper['note']
	working_out.append(entry)
write_yaml(WORKING_PAPER_FILE, working_out)

journal_out = []
for i, paper in enumerate(journal):
	journal_out.append({
		'title': paper['title'],
		'authors': author_list(paper['authors'], convert_website_author),
		'citation': website_journal_citation(paper),
		'link': f"{paper['link']}.pdf",
		'paper_id': f"J{len(journal) - i}",
	})
write_yaml(JOURNAL_PAPER_FILE, journal_out)

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
write_yaml(COMBINED_PAPER_FILE, combined)




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