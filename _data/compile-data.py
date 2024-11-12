import yaml
import os
import sys

WEBSITE_DIR_PATH = '/Users/daniel/Documents/Website'

DATA_DIR = os.path.join(WEBSITE_DIR_PATH, '_data')
TEX_DIR = os.path.join(WEBSITE_DIR_PATH, 'files', 'Academic-Resume')
print(DATA_DIR)

DATA_FILE = os.path.join(DATA_DIR, 'publication-data.yml')
print(DATA_FILE)
CONFERENCE_PAPER_FILE = os.path.join(DATA_DIR, 'publications.yml')
WORKING_PAPER_FILE = os.path.join(DATA_DIR, 'working-papers.yml')
UNPUBLISHED_PAPER_FILE = os.path.join(DATA_DIR, 'unpublished.yml')
JOURNAL_PAPER_FILE = os.path.join(DATA_DIR, 'journal.yml')
JOURNAL_SUBMISSIONS_FILE = os.path.join(DATA_DIR, 'journal-submissions.yml')
RESUME_PUBLICATIONS_FILE = os.path.join(TEX_DIR, 'publications.tex')
RESUME_WORKING_FILE = os.path.join(TEX_DIR, 'working.tex')
RESUME_JOURNAL_FILE = os.path.join(TEX_DIR, 'journal.tex')
RESUME_TEX_FILE = os.path.join(TEX_DIR, 'resume.tex')
RESUME_JOURNAL_SUBMISSION_FILE = os.path.join(TEX_DIR, 'journal-submission.tex')


with open(DATA_FILE, 'r') as f:
	all_data = yaml.safe_load(f)

coauthors = all_data['coauthors']
conference = all_data['conference']
working = all_data['working']
unpublished = all_data['unpublished']
journal = all_data['journal']
journal_submission = all_data['journal_submission']

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
	# if 'starting-page' in paper:
	# 	reference.append(f"pp. {paper['starting-page']}--{paper['ending-page']}, {paper['year']}.")
	# elif 'page' in paper:
	# 	reference.append(f"pp. {paper['page']}, {paper['year']}.")
	# elif 'no-forthcoming' in paper:
	# 	reference.append(f"{paper['year']}.")
	# else:
	# 	reference.append(f"{paper['year']}. Forthcoming.")

	reference.append(f"{paper['year']}.")
	if 'special' in paper:
		reference.append(f'\\\\$\\bigstar$ \\textbf{{{paper['special']}}}')
	return ' '.join(reference)


def journal_citation(paper):
	beginning_citation = f"In \\textit{{{paper['journal']}}} (\\textbf{{{paper['journal-short']}}})"
	if 'pub-data' in paper:
		pass
	else:
		return f"{beginning_citation}. Forthcoming."



with open(CONFERENCE_PAPER_FILE, 'w') as f:
	for paper in conference:
		f.write(f"- title: '{paper['title']}'\n"
			  	f"  citation: '{website_citation(paper)}'\n"
			  	f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
			  	f"  link: '{paper['link']}.pdf'\n")
		if 'special' in paper:
			f.write(f"  special: '**★ {paper['special']}**'\n")
		f.write("\n")


with open(UNPUBLISHED_PAPER_FILE, 'w') as f:
	for paper in unpublished:
		f.write(f"- title: '{paper['title']}'\n"
	  			f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
	  			f"  link: '{paper['link']}.pdf'\n\n")

with open(WORKING_PAPER_FILE, 'w') as f:
	for paper in working:
		if 'note' in paper:
			added_line = f"  citation: '{paper['note']}'\n\n"
		else:
			added_line = "\n"
		f.write(f"- title: '{paper['title']}'\n"
	  			f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
	  			f"  link: '{paper['link']}.pdf'\n" + added_line)

with open(JOURNAL_PAPER_FILE, 'w') as f:
	for paper in journal:
		f.write(f"- title: '{paper['title']}'\n"
				f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
				f"  citation: '{website_journal_citation(paper)}'\n"
				f"  link: '{paper['link']}.pdf'\n\n")

with open(JOURNAL_SUBMISSIONS_FILE, 'w') as f:
	for paper in journal_submission:
		f.write(f"- title: '{paper['title']}'\n"
				f"  authors: '{author_list(paper['authors'], convert_website_author)}'\n"
				f"  citation: '{paper['status']} *{paper['journal']}*'\n"
				f"  link: '{paper['link']}.pdf'\n\n")


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

with open(RESUME_JOURNAL_SUBMISSION_FILE, 'w') as f:
	for paper in journal_submission:
		f.write(f"\\item \\websitelink{{{paper['link']}}}{{{paper['title']}}}.\\\\{order_prefix(paper)}{author_list(paper['authors'], convert_resume_author)}.\\\\{paper['status']} \\textit{{{paper['journal']}}} (\\textbf{{{paper['journal-short']}}}).\n\n")



if len(sys.argv) == 1:
	os.chdir(TEX_DIR)
	os.system(f'pdflatex {RESUME_TEX_FILE}')
	os.system(f'pdflatex {RESUME_TEX_FILE}')
	os.system(f'pdflatex {RESUME_TEX_FILE}')