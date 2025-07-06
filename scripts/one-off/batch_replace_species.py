import sqlite3

def search_species(cursor, query):
    query = query.lower()
    cursor.execute("SELECT id, name FROM Species")
    return [(id_, name) for id_, name in cursor.fetchall() if query in name.lower()]

def bulk_remap_annotations(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1) Ask for source file ID
    source_id = input("🔍 Enter SourceFile ID: ").strip()
    cursor.execute("SELECT id, filename FROM SourceFiles WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    if not row:
        print(f"❌ SourceFile ID {source_id} not found.")
        conn.close()
        return
    print(f"✅ SourceFile found: {row[1]}")

    # 2) Allow searching for old species names
    old_species_ids = []
    old_species_names = []
    while True:
        query = input("🔎 Search species to remap (or # to finish): ").strip()
        if query == "#":
            break
        matches = search_species(cursor, query)
        if not matches:
            print("⚠️ No matches found.")
            continue
        for idx, (_, name) in enumerate(matches):
            print(f"{idx + 1}. {name}")
        selection = input("Select number(s) separated by commas: ").strip()
        try:
            selected_idxs = [int(s) - 1 for s in selection.split(',')]
            for si in selected_idxs:
                sid, sname = matches[si]
                if sid not in old_species_ids:
                    old_species_ids.append(sid)
                    old_species_names.append(sname)
                    print(f"✅ Added: {sname}")
        except Exception as e:
            print(f"⚠️ Invalid selection: {e}")

    if not old_species_ids:
        print("🚫 No old species selected, aborting.")
        conn.close()
        return

    print(f"🎯 Selected old species: {', '.join(old_species_names)}")

    # 3) Select new target species
    while True:
        query = input("🔎 Search new target species: ").strip()
        matches = search_species(cursor, query)
        if not matches:
            print("⚠️ No matches found.")
            continue
        for idx, (_, name) in enumerate(matches):
            print(f"{idx + 1}. {name}")
        selection = input("Choose target species number: ").strip()
        try:
            target_idx = int(selection) - 1
            target_species_id, target_species_name = matches[target_idx]
            print(f"✅ Target species selected: {target_species_name}")
            break
        except (ValueError, IndexError):
            print("⚠️ Invalid choice.")
            continue

    # 4) Find clips tied to source file
    cursor.execute("""
        SELECT id, clip_path FROM Clips
        WHERE source_id = ?
    """, (source_id,))
    clips = cursor.fetchall()
    print(f"📦 Found {len(clips)} clips for this source file.")

    updated_count = 0
    for clip_id, clip_path in clips:
        # Check if target species already exists in this clip
        cursor.execute("""
            SELECT 1 FROM ClipAnnotations
            WHERE clip_id = ? AND species_id = ?
        """, (clip_id, target_species_id))
        if cursor.fetchone():
            print(f"⚠️ Skipped clip {clip_path}: already has annotation for {target_species_name}")
            continue

        # Delete annotations for all old species in this clip
        cursor.execute(f"""
            DELETE FROM ClipAnnotations
            WHERE clip_id = ? AND species_id IN ({','.join(['?']*len(old_species_ids))})
        """, (clip_id, *old_species_ids))

        # Insert new annotation for target species
        cursor.execute("""
            INSERT INTO ClipAnnotations (clip_id, species_id, verified, notes)
            VALUES (?, ?, 1, NULL)
        """, (clip_id, target_species_id))

        updated_count += 1
        print(f"🔄 Remapped clip {clip_path} → {target_species_name}")

    conn.commit()
    conn.close()
    print(f"\n🏁 Done: Updated {updated_count} annotations.")

if __name__ == "__main__":
    bulk_remap_annotations("./db/chorusAvery.db")
