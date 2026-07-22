document.addEventListener('DOMContentLoaded', () => {
    let allNews = [];
    let filteredNews = [];
    let currentFilterType = 'ALL';
    let currentFilterIES = 'ALL';
    let searchQuery = '';

    const CSV_URL = './data/noticias.csv';

    const newsGrid = document.getElementById('news-grid');
    const searchInput = document.getElementById('search-input');
    const totalCountEl = document.getElementById('total-count');
    const iesCountEl = document.getElementById('ies-count');
    const lastUpdateEl = document.getElementById('last-update');
    const filterButtons = document.querySelectorAll('[data-filter]');

    // Fetch and parse CSV
    async function loadNews() {
        try {
            const resp = await fetch(CSV_URL);
            if (!resp.ok) throw new Error('Não foi possível carregar a base de notícias.');
            
            const csvText = await resp.text();
            allNews = parseCSV(csvText);
            
            // Sort by data_publicacao desc
            allNews.sort((a, b) => new Date(b.data_publicacao) - new Date(a.data_publicacao));
            
            filteredNews = [...allNews];
            updateStats();
            renderNews();
        } catch (err) {
            console.error('Erro ao carregar notícias:', err);
            newsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #ef4444; padding: 2rem;">
                ⚠️ Erro ao carregar dados do arquivo CSV. Verifique a conexão ou execute o coletor.
            </div>`;
        }
    }

    // CSV Parser Vanilla
    function parseCSV(text) {
        const lines = text.trim().split('\n');
        if (lines.length <= 1) return [];

        const headers = lines[0].split(',').map(h => h.trim());
        const data = [];

        for (let i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) continue;
            
            // Regex for CSV with quoted fields
            const row = [];
            let inQuotes = false;
            let current = '';

            for (let char of lines[i]) {
                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    row.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            row.push(current.trim());

            if (row.length === headers.length) {
                const item = {};
                headers.forEach((h, idx) => {
                    item[h] = row[idx].replace(/^"|"$/g, '');
                });
                data.push(item);
            }
        }
        return data;
    }

    // Update Header and Sidebar Stats
    function updateStats() {
        totalCountEl.textContent = allNews.length;
        
        const uniqueIES = new Set(allNews.map(n => n.instituicao_sigla));
        iesCountEl.textContent = uniqueIES.size;

        if (allNews.length > 0 && allNews[0].coletado_em) {
            const date = new Date(allNews[0].coletado_em);
            lastUpdateEl.textContent = date.toLocaleDateString('pt-BR') + ' às ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        }
    }

    // Render News Cards in Grid
    function renderNews() {
        newsGrid.innerHTML = '';

        if (filteredNews.length === 0) {
            newsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem;">
                Nenhuma notícia encontrada para os filtros selecionados.
            </div>`;
            return;
        }

        filteredNews.forEach(item => {
            const card = document.createElement('article');
            card.className = 'news-card';

            const formattedDate = item.data_publicacao 
                ? new Date(item.data_publicacao + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })
                : 'Data recente';

            card.innerHTML = `
                <div>
                    <div class="card-header">
                        <span class="ies-tag ${item.tipo}">${item.instituicao_sigla} • ${item.uf}</span>
                        <time class="news-date" datetime="${item.data_publicacao}">${formattedDate}</time>
                    </div>
                    <a href="${item.link}" target="_blank" rel="noopener" class="news-title" style="margin-top: 0.75rem;">
                        ${escapeHTML(item.titulo)}
                    </a>
                </div>
                <div class="card-footer">
                    <span class="categoria-badge">${escapeHTML(item.categoria || 'Geral')}</span>
                    <button class="action-btn" onclick="copyLink('${escapeHTML(item.link)}')">
                        📋 Copiar Link
                    </button>
                </div>
            `;
            newsGrid.appendChild(card);
        });
    }

    // Escape HTML helper
    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }

    // Copy Link Global Function
    window.copyLink = function(url) {
        navigator.clipboard.writeText(url).then(() => {
            alert('Link copiado para a área de transferência!');
        }).catch(err => {
            console.error('Erro ao copiar link:', err);
        });
    };

    // Filter Handlers
    filterButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const filterVal = btn.getAttribute('data-filter');
            currentFilterType = filterVal;
            applyFilters();
        });
    });

    // Search Input Handler
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        applyFilters();
    });

    // Apply Active Filters
    function applyFilters() {
        filteredNews = allNews.filter(item => {
            const matchesType = currentFilterType === 'ALL' || item.tipo === currentFilterType;
            const matchesSearch = searchQuery === '' || 
                item.titulo.toLowerCase().includes(searchQuery) || 
                item.instituicao_sigla.toLowerCase().includes(searchQuery) ||
                item.instituicao_nome.toLowerCase().includes(searchQuery);

            return matchesType && matchesSearch;
        });

        renderNews();
    }

    // Initialize
    loadNews();
});
