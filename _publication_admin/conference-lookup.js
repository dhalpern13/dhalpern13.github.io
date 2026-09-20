/* Verified baselines take priority; saved citations provide baselines for other venues. */
function ordinal(number) {
  const teen = number % 100;
  const suffix = teen >= 11 && teen <= 13 ? 'th' : ({1: 'st', 2: 'nd', 3: 'rd'}[number % 10] || 'th');
  return `${number}${suffix}`;
}

function lookupConference(venue, year, catalog, publications = []) {
  const normalize = value => String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
  const query = normalize(venue);
  if (!query || !/^\d{4}$/.test(String(year))) return null;
  const targetYear = Number(year);
  const verified = Object.entries(catalog).find(([key, entry]) =>
    [key, entry.name, ...(entry.aliases || [])].some(alias => normalize(alias) === query));
  let baseline;
  if (verified) {
    baseline = {...verified[1], conference: verified[0], origin: 'verified'};
  } else {
    const candidates = publications.filter(p => normalize(p.conference) === query && /^\d{4}$/.test(String(p.year)))
      .map(p => {
        const match = /^(\d+)(?:st|nd|rd|th)\s+(.+)$/i.exec(p.citation || '');
        return match ? {conference: p.conference, edition: Number(match[1]), name: match[2], year: Number(p.year), origin: 'publication'} : null;
      }).filter(Boolean).sort((a, b) => b.year - a.year);
    baseline = candidates[0];
    if (!baseline) return null;
    // Conflicting saved edition/year pairs need a verified baseline or a manual correction.
    if (candidates.some(candidate => candidate.edition - candidate.year !== baseline.edition - baseline.year)) {
      return {error: 'Existing citations disagree on the edition number. Enter the full name manually or correct a saved citation.'};
    }
  }
  const edition = baseline.edition + targetYear - baseline.year;
  if (edition < 1) return {error: 'This year would give an edition below 1. Enter the full name manually.'};
  return {...baseline, targetYear, targetEdition: edition, inferred: targetYear !== baseline.year,
    citation: `${ordinal(edition)} ${baseline.name}`};
}

if (typeof module !== 'undefined') module.exports = {ordinal, lookupConference};
