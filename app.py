from flask import Flask, request, jsonify, send_from_directory, send_file, Response, render_template
from flask_cors import CORS
import json
import yt_dlp
import requests
import os
import markdown
import uuid
import re
from datetime import timedelta
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
app = Flask(__name__, static_folder='/app/static')
CORS(app, resources={r"/*": {"origins": "<your domain name through which the app is exposed>"}})
logger = logging.getLogger(__name__)
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://host.docker.internal:11434/api')
TRANSCRIPTS_DIR = "/app/transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
DEFAULT_MODEL = "llama3.2:latest"
BASE_PROMPT = """You are a helpful assistant. Your only task is to summarize this transcript fragment for me. Be concise and formal. Start with an executive summary (150 words maximum), followed by a presentation of key information found in the transcript. Extract key information, such as events, activities, places, names or other key data (financial, social, scientific or otherwise) that can help me understand what that fragment is about. Present the data points in bulletpoint format and refer to the specific speaker as well as the occurrence time when it was mentioned and who said it. Complete this task based on the fragment (from {start_time} to {end_time})."""
# BASE_PROMPT = """Jesteś pomocnym asystentem. Twoim jedynym zadaniem jest podsumowanie tego fragmentu transkryptu. Rozpocznij od krótkiego opisu (maks. 150 słów), po którym przedstawione zostaną najważniejsze dane, dotyczące osób, tematów, miejsc, działań, aktywności lub innych danych (finansowych, społecznych itd), które pomogą mi lepiej zrozumieć, co jest przedmiotem tego fragmentu. Przedstaw wszystkie dane w postaci listy i do każdego punktu przypisz moment w transkrypcie, kiedy dany temat był omawiany. Wykonaj to zadanie w oparciu o fragment z {start_time} do {end_time}."""

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/')
def index():
    return render_template('index.html')

def download_subtitles(video_url, lang='en'):
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [lang],
        'skip_download': True,
        'outtmpl': os.path.join(TRANSCRIPTS_DIR, '%(id)s.%(ext)s'),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        subtitle_file = os.path.join(TRANSCRIPTS_DIR, f"{info['id']}.{lang}.vtt")
        
        if not os.path.exists(subtitle_file):
            raise Exception(f"No subtitles found for language: {lang}")
        
        with open(subtitle_file, 'r', encoding='utf-8') as file:
            subtitles = file.read()
        
        return subtitles, subtitle_file

def generate_with_progress(video_url, model, custom_base_prompt=None, subtitle_lang='en'):
    try:
        yield json.dumps({"progress": 10, "message": "Downloading subtitles..."}) + '\n'
        
        subtitles, subtitle_file = download_subtitles(video_url, subtitle_lang)
        yield json.dumps({"progress": 20, "message": "Subtitles downloaded"}) + '\n'
        
        chunks = chunk_subtitles(subtitles)
        yield json.dumps({"progress": 30, "message": "Preprocessing subtitles..."}) + '\n'
        
        summaries = []
        for i, (start_time, end_time, chunk_text) in enumerate(chunks):
            yield json.dumps({"progress": 30 + (i + 1) * 50 // len(chunks), "message": f"Summarizing chunk {i+1}/{len(chunks)}..."}) + '\n'
            chunk_summary = summarize_text(chunk_text, start_time, end_time, model, custom_base_prompt)
            summaries.append(f"## {start_time} - {end_time}\n\n{chunk_summary}")
        
        full_summary = "\n\n".join(summaries)
        
        transcript_filename = f"transcript_{uuid.uuid4().hex}.vtt"
        os.rename(subtitle_file, os.path.join(TRANSCRIPTS_DIR, transcript_filename))
        
        yield json.dumps({"progress": 90, "message": "Finalizing..."}) + '\n'
        
        result = {
            "summary": markdown.markdown(full_summary),
            "transcript_link": f"/transcript/{transcript_filename}"
        }
        
        yield json.dumps({"progress": 100, "message": "Complete!"}) + '\n'
        yield json.dumps(result) + '\n'
    except Exception as e:
        logger.exception("Error in generate_with_progress")
        yield json.dumps({"error": str(e)}) + '\n'

def parse_time(time_str):
    try:
        if '.' in time_str:
            h, m, rest = time_str.split(':')
            s, ms = rest.split('.')
            return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))
        else:
            h, m, s = time_str.split(':')
            return timedelta(hours=int(h), minutes=int(m), seconds=float(s))
    except ValueError as e:
        logger.error(f"Error parsing time: {time_str}. Error: {str(e)}")
        return None

def format_timedelta(td):
    if td is None:
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def sanitize_text(text):
    text = re.sub(r'\[.*?\]|\b[A-Z]{2,}\b:', '', text)
    return text.strip()

def chunk_subtitles(subtitles, chunk_duration=timedelta(minutes=5)):
    chunks = []
    current_chunk = []
    chunk_start_time = None
    chunk_end_time = None
    
    for line in subtitles.split('\n'):
        if '-->' in line:
            try:
                time_parts = line.split(' --> ')
                start_time = parse_time(time_parts[0].strip())
                end_time = parse_time(time_parts[1].split()[0].strip())
                
                if start_time is None or end_time is None:
                    continue
                
                if chunk_start_time is None:
                    chunk_start_time = start_time
                
                if start_time - chunk_start_time >= chunk_duration:
                    if current_chunk:
                        chunks.append((format_timedelta(chunk_start_time), format_timedelta(chunk_end_time), '\n'.join(current_chunk)))
                    current_chunk = []
                    chunk_start_time = start_time
                
                chunk_end_time = end_time
            except Exception as e:
                logger.error(f"Error processing time line: {line}. Error: {str(e)}")
                continue
        elif line.strip() and not line.strip().isdigit():
            current_chunk.append(line.strip())
    
    if current_chunk:
        chunks.append((format_timedelta(chunk_start_time), format_timedelta(chunk_end_time), '\n'.join(current_chunk)))
    
    return chunks

def summarize_text(text, start_time, end_time, model, custom_base_prompt=None):
    sanitized_text = sanitize_text(text)
    base_prompt = custom_base_prompt if custom_base_prompt else BASE_PROMPT
    prompt = base_prompt.format(start_time=start_time, end_time=end_time) + f"\n\n{sanitized_text}"
    
    logger.debug(f"Prompt sent to Ollama: {prompt}")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/generate", json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()['response']
        
        logger.debug(f"Response from Ollama: {result}")
        
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in Ollama request: {str(e)}")
        raise Exception(f"Error communicating with Ollama: {str(e)}")

@app.route('/summarize', methods=['POST'])
def summarize():
    video_url = request.json['video_url']
    model = request.json.get('model', 'llama3.2')
    custom_base_prompt = request.json.get('custom_base_prompt')
    subtitle_lang = request.json.get('subtitle_lang', 'en')
    
    return Response(generate_with_progress(video_url, model, custom_base_prompt, subtitle_lang), content_type='application/json')

@app.route('/transcript/<filename>')
def serve_transcript(filename):
    return send_file(os.path.join(TRANSCRIPTS_DIR, filename), as_attachment=True)

@app.route('/models', methods=['GET'])
def get_models():
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/tags")
        response.raise_for_status()
        models = response.json()['models']
        return jsonify({
            "models": models,
            "default_model": DEFAULT_MODEL
        })
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching models: {str(e)}")
        return jsonify({"error": f"Error fetching models: {str(e)}"}), 500

@app.route('/base_prompt', methods=['GET'])
def get_base_prompt():
    return jsonify({"base_prompt": BASE_PROMPT})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
