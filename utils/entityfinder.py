import sqlite3

class EntityFinder:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def search_species(self, query):
        """
        Returns a list of (id, name) for Species where name contains the query (case-insensitive).
        """
        self.cursor.execute("SELECT id, name FROM Species")
        matches = [
            (id_, name) for id_, name in self.cursor.fetchall()
            if query.lower() in name.lower()
        ]
        return matches

    def search_non_species(self, query):
        """
        Returns a list of (id, name) for NonAnimalSounds where name contains the query (case-insensitive).
        """
        self.cursor.execute("SELECT id, name FROM NonAnimalSounds")
        matches = [
            (id_, name) for id_, name in self.cursor.fetchall()
            if query.lower() in name.lower()
        ]
        return matches

    def prompt_search(self, mode):
        """
        Prompts user for a search query, performs the search, displays matches,
        and lets them select one or more items by number. Returns list of (id, name).
        mode: 'species' or 'non_species'
        """
        results = []
        while True:
            query = input(f"\n🔎 Enter search term for {mode.replace('_', ' ')} (or # to finish): ").strip()
            if query == "#":
                break

            if mode == 'species':
                matches = self.search_species(query)
            elif mode == 'non_species':
                matches = self.search_non_species(query)
            else:
                print("⚠️ Invalid mode.")
                continue

            if not matches:
                print("🚫 No matches found.")
                continue

            print(f"\nFound {len(matches)} matches:")
            for idx, (_, name) in enumerate(matches):
                print(f"{idx + 1}. {name}")

            sel = input("Select number(s) separated by commas, or leave blank to skip: ").strip()
            if not sel:
                continue
            try:
                selected = [int(s.strip()) - 1 for s in sel.split(',')]
                for s in selected:
                    if 0 <= s < len(matches) and matches[s] not in results:
                        results.append(matches[s])
                        print(f"✅ Added: {matches[s][1]}")
            except Exception as e:
                print(f"⚠️ Invalid selection: {e}")
        return results

    def close(self):
        self.conn.close()
