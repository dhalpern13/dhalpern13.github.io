"""Local publication editor. Run from the repository: uv run python _publication_admin/server.py"""

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent
CATEGORIES = {"working": "W", "conference": "C", "journal": "J", "theses": "T", "unpublished": "U"}
OUTPUTS = [f"_data/{name}.yml" for name in
           ("papers", "publications", "working-papers", "journal", "unpublished")]
OUTPUTS += [f"_resume/{name}.tex" for name in ("publications", "working", "journal")]


class Conflict(ValueError):
    pass


def replace_section(source, key, value):
    """Leave all other top-level sections, including their formatting, alone."""
    pattern = re.compile(r"^" + re.escape(key) + r":.*?(?=^[A-Za-z_][\w-]*:|\Z)", re.M | re.S)
    replacement = yaml.safe_dump({key: value}, sort_keys=False, allow_unicode=True, width=100) + "\n"
    return pattern.sub(lambda _: replacement, source, count=1) if pattern.search(source) else source.rstrip() + "\n\n" + replacement


def atomic_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(contents)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class PublicationStore:
    def __init__(self, root):
        self.root = root
        self.source = root / "_data/publication-data.yml"
        self.lock = threading.Lock()

    def read(self):
        raw = self.source.read_bytes()
        return raw, yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()

    def state(self):
        _, data, revision = self.read()
        return {"data": data, "revision": revision,
                "conferences": json.loads((ASSETS / "conferences.json").read_text()),
                "files": sorted(p.name for p in (self.root / "files").glob("*.pdf") if p.is_file())}

    def validate_paper(self, paper, category, data):
        required = ["title", "link"]
        required += {"conference": ["conference", "citation", "year"], "journal": ["journal"],
                     "theses": ["institution", "year"], "unpublished": ["year"], "working": []}[category]
        for key in required:
            if not isinstance(paper.get(key), str) or not paper[key].strip():
                raise ValueError(f"Please fill in {key.replace('_', ' ')}.")
        for key, value in paper.items():
            if key not in ("authors", "alphabetical", "random") and not isinstance(value, str):
                raise ValueError(f"Invalid value for {key}.")
        if paper.get("year") and not re.fullmatch(r"\d{4}", paper["year"]):
            raise ValueError("Use a four-digit year.")
        authors = paper.get("authors")
        if not isinstance(authors, list) or not authors or any(not isinstance(a, str) for a in authors):
            raise ValueError("Choose at least one author.")
        if len(set(authors)) != len(authors) or any(a != "me" and a not in data["coauthors"] for a in authors):
            raise ValueError("Choose each author once, from the collaborator list.")
        if "alphabetical" in paper and "random" in paper:
            raise ValueError("Choose one author-order convention.")
        filename = paper["link"] + ".pdf"
        if Path(filename).name != filename or not (self.root / "files" / filename).is_file():
            raise ValueError("Choose an existing PDF from the files folder.")

    def change(self, request):
        with self.lock:
            raw, data, revision = self.read()
            if request.get("revision") != revision:
                raise Conflict("The publication data changed since you opened it. Reload the dashboard before saving.")
            action = request.get("action")
            source = raw.decode()
            selected = None
            if action == "collaborator":
                author = request.get("author", {})
                key = author.get("key", "")
                if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", key):
                    raise ValueError("Use a short collaborator ID with lowercase letters, numbers, or hyphens.")
                if key == "me" or key in data["coauthors"]:
                    raise ValueError("That collaborator ID already exists.")
                if any(not isinstance(author.get(k), str) or not author[k].strip() for k in ("long", "short")):
                    raise ValueError("Enter a full name and a short name for the résumé.")
                website = author.get("website", "").strip()
                if website and (urlsplit(website).scheme not in ("http", "https") or not urlsplit(website).netloc):
                    raise ValueError("Use a complete http:// or https:// website address, or leave it blank.")
                data["coauthors"][key] = {k: author[k].strip() for k in ("long", "short")}
                data["coauthors"][key]["website"] = website
                source = replace_section(source, "coauthors", data["coauthors"])
            elif action in ("save", "delete"):
                category = request.get("category")
                original = request.get("originalCategory", category)
                if category not in CATEGORIES or original not in CATEGORIES:
                    raise ValueError("Choose a publication type.")
                # Freeze existing labels before inserting/deleting so other papers never renumber.
                touched = {category, original}
                for group in touched:
                    entries = data.setdefault(group, [])
                    for i, entry in enumerate(entries):
                        entry.setdefault("paper_id", f"{CATEGORIES[group]}{len(entries) - i}")
                index = request.get("index")
                if index is not None and (type(index) is not int or not 0 <= index < len(data[original])):
                    raise ValueError("This publication no longer exists. Reload the dashboard.")
                if action == "delete":
                    if index is None:
                        raise ValueError("Select a saved publication to delete.")
                    del data[original][index]
                else:
                    submitted = request.get("paper")
                    if not isinstance(submitted, dict):
                        raise ValueError("Invalid publication.")
                    paper = dict(data[original][index]) if index is not None else {}
                    # Explicitly removed optional fields; all other metadata is preserved.
                    for key in ("alphabetical", "random", "special", "special-latex", "note", "year", "conference", "citation", "journal", "institution"):
                        if key not in submitted:
                            paper.pop(key, None)
                    paper.update(submitted)
                    self.validate_paper(paper, category, data)
                    if index is not None and original == category:
                        paper["paper_id"] = data[original][index]["paper_id"]
                        data[category][index] = paper
                        selected = {"category": category, "index": index}
                    else:
                        # A high-water mark prevents reuse even if the highest label was deleted.
                        counters = data.setdefault("label_counters", {})
                        highest = max([int(p["paper_id"][1:]) for p in data[category]] + [int(counters.get(category, 0))])
                        paper["paper_id"] = f"{CATEGORIES[category]}{highest + 1}"
                        counters[category] = highest + 1
                        if index is not None:
                            del data[original][index]
                        data[category].insert(0, paper)
                        selected = {"category": category, "index": 0}
                # Retain pre-deletion label maxima as well as new labels.
                counters = data.setdefault("label_counters", {})
                previous = yaml.safe_load(raw)
                for group in touched:
                    old = previous.get(group, [])
                    highest = max([int(p.get("paper_id", f"{CATEGORIES[group]}{len(old) - i}")[1:]) for i, p in enumerate(old)] + [0])
                    counters[group] = max(int(counters.get(group, 0)), highest)
                    if group == "working":
                        for i, entry in enumerate(data[group]):
                            entry["paper_id"] = f"W{len(data[group]) - i}"
                        counters[group] = len(data[group])
                    source = replace_section(source, group, data[group])
                source = replace_section(source, "label_counters", counters)
            else:
                raise ValueError("Unknown action.")
            self.persist(source.encode(), raw)
            return {**self.state(), "selected": selected}

    def rebuild_resume(self, request):
        with self.lock:
            raw, _, revision = self.read()
            if request.get("revision") != revision:
                raise Conflict("The publication data changed. Reload the dashboard before rebuilding the résumé.")
            self.persist(raw, raw, compile_resume=True)
            return {"message": "Résumé rebuilt from saved publications.", "pdf": "/pdf/resume.pdf"}

    def persist(self, source, original, compile_resume=False):
        # Generate in isolation first: a compiler failure never damages real data.
        with tempfile.TemporaryDirectory(prefix="publication-build-") as tmp:
            stage = Path(tmp)
            (stage / "_data").mkdir()
            (stage / "_resume").mkdir()
            if compile_resume:
                shutil.copytree(self.root / "_resume", stage / "_resume", dirs_exist_ok=True)
                (stage / "_resume/resume.pdf").unlink(missing_ok=True)
                (stage / "files").mkdir()
            (stage / "_data/publication-data.yml").write_bytes(source)
            shutil.copy2(self.root / "compile-data.py", stage / "compile-data.py")
            environment = os.environ.copy()
            environment["PATH"] = environment.get("PATH", "") + os.pathsep + "/Library/TeX/texbin"
            result = subprocess.run(
                ["uv", "run", "--offline", "--no-project", "--python", sys.executable,
                 "python", str(stage / "compile-data.py")] + ([] if compile_resume else ["--no-latex"]),
                cwd=self.root, env=environment, capture_output=True, text=True, timeout=210 if compile_resume else 30)
            if result.returncode:
                if compile_resume:
                    raise ValueError("Could not rebuild the résumé. The previous PDF is unchanged.\n" + (result.stdout + result.stderr)[-2500:])
                raise ValueError("Could not regenerate publication files. Nothing was saved.\n" + result.stderr[-1500:])
            if self.source.read_bytes() != original:
                raise Conflict("The source file changed while saving. Reload the dashboard.")
            changes = {"_data/publication-data.yml": source}
            changes.update({name: (stage / name).read_bytes() for name in OUTPUTS})
            if compile_resume:
                for name in ("_resume/resume.pdf", "files/resume.pdf"):
                    pdf = (stage / name).read_bytes()
                    if not pdf.startswith(b"%PDF-"):
                        raise ValueError("The build did not produce a PDF. The previous résumé is unchanged.")
                    changes[name] = pdf
            changes = {name: content for name, content in changes.items()
                       if not (self.root / name).exists() or (self.root / name).read_bytes() != content}
            backup = self.root / "_publication_admin/backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
            before = {name: (self.root / name).read_bytes() if (self.root / name).exists() else None for name in changes}
            for name, content in before.items():
                if content is not None:
                    atomic_write(backup / name, content)
            try:
                for name, content in changes.items():
                    atomic_write(self.root / name, content)
            except OSError:
                for name, content in before.items():
                    if content is None:
                        (self.root / name).unlink(missing_ok=True)
                    else:
                        atomic_write(self.root / name, content)
                raise


