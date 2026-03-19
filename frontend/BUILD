shell_command(
    name="frontend-build",
    command="cd frontend && npm ci && npm run build",
    tools=["node", "npm"],
    output_directories=["dist"],
)

docker_image(
    name="frontend-image",
    source="Dockerfile",
)
