# YouTube Video Summarizer

## Overview

YouTube Video Summarizer is a web application that automatically generates concise summaries of YouTube videos using AI-powered language models. The application downloads video subtitles, processes them, and uses Ollama as an underlying FM hosting engine to create comprehensive summaries.

### Key Features:
- Automatic subtitle download from YouTube videos
- Support for multiple languages
- Customizable AI models for summarization based on one's own hosted Ollama library
- Progress tracking during the summarization process
- Downloadable transcripts
- Support for cookies [ (see this document for more details)](./cookie_extract.md)

## How It Works

1. Users input a YouTube URL and select their preferred language and AI model.
2. The application downloads the video's subtitles in the chosen language.
3. Subtitles are processed and divided into manageable chunks representing 5 minutes. This is to make sure that the transcript fragment does not go beyond selected FM's context window.
4. Each chunk is summarized using the selected AI model via the Ollama API.
5. The individual summaries are combined to create a comprehensive overview of the video content.

## Technical Requirements

To set up a development environment, you'll need:

- Python 3.9 or higher
- Docker and Docker Compose
- Ollama (running locally or on a accessible server)


## Dependencies

Main Python libraries used:
- Flask
- yt-dlp
- requests
- markdown

For a complete list, see `requirements.txt`.

## Containerization and Local Deployment

To containerize and run the application locally:


## Containerization and Local Deployment

To containerize and run the application locally:

1. Clone the repository:
   ```
   git clone https://github.com/your-username/youtube-video-summarizer.git
   cd youtube-video-summarizer
   ```

2. Build and run the Docker container:
   ```
   docker-compose up --build
   ```

3. Access the application at `http://localhost:17430`

## Environment Variables

The following environment variables are externalized in the `docker-compose.yml` file:

- `PORT`: The port on which the Flask application runs inside the container (default: 8080)
- `OLLAMA_BASE_URL`: The URL of the Ollama API (default: http://host.docker.internal:11434/api)

Variables that need to be modified inside `app.py`:

- `CORS` settings: Update the allowed origins if needed
- `DEFAULT_MODEL`: Change the default AI model if required
- `BASE_PROMPT`: Modify the base prompt for summarization if desired

## Note

Ensure that Ollama is running and accessible from the Docker container. The default configuration assumes Ollama is running on the host machine and is accessible via `host.docker.internal`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)
