import os
import sys
import json
import csv
import re
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTITUICOES_FILE = os.path.join(BASE_DIR, 'coletor', 'instituicoes.json')
CSV_FILE = os.path.join(BASE_DIR, 'data', 'noticias.csv')
METRICS_FILE = os.path.join(BASE_DIR, 'data', 'metrics.json')

HEADERS_HTTP = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36 EduClipBrasil/1.0'
}

MAX_RETENTION_DAYS = 45

# Blacklist de palavras e caminhos de URLs não jornalísticos (Setores, Contatos, Base Legal, etc.)
URL_BLACKLIST = re.compile(
    r'/(contato|sobre|equipe|quem-somos|localizacao|telefones|organograma|reitoria|gabinete|'
    r'suap|sigaa|moodle|webmail|ava|calendario|'
    r'base-legal|estudanteespecialgrad|resolucoes|atas|normativas|'
    r'mapa-do-site|acessibilidade|privacidade|internacionalizacao|servicos)', re.I
)

# Padrões preferenciais de notícias
URL_NEWS_PATTERN = re.compile(r'/(noticia|post|blog|view|comunicado|202\d)', re.I)

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_valid_news(url, titulo):
    if not url or not titulo:
        return False

    # 1. Checar Blacklist de URLs
    if URL_BLACKLIST.search(url):
        return False

    # 2. Checar títulos curtos ou puramente navegacionais
    titulo_lower = titulo.lower()
    if len(titulo) < 15:
        return False

    nav_terms = ['leia mais', 'saiba mais', 'veja mais', 'contato', 'home', 'transparência', 'ouvidoria', 'baixar', 'download', 'acesse aqui', 'clique aqui']
    if any(term in titulo_lower for term in nav_terms):
        return False

    # 3. Se não tiver padrão de notícia explícito na URL, exige título mais longo/robusto
    if not URL_NEWS_PATTERN.search(url):
        if len(titulo) < 28:
            return False

    return True

def load_existing_links():
    links = set()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'link' in row and row['link']:
                    links.add(row['link'].strip())
    return links

def is_within_24h(pub_date_str):
    if not pub_date_str:
        return True
    try:
        pub_dt = datetime.strptime(pub_date_str, '%Y-%m-%d').date()
        today = datetime.now(timezone.utc).date()
        diff = (today - pub_dt).days
        return diff <= 2
    except Exception:
        return True

def process_ies(ies):
    items = []
    
    # 1. Coleta via RSS
    if ies.get('feed_url'):
        try:
            resp = requests.get(ies['feed_url'], headers=HEADERS_HTTP, verify=False, timeout=6)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                for entry in feed.entries:
                    titulo = clean_text(entry.get('title', ''))
                    link = entry.get('link', '').strip()
                    
                    if not is_valid_news(link, titulo):
                        continue

                    pub_date = ''
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = time.strftime('%Y-%m-%d', entry.published_parsed)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = time.strftime('%Y-%m-%d', entry.updated_parsed)
                    else:
                        pub_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                    if not is_within_24h(pub_date):
                        continue

                    categoria = 'Geral'
                    if 'tags' in entry and entry.tags:
                        categoria = entry.tags[0].get('term', 'Geral')

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
        except Exception:
            pass

    # 2. Fallback via Scraping HTML
    if not items and ies.get('news_url'):
        try:
            resp = requests.get(ies['news_url'], headers=HEADERS_HTTP, verify=False, timeout=6)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Seletores específicos de títulos de notícias
                selectors = ['article a', '.post-title a', '.entry-title a', '.tileHeadline a', '.item-title a', '.noticia-titulo a', 'h2 a', 'h3 a']
                articles = []
                for sel in selectors:
                    articles.extend(soup.select(sel))
                
                if not articles:
                    articles = soup.find_all('a', href=True)

                for a_tag in articles[:15]:
                    if not a_tag.get('href'):
                        continue
                    titulo = clean_text(a_tag.get_text())
                    link = a_tag['href']
                    if not link.startswith('http'):
                        base_domain = '/'.join(ies['news_url'].split('/')[:3])
                        link = base_domain + link if link.startswith('/') else base_domain + '/' + link

                    if is_valid_news(link, titulo):
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
        except Exception:
            pass

    return items

