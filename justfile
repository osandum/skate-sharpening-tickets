# justfile
image_name := "skate-sharpening"
registry := "sandum.net:5000/osa"

# Build Docker image
build:
    docker build -t {{image_name}}:latest .

# Tag and push release
release version:
    docker build -t {{image_name}}:{{version}} .
    docker tag {{image_name}}:{{version}} {{registry}}/{{image_name}}:{{version}}
    docker push {{registry}}/{{image_name}}:{{version}}
