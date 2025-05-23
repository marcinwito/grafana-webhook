#!/bin/bash

# Plik logu
LOG_FILE="google_connection_log.txt"

# Funkcja do zapisu logu z timestampem
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Pętla nieskończona do sprawdzania połączenia
while true; do
    # Pobierz adres IP dla www.google.com
    IP=$(getent hosts www.google.com | awk '{ print $1 }' | head -n 1)

    if [ -z "$IP" ]; then
        log_message "Nie udało się ustalić adresu IP dla www.google.com"
    else
        # Test połączenia z timeoutem 5 sekund
        if curl --silent --connect-timeout 5 --head --fail "https://www.google.com" > /dev/null; then
            log_message "Połączenie z www.google.com (IP: $IP) udane"
        else
            # Sprawdzenie, czy błąd to timeout
            if [[ $? -eq 28 ]]; then
                log_message "Timeout podczas próby połączenia z www.google.com (IP: $IP)"
            else
                log_message "Błąd połączenia z www.google.com (IP: $IP)"
            fi
        fi
    fi
    # Czekaj 1 sekundę
    sleep 1
done