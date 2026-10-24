"""Hero design revision tables and R0 seed from Storefront pack.

Revision ID: f2a3b4c5d6e7
Revises: a2b3c4d5e6f7, a3f410b5c6d7 (merge)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: str | tuple[str, str] = ("a2b3c4d5e6f7", "a3f410b5c6d7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXPECTED_R0_SHA = "1d4e7aa46f2d6f3aa04578be67af18bbb9672e337ef1b1ad8eeaa16acbdae674"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upgrade() -> None:
    op.create_table(
        "hero_design_revisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("profile", sa.String(length=64), nullable=False, server_default="reborn-5@v1"),
        sa.Column("pack_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pack_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_revision_id", sa.String(length=36), sa.ForeignKey("hero_design_revisions.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("publish_comment", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','published','superseded','rolled_back')",
            name="ck_hero_design_revisions_status",
        ),
    )
    op.create_index("ix_hero_design_revisions_created_at", "hero_design_revisions", ["created_at"])
    op.create_index("ix_hero_design_revisions_status", "hero_design_revisions", ["status"])

    op.create_table(
        "hero_design_published",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("revision_id", sa.String(length=36), sa.ForeignKey("hero_design_revisions.id"), nullable=False),
        sa.Column("etag", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_hero_design_published_singleton"),
    )

    op.create_table(
        "hero_design_drafts",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("base_revision_id", sa.String(length=36), sa.ForeignKey("hero_design_revisions.id"), nullable=True),
        sa.Column("draft_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_hero_design_drafts_singleton"),
    )

    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT 1 FROM hero_design_published WHERE id = 1")).fetchone()
    if exists:
        return

    repo_root = Path(__file__).resolve().parents[2]
    pack_path = repo_root / "frontend" / "Storefront" / "public" / "hero-design.json"
    raw = pack_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    pack = json.loads(raw.decode("utf-8"))
    if len([s for s in pack.get("slides", []) if s.get("isActive")]) != 5:
        raise RuntimeError("hero-design.json must contain 5 active slides")
    if sha != EXPECTED_R0_SHA:
        raise RuntimeError(f"Unexpected R0 SHA {sha}")

    rev_id = str(uuid.uuid4())
    bind.execute(
        sa.text(
            """
            INSERT INTO hero_design_revisions
            (id, schema_version, profile, pack_json, pack_sha256, parent_revision_id, status)
            VALUES (:id, :schema_version, :profile, CAST(:pack_json AS JSONB), :sha, NULL, 'published')
            """
        ),
        {
            "id": rev_id,
            "schema_version": int(pack.get("version") or 1),
            "profile": "reborn-5@v1",
            "pack_json": json.dumps(pack, ensure_ascii=False),
            "sha": sha,
        },
    )
    bind.execute(
        sa.text(
            "INSERT INTO hero_design_published (id, revision_id, etag) VALUES (1, :rid, :etag)"
        ),
        {"rid": rev_id, "etag": sha},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO hero_design_drafts (id, base_revision_id, draft_json, lock_version)
            VALUES (1, :rid, CAST(:pack_json AS JSONB), 1)
            """
        ),
        {"rid": rev_id, "pack_json": json.dumps(pack, ensure_ascii=False)},
    )


def downgrade() -> None:
    op.drop_table("hero_design_drafts")
    op.drop_table("hero_design_published")
    op.drop_table("hero_design_revisions")
