# Publication dashboard

From the website directory, run:

```sh
uv run python _publication_admin/server.py
```

Open <http://127.0.0.1:4001/>. The dashboard uses the existing Python environment and PyYAML; no npm packages are needed. Use `--port 4002` if port 4001 is taken.

- Search publications by title, author, venue, year, or label.
- Add, edit, delete, or change the type of a publication.
- Search existing PDFs in `files/`. Put a new PDF there, then click **Reload data & PDFs** before starting a draft.
- Pick an existing conference, journal, or institution, or type a new one.
- Conference names and editions fill automatically from the official references in `conferences.json`, checked on 2026-09-19. The lookup covers EC, ICML, NeurIPS, AAAI, IJCAI, WINE, FOCS, SAGT, WWW, and EAAMO, and works offline after startup. Other years use `reference edition + selected year − reference year`, assuming an annual conference as requested. Each suggestion shows its reference link and whether it was inferred.
- Existing citations and manual overrides are preserved when opening a paper. If a citation differs from the lookup, **Use suggested name** applies the suggestion to the draft. Save the paper to persist it. For conferences outside the verified catalog, a previously saved numbered citation supplies the baseline; enter one manually if none exists. Conflicting saved baselines are flagged rather than guessed.
- Add authors from the searchable collaborator list, arrange their order with the arrows, or create a new collaborator. The full conference name and short author names are used by the résumé source.
- Save changes explicitly. Leaving a draft warns about unsaved changes. An externally modified source file must be reloaded before saving.

Saving updates `_data/publication-data.yml`, regenerates website YAML and résumé `.tex` files, and leaves the résumé PDF unchanged. A running Jekyll preview automatically picks up the generated data. The thesis category remains website-only.

The editor does **not** commit or push changes. Review and publish through Git as usual. Deleting an entry keeps its PDF. Existing labels are retained when adding, moving, or deleting entries; counters reserve deleted labels. On first edit, the affected category gets explicit labels matching the current website. Other top-level YAML sections retain their formatting.

Each save first runs the generator in a temporary directory, then backs up changed files under `_publication_admin/backups/<timestamp>/`. Backups are ignored by Git. To recover a change, stop the editor and copy the desired files from a backup to their matching repository paths. You can also use Git to review or undo tracked changes.

The server binds only to `127.0.0.1`. Its files live under an underscore directory, so Jekyll does not publish the dashboard or its backups. The **Website preview** link expects Jekyll on port 4000; the dashboard itself can run independently.

Tests (use temporary repositories, never the live publication data):

```sh
uv run python -m unittest discover -s _publication_admin -p 'test_*.py'
node --test _publication_admin/test_conference_lookup.cjs
```
