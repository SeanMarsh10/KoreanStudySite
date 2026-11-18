# Hangul Cards (Vue + Django + MySQL)

## Backend
    mysql -u root -p -e "CREATE DATABASE hangul_cards CHARACTER SET utf8mb4;"
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    # set DB_USER / DB_PASSWORD / DB_HOST if not root@localhost without password
    python manage.py makemigrations cards && python manage.py migrate
    python manage.py runserver

## Frontend
    cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api and /media to :8000)

The "All cards" entry on the deck list is a live view of every card across decks (not a copy), so nothing is stored twice. A card with the same Korean and English as an existing one is rejected.

CSV: "Export CSV" downloads the cards in view (pictures are not included). "Import CSV" needs `korean` and `english` columns; optional columns are `deck`, `romanization`, `example`, `notes`. A `deck` column files each row into that deck (created if new); otherwise rows go to the deck you are viewing. Cards already in your collection (same Korean + English) are skipped.

Playlists: on the home page, "New playlist" combines two or more decks into one study set (it holds no cards of its own, so nothing is duplicated). Select a playlist to study the due cards from all its decks. After pulling this update run `python manage.py makemigrations cards && python manage.py migrate`.

Typed answers: in study mode, tick "Type the answer" (available when the answer side is English). Matching ignores case, punctuation and text in brackets, and accepts any one of several meanings separated by `;`, `,` or `/`.

Card styles in study mode: Korean to English, English to Korean, Picture to Korean, Picture to English.
Spaced repetition: Leitner boxes (1 to 5); "Knew it" moves a card up and delays it (1, 3, 7, 21 days), "Still learning" resets it to box 1.
