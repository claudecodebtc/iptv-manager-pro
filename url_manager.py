import requests
import urllib.parse
from pathlib import Path

def load_urls_from_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def process_urls(urls):
    m3u_urls = []
    stream_urls = []
    for url in urls:
        if url.lower().startswith(('http://', 'https://')):
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            if 'type' in query and 'm3u' in query['type'][0].lower() or '.m3u' in url.lower():
                m3u_urls.append(url)
            else:
                stream_urls.append(url)
    return m3u_urls, stream_urls

def fetch_m3u_content(url):
    try:
        response = requests.get(url, verify=False, allow_redirects=True, timeout=5)
        response.raise_for_status()
        return response.text.splitlines()
    except requests.RequestException:
        return None

def extract_username(url):
    parsed_url = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed_url.query)
    return query.get('username', ['-'])[0]  # Returnează '-' dacă nu e username

def generate_m3u_filename(url):
    parsed_url = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed_url.query)
    base = parsed_url.netloc.replace('.', '_')
    if 'username' in query:
        return f"{base}_{query['username'][0]}.m3u"
    return f"{base}_lista.m3u"

def save_urls_to_m3u(stream_urls, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for url in stream_urls:
            name = url.split('/')[-1] if '/' in url else "Canal necunoscut"
            f.write(f'#EXTINF:-1 group-title="Importate",{name}\n{url}\n')
