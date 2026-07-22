document.addEventListener('DOMContentLoaded', () => {
    let allNews = [];
    let filteredNews = [];
    let currentFilterType = 'ALL';
    let searchQuery = '';
    let currentPage = 1;
    const ITEMS_PER_PAGE = 20;

    const CSV_URL = './data/noticias.csv';

    const newsGrid = document.getElementById('news-grid');
    const searchInput = document.getElementById('search-input');
    const totalCountEl = document.getElementById('total-count');
    const iesCountEl = document.getElementById('ies-count');
    const lastUpdateEl = document.getElementById('last-update');
    const filterButtons = document.querySelectorAll('[data-filter]');

    // Carregar CSV de Notícias
    async function loadNews() {
        try {
            const resp = await fetch(CSV_URL);
            if (!resp.ok) throw new Error('Não foi possível carregar a base de notícias.');
            
            const csvText = await resp.text();
            allNews = parseCSV(csvText);
            
            // Ordenar por data_publicacao desc
            allNews.sort((a, b) => new Date(b.data_publicacao) - new Date(a.data_publicacao));
            
            applyFilters();
        } catch (err) {
            console.error('Erro ao carregar notícias:', err);
            newsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #ef4444; padding: 2rem;">
                ⚠️ Erro ao carregar dados do arquivo CSV.
            </div>`;
        }
    }

    // Parser CSV Vanilla com suporte a campos com aspas
    function parseCSV(text) {
        const lines = text.trim().split('\n');
        if (lines.length <= 1) return [];

        const headers = lines[0].split(',').map(h => h.trim());
        const data = [];

        for (let i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) continue;
            
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

    // Aplicar Filtros e Reiniciar para Página 1
    function applyFilters() {
        filteredNews = allNews.filter(item => {
            const matchType = (currentFilterType === 'ALL') || (item.tipo === currentFilterType);
            const matchSearch = !searchQuery || 
                                (item.titulo && item.titulo.toLowerCase().includes(searchQuery)) ||
                                (item.instituicao_sigla && item.instituicao_sigla.toLowerCase().includes(searchQuery)) ||
                                (item.instituicao_nome && item.instituicao_nome.toLowerCase().includes(searchQuery)) ||
                                (item.uf && item.uf.toLowerCase().includes(searchQuery));
            return matchType && matchSearch;
        });

        currentPage = 1;
        updateStats();
        renderNews();
    }

    // Atualizar Estatísticas no Topo
    function updateStats() {
        totalCountEl.textContent = allNews.length;
        const uniqueIES = new Set(allNews.map(n => n.instituicao_sigla));
        iesCountEl.textContent = uniqueIES.size;

        if (allNews.length > 0 && allNews[0].coletado_em) {
            const date = new Date(allNews[0].coletado_em);
            lastUpdateEl.textContent = date.toLocaleDateString('pt-BR') + ' às ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        }
    }

    // Renderizar Notícias Paginadas (20 Itens por Página)
    function renderNews() {
        newsGrid.innerHTML = '';

        if (filteredNews.length === 0) {
            newsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem;">
                Nenhuma notícia encontrada para os filtros selecionados.
            </div>`;
            renderPaginationControls(0);
            return;
        }

        const totalPages = Math.ceil(filteredNews.length / ITEMS_PER_PAGE);
        if (currentPage > totalPages) currentPage = totalPages;

        const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
        const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, filteredNews.length);
        const pageItems = filteredNews.slice(startIndex, endIndex);

        pageItems.forEach(item => {
            const card = document.createElement('article');
            card.className = 'news-card';

            const formattedDate = item.data_publicacao 
                ? new Date(item.data_publicacao + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })
                : 'Data recente';

            card.innerHTML = `
                <div>
                    <div class="card-header">
                        <span class="ies-tag ${item.tipo}">${escapeHTML(item.instituicao_sigla)} • ${escapeHTML(item.uf)}</span>
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

        renderPaginationControls(totalPages, startIndex + 1, endIndex, filteredNews.length);
    }

    // Renderizar Painel de Controle da Paginação
    function renderPaginationControls(totalPages, startItem, endItem, totalFiltered) {
        let pagContainer = document.getElementById('pagination-container');
        if (!pagContainer) {
            pagContainer = document.createElement('div');
            pagContainer.id = 'pagination-container';
            pagContainer.className = 'pagination-container';
            newsGrid.parentNode.appendChild(pagContainer);
        }

        if (totalPages <= 1) {
            pagContainer.innerHTML = '';
            return;
        }

        let html = `
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 2rem; padding: 1rem 0; border-top: 1px solid var(--govbr-border); flex-wrap: wrap; gap: 1rem;">
                <span style="font-size: 0.85rem; color: #666;">Exibindo ${startItem}–${endItem} de ${totalFiltered} notícias</span>
                <div style="display: flex; gap: 0.4rem; align-items: center;">
                    <button id="btn-prev" class="action-btn" ${currentPage === 1 ? 'disabled style="opacity:0.4;"' : ''}>◄ Anterior</button>
                    <span style="font-size: 0.9rem; font-weight: 600; padding: 0 0.5rem;">Página ${currentPage} de ${totalPages}</span>
                    <button id="btn-next" class="action-btn" ${currentPage === totalPages ? 'disabled style="opacity:0.4;"' : ''}>Próxima ►</button>
                </div>
            </div>
        `;
        pagContainer.innerHTML = html;

        const btnPrev = document.getElementById('btn-prev');
        const btnNext = document.getElementById('btn-next');

        if (btnPrev && currentPage > 1) {
            btnPrev.onclick = () => { currentPage--; renderNews(); window.scrollTo({top: 0, behavior: 'smooth'}); };
        }
        if (btnNext && currentPage < totalPages) {
            btnNext.onclick = () => { currentPage++; renderNews(); window.scrollTo({top: 0, behavior: 'smooth'}); };
        }
    }

    // Helper Escape HTML
    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }

    window.copyLink = function(url) {
        navigator.clipboard.writeText(url).then(() => {
            alert('Link copiado para a área de transferência!');
        }).catch(err => {
            console.error('Erro ao copiar link:', err);
        });
    };

    // Listeners de Filtro
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilterType = btn.getAttribute('data-filter');
            applyFilters();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            applyFilters();
        });
    }

    // Iniciar
    loadNews();
});
