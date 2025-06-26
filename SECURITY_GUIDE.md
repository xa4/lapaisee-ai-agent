# 🔒 Guide de sécurisation du bot L'Apaisée

## 1. Obtenir votre ID Telegram

1. Relancez le bot : `python src/bot/telegram_bot.py`
2. Sur Telegram, envoyez `/myid` au bot
3. Copiez votre ID (un nombre comme 123456789)

## 2. Configurer la liste blanche

Ouvrez `src/bot/telegram_bot.py` et modifiez :

```python
# Remplacez :
AUTHORIZED_USERS = []

# Par :
AUTHORIZED_USERS = [123456789, 987654321]  # Vos IDs
```

## 3. IDs multiples

Pour autoriser plusieurs personnes :
```python
AUTHORIZED_USERS = [
    123456789,  # Vous
    987654321,  # Employé 1
    555555555,  # Employé 2
]
```

## 4. Autres options de sécurité

### Option A : Bot complètement privé
- Dans BotFather, utilisez `/setjoingroups` → Disable
- Le bot ne pourra pas être ajouté aux groupes

### Option B : Token dans variable d'environnement
- Ne jamais commiter le token sur GitHub
- Utiliser `.env` (déjà fait ✅)

### Option C : Logs d'accès
Le bot log déjà tous les accès :
- ✅ Accès autorisé
- ❌ Accès refusé
- ⚠️ Bot non sécurisé

## 5. Test de sécurité

1. Ajoutez votre ID dans AUTHORIZED_USERS
2. Relancez le bot
3. Testez avec votre compte → ✅ Devrait marcher
4. Testez avec un autre compte → ❌ Devrait être bloqué
