"""add multi-role support

Revision ID: 41880421d374
Revises: 59353a272550
Create Date: 2026-02-18 21:08:05.108113

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "41880421d374"
down_revision: Union[str, Sequence[str], None] = "59353a272550"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add multi-role support with user approval, roles, and permissions."""

    # Get database connection
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Helper to check if column exists
    def column_exists(table_name, column_name):
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        return column_name in columns

    # Helper to check if index exists
    def index_exists(table_name, index_name):
        indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
        return index_name in indexes

    # Add new columns to users table
    if not column_exists("users", "is_admin"):
        op.add_column(
            "users",
            sa.Column(
                "is_admin", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )

    if not column_exists("users", "approval_status"):
        op.add_column(
            "users",
            sa.Column(
                "approval_status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            ),
        )

    if not column_exists("users", "approval_note"):
        op.add_column(
            "users", sa.Column("approval_note", sa.String(length=500), nullable=True)
        )

    if not column_exists("users", "approved_by"):
        op.add_column("users", sa.Column("approved_by", sa.Integer(), nullable=True))
        # Add foreign key constraint
        op.create_foreign_key(
            "fk_users_approved_by",
            "users",
            "users",
            ["approved_by"],
            ["id"],
            ondelete="SET NULL",
        )

    if not column_exists("users", "approved_at"):
        op.add_column("users", sa.Column("approved_at", sa.DateTime(), nullable=True))

    if not column_exists("users", "is_password_changed"):
        op.add_column(
            "users",
            sa.Column(
                "is_password_changed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # Create index on approval_status
    if not index_exists("users", "ix_users_approval_status"):
        op.create_index("ix_users_approval_status", "users", ["approval_status"])

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create user_roles table
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # Create role_page_permissions table
    op.create_table(
        "role_page_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "page_id"),
    )

    # Create role_action_permissions table
    op.create_table(
        "role_action_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("action_name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "entity_type", "action_name"),
    )

    # Create role_entity_permissions table
    op.create_table(
        "role_entity_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("entity_class_name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "entity_class_name"),
    )

    # Insert system roles
    op.execute(
        """
        INSERT INTO roles (name, description, is_system, created_at, updated_at)
        VALUES
            ('admin', 'System administrator with full access', true, NOW(), NOW()),
            ('viewer', 'Read-only access to most features', true, NOW(), NOW()),
            ('editor', 'Can edit and create content', true, NOW(), NOW())
    """
    )

    # Get admin role ID
    admin_role_id = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'admin'")
    ).scalar()

    # Insert page permissions for admin role (all pages)
    pages = [
        "dashboard",
        "graph/management",
        "graph/instances",
        "graph/visualize",
        "graph/import",
        "data-products",
        "rules",
        "config",
        "users",
        "roles",
    ]

    for page in pages:
        op.execute(
            sa.text(
                "INSERT INTO role_page_permissions (role_id, page_id) VALUES (:role_id, :page_id)"
            ).bindparams(role_id=admin_role_id, page_id=page)
        )

    # Allow viewer to access chat and other basic pages
    viewer_role_id = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'viewer'")
    ).scalar()
    viewer_pages = ["chat", "dashboard", "instances", "data-products", "rules"]
    for page in viewer_pages:
        op.execute(
            sa.text(
                "INSERT INTO role_page_permissions (role_id, page_id) VALUES (:role_id, :page_id)"
            ).bindparams(role_id=viewer_role_id, page_id=page)
        )

    # Allow editor to access chat and other basic pages
    editor_role_id = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'editor'")
    ).scalar()
    editor_pages = [
        "chat",
        "dashboard",
        "instances",
        "data-products",
        "rules",
        "ontology",
        "import",
    ]
    for page in editor_pages:
        op.execute(
            sa.text(
                "INSERT INTO role_page_permissions (role_id, page_id) VALUES (:role_id, :page_id)"
            ).bindparams(role_id=editor_role_id, page_id=page)
        )


def downgrade() -> None:
    """Downgrade schema - Remove multi-role support."""

    # Drop tables in reverse order due to foreign keys
    op.drop_table("role_entity_permissions")
    op.drop_table("role_action_permissions")
    op.drop_table("role_page_permissions")
    op.drop_index("ix_user_roles_role_id", "user_roles")
    op.drop_index("ix_user_roles_user_id", "user_roles")
    op.drop_table("user_roles")
    op.drop_table("roles")

    # Drop index, foreign key and columns from users table
    op.drop_index("ix_users_approval_status", "users")
    op.drop_constraint("fk_users_approved_by", "users", type_="foreignkey")
    op.drop_column("users", "is_password_changed")
    op.drop_column("users", "approved_at")
    op.drop_column("users", "approved_by")
    op.drop_column("users", "approval_note")
    op.drop_column("users", "approval_status")
    op.drop_column("users", "is_admin")
