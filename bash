#!/bin/bash

# Plik logu
LOG_FILE="google_connection_log.txt"

# Funkcja do zapisu logu z timestampem
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Pętla nieskończona do sprawdzania połączenia
while true; do
    # Test połączenia z timeoutem 5 sekund
    if curl --silent --connect-timeout 5 --head --fail "https://www.google.com" > /dev/null; then
        log_message "Połączenie z www.google.com udane"
    else
        # Sprawdzenie, czy błąd to timeout
        if [[ $? -eq 28 ]]; then
            log_message "Timeout podczas próby połączenia z www.google.com"
        else
            log_message "Błąd połączenia z www.google.com"
        fi
    fi
    # Czekaj 1 sekundę
    sleep 1
done