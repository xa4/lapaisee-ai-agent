#!/usr/bin/env python3
"""
Bot Telegram pour traiter les commandes WhatsApp de L'Apaisée
"""

import os
import re
from datetime import datetime
from functools import wraps
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import chromadb
from chromadb.utils import embedding_functions
import ollama
from loguru import logger
import warnings
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

# Configuration
load_dotenv()
logger.add("data/logs/telegram_bot.log", rotation="10 MB")


# Configuration de sécurité
AUTHORIZED_USERS = [449781603]  # Liste vide = tout le monde autorisé
# Pour restreindre, ajoutez les user IDs Telegram autorisés :
# AUTHORIZED_USERS = [123456789, 987654321]  # Remplacez par vos IDs

def restricted(func):
    """Décorateur pour restreindre l'accès aux utilisateurs autorisés"""
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Si la liste est vide, tout le monde est autorisé
        if not AUTHORIZED_USERS:
            logger.warning(f"⚠️ ATTENTION: Bot non sécurisé! User {username} (ID: {user_id}) a accès.")
            logger.warning("Pour sécuriser, ajoutez des IDs dans AUTHORIZED_USERS")
            return await func(update, context, *args, **kwargs)
        
        # Vérifier si l'utilisateur est autorisé
        if user_id not in AUTHORIZED_USERS:
            logger.warning(f"❌ Accès refusé pour {username} (ID: {user_id})")
            await update.message.reply_text(
                "🚫 Désolé, vous n'êtes pas autorisé à utiliser ce bot.\n"
                "Ce bot est réservé à L'Apaisée."
            )
            return
        
        logger.info(f"✅ Accès autorisé pour {username} (ID: {user_id})")
        return await func(update, context, *args, **kwargs)
    
    return wrapped


