#!/bin/bash

# Plik logu
LOG_FILE="google_connection_log.txt"

# Funkcja do zapisu logu z timestampem
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Pętla nieskończona do sprawdzania połączenia
while true; do
    # Pobierz adres IP dla www.google.com, wymuszając IPv4
    # 'dig +short A www.google.com' zwraca tylko rekordy A (IPv4)
    IP=$(dig +short A www.google.com | head -n 1)

    if [ -z "$IP" ]; then
        log_message "Nie udało się ustalić adresu IP IPv4 dla www.google.com"
    else
        # Test połączenia z timeoutem 5 sekund, wymuszając IPv4 (-4)
        if curl -4 --silent --connect-timeout 5 --head --fail "https://www.google.com" > /dev/null; then
            log_message "Połączenie z www.google.com (IP: $IP) udane (IPv4)"
        else
            # Sprawdzenie, czy błąd to timeout
            if [[ $? -eq 28 ]]; then
                log_message "Timeout podczas próby połączenia z www.google.com (IP: $IP) (IPv4)"
            else
                log_message "Błąd połączenia z www.google.com (IP: $IP) (IPv4)"
            fi
        fi
    fi
    # Czekaj 1 sekundę
    sleep 1
done
