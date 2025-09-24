# justfile
image_name := "skate-sharpening"
registry := "sandum.net:5000/osa"

@_default:
    @just --list --unsorted

# Build Docker image
build version='latest':
    docker build -t {{image_name}}:{{version}} \
    --build-arg BUILD_TIME="$(date -u +'%Y-%m-%d %H:%M:%S UTC')" \
    --build-arg GIT_HASH="$(git rev-parse HEAD)" \
    --label org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --label org.opencontainers.image.source="$(git config --get remote.origin.url | sed 's/\.git$//')" \
    --label org.opencontainers.image.revision="$(git rev-parse HEAD)" \
    .

# Tag and push release
release version='latest':
    @just build {{version}}
    docker tag {{image_name}}:{{version}} {{registry}}/{{image_name}}:{{version}}
    @just refresh-staging {{version}}

# Refresh staging deployment
refresh-staging version='latest':
    docker push {{registry}}/{{image_name}}:{{version}}
    ssh abode docker compose -f ~/sms-ticket/compose.yml up -d --pull=always

# Test SMS functionality
test-sms:
    python test_sms.py

# Run development server
dev:
    FLASK_ENV=development FLASK_DEBUG=1 python app.py

# Install/update dependencies
install:
    pip install -r requirements.txt

# Show current environment variables for debugging
show-env:
    @echo "GATEWAYAPI_TOKEN: ${GATEWAYAPI_TOKEN}"
    @echo "BASE_URL: ${BASE_URL}"
    @echo "SECRET_KEY: ${SECRET_KEY}"
