const $ = id => document.getElementById(id);
const categories = {working: 'Working paper', conference: 'Conference paper', journal: 'Journal article', theses: 'Thesis', unpublished: 'Unpublished'};
const prefixes = {working: 'W', conference: 'C', journal: 'J', theses: 'T', unpublished: 'U'};
let state, selection = null, draftAuthors = [], baseline = '', busy = false, suggestedCitation = '';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function authorName(key) { return key === 'me' ? 'Daniel Halpern' : state.data.coauthors[key]?.long || key; }
function paperId(category, paper, index) { return (category !== 'working' && paper.paper_id) || `${prefixes[category]}${state.data[category].length - index}`; }
function notice(message, error = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
  $('notice').hidden = !message;
  if (error) $('notice').scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
function fingerprint() {
  return JSON.stringify({fields: [...$('paper-form').querySelectorAll('input,textarea,select')].map(e => [e.id, e.value]), authors: draftAuthors});
}
function isDirty() { return !$('paper-form').hidden && fingerprint() !== baseline; }
function changed() {
  $('edit-status').textContent = isDirty() ? 'Unsaved changes' : selection?.index != null ? 'Saved' : 'New draft';
  updatePreview();
}
function confirmAction(title, body, label = 'Continue') {
  return new Promise(resolve => {
    $('confirm-title').textContent = title;
    $('confirm-body').textContent = body;
    $('confirm-ok').textContent = label;
    const dialog = $('confirm-dialog');
    dialog.returnValue = '';
    dialog.onclose = () => resolve(dialog.returnValue === 'yes');
    $('confirm-ok').onclick = () => dialog.close('yes');
    $('confirm-cancel').onclick = () => dialog.close('no');
    dialog.showModal();
  });
}
async function mayLeave() {
  return !isDirty() || await confirmAction('Discard unsaved changes?', 'Your changes to this publication haven’t been saved.', 'Discard changes');
}
async function fetchState() {
  const response = await fetch('/api/state');
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}
async function mutate(payload) {
  const response = await fetch('/api/change', {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Editor-Token': state.token},
    body: JSON.stringify({...payload, revision: state.revision})
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  state = {...result, token: state.token};
  fillOptions();
  return result;
}
function setBusy(value) {
  busy = value;
  document.querySelectorAll('button, input, select, textarea').forEach(e => e.disabled = value);
  $('save').textContent = value ? 'Saving…' : 'Save changes';
  if (!value) renderAuthors();
}
function fillOptions() {
  $('pdf-options').replaceChildren(...state.files.map(file => {
    const option = element('option'); option.value = file; return option;
  }));
  const people = ['me', ...Object.keys(state.data.coauthors)].sort((a,b) => authorName(a).localeCompare(authorName(b)));
  $('author-options').replaceChildren(...people.map(key => {
    const option = element('option'); option.value = authorName(key); option.label = key; return option;
  }));
  updateCategory();
}
function renderList() {
  const query = $('search').value.toLowerCase().trim();
  const filter = $('filter').value;
  const papers = [];
  for (const [category, label] of Object.entries(categories)) {
    (state.data[category] || []).forEach((paper, index) => {
      const id = paperId(category, paper, index);
      const authors = paper.authors.map(authorName).join(', ');
      const searchable = `${paper.title} ${authors} ${label} ${paper.link} ${paper.conference || paper.journal || paper.institution || ''} ${paper.year || ''} ${id}`.toLowerCase();
      if ((filter === 'all' || category === filter) && (!query || searchable.includes(query))) papers.push({category, label, paper, index, id, authors});
    });
  }
  $('count').textContent = `${papers.length} ${papers.length === 1 ? 'paper' : 'papers'}`;
  $('paper-list').replaceChildren(...papers.map(({category, label, paper, index, id, authors}) => {
    const button = element('button', 'paper-card');
    button.type = 'button';
    const active = selection?.category === category && selection?.index === index;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
    const meta = element('div', 'paper-meta');
    meta.append(element('span', 'paper-id', id), element('span', '', `${paper.conference || paper.journal || label}${paper.year ? ' · ' + paper.year : ''}`));
    button.append(meta, element('strong', '', paper.title), element('div', 'paper-authors', authors));
    button.onclick = async () => { if (!busy && await mayLeave()) openPaper(category, index); };
    return button;
  }));
  if (!papers.length) $('paper-list').append(element('p', 'no-results', 'No publications match your search.'));
}
function openPaper(category = 'conference', index = null) {
  selection = {category, index};
  const paper = index !== null ? state.data[category][index] : {};
  $('paper-form').reset();
  $('paper-form').hidden = false;
  $('empty').hidden = true;
  $('category').value = category;
  $('title').value = paper.title || '';
  $('year').value = paper.year || (index === null && category !== 'working' ? String(new Date().getFullYear()) : '');
  $('pdf').value = paper.link ? paper.link + '.pdf' : '';
  $('venue').value = paper.conference || paper.journal || paper.institution || '';
  $('citation').value = paper.citation || '';
  suggestedCitation = '';
  for (const field of ['special', 'special-latex', 'note']) $(field).value = paper[field] || '';
  $('author-order').value = paper.alphabetical ? 'alphabetical' : paper.random ? 'random' : 'custom';
  draftAuthors = [...(paper.authors || ['me'])];
  $('editor-label').textContent = index === null ? 'NEW PUBLICATION' : `${paperId(category, paper, index)} · ${categories[category].toUpperCase()}`;
  $('editor-title').textContent = index === null ? 'Add to your research' : 'Publication details';
  $('delete-paper').hidden = index === null;
  $('extra-fields').open = Boolean(paper.special || paper['special-latex']);
  updateCategory(); renderAuthors(); renderList();
  suggestCitation(false);
  baseline = fingerprint(); changed();
}
function updateCategory() {
  if (!state) return;
  const category = $('category').value;
  const venueKind = {conference: 'conference', journal: 'journal', theses: 'institution'}[category];
  $('venue-fields').hidden = !venueKind;
  $('venue').required = Boolean(venueKind);
  $('citation-label').hidden = category !== 'conference';
  $('citation').required = category === 'conference';
  $('year-label').hidden = category === 'working';
  $('year').required = ['conference', 'theses', 'unpublished'].includes(category);
  $('year-help').hidden = category !== 'journal';
  $('note-label').hidden = category !== 'working';
  $('extra-fields').hidden = ['working', 'theses'].includes(category);
  $('special-latex').parentElement.hidden = category !== 'conference';
  $('venue-heading').textContent = {conference: 'Conference', journal: 'Journal', theses: 'Institution'}[category] || 'Venue';
  $('venue').placeholder = `Choose or type ${category === 'theses' ? 'an institution' : 'a ' + (venueKind || 'venue')}…`;
  const options = [...new Set([
    ...(state.data[category] || []).map(p => p[venueKind]).filter(Boolean),
    ...(category === 'conference' ? Object.keys(state.conferences || {}) : [])
  ])].sort();
  $('venue-options').replaceChildren(...options.map(value => { const option = element('option'); option.value = value; return option; }));
  // Fields hidden for a category must not interfere with native form validation.
  $('year').disabled = category === 'working';
  $('venue').disabled = !venueKind;
  $('citation').disabled = category !== 'conference';
  $('conference-reference').hidden = category !== 'conference';
  changed();
}
function renderAuthors() {
  $('authors').replaceChildren(...draftAuthors.map((key, index) => {
    const row = element('div', 'author-row');
    const name = authorName(key);
    const initials = name.split(/\s+/).map(s => s[0]).slice(0,2).join('');
    const label = element('div', 'author-name', name);
    if (key === 'me') label.append(element('span', '', 'you'));
    const controls = element('div', 'author-controls');
    for (const [symbol, action, disabled] of [['↑', 'Move up', index === 0], ['↓', 'Move down', index === draftAuthors.length - 1], ['×', 'Remove', false]]) {
      const button = element('button', '', symbol); button.type = 'button'; button.disabled = disabled || busy;
      button.setAttribute('aria-label', `${action}: ${name}`);
      button.onclick = () => {
        if (symbol === '×') draftAuthors.splice(index, 1);
        else { const other = index + (symbol === '↑' ? -1 : 1); [draftAuthors[index], draftAuthors[other]] = [draftAuthors[other], draftAuthors[index]]; }
        renderAuthors(); changed();
      };
      controls.append(button);
    }
    row.append(element('span', 'author-initials', initials), label, controls); return row;
  }));
}
function addAuthor() {
  const value = $('author-search').value.trim().toLowerCase();
  const matches = ['me', ...Object.keys(state.data.coauthors)].filter(key => authorName(key).toLowerCase() === value || key === value);
  if (matches.length !== 1) { notice('Choose a collaborator from the list, or use “New collaborator.”', true); return; }
  if (draftAuthors.includes(matches[0])) { notice('That author is already on this paper.', true); return; }
  draftAuthors.push(matches[0]); $('author-search').value = ''; renderAuthors(); changed(); notice('');
}
function updatePreview() {
  if (!state) return;
  $('preview-title').textContent = $('title').value || 'Your paper title';
  $('preview-authors').textContent = draftAuthors.map(authorName).join(', ');
  const category = $('category').value;
  const venue = $('venue').value;
  $('preview-venue').textContent = category === 'theses' ? `PhD thesis${venue ? ', ' + venue : ''} · ${$('year').value}` : category === 'working' ? $('note').value || 'Working paper' : `${venue || categories[category]}${$('year').value ? ' · ' + $('year').value : ' · Forthcoming'}`;
  const file = $('pdf').value;
  $('pdf-preview').hidden = !state.files.includes(file);
  $('pdf-preview').href = '/pdf/' + encodeURIComponent(file);
}
function paperFromForm() {
  const category = $('category').value;
  const paper = {title: $('title').value.trim(), link: $('pdf').value.trim().replace(/\.pdf$/, ''), authors: [...draftAuthors]};
  if (category !== 'working' && $('year').value.trim()) paper.year = $('year').value.trim();
  const venueKey = {conference: 'conference', journal: 'journal', theses: 'institution'}[category];
  if (venueKey) paper[venueKey] = $('venue').value.trim();
  if (category === 'conference') paper.citation = $('citation').value.trim();
  if (category === 'working' && $('note').value.trim()) paper.note = $('note').value.trim();
  for (const field of ['special', 'special-latex']) if ($(field).value.trim()) paper[field] = $(field).value.trim();
  if ($('author-order').value !== 'custom') paper[$('author-order').value] = true;
  return paper;
}
$('paper-form').addEventListener('input', changed);
$('rebuild-resume').onclick = async () => {
  if (busy) return;
  if (isDirty()) {
    notice('Save or discard your publication edits before rebuilding the résumé.', true);
    return;
  }
  setBusy(true);
  $('rebuild-resume').textContent = 'Building résumé…';
  $('resume-result').hidden = true;
  notice('Compiling the résumé from your saved publications…');
  try {
    const response = await fetch('/api/rebuild-resume', {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Editor-Token': state.token},
      body: JSON.stringify({revision: state.revision})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    $('resume-result').href = result.pdf + '?v=' + Date.now();
    $('resume-result').hidden = false;
    notice('Résumé PDF rebuilt successfully. Use “Open résumé” to view it. Publish through Git when ready.');
  } catch (error) { notice(error.message, true); }
  finally {
    setBusy(false); updateCategory();
    $('rebuild-resume').textContent = 'Rebuild résumé';
  }
};
$('category').onchange = () => {
  $('venue').value = ''; $('citation').value = ''; suggestedCitation = '';
  updateCategory();
  suggestCitation();
};
function suggestCitation(autofill = true) {
  $('conference-reference').hidden = true;
  $('conference-source').hidden = true;
  $('use-conference-suggestion').hidden = true;
  if ($('category').value !== 'conference') return;
  const suggestion = lookupConference($('venue').value, $('year').value, state.conferences || {}, state.data.conference);
  if (autofill && (!$('citation').value || $('citation').value === suggestedCitation)) {
    $('citation').value = suggestion?.citation || '';
    suggestedCitation = suggestion?.citation || '';
  } else if (!autofill && suggestion?.citation === $('citation').value) {
    // Matching saved values can follow future year changes; manual overrides are retained.
    suggestedCitation = suggestion.citation;
  }
  if (!$('venue').value.trim()) { changed(); return; }
  $('conference-reference').hidden = false;
  if (!/^\d{4}$/.test($('year').value)) {
    $('conference-explanation').textContent = 'Enter a four-digit year to look up the conference edition.';
  } else if (!suggestion) {
    $('conference-explanation').textContent = 'No known reference for this conference yet. Enter an edition and full name once (e.g. “12th Example Conference”); future entries can infer other years from that saved paper.';
  } else if (suggestion.error) {
    $('conference-explanation').textContent = suggestion.error;
  } else {
    const reference = `${suggestion.conference} ${suggestion.year} was the ${ordinal(suggestion.edition)} edition`;
    const explanation = suggestion.inferred
      ? `Inferred ${ordinal(suggestion.targetEdition)} for ${suggestion.targetYear}, assuming one edition per year. ${reference}.`
      : `${suggestion.origin === 'verified' ? 'Verified reference' : 'From a saved publication'}: ${reference}.`;
    const differs = $('citation').value !== suggestion.citation;
    $('conference-explanation').textContent = differs ? `${explanation} Suggested: ${suggestion.citation}.` : explanation;
    if (suggestion.source) {
      $('conference-source').href = suggestion.source;
      $('conference-source').hidden = false;
    }
    $('use-conference-suggestion').hidden = !differs;
    $('use-conference-suggestion').onclick = () => {
      $('citation').value = suggestion.citation;
      suggestedCitation = suggestion.citation;
      suggestCitation(false);
    };
  }
  changed();
}
$('venue').oninput = () => suggestCitation();
$('year').oninput = () => suggestCitation();
$('citation').oninput = () => suggestCitation(false);
$('search').oninput = renderList;
$('filter').onchange = renderList;
$('add-author').onclick = addAuthor;
$('author-search').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); addAuthor(); } };
$('new-paper').onclick = async () => { if (await mayLeave()) { notice(''); openPaper(); $('title').focus(); } };
$('discard').onclick = async () => { if (await mayLeave()) { openPaper(selection.category, selection.index); notice(''); } };
$('reload').onclick = async () => {
  if (!await mayLeave()) return;
  try {
    state = await fetchState(); selection = null; fillOptions(); renderList();
    $('paper-form').hidden = true; $('empty').hidden = false;
    notice('Publication data and PDF list refreshed.');
  } catch (error) { notice(error.message, true); }
};
$('paper-form').onsubmit = async event => {
  event.preventDefault(); if (busy) return;
  const payload = {action: 'save', category: $('category').value, originalCategory: selection.category, index: selection.index, paper: paperFromForm()};
  if (!state.files.includes($('pdf').value.trim())) { notice('Choose a PDF from the files list.', true); $('pdf').focus(); return; }
  if (!draftAuthors.length) { notice('Choose at least one author.', true); return; }
  setBusy(true);
  try {
    const result = await mutate(payload);
    openPaper(result.selected.category, result.selected.index);
    notice('Saved. Website data and résumé source updated; the résumé PDF is unchanged.');
  } catch (error) { notice(error.message, true); }
  finally { setBusy(false); updateCategory(); }
};
$('delete-paper').onclick = async () => {
  if (busy || selection?.index == null) return;
  const paper = state.data[selection.category][selection.index];
  if (!await confirmAction('Delete this publication?', `“${paper.title}” will be removed from the publication list. Its PDF will stay in files/. Working-paper labels will be renumbered consecutively.`, 'Delete publication')) return;
  setBusy(true);
  try {
    await mutate({action: 'delete', category: selection.category, index: selection.index});
    selection = null; $('paper-form').hidden = true; $('empty').hidden = false; renderList();
    notice('Publication deleted. Its PDF has been kept.');
  } catch (error) { notice(error.message, true); }
  finally { setBusy(false); updateCategory(); }
};
$('new-author').onclick = () => { $('author-form').reset(); delete $('author-key').dataset.edited; $('author-error').textContent = ''; $('author-dialog').showModal(); };
$('cancel-author').onclick = () => $('author-dialog').close();
$('author-long').oninput = () => {
  if (!$('author-key').dataset.edited) $('author-key').value = $('author-long').value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, '');
};
$('author-key').oninput = () => $('author-key').dataset.edited = 'true';
$('author-form').onsubmit = async event => {
  event.preventDefault(); if (busy) return;
  const author = Object.fromEntries(['long', 'short', 'key', 'website'].map(key => [key, $('author-' + key).value.trim()]));
  setBusy(true);
  try {
    await mutate({action: 'collaborator', author});
    draftAuthors.push(author.key); renderAuthors(); changed(); renderList();
    $('author-dialog').close(); notice('Collaborator added. Save the publication to include them on this paper.');
  } catch (error) { $('author-error').textContent = error.message; }
  finally { setBusy(false); updateCategory(); }
};
window.addEventListener('beforeunload', event => { if (isDirty()) { event.preventDefault(); event.returnValue = ''; } });
(async () => {
  try {
    state = await fetchState(); fillOptions(); renderList();
    // Start with the first listed paper, ready to inspect or edit.
    const category = Object.keys(categories).find(key => state.data[key]?.length);
    if (category) openPaper(category, 0);
  } catch (error) { notice('Could not connect to the local editor. ' + error.message, true); }
})();
