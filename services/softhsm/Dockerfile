FROM debian:stable-slim

# Install SoftHSM2 and dependencies
RUN apt-get update && apt-get install -y \
    softhsm2 \
    opensc \
    libsofthsm2 \
    libsofthsm2-dev \
    openssl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create token directory
RUN mkdir -p /var/lib/softhsm/tokens && \
    chmod 700 /var/lib/softhsm/tokens

# Copy configuration file
COPY softhsm2.conf /etc/softhsm2/softhsm2.conf

# Copy initialization script
COPY init_softhsm.sh /usr/local/bin/init_softhsm.sh
RUN chmod +x /usr/local/bin/init_softhsm.sh

# Expose PKCS#11 interface port (optional, for remote access)
EXPOSE 5696

# Default command - show slots
CMD ["softhsm2-util", "--show-slots"]
