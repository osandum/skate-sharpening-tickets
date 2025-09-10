# justfile
image_name := "skate-sharpening"
registry := "sandum.net:5000/osa"

@_default:
    @just --list --unsorted

# Build Docker image
build:
    docker build -t {{image_name}}:latest .

# Tag and push release
release version='latest':
    docker build -t {{image_name}}:{{version}} .
    docker tag {{image_name}}:{{version}} {{registry}}/{{image_name}}:{{version}}
    docker push {{registry}}/{{image_name}}:{{version}}
    @just refresh-staging

# Refresh staging deployment
refresh-staging:
    ssh abode docker compose -f ~/sms-ticket/compose.yml up -d --pull=always

# Test SMS functionality
test-sms:
    #!/usr/bin/env bash
    source venv/bin/activate
    python test_sms.py

# Run development server
dev:
    #!/usr/bin/env bash
    source venv/bin/activate
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    python app.py

# Install/update dependencies
install:
    #!/usr/bin/env bash
    source venv/bin/activate
    pip install -r requirements.txt

# Show current environment variables for debugging
show-env:
    @echo "GATEWAYAPI_TOKEN: ${GATEWAYAPI_TOKEN}"
    @echo "BASE_URL: ${BASE_URL}"
    @echo "SECRET_KEY: ${SECRET_KEY}"
