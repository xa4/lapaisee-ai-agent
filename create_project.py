#!/usr/bin/env python3
"""
Script pour créer le projet L'Apaisée AI Agent
"""

import os
import subprocess

# Définir tous les fichiers à créer
FILES = {
    ".gitignore": """# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# IMPORTANT: Ne jamais commit le .env avec les clés!
.env

# Data
data/chromadb/
data/logs/*.log

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/

# Distribution
dist/
build/
*.egg-info/
""",

    ".env.example": """# WooCommerce Configuration
WOOCOMMERCE_URL=https://lapaisee.ch
WOOCOMMERCE_KEY=your_consumer_key_here
WOOCOMMERCE_SECRET=your_consumer_secret_here

# Trello Configuration (optionnel pour le moment)
TRELLO_API_KEY=your_trello_api_key
TRELLO_TOKEN=your_trello_token
TRELLO_BOARD_COMMANDES=board_id_for_commandes
TRELLO_BOARD_FERMENTEURS=board_id_for_fermenteurs
TRELLO_BOARD_PRODUCTION=board_id_for_production

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./data/chromadb

# Telegram Bot (pour plus tard)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Logging
LOG_LEVEL=INFO
LOG_FILE=./data/logs/lapaisee-ai.log
""",

    "requirements.txt": """# Core
fastapi==0.108.0
uvicorn==0.25.0
streamlit==1.29.0
python-dotenv==1.0.0

# Database & Vector Store
chromadb==0.4.20
sqlalchemy==2.0.23

# LLM
ollama==0.1.6
langchain==0.0.352
langchain-community==0.0.10

# API Integrations
woocommerce==3.0.0
py-trello==0.19.0
python-telegram-bot==20.7

# Data Processing
pandas==2.1.4
numpy==1.26.2
pydantic==2.5.3

# Utils
requests==2.31.0
aiohttp==3.9.1
python-dateutil==2.8.2
loguru==0.7.2
""",

    "README.md": """# L'Apaisée AI Agent 🍺

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
venv\\Scripts\\activate  # Windows

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
""",

    "src/sync_woocommerce.py": '''#!/usr/bin/env python3
"""
Synchronise les données WooCommerce avec ChromaDB
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from woocommerce import API
import chromadb
from chromadb.utils import embedding_functions
from loguru import logger

# Charger les variables d'environnement
load_dotenv()

# Configuration logging
logger.add("data/logs/sync_woocommerce.log", rotation="10 MB")

class WooCommerceSyncer:
    def __init__(self):
        """Initialise les connexions WooCommerce et ChromaDB"""
        # WooCommerce API
        self.wcapi = API(
            url=os.getenv("WOOCOMMERCE_URL"),
            consumer_key=os.getenv("WOOCOMMERCE_KEY"),
            consumer_secret=os.getenv("WOOCOMMERCE_SECRET"),
            version="wc/v3",
            timeout=30
        )
        
        # ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chromadb")
        )
        
        # Embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # Collections
        self.products_collection = self.chroma_client.get_or_create_collection(
            name="products",
            embedding_function=self.embedding_function
        )
        
        self.context_collection = self.chroma_client.get_or_create_collection(
            name="brewery_context",
            embedding_function=self.embedding_function
        )
    
    def classify_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifie un produit selon les règles de L'Apaisée
        """
        name = product.get('name', '').lower()
        categories = [cat['name'].lower() for cat in product.get('categories', [])]
        
        # Classification par défaut
        classification = {
            'type': 'unknown',
            'format': 'unknown',
            'gamme': 'unknown',
            'container_type': 'unknown'
        }
        
        # Détection du type de bière
        if any(term in name for term in ['ipa', 'lager', 'stout', 'pilsner', 'pale ale']):
            classification['gamme'] = 'clean'
            classification['container_type'] = 'canette'
        elif any(term in name for term in ['wild', 'spontané', 'mixte', 'lambic', 'gueuze']):
            classification['gamme'] = 'wild'
            classification['container_type'] = 'bouteille'
        
        # Détection du format
        if 'fût' in name or 'fut' in name or 'keg' in name:
            classification['format'] = 'fût 20L'
            classification['container_type'] = 'fût'
        elif '12x' in name or 'carton 12' in name:
            classification['format'] = 'carton 12 canettes 44cl'
        elif '24x' in name or 'carton 24' in name:
            classification['format'] = 'carton 24 bouteilles 33cl'
        elif '6x' in name or 'carton 6' in name:
            classification['format'] = 'carton 6 bouteilles 75cl'
        elif '75cl' in name or '750ml' in name:
            classification['format'] = 'bouteille 75cl'
        elif '33cl' in name or '330ml' in name:
            classification['format'] = 'bouteille 33cl'
        elif '44cl' in name or '440ml' in name:
            classification['format'] = 'canette 44cl'
        
        return classification
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Récupère tous les produits depuis WooCommerce"""
        all_products = []
        page = 1
        
        while True:
            logger.info(f"Récupération page {page}...")
            response = self.wcapi.get("products", params={"per_page": 100, "page": page})
            
            if response.status_code != 200:
                logger.error(f"Erreur API: {response.status_code}")
                break
            
            products = response.json()
            if not products:
                break
                
            all_products.extend(products)
            page += 1
        
        logger.info(f"Total produits récupérés: {len(all_products)}")
        return all_products
    
    def process_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Traite et enrichit les données d'un produit"""
        classification = self.classify_product(product)
        
        # Extraire les infos importantes
        processed = {
            'id': str(product['id']),
            'name': product['name'],
            'sku': product.get('sku', ''),
            'price': product.get('price', '0'),
            'stock_quantity': product.get('stock_quantity', 0),
            'stock_status': product.get('stock_status', 'unknown'),
            'categories': [cat['name'] for cat in product.get('categories', [])],
            'description': product.get('description', ''),
            'short_description': product.get('short_description', ''),
            **classification,
            'last_sync': datetime.now().isoformat()
        }
        
        return processed
    
    def sync_products(self):
        """Synchronise tous les produits dans ChromaDB"""
        logger.info("Début de la synchronisation des produits...")
        
        # Récupérer tous les produits
        products = self.get_all_products()
        
        # Préparer les données pour ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for product in products:
            processed = self.process_product(product)
            
            # ID unique
            ids.append(processed['id'])
            
            # Document texte pour l'embedding
            doc = f"""
            Produit: {processed['name']}
            SKU: {processed['sku']}
            Gamme: {processed['gamme']}
            Format: {processed['format']}
            Type de contenant: {processed['container_type']}
            Prix: {processed['price']}€
            Stock: {processed['stock_quantity']} unités
            Statut stock: {processed['stock_status']}
            Description: {processed['short_description']}
            """
            documents.append(doc)
            
            # Métadonnées
            metadatas.append(processed)
        
        # Ajouter à ChromaDB (en remplaçant les existants)
        if ids:
            self.products_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"{len(ids)} produits synchronisés dans ChromaDB")
    
    def add_brewery_context(self):
        """Ajoute le contexte de la brasserie dans ChromaDB"""
        logger.info("Ajout du contexte de la brasserie...")
        
        contexts = [
            {
                'id': 'context_1',
                'text': """
                L'Apaisée est une brasserie artisanale qui produit deux gammes de bières:
                - Les bières clean (IPA, Lager, Stout, etc.) qui sont conditionnées en canettes
                - Les bières wild (fermentation mixte ou spontanée) qui sont en bouteilles
                """,
                'type': 'general_info'
            },
            {
                'id': 'context_2',
                'text': """
                Formats de vente chez L'Apaisée:
                - Canettes 44cl vendues en cartons de 12 (panachables)
                - Bouteilles 33cl vendues en cartons de 24 (panachables)
                - Bouteilles 75cl vendues en cartons de 6 (panachables)
                - Fûts 20L (95% inox avec bières clean, 5% KeyKeg avec bières wild)
                """,
                'type': 'formats'
            },
            {
                'id': 'context_3',
                'text': """
                Saisonnalité chez L'Apaisée:
                - Avril, mai et juin sont les meilleurs mois de vente
                - Juillet et août sont plus calmes
                - Les bières houblonnées (IPA) se vendent mieux au printemps
                - Les bières fortes et stouts sont populaires en hiver
                """,
                'type': 'seasonality'
            }
        ]
        
        # Ajouter au contexte
        self.context_collection.upsert(
            ids=[c['id'] for c in contexts],
            documents=[c['text'] for c in contexts],
            metadatas=[{'type': c['type']} for c in contexts]
        )
        
        logger.info("Contexte de la brasserie ajouté")
    
    def test_search(self, query: str):
        """Test une recherche dans la base"""
        results = self.products_collection.query(
            query_texts=[query],
            n_results=5
        )
        
        logger.info(f"Recherche: '{query}'")
        for i, metadata in enumerate(results['metadatas'][0]):
            logger.info(f"  {i+1}. {metadata['name']} - Stock: {metadata['stock_quantity']}")

def main():
    """Fonction principale"""
    syncer = WooCommerceSyncer()
    
    # Synchroniser les produits
    syncer.sync_products()
    
    # Ajouter le contexte
    syncer.add_brewery_context()
    
    # Test
    logger.info("\\n=== Tests de recherche ===")
    syncer.test_search("IPA en stock")
    syncer.test_search("bières en fût")
    syncer.test_search("carton de canettes")

if __name__ == "__main__":
    main()
''',

    "src/interface/app.py": '''#!/usr/bin/env python3
"""
Interface Streamlit pour L'Apaisée AI Agent
"""

import streamlit as st
import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
import ollama
from datetime import datetime
import json
from loguru import logger

# Configuration de la page
st.set_page_config(
    page_title="L'Apaisée AI Agent",
    page_icon="🍺",
    layout="wide"
)

# Charger les variables d'environnement
load_dotenv()

# Style CSS personnalisé
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_chromadb():
    """Initialise la connexion ChromaDB"""
    client = chromadb.PersistentClient(
        path=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chromadb")
    )
    
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    products_collection = client.get_or_create_collection(
        name="products",
        embedding_function=embedding_function
    )
    
    context_collection = client.get_or_create_collection(
        name="brewery_context",
        embedding_function=embedding_function
    )
    
    return products_collection, context_collection

def search_products(collection, query: str, n_results: int = 5):
    """Recherche dans la collection de produits"""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results

def generate_context(products_results, context_results):
    """Génère le contexte pour le LLM"""
    context = "Contexte de la brasserie L'Apaisée:\\n\\n"
    
    # Ajouter le contexte général
    if context_results['documents'][0]:
        context += "Informations générales:\\n"
        for doc in context_results['documents'][0]:
            context += f"- {doc}\\n"
        context += "\\n"
    
    # Ajouter les produits pertinents
    if products_results['documents'][0]:
        context += "Produits pertinents:\\n"
        for i, metadata in enumerate(products_results['metadatas'][0]):
            context += f"\\n{i+1}. {metadata['name']}\\n"
            context += f"   - Format: {metadata.get('format', 'Non spécifié')}\\n"
            context += f"   - Stock: {metadata.get('stock_quantity', 0)} unités\\n"
            context += f"   - Prix: {metadata.get('price', 'N/A')}€\\n"
            context += f"   - Gamme: {metadata.get('gamme', 'Non classifié')}\\n"
    
    return context

def query_llm(question: str, context: str):
    """Interroge le LLM avec le contexte"""
    prompt = f"""Tu es l'assistant AI de la brasserie L'Apaisée. Tu connais parfaitement les produits, 
    les stocks et le fonctionnement de la brasserie.

{context}

Question: {question}

Réponds de manière précise et concise. Si tu parles de produits spécifiques, mentionne toujours 
le stock disponible et le format."""
    
    try:
        response = ollama.chat(
            model=os.getenv("OLLAMA_MODEL", "deepseek-r1:7b"),
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )
        return response['message']['content']
    except Exception as e:
        logger.error(f"Erreur LLM: {e}")
        return f"Erreur lors de la génération de la réponse: {str(e)}"

def main():
    st.title("🍺 L'Apaisée AI Agent")
    st.markdown("Assistant intelligent pour la gestion de votre brasserie")
    
    # Initialiser les collections
    products_collection, context_collection = init_chromadb()
    
    # Sidebar avec les stats
    with st.sidebar:
        st.header("📊 Statistiques")
        
        # Compter les produits
        try:
            product_count = products_collection.count()
            st.metric("Produits en base", product_count)
        except:
            st.metric("Produits en base", "N/A")
        
        st.divider()
        
        # Actions rapides
        st.header("⚡ Actions rapides")
        if st.button("🔄 Synchroniser WooCommerce"):
            st.info("Lancer `python src/sync_woocommerce.py` dans le terminal")
        
        if st.button("📝 Voir les logs"):
            try:
                with open("data/logs/sync_woocommerce.log", "r") as f:
                    logs = f.readlines()[-20:]  # 20 dernières lignes
                    st.text("\\n".join(logs))
            except:
                st.warning("Aucun log disponible")
    
    # Tabs principales
    tab1, tab2, tab3 = st.tabs(["💬 Assistant", "📦 Produits", "📈 Analyses"])
    
    with tab1:
        st.header("Posez vos questions sur votre brasserie")
        
        # Zone de chat
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Afficher l'historique
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Input utilisateur
        if prompt := st.chat_input("Ex: Quel est le stock de Jonquille?"):
            # Ajouter le message utilisateur
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Rechercher dans les bases
            with st.spinner("Recherche en cours..."):
                products_results = search_products(products_collection, prompt)
                context_results = search_products(context_collection, prompt, n_results=3)
                
                # Générer le contexte
                context = generate_context(products_results, context_results)
                
                # Interroger le LLM
                response = query_llm(prompt, context)
            
            # Afficher la réponse
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    with tab2:
        st.header("Recherche de produits")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("Rechercher un produit", placeholder="Ex: IPA, fût, canette...")
        with col2:
            n_results = st.number_input("Résultats", min_value=1, max_value=20, value=10)
        
        if search_query:
            results = search_products(products_collection, search_query, n_results)
            
            if results['metadatas'][0]:
                st.subheader(f"Résultats ({len(results['metadatas'][0])})")
                
                for metadata in results['metadatas'][0]:
                    with st.expander(f"🍺 {metadata['name']}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Stock", f"{metadata.get('stock_quantity', 0)} unités")
                            st.caption(f"Statut: {metadata.get('stock_status', 'unknown')}")
                        
                        with col2:
                            st.metric("Prix", f"{metadata.get('price', 'N/A')}€")
                            st.caption(f"Format: {metadata.get('format', 'Non spécifié')}")
                        
                        with col3:
                            st.metric("Gamme", metadata.get('gamme', 'Non classifié'))
                            st.caption(f"SKU: {metadata.get('sku', 'N/A')}")
                        
                        if metadata.get('short_description'):
                            st.markdown("**Description:**")
                            st.markdown(metadata['short_description'])
            else:
                st.info("Aucun résultat trouvé")
    
    with tab3:
        st.header("Analyses et tendances")
        
        # Analyses prédéfinies
        st.subheader("Questions fréquentes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Produits les plus en stock"):
                with st.spinner("Analyse en cours..."):
                    response = query_llm(
                        "Quels sont les 5 produits avec le plus de stock?",
                        generate_context(
                            search_products(products_collection, "stock", 20),
                            search_products(context_collection, "stock", 1)
                        )
                    )
                    st.info(response)
            
            if st.button("🔻 Produits en rupture"):
                with st.spinner("Analyse en cours..."):
                    response = query_llm(
                        "Quels produits sont en rupture de stock ou presque?",
                        generate_context(
                            search_products(products_collection, "rupture stock", 20),
                            search_products(context_collection, "stock", 1)
                        )
                    )
                    st.warning(response)
        
        with col2:
            if st.button("🍺 Bières clean disponibles"):
                with st.spinner("Analyse en cours..."):
                    response = query_llm(
                        "Liste toutes les bières clean (IPA, Lager, Stout) disponibles",
                        generate_context(
                            search_products(products_collection, "clean IPA lager stout", 20),
                            search_products(context_collection, "clean", 2)
                        )
                    )
                    st.success(response)
            
            if st.button("🌿 Bières wild disponibles"):
                with st.spinner("Analyse en cours..."):
                    response = query_llm(
                        "Liste toutes les bières wild (fermentation mixte/spontanée) disponibles",
                        generate_context(
                            search_products(products_collection, "wild fermentation mixte spontanée", 20),
                            search_products(context_collection, "wild", 2)
                        )
                    )
                    st.success(response)

if __name__ == "__main__":
    main()
'''
}

