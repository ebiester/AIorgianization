"""Disposable SQLite full-text index derived exclusively from vault Markdown."""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from aio.services.vault import VaultService
from aio.utils.frontmatter import read_frontmatter


class VaultIndex:
    """Maintain inventory, FTS, and wikilink edges for a local vault."""

    EXCLUDED_PARTS = {".aio", ".obsidian", ".trash", "trash", "Backup"}

    def __init__(self, vault: VaultService) -> None:
        self.vault = vault
        self.path = vault.config_path / "index.sqlite"

    def reconcile(self, rebuild: bool = False) -> dict[str, Any]:
        """Incrementally reconcile source Markdown into the disposable index."""
        self.vault.ensure_initialized()
        self.path.parent.mkdir(exist_ok=True)
        with self._connect() as conn:
            self._create_schema(conn)
            if rebuild:
                conn.execute("DELETE FROM links")
                conn.execute("DELETE FROM documents")
                conn.execute("DELETE FROM documents_fts")
            seen: set[str] = set()
            errors = 0
            for path in self._markdown_files():
                relative = path.relative_to(self.vault.vault_path).as_posix()
                seen.add(relative)
                try:
                    raw = path.read_bytes()
                    digest = hashlib.sha256(raw).hexdigest()
                    row = conn.execute(
                        "SELECT sha256 FROM documents WHERE path = ?", (relative,)
                    ).fetchone()
                    if row is not None and row[0] == digest:
                        continue
                    metadata, body = read_frontmatter(path)
                    title = self._title(body, path)
                    entity_type = str(metadata.get("type") or self._entity_type(relative))
                    tags = " ".join(str(tag) for tag in metadata.get("tags", []))
                    modified = path.stat().st_mtime
                    conn.execute("DELETE FROM documents WHERE path = ?", (relative,))
                    conn.execute("DELETE FROM documents_fts WHERE path = ?", (relative,))
                    conn.execute(
                        "INSERT INTO documents("
                        "path, title, body, metadata, entity_type, tags, sha256, modified"
                        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            relative,
                            title,
                            body,
                            repr(metadata),
                            entity_type,
                            tags,
                            digest,
                            modified,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO documents_fts(path, title, body, tags) VALUES (?, ?, ?, ?)",
                        (relative, title, body, tags),
                    )
                    conn.execute("DELETE FROM links WHERE source = ?", (relative,))
                    for target in self._links(body, metadata):
                        conn.execute(
                            "INSERT OR IGNORE INTO links(source, target) VALUES (?, ?)",
                            (relative, target),
                        )
                except Exception:
                    errors += 1
            stale = [
                row[0] for row in conn.execute("SELECT path FROM documents") if row[0] not in seen
            ]
            for relative in stale:
                conn.execute("DELETE FROM documents WHERE path = ?", (relative,))
                conn.execute("DELETE FROM documents_fts WHERE path = ?", (relative,))
                conn.execute(
                    "DELETE FROM links WHERE source = ? OR target = ?", (relative, relative)
                )
            conn.execute(
                "INSERT OR REPLACE INTO index_meta(key, value) VALUES ('last_reconciled', ?)",
                (datetime.now().isoformat(),),
            )
            return {
                "indexed": conn.execute("SELECT count(*) FROM documents").fetchone()[0],
                "errors": errors,
                "removed": len(stale),
            }

    def status(self) -> dict[str, Any]:
        """Return lightweight index health without forcing a scan."""
        if not self.path.exists():
            return {
                "exists": False,
                "indexed": 0,
                "pending": 0,
                "errors": 0,
                "last_reconciled": None,
                "exclusions": sorted(self.EXCLUDED_PARTS),
            }
        with self._connect() as conn:
            self._create_schema(conn)
            row = conn.execute(
                "SELECT value FROM index_meta WHERE key = 'last_reconciled'"
            ).fetchone()
            return {
                "exists": True,
                "indexed": conn.execute("SELECT count(*) FROM documents").fetchone()[0],
                "pending": 0,
                "errors": 0,
                "last_reconciled": row[0] if row else None,
                "exclusions": sorted(self.EXCLUDED_PARTS),
            }

    def search(self, query: str, scope: str | None = None, limit: int = 10) -> list[dict[str, str]]:
        """Search indexed content using SQLite FTS5, reconciling lazily when needed."""
        if not self.path.exists():
            self.reconcile()
        with self._connect() as conn:
            sql = (
                "SELECT d.path, d.title, d.body, d.entity_type, d.tags, "
                "snippet(documents_fts, 2, '<mark>', '</mark>', '…', 20) "
                "FROM documents_fts JOIN documents d USING(path) "
                "WHERE documents_fts MATCH ?"
            )
            args: list[Any] = [self._fts_query(query)]
            if scope:
                sql += " AND d.path LIKE ?"
                args.append(f"{scope.strip('/')}/%")
            sql += " ORDER BY bm25(documents_fts) LIMIT ?"
            args.append(max(1, min(limit, 50)))
            rows = conn.execute(sql, args).fetchall()
            return [
                {
                    "path": r[0],
                    "title": r[1],
                    "excerpt": r[5] or r[2][:300],
                    "entity_type": r[3],
                    "tags": r[4],
                    "match_reason": "full-text match",
                }
                for r in rows
            ]

    def backlinks(self, path: str) -> list[str]:
        """Return paths explicitly linking to a document."""
        if not self.path.exists():
            self.reconcile()
        with self._connect() as conn:
            return [
                r[0] for r in conn.execute("SELECT source FROM links WHERE target = ?", (path,))
            ]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _create_schema(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                path TEXT PRIMARY KEY, title TEXT, body TEXT, metadata TEXT,
                entity_type TEXT, tags TEXT, sha256 TEXT, modified REAL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
                USING fts5(path UNINDEXED, title, body, tags);
            CREATE TABLE IF NOT EXISTS links (
                source TEXT, target TEXT, PRIMARY KEY(source, target)
            );
            CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )

    def _markdown_files(self) -> list[Path]:
        return [
            path
            for path in self.vault.vault_path.rglob("*.md")
            if not any(
                part in self.EXCLUDED_PARTS
                for part in path.relative_to(self.vault.vault_path).parts
            )
            and not path.name.startswith(".")
        ]

    @staticmethod
    def _title(body: str, path: Path) -> str:
        return next(
            (line[2:].strip() for line in body.splitlines() if line.startswith("# ")),
            path.stem.replace("-", " "),
        )

    @staticmethod
    def _entity_type(path: str) -> str:
        return next(
            (
                part.lower().replace("-", "_")
                for part in path.split("/")
                if part in {"Tasks", "Projects", "Areas", "People", "ADRs", "Context-Packs"}
            ),
            "note",
        )

    @staticmethod
    def _links(body: str, metadata: dict[str, Any]) -> list[str]:
        import re

        links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", body)
        for value in metadata.values():
            if isinstance(value, str):
                links.extend(re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", value))
            elif isinstance(value, list):
                links.extend(
                    link[2:-2]
                    for link in value
                    if isinstance(link, str) and link.startswith("[[") and link.endswith("]]")
                )
        return [
            link.removesuffix(".md") + ".md" if not link.endswith(".md") else link for link in links
        ]

    @staticmethod
    def _fts_query(query: str) -> str:
        terms = [term.replace('"', "") for term in query.split() if term]
        return " AND ".join(f'"{term}"*' for term in terms) or '""'
