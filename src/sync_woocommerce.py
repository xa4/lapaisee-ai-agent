#!/usr/bin/env python3
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
import re

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
    
    
    def clean_html(self, text: str) -> str:
        """Nettoie le HTML d'un texte"""
        if not text:
            return ""
        
        # Remplacer les <br> par des espaces
        text = re.sub(r'<br\s*/?>', ' ', text)
        
        # Supprimer toutes les balises HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # Nettoyer les espaces multiples
        text = ' '.join(text.split())
        
        return text.strip()

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
        if any(term in name for term in ['ipa', 'lager', 'stout', 'pilsner', 'pale ale', 'jonquille', 'pointe']):
            classification['gamme'] = 'clean'
            classification['container_type'] = 'canette'
        elif any(term in name for term in ['wild', 'spontané', 'mixte', 'lambic', 'gueuze']):
            classification['gamme'] = 'wild'
            classification['container_type'] = 'bouteille'
        
        # Détection du format - AMÉLIORATION pour 12x et 24x
        if 'fût' in name or 'fut' in name or 'keg' in name:
            classification['format'] = 'fût 20L'
            classification['container_type'] = 'fût'
        # IMPORTANT: Détecter 12x AVANT les autres formats
        elif '12x' in name.lower() or '12 x' in name.lower():
            classification['format'] = 'carton 12 canettes 44cl'
            classification['container_type'] = 'carton'
            classification['gamme'] = 'clean'  # Les 12x sont toujours des canettes donc clean
        # Détecter 24x
        elif '24x' in name.lower() or '24 x' in name.lower() or 'carton de 24' in name.lower():
            classification['format'] = 'carton 24 bouteilles 33cl'
            classification['container_type'] = 'carton'
        elif '12x' in name.lower() or '12 x' in name.lower() or 'carton 12' in name.lower():
            classification['format'] = 'carton 12 canettes 44cl'
        elif '24x' in name.lower() or '24 x' in name.lower() or 'carton 24' in name.lower() or 'carton de 24' in name.lower():
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
            logger.info(f"  Params: per_page=100, page={page}")
            response = self.wcapi.get("products", params={"per_page": 100, "page": page, "status": "any"})
            
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
            'categories': ', '.join([cat['name'] for cat in product.get('categories', [])]),
            'description': product.get('description', ''),
            'short_description': product.get('short_description', ''),
            **classification,
            'last_sync': datetime.now().isoformat()
        }
        # Nettoyer les valeurs None pour ChromaDB
        for key in list(processed.keys()):
            if processed[key] is None:
                processed[key] = ''
                
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
            Prix: {processed['price']} CHF
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
                'id': 'context_0',
                'text': """
                IMPORTANT - Produits spécifiques:
                - JONQUILLE : Bière CLEAN, TOUJOURS en CANETTES 44cl
                - Les cartons de Jonquille contiennent TOUJOURS 12 canettes (jamais 24!)
                - Stock total Jonquille = canettes individuelles + (nombre de cartons × 12)
                - Si tu vois "Carton Jonquille" ou "Carton de X Jonquilles", c'est TOUJOURS 12 canettes par carton
                """,
                'type': 'jonquille_info'
            },
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
            },
            {
                'id': 'context_4',
                'text': """
                Informations spécifiques sur les produits:
                - Jonquille: bière clean emblématique, toujours en canettes 44cl
                - Pointe: autre bière clean populaire
                - Les cartons de canettes contiennent toujours 12 unités
                - Tous les prix sont en CHF (francs suisses)
                - Pour calculer le stock total: unités + (nombre de cartons × 12)
                """,
                'type': 'product_info'
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
    logger.info("\n=== Tests de recherche ===")
    syncer.test_search("IPA en stock")
    syncer.test_search("bières en fût")
    syncer.test_search("carton de canettes")

if __name__ == "__main__":
    main()
