"""SQLite mirror of run history — powers list_runs / get_run_status / compare_runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    scenario_id   TEXT NOT NULL,
    room_name     TEXT,
    agent_name    TEXT,
    status        TEXT NOT NULL DEFAULT 'running',
    started_utc   TEXT NOT NULL,
    ended_utc     TEXT,
    duration_ms   INTEGER,
    turn_count    INTEGER,
    tool_errors   INTEGER,
    verdict       TEXT,
    report_dir    TEXT,
    summary_json  TEXT
);

CREATE TABLE IF NOT EXISTS run_events (
    run_id        TEXT NOT NULL,
    event_id      TEXT NOT NULL,
    seq           INTEGER NOT NULL,
    turn          INTEGER,
    kind          TEXT NOT NULL,
    ts            INTEGER NOT NULL,
    datetime_utc  TEXT NOT NULL,
    source        TEXT,
    payload_json  TEXT NOT NULL,
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_run_events_kind ON run_events (run_id, kind);

CREATE TABLE IF NOT EXISTS run_turns (
    run_id          TEXT NOT NULL,
    turn            INTEGER NOT NULL,
    user_text       TEXT,
    agent_text      TEXT,
    turn_taking_ms  INTEGER,
    tool_count      INTEGER,
    tool_errors     INTEGER,
    interrupted     INTEGER,
    PRIMARY KEY (run_id, turn)
);
"""


class RunStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)

    async def _connect(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path)
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA)
        return db

    async def create_run(
        self,
        run_id: str,
        scenario_id: str,
        room_name: str,
        agent_name: str,
        started_utc: str,
        report_dir: str,
    ) -> None:
        db = await self._connect()
        try:
            await db.execute(
                "INSERT INTO runs (run_id, scenario_id, room_name, agent_name, status, started_utc, report_dir)"
                " VALUES (?, ?, ?, ?, 'running', ?, ?)",
                (run_id, scenario_id, room_name, agent_name, started_utc, report_dir),
            )
            await db.commit()
        finally:
            await db.close()

    async def finish_run(self, run_id: str, status: str, summary: dict[str, Any], ended_utc: str) -> None:
        verdict = summary.get("verdict")
        db = await self._connect()
        try:
            await db.execute(
                "UPDATE runs SET status=?, ended_utc=?, duration_ms=?, turn_count=?, tool_errors=?,"
                " verdict=?, summary_json=? WHERE run_id=?",
                (
                    status,
                    ended_utc,
                    summary.get("duration_ms"),
                    summary.get("turn_count"),
                    summary.get("tool_errors"),
                    json.dumps(verdict, ensure_ascii=False) if verdict else None,
                    json.dumps(summary, ensure_ascii=False),
                    run_id,
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def insert_events(self, run_id: str, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        db = await self._connect()
        try:
            await db.executemany(
                "INSERT OR REPLACE INTO run_events"
                " (run_id, event_id, seq, turn, kind, ts, datetime_utc, source, payload_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        e["event_id"],
                        e["seq"],
                        e.get("turn"),
                        e["kind"],
                        e["ts"],
                        e["datetime_utc"],
                        e.get("source"),
                        json.dumps(e, ensure_ascii=False),
                    )
                    for e in events
                ],
            )
            await db.commit()
        finally:
            await db.close()

    async def insert_turns(self, run_id: str, turns: list[dict[str, Any]]) -> None:
        if not turns:
            return
        db = await self._connect()
        try:
            await db.executemany(
                "INSERT OR REPLACE INTO run_turns"
                " (run_id, turn, user_text, agent_text, turn_taking_ms, tool_count, tool_errors, interrupted)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        t["turn"],
                        t.get("user_text"),
                        t.get("agent_text"),
                        t.get("turn_taking_ms"),
                        t.get("tool_count", 0),
                        t.get("tool_errors", 0),
                        1 if t.get("interrupted") else 0,
                    )
                    for t in turns
                ],
            )
            await db.commit()
        finally:
            await db.close()

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        db = await self._connect()
        try:
            cur = await db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,))
            row = await cur.fetchone()
            return dict(row) if row else None
        finally:
            await db.close()

    async def list_runs(self, limit: int = 20, scenario_id: str | None = None) -> list[dict[str, Any]]:
        db = await self._connect()
        try:
            if scenario_id:
                cur = await db.execute(
                    "SELECT run_id, scenario_id, room_name, agent_name, status, started_utc, duration_ms,"
                    " turn_count, tool_errors, verdict FROM runs WHERE scenario_id=?"
                    " ORDER BY started_utc DESC LIMIT ?",
                    (scenario_id, limit),
                )
            else:
                cur = await db.execute(
                    "SELECT run_id, scenario_id, room_name, agent_name, status, started_utc, duration_ms,"
                    " turn_count, tool_errors, verdict FROM runs ORDER BY started_utc DESC LIMIT ?",
                    (limit,),
                )
            return [dict(r) for r in await cur.fetchall()]
        finally:
            await db.close()

    async def get_turns(self, run_id: str) -> list[dict[str, Any]]:
        db = await self._connect()
        try:
            cur = await db.execute("SELECT * FROM run_turns WHERE run_id=? ORDER BY turn", (run_id,))
            return [dict(r) for r in await cur.fetchall()]
        finally:
            await db.close()
