import sqlite3
import os
import re

def link_clips_to_sources_flex(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get clips missing a source_id
    cursor.execute("""
        SELECT id, clip_path FROM Clips
        WHERE source_id IS NULL
    """)
    clips_to_update = cursor.fetchall()

    print(f"🔎 Found {len(clips_to_update)} clips needing source linking...")

    updated_count = 0
    for clip_id, clip_path in clips_to_update:
        base_name = os.path.splitext(os.path.basename(clip_path))[0]
        match_found = False

        # Create fallback patterns:
        patterns = []

        # 1) Full base name
        patterns.append(base_name)

        # 2) Strip after last underscore, if exists
        if "_" in base_name:
            shortened = "_".join(base_name.split("_")[:-1])
            if shortened:
                patterns.append(shortened)

        # 3) Only date part: first 6 digits (yyMMdd)
        date_match = re.match(r'^\d{6}', base_name)
        if date_match:
            patterns.append(date_match.group(0))

        for pat in patterns:
            cursor.execute("""
                SELECT id, from_date, to_date FROM SourceFiles
                WHERE filename LIKE ?
                ORDER BY filename ASC
                LIMIT 1
            """, (f"{pat}%",))
            source = cursor.fetchone()
            if source:
                source_id, from_date, to_date = source
                cursor.execute("""
                    UPDATE Clips
                    SET source_id = ?, start_date_source = ?, end_date_source = ?
                    WHERE id = ?
                """, (source_id, from_date, to_date, clip_id))
                updated_count += 1
                print(f"✅ Linked Clip ID {clip_id} -> Source ID {source_id} using pattern '{pat}%'")
                match_found = True
                break

        if not match_found:
            print(f"⚠️ No matching source found for clip: {clip_path}")

    conn.commit()
    conn.close()
    print(f"\n🏁 Done: Linked {updated_count} of {len(clips_to_update)} clips.")

if __name__ == "__main__":
    link_clips_to_sources_flex("./db/chorusAvery.db")