def make_handler(store, token, port):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def do_GET(self):
            if not self.allowed():
                return self.reply(403, {"error": "Use the localhost dashboard URL."})
            path = unquote(urlsplit(self.path).path)
            try:
                if path == "/api/state":
                    with store.lock:
                        return self.reply(200, {**store.state(), "token": token})
                assets = {"/": ("index.html", "text/html; charset=utf-8"),
                          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                          "/conference-lookup.js": ("conference-lookup.js", "text/javascript; charset=utf-8"),
                          "/style.css": ("style.css", "text/css; charset=utf-8")}
                if path in assets:
                    name, mime = assets[path]
                    return self.reply(200, (ASSETS / name).read_bytes(), mime)
                if path.startswith("/pdf/"):
                    name = path[5:]
                    file = store.root / "files" / name
                    if Path(name).name == name and name.endswith(".pdf") and file.is_file():
                        return self.reply(200, file.read_bytes(), "application/pdf")
                return self.reply(404, {"error": "Not found."})
            except (OSError, yaml.YAMLError) as exc:
                return self.reply(500, {"error": str(exc)})

        def do_POST(self):
            if not self.allowed() or self.headers.get("X-Editor-Token") != token:
                return self.reply(403, {"error": "Reload the dashboard to reconnect."})
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
                return self.reply(403, {"error": "This editor accepts local requests only."})
            if self.path not in ("/api/change", "/api/rebuild-resume"):
                return self.reply(404, {"error": "Not found."})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length < 100_000:
                    raise ValueError("Invalid request size.")
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError("Invalid request.")
                return self.reply(200, store.rebuild_resume(request) if self.path == "/api/rebuild-resume" else store.change(request))
            except Conflict as exc:
                return self.reply(409, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            except (OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
                return self.reply(500, {"error": f"Save failed: {exc}"})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4001)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(PublicationStore(ROOT), secrets.token_urlsafe(32), args.port))
    print(f"Publication dashboard: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
