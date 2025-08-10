from app.database import get_db
from app.models import WineListFile, WineEntry

def print_entry(entry, idx):
    print(f'  Entry {idx+1}:')
    print(f'    Producer: {entry.producer}')
    print(f'    Cuvee: {entry.cuvee}')
    print(f'    Vintage: {entry.vintage}')
    print(f'    Price: {entry.price}')
    print(f'    Grape: {entry.grape_variety}')
    print(f'    Country: {entry.country}')
    print(f'    Region: {entry.region}')
    print(f'    Confidence: {entry.row_confidence}')
    raw = (entry.raw_text[:80] + '...') if entry.raw_text and len(entry.raw_text) > 80 else entry.raw_text
    print(f'    Raw: {raw}')
    print()

def main():
    db = next(get_db())
    wine_lists = db.query(WineListFile).all()
    print('--- DETAILED EXTRACTION BREAKDOWN ---')
    for wl in wine_lists:
        print(f'\nFile: {wl.filename} (Restaurant: {wl.restaurant.name})')
        print(f'Entries: {len(wl.wine_entries)}')
        for i, entry in enumerate(wl.wine_entries[:5]):
            print_entry(entry, i)

if __name__ == "__main__":
    main() 