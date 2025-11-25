# ---- Build stage ----
FROM golang:1.22 AS builder
WORKDIR /app

# Copy everything and resolve dependencies
COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o extractor .

# ---- Runtime stage ----
FROM alpine:3.20
WORKDIR /app

# Install CA certs for HTTPS (needed for Socrata API)
RUN apk add --no-cache ca-certificates

# Copy binary from builder
COPY --from=builder /app/extractor /app/extractor

# Expose metrics port
EXPOSE 8000

# Run the extractor
ENTRYPOINT ["/app/extractor"]