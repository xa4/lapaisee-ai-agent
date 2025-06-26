# L'Apaisée AI Agent 🍺

Agent AI intelligent pour la gestion des commandes et du contexte de la brasserie L'Apaisée.

## 🎯 Objectifs

- Comprendre le contexte complet de la brasserie (produits, clients, commandes)
- Répondre aux questions sur les stocks, ventes et tendances
- Analyser et traiter les commandes WhatsApp
- Assister dans les tâches quotidiennes de gestion

## 🛠️ Stack Technique

- **LLM** : deepseek-r1:7b (local via Ollama)
- **Base vectorielle** : ChromaDB
- **Backend** : FastAPI
- **Interface** : Streamlit
- **Intégrations** : WooCommerce API, Trello API, Telegram Bot

## 📦 Structure des Produits

### Bières Clean (canettes)
- IPAs, Lagers, Stouts...
- Format principal : canettes 44cl (cartons de 12)
- Fûts : 95% des fûts (inox, 20L)

### Bières Wild (bouteilles)
- Fermentation mixte/spontanée
- Formats : 
  - Bouteilles 33cl (cartons de 24)
  - Bouteilles 75cl (cartons de 6)
- Fûts : 5% des fûts (principalement KeyKeg)

## 🚀 Installation

### Prérequis
- Python 3.9+
- Ollama avec deepseek-r1:7b installé
- Clés API WooCommerce
- (Optionnel) Clés API Trello

### Setup

```bash
# Cloner le repo
git clone https://github.com/[your-username]/lapaisee-ai-agent.git
cd lapaisee-ai-agent

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

### Configuration

1. Éditer `.env` avec vos informations :
```
WOOCOMMERCE_URL=https://lapaisee.ch
WOOCOMMERCE_KEY=your_key
WOOCOMMERCE_SECRET=your_secret
TRELLO_API_KEY=your_key
TRELLO_TOKEN=your_token
OLLAMA_BASE_URL=http://localhost:11434
```

2. Lancer Ollama si ce n'est pas déjà fait :
```bash
ollama serve
```

## 🏃 Utilisation

### Lancer l'interface Streamlit

```bash
streamlit run src/interface/app.py
```

### Synchroniser les données WooCommerce

```bash
python src/sync_woocommerce.py
```

### Préparer un jeu d'exemples pour le fine-tuning

Un script utilitaire `scripts/setup_transformers_training.py` ajoute la dépendance
`transformers` et crée un fichier `data/finetune_samples.jsonl` contenant quelques
paires instruction/réponse.

```bash
python scripts/setup_transformers_training.py
```

## 📱 Roadmap

### Phase 1 : Base ✅
- [x] Structure du projet
- [ ] Connexion WooCommerce
- [ ] Import des produits dans ChromaDB
- [ ] Interface Streamlit basique

### Phase 2 : Intelligence 🚧
- [ ] Contexte enrichi (gammes, formats, saisonnalité)
- [ ] Analyse des commandes
- [ ] Apprentissage par feedback

### Phase 3 : Bot WhatsApp 📅
- [ ] Bot Telegram
- [ ] Parser de commandes
- [ ] Validation et suggestions

## 🤝 Contribution

Ce projet est spécifique à L'Apaisée mais les contributions sont bienvenues !

## 📄 License

Propriétaire - L'Apaisée
