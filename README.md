# 📰 EduClip Brasil

> **Agregador Nacional de Notícias da Rede Federal de Ensino Superior e Técnica para o Ministério da Educação (MEC).**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-green.svg)
![Frontend](https://img.shields.io/badge/Frontend-HTML5%20%7C%20CSS3%20%7C%20JS%20Vanilla-orange.svg)
![Host](https://img.shields.io/badge/Deploy-GitHub%20Pages-purple.svg)

---

## 📌 Sobre o Projeto

O **EduClip Brasil** é uma plataforma open-source desenvolvida para coletar, consolidar e exibir em tempo real as últimas publicações e notícias oficiais das Universidades Federais (UFs), Institutos Federais (IFs) e Universidades Estaduais (UEs) de todo o Brasil.

O objetivo principal é fornecer ao **Ministério da Educação (MEC)** um painel centralizado onde a equipe de comunicação possa visualizar, filtrar por instituição/UF e replicar matérias relevantes em seus portais oficiais.

---

## ⚡ Arquitetura Estática & Zero Custos

A aplicação foi desenhada para rodar de forma inteiramente **estática e automatizada**:

1. **Backend (Coletor)**: Script Python (`coletor/coletor_noticias.py`) que consome feeds RSS e executa scraping HTML como fallback.
2. **Dados (Storage)**: Banco leve mantido diretamente em arquivo CSV ([`data/noticias.csv`](./data/noticias.csv)) e métricas agregadas em JSON ([`data/metrics.json`](./data/metrics.json)).
3. **Automação (CI/CD)**: O **GitHub Actions** executa o coletor automaticamente a cada **24 horas**, realizando commit automático das novas matérias.
4. **Frontend**: Interface construída em **HTML5 Semântico**, **CSS3 Moderno** (Padrão Digital Gov.br / MEC) e **JavaScript ES6+ Vanilla**, lendo o CSV diretamente via `fetch()`. Hospedado gratuitamente no **GitHub Pages**.

---

## 🏛️ Créditos e Desenvolvimento

Desenvolvido por **IFBAIANO** para a Rede Federal de Ensino e Ministério da Educação (MEC).

---

## 🚀 Estrutura de Pastas

```text
educlip-brasil/
├── .github/
│   └── workflows/
│       └── coletar_noticias.yml      # Cron no GitHub Actions (24h)
├── coletor/
│   ├── coletor_noticias.py           # Coletor RSS + Web Scraper Python
│   ├── instituicoes.json             # Cadastro das IES monitoradas
│   └── requirements.txt             # Dependências Python
├── data/
│   ├── noticias.csv                  # Base de notícias (banco principal)
│   └── metrics.json                  # Métricas agregadas
├── assets/
│   ├── css/
│   │   └── style.css                 # CSS3 Dark Mode com Glassmorphism
│   └── js/
│       └── app.js                    # Parser de CSV e renderizador DOM
├── index.html                        # Dashboard HTML5 semântico
└── README.md                         # Documentação oficial
```

---

## 🛠️ Como Executar Localmente

### 1. Executar o Coletor de Notícias (Python)
```bash
# Clone o repositório
git clone https://github.com/SEU-USUARIO/educlip-brasil.git
cd educlip-brasil

# Instale as dependências
pip install -r coletor/requirements.txt

# Execute a coleta manual
python coletor/coletor_noticias.py
```

### 2. Visualizar o Dashboard
Como a aplicação é 100% estática, basta abrir o arquivo `index.html` em qualquer navegador ou utilizar a extensão **Live Server** do VS Code / Antigravity.

---

## 📄 Licença
Este projeto é distribuído sob a licença **MIT**.
