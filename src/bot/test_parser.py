#!/usr/bin/env python3
"""
Test du parser de commandes
"""

import sys
sys.path.append('.')

from src.bot.telegram_bot import LapaiseeBot

def test_parser():
    bot = LapaiseeBot()
    
    # Messages de test
    test_messages = [
        "Salut Xavier, j'espère que tu vas bien, pourrais-tu nous livrer 2 fûts de jonquille et 1 de pointe. Et dis moi si tu as des nouveautés en ce moment. Ciao!",
        "Bonjour, je voudrais 3 cartons de 12 canettes de IPA svp",
        "2 fûts de jonquille, 3 cartons de pointe et 5 bouteilles de wild",
        "Besoin de 10 canettes de stout pour demain",
        "Hello! 1 fût IPA + 2 cartons bizule merci"
    ]
    
    print("🧪 Test du parser de commandes\n")
    
    for msg in test_messages:
        print(f"Message: {msg}")
        order = bot.parse_order(msg)
        print(f"Résultat: {order}")
        print("-" * 50)

if __name__ == "__main__":
    test_parser()
