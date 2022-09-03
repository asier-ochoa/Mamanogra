def generate() -> str:
    servers_schema = """
    CREATE TABLE "servers" (
        "id"	INTEGER NOT NULL UNIQUE,
        "discord_id" TEXT NOT NULL UNIQUE,
        "name"	TEXT NOT NULL,
        "owner"	INTEGER NOT NULL,
        "whitelist"	INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY("id" AUTOINCREMENT),
        FOREIGN KEY("owner") REFERENCES "users"("id")
    );
    """

    users_schema = """
    CREATE TABLE "users" (
        "id"	INTEGER NOT NULL UNIQUE,
        "discord_id"	TEXT NOT NULL UNIQUE,
        "name"	TEXT NOT NULL,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
    """

    user_membership_schema = """
    CREATE TABLE "user_membership" (
        "server_id"	INTEGER NOT NULL,
        "user_id"	INTEGER NOT NULL,
        "perm_level"	TEXT NOT NULL,
        FOREIGN KEY("server_id") REFERENCES "servers"("id"),
        FOREIGN KEY("user_id") REFERENCES "users"("id")
    );
    """

    return "".join([v for v in locals().values()])