class LapaiseeBot:
    def __init__(self):
        """Initialise le bot avec ChromaDB et Ollama"""
        # ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chromadb")
        )
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        self.products_collection = self.chroma_client.get_collection(
            name="products",
            embedding_function=self.embedding_function
        )
        
        # Patterns pour reconnaître les commandes
        self.patterns = {
            'quantity': r'(\d+)\s*(fûts?|bouteilles?|canettes?|cartons?|caisses?)',
            'product': r'de\s+([\w\s]+?)(?:\s+et|\s*,|\s*\.|$)',
            'greeting': r'(salut|bonjour|hello|coucou|bonsoir)',
            'politeness': r'(s\'?il\s*te\s*pla[îi]t|stp|svp|merci)',
        }
        
        logger.info("Bot initialisé")
    
    def parse_order(self, text: str) -> Dict:
        """Parse un message de commande WhatsApp"""
        logger.info(f"Parsing: {text}")
        
        order = {
            'items': [],
            'greeting': bool(re.search(self.patterns['greeting'], text, re.IGNORECASE)),
            'polite': bool(re.search(self.patterns['politeness'], text, re.IGNORECASE)),
            'original_text': text
        }
        
        # Nettoyer le texte
        text = text.lower().strip()
        
        # Chercher les quantités et produits
        # Exemples: "2 fûts de jonquille", "3 cartons de pointe"
        matches = re.finditer(r'(\d+)\s*(fûts?|bouteilles?|canettes?|cartons?|caisses?)\s*(?:de\s+)?([\w\s]+?)(?:\s+et|\s*,|\s*\.|\s*$|\s+\d)', text)
        
        for match in matches:
            quantity = int(match.group(1))
            container = match.group(2)
            product = match.group(3).strip()
            
            # Normaliser le type de contenant
            if 'fût' in container:
                container_type = 'fût'
            elif 'carton' in container or 'caisse' in container:
                container_type = 'carton'
            elif 'canette' in container:
                container_type = 'canette'
            elif 'bouteille' in container:
                container_type = 'bouteille'
            else:
                container_type = container
            
            order['items'].append({
                'quantity': quantity,
                'container': container_type,
                'product': product
            })
        
        # Si aucun pattern trouvé, essayer une approche plus simple
        if not order['items']:
            # Chercher juste des nombres suivis de mots
            simple_matches = re.finditer(r'(\d+)\s+([\w\s]+?)(?:\s+et|\s*,|\s*\.|$)', text)
            for match in simple_matches:
                order['items'].append({
                    'quantity': int(match.group(1)),
                    'container': 'unité',
                    'product': match.group(2).strip()
                })
        
        return order
    
    def search_product(self, product_name: str, container_type: str = None) -> List[Dict]:
        """Recherche un produit dans ChromaDB"""
        # Construire la requête
        query = product_name
        if container_type == 'carton':
            query += " carton 12x"
        elif container_type == 'fût':
            query += " fût"
        
        results = self.products_collection.query(
            query_texts=[query],
            n_results=5
        )
        
        # Filtrer par type de contenant si spécifié
        filtered_results = []
        for i, metadata in enumerate(results['metadatas'][0]):
            if container_type:
                if container_type == 'carton' and ('12x' in metadata['name'].lower() or 'carton' in metadata['format'].lower()):
                    filtered_results.append(metadata)
                elif container_type == 'fût' and 'fût' in metadata['format'].lower():
                    filtered_results.append(metadata)
                elif container_type in ['canette', 'bouteille'] and container_type in metadata['format'].lower():
                    filtered_results.append(metadata)
            else:
                filtered_results.append(metadata)
        
        return filtered_results
    
    def check_stock(self, product: Dict, quantity: int) -> Tuple[bool, str]:
        """Vérifie si le stock est suffisant"""
        # Convertir le stock en entier (au cas où c'est une string)
        try:
            stock = int(product.get('stock_quantity', 0) or 0)
        except (ValueError, TypeError):
            stock = 0
        
        available = stock >= quantity
        
        if available:
            message = f"✅ {product['name']}: {stock} en stock (demande: {quantity})"
        else:
            if stock == 0:
                message = f"❌ {product['name']}: rupture de stock (demande: {quantity})"
            else:
                message = f"⚠️ {product['name']}: seulement {stock} en stock (demande: {quantity})"
        
        return available, message
    
    def generate_response(self, order: Dict, stock_check: List[Dict]) -> str:
        """Génère une réponse pour le client"""
        # Construire le contexte pour Ollama
        context = f"""
        Tu es l'assistant de la brasserie L'Apaisée. Un client a envoyé cette commande: "{order['original_text']}"
        
        Résultats de la vérification des stocks:
        {chr(10).join([item['message'] for item in stock_check])}
        
        Règles:
        - Sois amical et professionnel
        - Si le client a été poli, remercie-le
        - Confirme ce qui est disponible
        - Propose des alternatives pour ce qui manque
        - Termine par demander confirmation
        - Utilise des émojis avec modération
        - Mentionne les prix en CHF
        """
        
        try:
            response = ollama.chat(
                model=os.getenv("OLLAMA_MODEL", "deepseek-r1:7b"),
                messages=[{'role': 'user', 'content': context}]
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Erreur Ollama: {e}")
            # Réponse de secours
            return self.generate_fallback_response(order, stock_check)
    
    def generate_fallback_response(self, order: Dict, stock_check: List[Dict]) -> str:
        """Génère une réponse de secours si Ollama échoue"""
        response = []
        
        if order['greeting']:
            response.append("Bonjour ! 👋")
        
        response.append("Voici le récapitulatif de votre commande :")
        
        total_ok = sum(1 for item in stock_check if item['available'])
        total_items = len(stock_check)
        
        for item in stock_check:
            response.append(item['message'])
        
        if total_ok == total_items:
            response.append("\n✅ Tout est disponible !")
        else:
            response.append("\n⚠️ Certains produits ne sont pas disponibles en quantité suffisante.")
        
        response.append("\nSouhaitez-vous confirmer cette commande ?")
        
        if order['polite']:
            response.append("\nMerci pour votre commande ! 🍺")
        
        return "\n".join(response)

# Handlers Telegram
@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour /start"""
    await update.message.reply_text(
        "🍺 Bienvenue sur le bot L'Apaisée!\n\n"
        "Envoyez-moi vos commandes WhatsApp et je vais:\n"
        "1. Analyser la commande\n"
        "2. Vérifier les stocks\n"
        "3. Préparer une réponse\n\n"
        "Exemple: 'Salut, j'aurais besoin de 2 fûts de jonquille et 3 cartons de pointe stp'"
    )

@restricted
async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite un message de commande"""
    bot = context.bot_data.get('lapaisee_bot')
    if not bot:
        bot = LapaiseeBot()
        context.bot_data['lapaisee_bot'] = bot
    
    message = update.message.text
    user = update.effective_user
    
    logger.info(f"Commande de {user.username}: {message}")
    
    # Parser la commande
    order = bot.parse_order(message)
    
    if not order['items']:
        await update.message.reply_text(
            "❓ Je n'ai pas compris la commande.\n\n"
            "Essayez un format comme:\n"
            "'2 fûts de jonquille et 3 cartons de pointe'"
        )
        return
    
    # Vérifier les stocks
    await update.message.reply_text("🔍 Je vérifie les stocks...")
    
    stock_check = []
    for item in order['items']:
        # Rechercher le produit
        products = bot.search_product(item['product'], item['container'])
        
        if products:
            product = products[0]  # Prendre le plus pertinent
            available, message = bot.check_stock(product, item['quantity'])
            stock_check.append({
                'item': item,
                'product': product,
                'available': available,
                'message': message
            })
        else:
            stock_check.append({
                'item': item,
                'product': None,
                'available': False,
                'message': f"❌ Produit non trouvé: {item['product']} ({item['container']})"
            })
    
    # Générer la réponse
    response = bot.generate_response(order, stock_check)
    
    # Envoyer la réponse
    await update.message.reply_text(response)
    
    # Log pour suivi
    logger.info(f"Réponse envoyée pour {len(order['items'])} articles")

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour /help"""
    await update.message.reply_text(
        "💡 **Aide du bot L'Apaisée**\n\n"
        "Envoyez simplement votre commande comme vous le feriez sur WhatsApp!\n\n"
        "**Formats acceptés:**\n"
        "- 2 fûts de jonquille\n"
        "- 3 cartons de pointe\n"
        "- 5 bouteilles de wild\n"
        "- 1 fût de IPA et 2 cartons de stout\n\n"
        "**Commandes:**\n"
        "/start - Démarrer le bot\n"
        "/help - Afficher cette aide\n"
        "/stock [produit] - Vérifier le stock d'un produit"
    )

@restricted
async def check_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour /stock"""
    bot = context.bot_data.get('lapaisee_bot')
    if not bot:
        bot = LapaiseeBot()
        context.bot_data['lapaisee_bot'] = bot
    
    if not context.args:
        await update.message.reply_text("Usage: /stock [nom du produit]")
        return
    
    product_name = ' '.join(context.args)
    products = bot.search_product(product_name)
    
    if products:
        response = f"📦 Stock pour '{product_name}':\n\n"
        for p in products[:5]:
            response += f"• {p['name']}\n"
            response += f"  Stock: {p['stock_quantity']} unités\n"
            response += f"  Prix: {p['price']} CHF\n\n"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(f"❌ Aucun produit trouvé pour '{product_name}'")



async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche l'ID Telegram de l'utilisateur"""
    user = update.effective_user
    message = f"""🆔 Vos informations:
ID: {user.id}
Username: @{user.username or 'Non défini'}
Nom: {user.first_name} {user.last_name or ''}

👉 Copiez votre ID: {user.id}

Pour sécuriser le bot, ajoutez cet ID dans AUTHORIZED_USERS"""
    
    await update.message.reply_text(message)

def main():
    """Lance le bot"""
    # Token du bot
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN non défini dans .env")
        return
    
    # Créer l'application
    application = Application.builder().token(token).build()
    
    # Ajouter les handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stock", check_stock_command))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_order))
    
    # Lancer le bot
    logger.info("Bot démarré...")
    application.run_polling()

if __name__ == "__main__":
    main()
