#!/usr/bin/env python3
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
    context = "Contexte de la brasserie L'Apaisée:\n\n"
    
    # Ajouter le contexte général
    if context_results['documents'][0]:
        context += "Informations générales:\n"
        for doc in context_results['documents'][0]:
            context += f"- {doc}\n"
        context += "\n"
    
    # Ajouter les produits pertinents
    if products_results['documents'][0]:
        context += "Produits pertinents:\n"
        for i, metadata in enumerate(products_results['metadatas'][0]):
            context += f"\n{i+1}. {metadata['name']}\n"
            context += f"   - Format: {metadata.get('format', 'Non spécifié')}\n"
            context += f"   - Stock: {metadata.get('stock_quantity', 0)} unités\n"
            context += f"   - Prix: {metadata.get('price', 'N/A')}€\n"
            context += f"   - Gamme: {metadata.get('gamme', 'Non classifié')}\n"
    
    return context

def query_llm(question: str, context: str):
    """Interroge le LLM avec le contexte"""
    prompt = f"""Tu es l'assistant AI de la brasserie L'Apaisée en Suisse. Tu connais parfaitement les produits, 
    les stocks et le fonctionnement de la brasserie.

    RÈGLES IMPORTANTES:
    1. Tous les prix sont en CHF (francs suisses), JAMAIS en euros
    2. Les bières clean (IPA, Jonquille, Pointe, etc.) sont TOUJOURS en canettes 44cl
    3. Les bières wild sont en bouteilles
    4. Les cartons de canettes contiennent 12 unités
    5. Quand on demande le stock, calcule le total: unités + (cartons × 12)

    {context}

    Question: {question}

    Réponds de manière précise. Pour les stocks, donne toujours:
    - Le nombre total de canettes/bouteilles disponibles
    - Le détail (X unités + Y cartons)
    - Utilise CHF pour les prix"""
    
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
    
    # Initialiser l'historique des messages dans session_state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
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
                    st.text("\n".join(logs))
            except:
                st.warning("Aucun log disponible")
    
    # Tabs principales
    tab1, tab2, tab3 = st.tabs(["💬 Assistant", "📦 Produits", "📈 Analyses"])
    
    with tab1:
        st.header("Posez vos questions sur votre brasserie")
        
        # Afficher l'historique
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Zone pour la réponse du dernier message
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            with st.spinner("Recherche en cours..."):
                # Rechercher dans les bases
                question = st.session_state.messages[-1]["content"]
                products_results = search_products(products_collection, question)
                context_results = search_products(context_collection, question, n_results=3)
                
                # Générer le contexte
                context = generate_context(products_results, context_results)
                
                # Interroger le LLM
                response = query_llm(question, context)
                
                # Afficher et stocker la réponse
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
                            st.metric("Prix", f"{metadata.get('price', 'N/A')} CHF")
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
    
    # Chat input EN DEHORS des tabs
    if prompt := st.chat_input("Ex: Quel est le stock de Jonquille?"):
        # Ajouter le message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

if __name__ == "__main__":
    main()