def prune_old_news():
    if not os.path.exists(CSV_FILE):
        return

    today = datetime.now(timezone.utc).date()
    cutoff_date = today - timedelta(days=MAX_RETENTION_DAYS)
    
    kept_rows = []
    fieldnames = ['titulo', 'data_publicacao', 'link', 'instituicao_sigla', 'instituicao_nome', 'uf', 'tipo', 'categoria', 'coletado_em']

    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = row.get('link', '')
            titulo = row.get('titulo', '')
            
            # Aplicar filtro de saneamento também na poda
            if not is_valid_news(link, titulo):
                continue
                
            pub_date_str = row.get('data_publicacao', '')
            try:
                pub_dt = datetime.strptime(pub_date_str, '%Y-%m-%d').date()
                if pub_dt >= cutoff_date:
                    kept_rows.append(row)
            except Exception:
                kept_rows.append(row)

    with open(CSV_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    print(f"Poda e Saneamento realizados: Mantidas {len(kept_rows)} noticias saneadas.")

def run_collector():
    print("=" * 60)
    print("EduClip Brasil — Coletor Saneado de Noticias")
    print(f"Executado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    if not os.path.exists(INSTITUICOES_FILE):
        print(f"Erro: {INSTITUICOES_FILE} nao encontrado!")
        sys.exit(1)

    with open(INSTITUICOES_FILE, 'r', encoding='utf-8') as f:
        instituicoes = json.load(f)

    existing_links = load_existing_links()
    new_items = []
    total_coletadas = 0

    print(f"Iniciando coleta paralela saneada para {len(instituicoes)} instituicoes...")

    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(process_ies, ies): ies for ies in instituicoes}
        for future in as_completed(futures):
            items = future.result()
            for item in items:
                total_coletadas += 1
                if item['link'] not in existing_links:
                    new_items.append(item)
                    existing_links.add(item['link'])

    print("Resultado da Coleta:")
    print(f"  • Materias validas recentes processadas: {total_coletadas}")
    print(f"  • Novas materias saneadas adicionadas: {len(new_items)}")

    file_exists = os.path.exists(CSV_FILE)
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    fieldnames = ['titulo', 'data_publicacao', 'link', 'instituicao_sigla', 'instituicao_nome', 'uf', 'tipo', 'categoria', 'coletado_em']

    with open(CSV_FILE, mode='a' if file_exists else 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for item in new_items:
            writer.writerow(item)

    prune_old_news()
    generate_metrics(len(instituicoes))

def generate_metrics(total_ies):
    if not os.path.exists(CSV_FILE):
        return

    noticias_all = []
    por_uf = {}
    por_tipo = {}
    por_ies = {}

    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            noticias_all.append(row)
            uf = row.get('uf', 'Outros')
            tipo = row.get('tipo', 'Outros')
            ies = row.get('instituicao_sigla', 'Outros')

            por_uf[uf] = por_uf.get(uf, 0) + 1
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
            por_ies[ies] = por_ies.get(ies, 0) + 1

    top_ies = sorted([{'sigla': k, 'total': v} for k, v in por_ies.items()], key=lambda x: x['total'], reverse=True)

    metrics = {
        'ultima_coleta': datetime.now(timezone.utc).isoformat(),
        'total_noticias': len(noticias_all),
        'total_instituicoes': total_ies,
        'por_uf': por_uf,
        'por_tipo': por_tipo,
        'top_instituicoes': top_ies[:10]
    }

    with open(METRICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"Metricas atualizadas em: {METRICS_FILE}")

if __name__ == '__main__':
    run_collector()
