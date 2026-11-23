
import sqlite3

conn = sqlite3.connect("sessions.db")
cursor = conn.cursor()

columns = [
    ("emotional_progression", "TEXT"),
    ("replay_transcript", "TEXT")
]

existing_columns = [
    row[1] for row in cursor.execute(
        "PRAGMA table_info(sessions)"
    ).fetchall()
]

for column, data_type in columns:
    if column not in existing_columns:
        cursor.execute(
            f"ALTER TABLE sessions ADD COLUMN {column} {data_type}"
        )
        print(f"{column} added successfully")
    else:
        print(f"{column} already exists")

conn.commit()
conn.close()

print("Database update completed!")
