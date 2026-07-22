import os
import sys
import json
import csv
import re
import time
from datetime import datetime, timezone
import feedparser
import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings for gov sites with self-signed or intermediate cert issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTITUICOES_FILE = os.path.join(BASE_DIR, 'coletor', 'instituicoes.json')
CSV_FILE = os.path.join(BASE_DIR, 'data', 'noticias.csv')
METRICS_FILE = os.path.join(BASE_DIR, 'data', 'metrics.json')

HEADERS_HTTP = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36 EduClipBrasil/1.0'
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)  # remove HTML tags
    text = re.sub(r'\s+', ' ', text)     # normalize spaces
    return text.strip()

def load_existing_links():
    links = set()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'link' in row and row['link']:
                    links.add(row['link'].strip())
    return links

def fetch_rss(ies):
    items = []
    feed_url = ies.get('feed_url')
    if not feed_url:
        return items
    
    print(f"  --> Coletando RSS de {ies['sigla']}: {feed_url}")
    try:
        # Use requests to bypass SSL verification if needed, then pass content to feedparser
        resp = requests.get(feed_url, headers=HEADERS_HTTP, verify=False, timeout=15)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                titulo = clean_text(entry.get('title', ''))
                link = entry.get('link', '').strip()
                
                # Extract publication date
                pub_date = ''
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = time.strftime('%Y-%m-%d', entry.published_parsed)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = time.strftime('%Y-%m-%d', entry.updated_parsed)
                else:
                    pub_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                # Category
                categoria = 'Geral'
                if 'tags' in entry and entry.tags:
                    categoria = entry.tags[0].get('term', 'Geral')

                if titulo and link:
                    items.append({
                        'titulo': titulo,
                        'data_publicacao': pub_date,
                        'link': link,
                        'instituicao_sigla': ies['sigla'],
                        'instituicao_nome': ies['nome'],
                        'uf': ies['uf'],
                        'tipo': ies['tipo'],
                        'categoria': clean_text(categoria),
                        'coletado_em': datetime.now(timezone.utc).isoformat()
                    })
    except Exception as e:
        print(f"  [ERRO] Falha no RSS de {ies['sigla']}: {e}")
    return items

def fetch_scraping(ies):
    items = []
    news_url = ies.get('news_url')
    if not news_url:
        return items
    
    print(f"  --> Scraping HTML de {ies['sigla']}: {news_url}")
    try:
        resp = requests.get(news_url, headers=HEADERS_HTTP, verify=False, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Generic links search in news page
            articles = soup.find_all(['article', 'div', 'li', 'h2', 'h3'], class_=re.compile(r'noticia|post|item|card|titulo|news', re.I))
            
            if not articles:
                articles = soup.find_all('a', href=True)

            for art in articles[:20]:
                a_tag = art if art.name == 'a' else art.find('a', href=True)
                if not a_tag:
                    continue
                titulo = clean_text(a_tag.get_text())
                link = a_tag['href']
                if not link.startswith('http'):
                    base_domain = '/'.join(news_url.split('/')[:3])
                    link = base_domain + link if link.startswith('/') else base_domain + '/' + link

                if titulo and len(titulo) > 20 and not re.search(r'leia mais|saiba mais|veja mais|contato|home', titulo, re.I):
                    items.append({
                        'titulo': titulo,
                        'data_publicacao': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                        'link': link,
                        'instituicao_sigla': ies['sigla'],
                        'instituicao_nome': ies['nome'],
                        'uf': ies['uf'],
                        'tipo': ies['tipo'],
                        'categoria': 'Geral',
                        'coletado_em': datetime.now(timezone.utc).isoformat()
                    })
    except Exception as e:
        print(f"  [ERRO] Falha no Scraping de {ies['sigla']}: {e}")
    return items

def run_collector():
    print("=" * 60)
    print("📰 EduClip Brasil — Coletor Nacional de Notícias")
    print(f"⏰ Executado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    if not os.path.exists(INSTITUICOES_FILE):
        print(f"Erro: Arquivo {INSTITUICOES_FILE} não encontrado!")
        sys.exit(1)

    with open(INSTITUICOES_FILE, 'r', encoding='utf-8') as f:
        instituicoes = json.load(f)

    existing_links = load_existing_links()
    print(f"Base atual possui {len(existing_links)} notícias cadastradas.")

    new_items = []
    total_coletadas = 0

    for ies in instituicoes:
        items = []
        if ies.get('feed_url'):
            items = fetch_rss(ies)
        elif ies.get('news_url'):
            items = fetch_scraping(ies)
        
        print(f"      Encontradas: {len(items)} matérias.")
        for item in items:
            total_coletadas += 1
            if item['link'] not in existing_links:
                new_items.append(item)
                existing_links.add(item['link'])

    print(f"\n📊 Resultado da Coleta:")
    print(f"  • Total de matérias processadas: {total_coletadas}")
    print(f"  • Novas matérias adicionadas: {len(new_items)}")

    # Write to CSV
    file_exists = os.path.exists(CSV_FILE)
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    
    fieldnames = ['titulo', 'data_publicacao', 'link', 'instituicao_sigla', 'instituicao_nome', 'uf', 'tipo', 'categoria', 'coletado_em']
    
    with open(CSV_FILE, mode='a' if file_exists else 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for item in new_items:
            writer.writerow(item)

    print(f"✅ CSV atualizado em: {CSV_FILE}")

    # Generate Metrics JSON
    generate_metrics(len(instituicoes))

def generate_metrics(total_ies):
    if not os.path.exists(CSV_FILE):
        return

    noticias_all = []
    por_uf = {}
    por_tipo = {}
    por_ies = {}
    por_dia = {}

    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            noticias_all.append(row)
            uf = row.get('uf', 'Outros')
            tipo = row.get('tipo', 'Outros')
            ies = row.get('instituicao_sigla', 'Outros')
            dia = row.get('data_publicacao', 'Outros')

            por_uf[uf] = por_uf.get(uf, 0) + 1
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
            por_ies[ies] = por_ies.get(ies, 0) + 1
            por_dia[dia] = por_dia.get(dia, 0) + 1

    top_ies = sorted([{'sigla': k, 'total': v} for k, v in por_ies.items()], key=lambda x: x['total'], reverse=True)

    metrics = {
        'ultima_coleta': datetime.now(timezone.utc).isoformat(),
        'total_noticias': len(noticias_all),
        'total_instituicoes': total_ies,
        'por_uf': por_uf,
        'por_tipo': por_tipo,
        'por_dia': por_dia,
        'top_instituicoes': top_ies[:5]
    }

    with open(METRICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"✅ Métricas JSON geradas em: {METRICS_FILE}")

if __name__ == '__main__':
    run_collector()
