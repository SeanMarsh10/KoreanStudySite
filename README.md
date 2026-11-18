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

Card styles in study mode: Korean to English, English to Korean, Picture to Korean, Picture to English.
Spaced repetition: Leitner boxes (1 to 5); "Knew it" moves a card up and delays it (1, 3, 7, 21 days), "Still learning" resets it to box 1.