def create_structure():
    """Crée la structure de dossiers"""
    print("📁 Création de la structure...")
    
    # Créer les dossiers
    dirs = [
        "src/connectors",
        "src/database", 
        "src/ai",
        "src/interface",
        "src/utils",
        "data/chromadb",
        "data/logs",
        "config",
        "docs",
        "tests"
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # Créer les __init__.py
    init_paths = [
        "src/__init__.py",
        "src/connectors/__init__.py",
        "src/database/__init__.py",
        "src/ai/__init__.py",
        "src/interface/__init__.py",
        "src/utils/__init__.py"
    ]
    
    for init_path in init_paths:
        open(init_path, 'a').close()
    
    # Créer les .gitkeep
    gitkeep_paths = [
        "data/logs/.gitkeep",
        "config/.gitkeep",
        "docs/.gitkeep",
        "tests/.gitkeep"
    ]
    
    for gitkeep_path in gitkeep_paths:
        open(gitkeep_path, 'a').close()
    
    print("✅ Structure créée")

def create_files():
    """Crée tous les fichiers du projet"""
    print("📝 Création des fichiers...")
    
    for filename, content in FILES.items():
        print(f"  - {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print("✅ Fichiers créés")

def init_git():
    """Initialise le repo git"""
    print("🔧 Initialisation de Git...")
    
    if not os.path.exists('.git'):
        subprocess.run(['git', 'init'], check=True)
        print("✅ Git initialisé")
    else:
        print("⚠️  Git déjà initialisé")
    
    # Premier commit
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', 'commit', '-m', '🍺 Initial commit: L\'Apaisée AI Agent'], check=True)
    print("✅ Premier commit créé")

def main():
    print("🍺 Création du projet L'Apaisée AI Agent")
    print("=" * 40)
    
    # Créer la structure
    create_structure()
    
    # Créer les fichiers
    create_files()
    
    # Initialiser git
    init_git()
    
    print("\n✅ Projet créé avec succès!")
    print("\n📋 Prochaines étapes:")
    print("1. Copier .env.example vers .env et ajouter vos clés API")
    print("   cp .env.example .env")
    print("\n2. Créer et activer l'environnement virtuel:")
    print("   python3 -m venv venv")
    print("   source venv/bin/activate")
    print("\n3. Installer les dépendances:")
    print("   pip install -r requirements.txt")
    print("\n4. Pousser sur GitHub:")
    print("   - Créer un nouveau repo sur https://github.com/new")
    print("   - git remote add origin https://github.com/VOTRE_USERNAME/lapaisee-ai-agent.git")
    print("   - git branch -M main")
    print("   - git push -u origin main")
    print("\n⚠️  IMPORTANT: Le fichier .env ne sera PAS poussé sur GitHub grâce au .gitignore")

if __name__ == "__main__":
    main()
